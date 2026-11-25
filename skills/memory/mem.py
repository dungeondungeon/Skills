#!/usr/bin/env python3
"""Plain-file project memory: one fact per file, a small index, keyword search, audit.

Stdlib only, so it works under Claude Code, Codex or any assistant that can run Python.
Usage: mem.py [--dir .memory] init | add | search | audit | forget | brief
"""
import argparse, re, sys, time
from pathlib import Path

INDEX = "MEMORY.md"
TYPES = ("user", "feedback", "project", "reference")
INDEX_BUDGET_TOKENS = 1500   # index is read every session; keep it under this
FILE_MAX_BYTES = 4096
STALE_DAYS = 90
WORD = re.compile(r"[a-z0-9_]{3,}")
STOP = set("the and for with that this from are was not but you your have has had will can all use when what how".split())


def toks(text):
    return {w for w in WORD.findall(text.lower()) if w not in STOP}


def est_tokens(text):
    return (len(text) + 3) // 4  # rough: ~4 chars per token


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60]


def parse(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"---\n(.*?)\n---\n?(.*)", raw, re.S)
    meta, body = {}, raw
    if m:
        body = m.group(2)
        for line in m.group(1).splitlines():
            if ":" in line and not line.startswith(" "):
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
    return meta, body, raw


def memories(d):
    return sorted(p for p in d.glob("*.md") if p.name != INDEX)


def index_lines(d):
    p = d / INDEX
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


def write_index(d, entries):
    head = "# Memory index\n"
    body = "\n".join(f"- [{n}]({n}.md): {desc}" for n, desc in sorted(entries.items()))
    (d / INDEX).write_text(head + body + "\n", encoding="utf-8")


def read_entries(d):
    out = {}
    for line in index_lines(d):
        m = re.match(r"- \[([^\]]+)\]\([^)]*\): (.*)", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def cmd_init(a, d):
    d.mkdir(parents=True, exist_ok=True)
    if not (d / INDEX).exists():
        write_index(d, {})
    print(f"Created {d}/{INDEX}. Add this to CLAUDE.md or AGENTS.md (costs ~60 tokens per session):\n")
    print(f"## Memory\nFacts that outlive a session live in `{d.name}/`. Read `{d.name}/{INDEX}` only when the task may "
          f"depend on past decisions; open a file only if its line matches. Save new durable facts with "
          f"`python <skill>/mem.py --dir {d.name} add`. Never store secrets.")


def cmd_add(a, d):
    d.mkdir(parents=True, exist_ok=True)
    if a.type not in TYPES:
        sys.exit(f"type must be one of {TYPES}")
    name = slug(a.name)
    path = d / f"{name}.md"
    entries = read_entries(d)
    if path.exists() and not a.update:
        sys.exit(f"{name} exists. Use --update to replace it (one fact per file, no duplicates).")
    if re.search(r"(api[_-]?key|secret|password|token)\s*[:=]\s*\S{8,}|sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}", a.body, re.I):
        sys.exit("Body looks like it contains a credential. Memory is plain text and often committed. Not saved.")
    mine = toks(a.desc + " " + a.name)
    for n, desc in entries.items():
        if n != name and mine and len(mine & toks(desc + " " + n)) / len(mine) > 0.6:
            print(f"warning: close to existing '{n}' ({desc}). Consider --update on that one instead.", file=sys.stderr)
    text = f"---\nname: {name}\ndescription: {a.desc}\nmetadata:\n  type: {a.type}\n  saved: {time.strftime('%Y-%m-%d')}\n---\n\n{a.body.strip()}\n"
    if len(text.encode()) > FILE_MAX_BYTES:
        sys.exit(f"{len(text.encode())} bytes is over {FILE_MAX_BYTES}. Split it into two facts or summarise.")
    path.write_text(text, encoding="utf-8")
    entries[name] = a.desc
    write_index(d, entries)
    print(f"saved {path} (index now ~{est_tokens((d / INDEX).read_text())} tokens)")


def cmd_search(a, d):
    q = toks(" ".join(a.terms))
    if not q:
        sys.exit("give at least one search word of 3+ letters")
    ranked = []
    for p in memories(d):
        meta, body, _ = parse(p)
        head = toks(p.stem + " " + meta.get("description", ""))
        score = 3 * len(q & head) + len(q & toks(body))
        if score:
            ranked.append((score, p, meta, body))
    ranked.sort(key=lambda r: (-r[0], r[1].name))
    if not ranked:
        print("no match")
    for score, p, meta, body in ranked[: a.limit]:
        print(f"{p.stem}: {meta.get('description', '')}")
        if a.full:
            print(body.strip() + "\n")


def cmd_brief(a, d):
    """Print the index plus the top-N files matching terms; the only thing a SessionStart hook should call."""
    print("".join(l + "\n" for l in index_lines(d)).rstrip())
    if a.terms:
        print("\n## Likely relevant")
        a.full, a.limit = True, a.limit
        cmd_search(a, d)


def cmd_audit(a, d):
    problems, entries = [], read_entries(d)
    idx = (d / INDEX).read_text() if (d / INDEX).exists() else ""
    t = est_tokens(idx)
    print(f"index: {len(entries)} entries, ~{t} tokens (budget {INDEX_BUDGET_TOKENS}) -> paid on every session that reads it")
    if t > INDEX_BUDGET_TOKENS:
        problems.append("index over budget: merge or delete entries, shorten descriptions")
    files = {p.stem: p for p in memories(d)}
    for n in entries:
        if n not in files:
            problems.append(f"index entry without file: {n}")
    now = time.time()
    for n, p in files.items():
        if n not in entries:
            problems.append(f"file not in index (never found): {n}")
        meta, body, raw = parse(p)
        if len(raw.encode()) > FILE_MAX_BYTES:
            problems.append(f"{n}: over {FILE_MAX_BYTES} bytes")
        if not meta.get("description"):
            problems.append(f"{n}: no description line")
        if (now - p.stat().st_mtime) / 86400 > STALE_DAYS:
            problems.append(f"{n}: not touched in {STALE_DAYS}+ days, verify or delete")
        if re.search(r"\b(today|yesterday|this week|currently|right now)\b", body, re.I):
            problems.append(f"{n}: relative time words, convert to absolute dates")
    names = sorted(entries)
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            tx, ty = toks(entries[x]), toks(entries[y])
            if tx and ty and len(tx & ty) / min(len(tx), len(ty)) > 0.7:
                problems.append(f"possible duplicates: {x} / {y}")
    print("\n".join(f"- {p}" for p in problems) or "clean")
    return 1 if problems else 0


def cmd_forget(a, d):
    name = slug(a.name)
    entries = read_entries(d)
    p = d / f"{name}.md"
    if not p.exists() and name not in entries:
        sys.exit("no such memory")
    p.unlink(missing_ok=True)
    entries.pop(name, None)
    write_index(d, entries)
    print(f"forgot {name}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default=".memory")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    s = sub.add_parser("add")
    s.add_argument("--name", required=True); s.add_argument("--type", required=True)
    s.add_argument("--desc", required=True); s.add_argument("--body", required=True)
    s.add_argument("--update", action="store_true")
    s = sub.add_parser("search")
    s.add_argument("terms", nargs="+"); s.add_argument("--full", action="store_true"); s.add_argument("--limit", type=int, default=5)
    s = sub.add_parser("brief")
    s.add_argument("terms", nargs="*"); s.add_argument("--limit", type=int, default=2)
    sub.add_parser("audit")
    s = sub.add_parser("forget"); s.add_argument("name")
    a = ap.parse_args()
    d = Path(a.dir)
    if a.cmd != "init" and a.cmd != "add" and not d.exists():
        sys.exit(f"{d} not found. Run: mem.py --dir {d} init")
    sys.exit({"init": cmd_init, "add": cmd_add, "search": cmd_search, "brief": cmd_brief,
              "audit": cmd_audit, "forget": cmd_forget}[a.cmd](a, d) or 0)


if __name__ == "__main__":
    main()
