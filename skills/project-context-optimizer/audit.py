"""Report what a project makes Claude load: CLAUDE.md files, memory index, skills, big docs, plans/ and tools/.

  python audit.py <project-root>
"""
import os
import re
import sys

SKIP = {".git", "node_modules", "build", ".gradle", "dist", "out", "target", ".venv", "venv", "__pycache__", ".idea"}
DOC_EXT = {".md", ".txt", ".rst", ".adoc"}


def tokens(n_chars):
    return n_chars // 4


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP]
        for f in files:
            yield os.path.join(d, f)


def main(root):
    root = os.path.abspath(root)
    rel = lambda p: os.path.relpath(p, root)
    print(f"Project: {root}\n")

    print("CLAUDE.md files (root loads every session; subfolder ones load when working there):")
    for p in walk(root):
        if os.path.basename(p) in ("CLAUDE.md", "CLAUDE.local.md"):
            t = open(p, encoding="utf-8", errors="ignore").read()
            flag = "  <- trim" if t.count("\n") > 150 else ""
            print(f"  {rel(p)}: {t.count(chr(10))} lines, ~{tokens(len(t)):,} tokens{flag}")

    mem = os.path.join(os.path.expanduser("~"), ".claude", "projects",
                       re.sub(r"[^A-Za-z0-9]", "-", root), "memory", "MEMORY.md")
    if os.path.exists(mem):
        t = open(mem, encoding="utf-8").read()
        print(f"\nMemory index: {t.count(chr(10))} entries, ~{tokens(len(t)):,} tokens ({mem})")
    else:
        print("\nMemory index: none found for this path")

    sk = os.path.join(root, ".claude", "skills")
    print("\nProject skills (descriptions load every session):")
    if os.path.isdir(sk):
        for name in sorted(os.listdir(sk)):
            f = os.path.join(sk, name, "SKILL.md")
            if os.path.exists(f):
                t = open(f, encoding="utf-8").read()
                m = re.search(r"^description:\s*(.+)$", t, re.M)
                print(f"  {name}: description {len(m.group(1)) if m else 0} chars, body ~{tokens(len(t)):,} tokens")
    else:
        print("  none")

    print("\nLargest docs (split anything over ~20k tokens that sessions read):")
    docs = []
    for p in walk(root):
        if os.path.splitext(p)[1].lower() in DOC_EXT:
            try:
                docs.append((os.path.getsize(p), p))
            except OSError:
                pass
    for size, p in sorted(docs, reverse=True)[:10]:
        print(f"  ~{tokens(size):>8,} tokens  {rel(p)}")

    print("\nFolders:")
    for d in ("plans", "tools"):
        print(f"  {d}/: {'yes' if os.path.isdir(os.path.join(root, d)) else 'missing'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
