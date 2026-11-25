"""squeeze: shrink big text before Claude reads it, reversibly. Standard library only.

  squeeze.py show FILE [--max-lines N]   compact view of FILE (auto-detects JSON, HTML, logs, text)
  squeeze.py filter                      same, from stdin (pipe a command's output into it)
  squeeze.py get ID [A-B]                the original back, whole or a line range (from the [squeezed ...] footer)
  squeeze.py stats                       totals saved so far

The original is always stashed in ~/.claude/squeeze/ (or $SQUEEZE_DIR), so nothing is lost:
the footer names an id and `get` returns the exact text. Sizes are estimated as chars/4.
Small inputs (under 1500 chars) pass through unchanged.
"""
import hashlib, json, os, re, sys, time
from html.parser import HTMLParser

STASH = os.environ.get("SQUEEZE_DIR") or os.path.join(os.path.expanduser("~"), ".claude", "squeeze")
MIN_CHARS = 1500
tok = lambda s: (len(s) + 3) // 4


# ---------- JSON: collapse arrays of same-shape objects ----------
def shape(o):
    return tuple(sorted(o.keys())) if isinstance(o, dict) else None

def crush_json(o, depth=0):
    if isinstance(o, list) and len(o) > 6:
        shapes = {shape(x) for x in o}
        if len(shapes) == 1 and None not in shapes:  # table of same-shape rows
            keys = list(next(iter(shapes)))
            rows = [[crush_json(x[k], depth + 1) for k in keys] for x in o[:3]]
            return {"_table": {"columns": keys, "rows": rows, "total_rows": len(o), "omitted": len(o) - 3}}
        if all(not isinstance(x, (dict, list)) for x in o):
            return o[:5] + [f"... {len(o) - 5} more"]
        return [crush_json(x, depth + 1) for x in o[:5]] + [f"... {len(o) - 5} more items"]
    if isinstance(o, list):
        return [crush_json(x, depth + 1) for x in o]
    if isinstance(o, dict):
        return {k: crush_json(v, depth + 1) for k, v in o.items()}
    if isinstance(o, str) and len(o) > 300:
        return o[:200] + f"...[{len(o) - 200} chars cut]"
    return o


# ---------- HTML: outline, with source line numbers, instead of the full page ----------
class Outline(HTMLParser):
    HEAD = {"h1", "h2", "h3", "h4", "title"}
    SKIP = {"script", "style", "svg", "path"}

    def __init__(self):
        super().__init__()
        self.out, self.cur, self.skip, self.buf = [], None, 0, {}

    def handle_starttag(self, tag, attrs):
        ln = self.getpos()[0]
        a = dict(attrs)
        if tag in self.SKIP:
            self.skip += 1
            if tag == "script":
                self.out.append(f"L{ln}  <script>{' src=' + a['src'] if a.get('src') else ''}")
            elif tag == "style":
                self.out.append(f"L{ln}  <style>")
        elif tag in self.HEAD:
            self.cur = (tag, ln); self.buf[tag] = ""
        elif a.get("id") and tag in {"section", "div", "main", "nav", "header", "footer", "article", "table", "form"}:
            self.out.append(f"L{ln}  <{tag} id={a['id']}>")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
            if tag in ("script", "style"):
                self.out.append(f"L{self.getpos()[0]}  </{tag}>")
        if self.cur and tag == self.cur[0]:
            t, ln = self.cur
            self.out.append(f"L{ln}  <{t}> {' '.join(self.buf[t].split())[:100]}")
            self.cur = None

    def handle_data(self, d):
        if self.cur and not self.skip:
            self.buf[self.cur[0]] += d


def crush_html(text):
    p = Outline(); p.feed(text)
    return "HTML outline (line numbers are in the original; use `get ID A-B` for a range)\n" + "\n".join(p.out)


# ---------- Logs / text: collapse repeats, keep errors and the tail ----------
NUM = re.compile(r"\d+")
TS = re.compile(r"^\s*[\[\(]?\d{4}-\d\d-\d\d[T ]\d\d:\d\d:\d\d[.,\d]*Z?[\]\)]?\s*")
KEEP = re.compile(r"error|exception|fail|fatal|traceback|panic|warn|denied|timeout|\bnot found\b", re.I)

def crush_text(text, max_lines):
    lines = text.splitlines()
    out, prev, run, first = [], None, 0, 0
    def flush():
        if prev is None: return
        if run > 1: out.append(f"  ^ repeated {run}x (lines {first}-{first + run - 1})")
    for i, line in enumerate(lines, 1):
        key = NUM.sub("#", TS.sub("", line)).strip()
        if key and key == prev:
            run += 1
            continue
        flush()
        out.append(line.rstrip()[:300]); prev, run, first = key, 1, i
    flush()
    if len(out) > max_lines:
        keep, n = set(), len(out)
        for i, l in enumerate(out):
            if KEEP.search(l):
                keep.update(range(max(0, i - 1), min(n, i + 2)))
        keep.update(range(0, 10)); keep.update(range(max(0, n - 25), n))
        res, last = [], -1
        for i in sorted(keep)[:max_lines]:
            if i != last + 1: res.append(f"  ... {i - last - 1} lines omitted ...")
            res.append(out[i]); last = i
        if last < n - 1: res.append(f"  ... {n - 1 - last} lines omitted ...")
        out = res
    return "\n".join(out)


def detect(text, name=""):
    s = text.lstrip()[:200].lower()
    if name.endswith((".html", ".htm")) or s.startswith(("<!doctype html", "<html")):
        return "html"
    if s[:1] in "{[":
        try: json.loads(text); return "json"
        except ValueError: pass
    return "text"


def squeeze(text, name="", max_lines=120):
    if len(text) < MIN_CHARS:
        return text, None
    kind = detect(text, name)
    if kind == "json":
        body = json.dumps(crush_json(json.loads(text)), separators=(",", ":"))
    elif kind == "html":
        body = crush_html(text)
    else:
        if text.count("\n") < 40:  # short or prose-like: nothing safe to drop
            return text, None
        body = crush_text(text, max_lines)
    if tok(body) >= tok(text) * 0.9:  # not worth hiding anything
        return text, None
    sid = hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:10]
    os.makedirs(STASH, exist_ok=True)
    with open(os.path.join(STASH, sid + ".txt"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(STASH, "log.jsonl"), "a") as f:
        f.write(json.dumps({"t": int(time.time()), "id": sid, "kind": kind, "before": tok(text), "after": tok(body)}) + "\n")
    foot = f"\n[squeezed {kind}: ~{tok(text)} -> ~{tok(body)} tokens. Full original: squeeze.py get {sid} [A-B]]"
    return body + foot, (kind, tok(text), tok(body))


def get(sid, rng=None):
    p = os.path.join(STASH, re.sub(r"[^0-9a-f]", "", sid) + ".txt")
    if not os.path.exists(p):
        sys.exit(f"no stashed original for {sid} in {STASH}")
    text = open(p, encoding="utf-8").read()
    if rng:
        a, _, b = rng.partition("-")
        ls = text.splitlines()
        a = int(a); b = int(b or a)
        return "\n".join(f"{i}: {l}" for i, l in enumerate(ls[a - 1:b], a))
    return text


def stats():
    p = os.path.join(STASH, "log.jsonl")
    if not os.path.exists(p):
        return "nothing squeezed yet"
    rows = [json.loads(l) for l in open(p)]
    b, a = sum(r["before"] for r in rows), sum(r["after"] for r in rows)
    return f"{len(rows)} squeezes, ~{b} -> ~{a} tokens ({100 - 100 * a // max(b, 1)}% less, first read only; chars/4 estimate)"


def main(argv):
    if not argv: print(__doc__); return
    cmd, rest = argv[0], argv[1:]
    ml = 120
    if "--max-lines" in rest:
        i = rest.index("--max-lines"); ml = int(rest[i + 1]); del rest[i:i + 2]
    if cmd == "show" and rest:
        text = open(rest[0], encoding="utf-8", errors="replace").read()
        print(squeeze(text, rest[0], ml)[0])
    elif cmd == "filter":
        print(squeeze(sys.stdin.read(), "", ml)[0])
    elif cmd == "get" and rest:
        print(get(rest[0], rest[1] if len(rest) > 1 else None))
    elif cmd == "stats":
        print(stats())
    else:
        print(__doc__)

if __name__ == "__main__":
    main(sys.argv[1:])
