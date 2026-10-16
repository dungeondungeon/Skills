"""Reuse tested scripts instead of rewriting them: find them, log misses and reuses, and audit the skills they live in.

  python library.py find <words...>              scripts and skills matching a need, best first
  python library.py log miss "<task>" [--script PATH]   Claude wrote a new script it might need again
  python library.py log reuse <script-path>      Claude ran an existing library script
  python library.py review [--days N]            repeated misses (build these next) and reuse counts
  python library.py audit [ROOT...]              broken, stale, unused or overlapping skills and scripts

Roots default to ~/.claude/skills and ./.claude/skills. The log is ~/.claude/script-library/log.jsonl
(override with SCRIPT_LIBRARY_LOG). Standard library only.
"""
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

LOG = Path(os.environ.get("SCRIPT_LIBRARY_LOG") or Path.home() / ".claude" / "script-library" / "log.jsonl")
SCRIPT_EXT = {".py", ".ps1", ".sh", ".js", ".mjs"}
STALE_DAYS = 120
STOP = set("a an and are as at be by for from how i in into is it its of on or the this to use used using when with "
           "you your can not any all each new one".split())
NOT_CLAUSE = re.compile(r"\b(not for|don'?t use|do not use|never use|skip (?:it|this) )", re.I)


def words(text):
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOP}


def default_roots():
    return [p for p in (Path.home() / ".claude" / "skills", Path.cwd() / ".claude" / "skills") if p.is_dir()]


def frontmatter(skill_md):
    text = skill_md.read_text(encoding="utf-8", errors="ignore")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    fields = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M)) if m else {}
    return fields, text


def script_summary(path):
    """First line of a Python docstring or the leading comment block of another script."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if path.suffix == ".py":
        try:
            doc = ast.get_docstring(ast.parse(text)) or ""
        except SyntaxError:
            doc = ""
        if doc:
            return doc.strip()
    lines = []
    for line in text.splitlines()[:15]:
        s = line.strip()
        if s.startswith(("#!", "<#", "#>")):
            continue
        if s.startswith(("#", "//")):
            lines.append(s.lstrip("#/ ").strip())
        elif s:
            break
    return " ".join(lines)


def skills(roots):
    """Yield (skill_dir, fields, text, [scripts]) for every SKILL.md under the roots."""
    for root in roots:
        for d in skill_dirs(Path(root)):
            fields, text = frontmatter(d / "SKILL.md")
            scripts = sorted(Path(r) / f for r, dirs, files in os.walk(d) for f in files
                             if Path(f).suffix in SCRIPT_EXT and "__pycache__" not in r)
            yield d, fields, text, scripts


def skill_dirs(root, depth=3):
    """Folders holding a SKILL.md, following links (installed skills are usually links), not looking inside a skill."""
    if (root / "SKILL.md").is_file():
        yield root
        return
    if depth and root.is_dir():
        for child in sorted(root.iterdir()):
            if child.is_dir() and not child.name.startswith("."):
                yield from skill_dirs(child, depth - 1)


# ---------- find ----------

def find(query, roots):
    q = words(query)
    if not q:
        sys.exit("Give a few words describing what the script should do.")
    hits = []
    for d, fields, _, scripts in skills(roots):
        desc = fields.get("description", "")
        for s in scripts:
            summary = script_summary(s)
            text = f"{s.stem.replace('_', ' ')} {summary} {desc}"
            score = len(q & words(text)) / len(q)
            if score:
                hits.append((score, str(s), summary.splitlines()[0] if summary else "(no docstring)", d.name))
        score = len(q & words(f"{d.name.replace('-', ' ')} {desc}")) / len(q)
        if score and not scripts:
            hits.append((score, str(d / "SKILL.md"), desc[:120], d.name))
    if not hits:
        print("No match. If you write a new script for this, log it:  library.py log miss \"<task>\" --script <path>")
        return
    for score, path, summary, skill in sorted(hits, reverse=True)[:8]:
        print(f"{score:4.0%}  {path}\n      [{skill}] {summary}")
    print("\nMatch % is the share of your words found in the script's name, docstring and skill description. "
          "Read the script's docstring before trusting a match.")


# ---------- log ----------

def log(kind, value, script=None):
    entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "cwd": str(Path.cwd())}
    if kind == "miss":
        entry["task"] = value
        if script:
            entry["script"] = str(Path(script).resolve())
    else:
        entry["script"] = str(Path(value).resolve())
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"logged {kind} -> {LOG}")


def read_log(days=None):
    if not LOG.exists():
        return []
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - days * 86400)) if days else ""
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("at", "") >= cutoff:
            out.append(e)
    return out


# ---------- review ----------

def similar(a, b):
    return len(a & b) / max(1, len(a | b))


def review(days=None):
    entries = read_log(days)
    if not entries:
        print(f"Log is empty ({LOG}). Nothing to review yet.")
        return
    misses = [e for e in entries if e["kind"] == "miss"]
    groups = []  # [word set, [entries]]
    for e in misses:
        w = words(e.get("task", ""))
        for g in groups:
            if similar(w, g[0]) >= 0.35:
                g[1].append(e)
                g[0] |= w
                break
        else:
            groups.append([w, [e]])
    groups.sort(key=lambda g: -len(g[1]))
    print(f"Missed requests ({len(misses)} logged{f', last {days} days' if days else ''}):")
    for _, es in groups:
        tag = "BUILD THIS" if len(es) >= 2 else "once"
        projects = sorted({Path(e['cwd']).name for e in es})
        print(f"  {len(es)}x [{tag}] {es[-1]['task']}  (projects: {', '.join(projects)})")
        for e in es:
            if e.get("script"):
                print(f"       draft: {e['script']}")
    reuses = {}
    for e in entries:
        if e["kind"] == "reuse":
            reuses[e["script"]] = reuses.get(e["script"], 0) + 1
    print(f"\nReuses ({sum(reuses.values())} runs of library scripts instead of rewrites):")
    for s, n in sorted(reuses.items(), key=lambda x: -x[1]):
        print(f"  {n:3}x  {s}")
    print("\nA miss seen 2+ times is worth turning into a tested script in a skill. A one-off can wait.")


# ---------- audit ----------

def last_commit_days(path):
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%ct", "--", path.name], cwd=path.parent,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return (time.time() - int(out)) / 86400 if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def missing_imports(path):
    """Top-level imports of a Python script that aren't installed here (and aren't next to it)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except SyntaxError:
        return []
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return sorted(n for n in names if not (path.parent / f"{n}.py").exists()
                  and importlib.util.find_spec(n) is None)


def audit(roots):
    reused = {e["script"] for e in read_log() if e["kind"] == "reuse"}
    log_exists = LOG.exists()
    all_skills = list(skills(roots))
    problems = 0
    for d, fields, text, scripts in all_skills:
        notes = []
        desc = fields.get("description", "")
        if fields.get("name") != d.name:
            notes.append(f"name '{fields.get('name')}' doesn't match folder '{d.name}'")
        if not desc:
            notes.append("no description (the skill will never trigger)")
        elif len(desc) > 1024:
            notes.append(f"description {len(desc)} chars, over the 1024 limit")
        elif not NOT_CLAUSE.search(desc):
            notes.append("description has no 'Not for ...' line (helps Claude skip it when it doesn't fit)")
        for ref in set(re.findall(r"`([\w./-]+\.(?:py|ps1|sh|js|mjs))`", text)):
            if "/" not in ref and not (d / ref).exists() and not any(ref in f for _, _, f in os.walk(d)):
                notes.append(f"SKILL.md mentions `{ref}` but no such file is in the skill")
        for s in scripts:
            rel = s.relative_to(d)
            if s.suffix == ".py":
                try:
                    compile(s.read_text(encoding="utf-8", errors="ignore"), str(s), "exec")
                except SyntaxError as e:
                    notes.append(f"{rel}: FAILS to compile (line {e.lineno}: {e.msg})")
                if miss := missing_imports(s):
                    notes.append(f"{rel}: needs {', '.join(miss)} (not installed here)")
            if not script_summary(s):
                notes.append(f"{rel}: no docstring or header comment, so `find` can't match it")
            if log_exists and str(s.resolve()) not in reused:
                notes.append(f"{rel}: never logged as reused")
        age = last_commit_days(d / "SKILL.md")
        if age is not None and age > STALE_DAYS:
            notes.append(f"SKILL.md unchanged for {age:.0f} days: check it still matches the project")
        problems += len(notes)
        print(f"{d.name} ({d})" + ("" if notes else ": ok"))
        for n in notes:
            print(f"  - {n}")
    for i, (a, fa, _, _) in enumerate(all_skills):
        for b, fb, _, _ in all_skills[i + 1:]:
            if similar(words(fa.get("description", "")), words(fb.get("description", ""))) > 0.45:
                print(f"overlap: {a.name} and {b.name} have very similar descriptions; merge or sharpen them")
                problems += 1
    if not log_exists:
        print(f"\n(No log at {LOG} yet, so unused scripts can't be checked.)")
    print(f"\n{len(all_skills)} skills, {problems} notes.")


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd, rest = argv[1], argv[2:]
    if cmd == "find":
        find(" ".join(rest), default_roots())
    elif cmd == "log" and len(rest) >= 2 and rest[0] in ("miss", "reuse"):
        script = rest[rest.index("--script") + 1] if "--script" in rest[:-1] else None
        log(rest[0], rest[1], script)
    elif cmd == "review":
        review(int(rest[rest.index("--days") + 1]) if "--days" in rest[:-1] else None)
    elif cmd == "audit":
        audit([Path(r) for r in rest] or default_roots())
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
