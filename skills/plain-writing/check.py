"""Flag em dashes, stock AI words and phrases, long sentences, long paragraphs and passive voice in prose.

  python check.py <file>        check a Markdown or text file ("-" reads stdin)
  python check.py --ste <file>  stricter Simplified Technical English limits (20 words per step, 25 otherwise)

Skips fenced code blocks, inline code and URLs. Exits 1 if anything is flagged. Standard library only.
"""
import re
import sys

AI_WORDS = {
    "delve", "delves", "delving", "leverage", "leverages", "leveraging", "utilize", "utilizes", "utilizing",
    "seamless", "seamlessly", "robust", "comprehensive", "pivotal", "crucial", "vital", "tapestry", "realm",
    "landscape", "testament", "showcase", "showcases", "showcasing", "foster", "fosters", "fostering", "elevate",
    "elevates", "unleash", "unlock", "unlocks", "empower", "empowers", "streamline", "streamlines", "harness",
    "intricate", "nuanced", "multifaceted", "holistic", "paramount", "meticulous", "meticulously", "embark",
    "endeavor", "bustling", "vibrant", "furthermore", "moreover", "additionally", "notably", "ultimately",
    "game-changer", "cutting-edge", "synergy", "navigate", "navigating", "underscore", "underscores", "boasts",
}
AI_PHRASES = [
    "it's important to note", "it is important to note", "it's worth noting", "it is worth noting",
    "in today's fast-paced", "in the world of", "in the realm of", "at the end of the day", "plays a crucial role",
    "plays a vital role", "a testament to", "whether you're", "look no further", "dive into", "let's dive",
    "deep dive", "not only", "in conclusion", "in summary", "i hope this helps", "great question",
    "feel free to", "rest assured", "when it comes to", "it's not just", "the power of", "embark on",
    "stands as", "serves as a", "a wide range of", "ever-evolving", "ever-changing", "elevate your",
]
BE = r"(?:is|are|was|were|be|been|being|gets|got)"
PASSIVE = re.compile(rf"\b{BE}\s+(?:\w+ly\s+)?(\w+ed|built|done|made|shown|given|taken|written|known|seen|found|sent|set|kept|left)\b", re.I)
STEP = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+")


def prose_lines(text):
    in_code = False
    lines = text.splitlines()
    front = lines.index("---", 1) + 1 if lines[:1] == ["---"] and "---" in lines[1:] else 0
    for n, line in enumerate(lines, 1):
        if n <= front:
            yield n, ""
            continue
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            continue
        if in_code or line.startswith("    ") and not STEP.match(line):
            yield n, ""
            continue
        line = re.sub(r"`[^`]*`|https?://\S+|\]\([^)]*\)", " ", line)
        yield n, line


def check(text, ste=False):
    out = []
    long_desc, long_step, max_para = (25, 20, 6) if ste else (30, 30, 0)
    para, para_start = 0, None
    for n, line in prose_lines(text):
        low = line.lower()
        if "—" in line or " -- " in line or "–" in line and re.search(r"\s–\s", line):
            out.append((n, "dash", "em/en dash: use a full stop, comma or brackets"))
        for w in sorted(set(re.findall(r"[a-z][a-z'-]+", low)) & AI_WORDS):
            out.append((n, "word", f"stock AI word '{w}'"))
        for p in AI_PHRASES:
            if p in low.replace("’", "'"):
                out.append((n, "phrase", f"stock AI phrase '{p}'"))
        for m in PASSIVE.finditer(line):
            out.append((n, "passive", f"passive voice '{m.group(0)}': say who does it"))
        if line.strip().startswith("#") or not line.strip():
            if max_para and para > max_para:
                out.append((para_start, "paragraph", f"paragraph has {para} sentences (STE max {max_para})"))
            para, para_start = 0, None
            continue
        limit = long_step if STEP.match(line) else long_desc
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", STEP.sub("", line)) if s.strip()]
        para += len(sentences)
        para_start = para_start or n
        for s in sentences:
            words = len(re.findall(r"[\w'-]+", s))
            if words > limit:
                out.append((n, "long", f"sentence of {words} words (max {limit}): '{s.strip()[:50]}...'"))
    if max_para and para > max_para:
        out.append((para_start, "paragraph", f"paragraph has {para} sentences (STE max {max_para})"))
    return sorted(out)


def main(argv):
    ste = "--ste" in argv
    args = [a for a in argv[1:] if a != "--ste"]
    if len(args) != 1:
        print(__doc__)
        return 2
    text = sys.stdin.read() if args[0] == "-" else open(args[0], encoding="utf-8").read()
    found = check(text, ste)
    for n, kind, msg in found:
        print(f"line {n}: [{kind}] {msg}")
    counts = {}
    for _, kind, _ in found:
        counts[kind] = counts.get(kind, 0) + 1
    print(f"{len(found)} issue(s)" + (": " + ", ".join(f"{v} {k}" for k, v in counts.items()) if found else ""))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
