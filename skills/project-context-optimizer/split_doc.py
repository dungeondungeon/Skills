"""Split a markdown/text doc into one file per `## ` section, join it back, or rebuild the index.

  python split_doc.py split <doc> <outdir>   # writes NN-slug.md files + README.md, verifies exact round trip
  python split_doc.py join  <dir> <out>      # concatenates the section files (name order) into one file
  python split_doc.py index <dir>            # rewrites <dir>/README.md (file, heading, lines, ~tokens)

Everything before the first `## ` heading other than a "Table of Contents" goes into 00-header.md.
"""
import os
import re
import sys


def sections(dirpath):
    return sorted(f for f in os.listdir(dirpath) if f.endswith(".md") and f != "README.md")


def read(path):
    return open(path, encoding="utf-8", newline="").read()


def write_index(dirpath, title="Section index"):
    files = sections(dirpath)
    rows, total = [], 0
    for f in files:
        text = read(os.path.join(dirpath, f))
        total += len(text)
        heading = next((l.lstrip("#").strip() for l in text.splitlines() if l.startswith("#")), f)
        rows.append(f"| `{f}` | {heading} | {text.count(chr(10))} | ~{len(text) // 4:,} |")
    out = "\n".join([
        f"# {title} (GENERATED, don't edit)",
        "",
        f"One file per section; read only what the task needs (whole doc ~{total // 4:,} tokens).",
        "Files join in name order. A new section's name must sort into place (`18a-...` goes after `18-...`).",
        "",
        "| File | Section | Lines | Tokens |",
        "|---|---|---|---|",
    ] + rows) + "\n"
    open(os.path.join(dirpath, "README.md"), "w", encoding="utf-8").write(out)


def split(doc, outdir):
    raw = read(doc)
    lines = raw.splitlines(keepends=True)
    cuts = [i for i, l in enumerate(lines) if l.startswith("## ")]
    if not cuts:
        sys.exit("no '## ' headings found")
    # keep a leading table of contents with the header
    body = [c for c in cuts if not re.match(r"## +(table of )?contents", lines[c], re.I)]
    parts = [("header", lines[:body[0]])] if body[0] > 0 else []
    for k, i in enumerate(body):
        j = body[k + 1] if k + 1 < len(body) else len(lines)
        title = re.sub(r"\(.*?\)", "", lines[i][3:].strip())
        parts.append((title, lines[i:j]))
    os.makedirs(outdir, exist_ok=True)
    if sections(outdir):
        sys.exit(f"{outdir} already has section files; refusing to overwrite")
    for n, (title, ls) in enumerate(parts):
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40].strip("-") or "section"
        open(os.path.join(outdir, f"{n:02d}-{slug}.md"), "w", encoding="utf-8", newline="").write("".join(ls))
    joined = "".join(read(os.path.join(outdir, f)) for f in sections(outdir))
    if joined != raw:
        sys.exit("ROUND TRIP FAILED: section files don't join back to the original. Original left untouched.")
    write_index(outdir)
    print(f"split into {len(parts)} files in {outdir}; round trip identical; index written")


def join(dirpath, out):
    text = "".join(read(os.path.join(dirpath, f)) for f in sections(dirpath))
    open(out, "w", encoding="utf-8", newline="").write(text)
    print(f"wrote {out} ({len(text) // 4:,} tokens)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "split" and len(sys.argv) == 4:
        split(sys.argv[2], sys.argv[3])
    elif cmd == "join" and len(sys.argv) == 4:
        join(sys.argv[2], sys.argv[3])
    elif cmd == "index":
        write_index(sys.argv[2])
    else:
        sys.exit(__doc__)
