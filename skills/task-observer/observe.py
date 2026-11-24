"""Find repeated work in your local Claude Code transcripts and suggest skills, rules or scripts for it.

  python observe.py scan [--days 30] [--min-sessions 3] [--match <folder>] [--projects ~/.claude/projects]
                         [--skills ~/.claude/skills] [--skills <more dirs>] [--json out.json]
  python observe.py install <draft-folder> [--to ~/.claude/skills] [--yes]

scan reads ~/.claude/projects/**/*.jsonl (nothing is sent anywhere) and reports patterns that show up in at
least --min-sessions different sessions:
  - repeated phrases in your prompts (the same kind of request)
  - repeated corrections ("no, don't...", "I said...", "instead...") -> usually a CLAUDE.md rule
  - repeated shell commands and tool sequences -> usually a script
  - files read in many sessions -> usually a reference file or CLAUDE.md pointer
Each candidate says which of those it looks like, and is marked "covered" if an installed skill's
description already shares its key words. It only counts and quotes; Claude (or you) decides what is worth building.

install copies a drafted skill folder into your skills directory. It prints what it would do and writes
nothing unless you pass --yes. Nothing in this tool installs or edits a skill on its own.

Limits: a count of repeats is a hint, not proof of value. Prompts are quoted truncated, with obvious secrets
masked, but read the report before pasting it into a chat.
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

STOP = set("""a about above after again all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here hers
him his how i if in into is it its just like me more most my no nor not now of off on once only or other our out over
own please same she should so some such than that the their them then there these they this those through to too
under until up us very was we were what when where which while who whom why will with would you your yours
can't don't it's i'm let's make sure need want get got use using one two new file files code thing things
""".split())
CORRECT = re.compile(r"^\s*(no[,. ]|nope|don'?t |do not |stop |wrong|actually|instead|i said|i told you|not what i|that'?s not|"
                     r"why did you|you (forgot|missed|didn'?t|shouldn'?t)|never |always )", re.I)
SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{12,}|xox[abp]-[A-Za-z0-9-]{10,}|"
                    r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}|(?i:password|secret|token|api[_-]?key)\s*[=:]\s*\S+)")
BUILD_WORDS = {"gradlew", "gradle", "pytest", "npm", "yarn", "pnpm", "cargo", "mvn", "make", "git", "ls", "cd", "echo", "cat"}


def mask(t):
    return SECRET.sub("[masked]", t)


def ts(e):
    try:
        return datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
    except (KeyError, ValueError, AttributeError):
        return None


def words(t):
    return [w for w in re.findall(r"[a-z][a-z0-9'_-]{1,}", t.lower()) if w not in STOP]


def ngrams(ws, n):
    return {" ".join(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def user_text(m):
    c = m.get("content")
    parts = [c] if isinstance(c, str) else [b.get("text", "") for b in c or [] if isinstance(b, dict) and b.get("type") == "text"]
    out = []
    for t in parts:
        t = re.sub(r"<([\w-]+)[^>]*>.*?</\1>", " ", t, flags=re.S)  # harness-added tagged blocks
        t = mask(" ".join(t.split()))
        if t and not t.startswith("<") and not t.startswith("[Request interrupted"):
            out.append(t)
    return out


def norm_cmd(cmd):
    """'git -C x commit -m ...' -> 'git commit'; keep the first two plain words."""
    toks = [t for t in re.split(r"\s+", cmd.strip()) if t and not t.startswith("-") and "=" not in t.split("/")[-1][:1]]
    toks = [re.sub(r"^.*[/\\]", "", t) for t in toks[:3]]
    return " ".join(toks[:2]) if toks else ""


def load(projects, since, match):
    sess = {}
    for f in glob.glob(os.path.join(os.path.expanduser(projects), "**", "*.jsonl"), recursive=True):
        if "subagents" in f.replace("\\", "/").split("/"):
            continue
        for line in open(f, encoding="utf-8", errors="ignore"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("isSidechain"):
                continue
            sid = e.get("sessionId") or os.path.basename(f)
            s = sess.setdefault(sid, {"cwd": "", "end": None, "prompts": [], "cmds": [], "tools": [], "reads": set()})
            s["cwd"] = s["cwd"] or e.get("cwd") or ""
            t = ts(e)
            if t:
                s["end"] = max(s["end"] or t, t)
            m = e.get("message") if isinstance(e.get("message"), dict) else {}
            if e.get("type") == "user" and not e.get("isMeta"):
                s["prompts"] += user_text(m)
            elif e.get("type") == "assistant":
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        name, inp = b.get("name", "?"), b.get("input") or {}
                        s["tools"].append(name)
                        if name == "Bash" and inp.get("command"):
                            c = norm_cmd(inp["command"].splitlines()[0])
                            if c:
                                s["cmds"].append(c)
                        elif name == "Read" and inp.get("file_path"):
                            s["reads"].add(inp["file_path"])
    return {k: v for k, v in sess.items() if v["end"] and v["end"] >= since and v["prompts"]
            and (not match or match.lower() in v["cwd"].lower())}


def installed_skills(dirs):
    found = {}
    for d in dirs:
        for p in glob.glob(os.path.join(os.path.expanduser(d), "**", "SKILL.md"), recursive=True):
            txt = open(p, encoding="utf-8", errors="ignore").read(3000)
            m = re.search(r"^description:\s*(.+)$", txt, re.M)
            n = re.search(r"^name:\s*(.+)$", txt, re.M)
            if m and n:
                found[n.group(1).strip()] = set(words(m.group(1)))
    return found


def covered_by(phrase, skills):
    pw = set(words(phrase))
    best = max(((len(pw & kw) / max(len(pw), 1), n) for n, kw in skills.items()), default=(0, ""))
    return best[1] if best[0] >= 0.5 else ""


def recurring(per_session, min_sessions):
    """per_session: {sid: set(items)} -> [(item, n_sessions)] for items in >= min_sessions sessions."""
    c = Counter(i for items in per_session.values() for i in items)
    return [(i, n) for i, n in c.most_common() if n >= min_sessions]


def dedupe_phrases(items, per_session):
    """Phrases that occur in exactly the same sessions are one finding; keep the longest of each group."""
    groups = {}
    for p, n in items:
        sig = frozenset(sid for sid, g in per_session.items() if p in g)
        if sig not in groups or len(p) > len(groups[sig][0]):
            groups[sig] = (p, n)
    return sorted(groups.values(), key=lambda x: -x[1])


def scan(a):
    since = datetime.now(timezone.utc) - timedelta(days=a.days)
    sess = load(a.projects, since, a.match)
    if not sess:
        print(f"No sessions found in the last {a.days} days under {a.projects}. Run this on the machine where you use Claude Code.")
        return 1
    skills = installed_skills(a.skills)
    print(f"# Task observer: {len(sess)} sessions, last {a.days} days"
          + (f", folders matching '{a.match}'" if a.match else "") + f", repeat threshold {a.min_sessions} sessions\n")
    out = {"sessions": len(sess), "prompt_phrases": [], "corrections": [], "commands": [], "reads": []}

    # 1. Phrases in ordinary prompts and in corrections, counted by distinct sessions
    for label, key, test in (("Repeated requests", "prompt_phrases", lambda p: not CORRECT.match(p) and len(p) > 15),
                             ("Repeated corrections (a rule in CLAUDE.md usually fixes these)", "corrections", lambda p: bool(CORRECT.match(p)))):
        per = {}
        examples = defaultdict(list)
        for sid, s in sess.items():
            grams = set()
            for p in filter(test, s["prompts"]):
                ws = words(p)
                for n in (2, 3, 4):
                    for g in ngrams(ws, n):
                        grams.add(g)
                        if len(examples[g]) < 2 and (sid, p) not in examples[g]:
                            examples[g].append((sid, p))
            per[sid] = grams
        rows = dedupe_phrases(recurring(per, a.min_sessions), per)[:8]
        print(f"## {label}")
        if not rows:
            print("None above the threshold.\n")
        for phrase, n in rows:
            cov = covered_by(phrase, skills)
            folders = Counter(os.path.basename(sess[sid]["cwd"].rstrip("/\\")) or "?" for sid, _ in examples[phrase])
            print(f"- \"{phrase}\" in {n} sessions" + (f"; looks covered by skill `{cov}`" if cov else "; no installed skill matches"))
            for _, p in examples[phrase]:
                print(f"  - e.g. {mask(p)[:140]}")
            out[key].append({"phrase": phrase, "sessions": n, "covered_by": cov, "folders": list(folders)})
        print()

    # 2. Shell command prefixes and tool sequences
    per_cmd = {sid: {c for c in s["cmds"] if c.split()[0] not in BUILD_WORDS or " " in c} for sid, s in sess.items()}
    print("## Repeated shell commands (a script or a skill with a script)")
    rows = [(c, n) for c, n in recurring(per_cmd, a.min_sessions) if c.split()[0] not in {"cd", "ls", "echo", "cat"}][:8]
    for c, n in rows or []:
        print(f"- `{mask(c)}` in {n} sessions")
        out["commands"].append({"command": c, "sessions": n})
    if not rows:
        print("None above the threshold.")
    seqs = {sid: {" > ".join(s["tools"][i:i + 3]) for i in range(len(s["tools"]) - 2)} for sid, s in sess.items()}
    seqs = {sid: {q for q in v if len(set(q.split(" > "))) > 1} for sid, v in seqs.items()}
    top = recurring(seqs, max(a.min_sessions, len(sess) // 2))[:3]
    if top:
        print("\nTool sequences common to half your sessions or more (normal workflow, rarely worth a skill): "
              + "; ".join(f"`{q}` ({n})" for q, n in top))
    print()

    # 3. Files read in many sessions
    print("## Files read in many sessions (put a pointer in CLAUDE.md, or move the facts into a reference file)")
    rows = recurring({sid: s["reads"] for sid, s in sess.items()}, a.min_sessions)[:8]
    for f, n in rows:
        print(f"- {mask(f)} in {n} sessions")
        out["reads"].append({"file": f, "sessions": n})
    if not rows:
        print("None above the threshold.")

    print("\n## Next step\nPick at most two candidates. A repeated request with no covering skill is a skill; a "
          "correction is a rule; a repeated command is a script. See SKILL.md for drafting and approval.")
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
    return 0


def install(a):
    src = os.path.abspath(a.draft)
    skill_md = os.path.join(src, "SKILL.md")
    if not os.path.isfile(skill_md):
        print(f"{src} has no SKILL.md.")
        return 1
    name = os.path.basename(src.rstrip("/\\"))
    dest = os.path.join(os.path.expanduser(a.to), name)
    if os.path.exists(dest):
        print(f"{dest} already exists; remove or rename it first. Nothing written.")
        return 1
    files = [os.path.relpath(os.path.join(r, f), src) for r, _, fs in os.walk(src) for f in fs]
    print(f"Would copy {len(files)} files from {src} to {dest}:\n  " + "\n  ".join(sorted(files)))
    if not a.yes:
        print("Dry run. Re-run with --yes after you have read the draft.")
        return 0
    shutil.copytree(src, dest)
    print(f"Installed {name}. Restart Claude Code (or start a new session) to load it.")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--days", type=int, default=30)
    s.add_argument("--min-sessions", type=int, default=3)
    s.add_argument("--match")
    s.add_argument("--projects", default="~/.claude/projects")
    s.add_argument("--skills", action="append", default=None)
    s.add_argument("--json")
    i = sub.add_parser("install")
    i.add_argument("draft")
    i.add_argument("--to", default="~/.claude/skills")
    i.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    if a.cmd == "scan":
        a.skills = a.skills or ["~/.claude/skills", ".claude/skills"]
    sys.exit(scan(a) if a.cmd == "scan" else install(a))
