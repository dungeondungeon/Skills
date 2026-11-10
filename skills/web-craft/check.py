#!/usr/bin/env python3
"""Static checks for common speed, usability and accessibility mistakes in HTML/CSS.

Usage: python check.py <file-or-dir> [...]
Prints one finding per line as path:line: [rule] message. Exit code 1 if any finding.
Heuristics only: it cannot measure real speed, contrast or screen-reader behaviour.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.f = []  # (line, rule, msg)
        self.h1 = 0
        self.imgs = 0
        self.seen = set()
        self.in_head = False
        self.in_title = False
        self.title = ""
        self.last_level = 0
        self.labels_for = set()
        self.inputs = []  # (line, id, attrs)
        self.in_label = 0
        self.in_button = None
        self.button_text = ""
        self.in_a = None
        self.a_text = ""

    def add(self, rule, msg):
        self.f.append((self.getpos()[0], rule, msg))

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.seen.add(tag)
        if tag == "head":
            self.in_head = True
        elif tag == "html" and not a.get("lang"):
            self.add("lang", "<html> has no lang attribute")
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            if a.get("name") == "viewport":
                self.seen.add("viewport")
                c = a.get("content", "")
                if re.search(r"user-scalable\s*=\s*(no|0)|maximum-scale\s*=\s*1(\.0)?\b", c):
                    self.add("zoom", "viewport blocks pinch zoom")
            if a.get("name") == "description":
                self.seen.add("description")
        elif tag == "img":
            self.imgs += 1
            if "alt" not in a:
                self.add("alt", "<img> without alt (use alt=\"\" for decoration)")
            if not (a.get("width") and a.get("height")) and "aspect-ratio" not in a.get("style", ""):
                self.add("cls", "<img> without width/height: causes layout shift")
            if self.imgs > 1 and a.get("loading") != "lazy" and a.get("fetchpriority") != "high":
                self.add("lazy", "non-first <img> without loading=\"lazy\" (ignore if above the fold)")
            if (a.get("src") or "").startswith("data:") and len(a["src"]) > 10000:
                self.add("inline-image", "large base64 image inlined in HTML")
        elif tag == "script":
            if a.get("src") and self.in_head and not ("defer" in a or "async" in a or a.get("type") == "module"):
                self.add("blocking", "script in <head> without defer/async blocks rendering")
        elif tag == "link" and a.get("rel") == "stylesheet" and a.get("href", "").startswith("http"):
            self.seen.add("external-css")
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            lvl = int(tag[1])
            if lvl == 1:
                self.h1 += 1
            if self.last_level and lvl > self.last_level + 1:
                self.add("headings", f"<{tag}> follows <h{self.last_level}>: skipped heading level")
            self.last_level = lvl
        elif tag == "label":
            self.in_label += 1
            if a.get("for"):
                self.labels_for.add(a["for"])
        elif tag in ("input", "select", "textarea"):
            if a.get("type") not in ("hidden", "submit", "button", "image", "reset"):
                self.inputs.append((self.getpos()[0], a.get("id"), a, self.in_label > 0))
        elif tag == "button":
            self.in_button = (self.getpos()[0], a)
            self.button_text = ""
        elif tag == "a":
            self.in_a = (self.getpos()[0], a)
            self.a_text = ""
            if "href" not in a and "name" not in a and "id" not in a:
                self.add("link", "<a> without href: use <button> for actions")
            if a.get("target") == "_blank" and "noopener" not in a.get("rel", "") :
                self.add("noopener", 'target="_blank" without rel="noopener"')
        if tag not in ("a", "button", "input") and ("onclick" in a) and tag in ("div", "span", "li", "p", "img"):
            self.add("semantics", f"clickable <{tag}>: use <button> or <a href>")

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        elif tag == "title":
            self.in_title = False
        elif tag == "label":
            self.in_label = max(0, self.in_label - 1)
        elif tag == "button" and self.in_button:
            line, a = self.in_button
            if not self.button_text.strip() and not (a.get("aria-label") or a.get("aria-labelledby") or a.get("title")):
                self.f.append((line, "name", "<button> with no text or aria-label"))
            self.in_button = None
        elif tag == "a" and self.in_a:
            line, a = self.in_a
            if "href" in a and not self.a_text.strip() and not (a.get("aria-label") or a.get("aria-labelledby")):
                self.f.append((line, "name", "<a> with no text or aria-label (icon-only link?)"))
            if self.a_text.strip().lower() in ("click here", "here", "read more", "more"):
                self.f.append((line, "link-text", f'vague link text "{self.a_text.strip()}"'))
            self.in_a = None

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.in_button:
            self.button_text += data
        if self.in_a:
            self.a_text += data

    def finish(self, full_page):
        for line, iid, a, inside in self.inputs:
            if not (inside or (iid and iid in self.labels_for) or a.get("aria-label") or a.get("aria-labelledby")):
                self.f.append((line, "label", "form field without an associated <label>"))
        if full_page:
            if "viewport" not in self.seen:
                self.f.append((1, "viewport", "no <meta name=viewport>: page will not be mobile-friendly"))
            if not self.title.strip():
                self.f.append((1, "title", "missing or empty <title>"))
            if "description" not in self.seen:
                self.f.append((1, "description", "no meta description"))
            if self.h1 != 1:
                self.f.append((1, "h1", f"{self.h1} <h1> elements (want exactly 1)"))
            if "main" not in self.seen:
                self.f.append((1, "landmark", "no <main> landmark"))


def css_checks(text, base_line=1):
    out = []
    lines = text.split("\n")
    has_anim = bool(re.search(r"@keyframes|animation\s*:|transition\s*:", text))
    has_reduce = "prefers-reduced-motion" in text
    for i, ln in enumerate(lines, base_line):
        if re.search(r"transition\s*:\s*all\b", ln):
            out.append((i, "transition-all", "transition: all animates layout properties; list properties"))
        if re.search(r"outline\s*:\s*(none|0)\b", ln) and "focus-visible" not in text:
            out.append((i, "focus", "outline removed without a :focus-visible replacement"))
        if re.search(r"font-size\s*:\s*(\d|1[01])px\b", ln) and not re.search(r"font-size\s*:\s*1[2-9]px", ln):
            out.append((i, "small-text", "font-size under 12px"))
        if re.search(r"@font-face", ln) and "font-display" not in text:
            out.append((i, "font-display", "@font-face without font-display"))
        if re.search(r"(?<![\w-])(width|min-width)\s*:\s*\d{4,}px", ln):
            out.append((i, "fixed-width", "fixed width over 999px breaks mobile"))
    if has_anim and not has_reduce:
        out.append((1, "reduced-motion", "animations present but no prefers-reduced-motion handling"))
    return out


def check_file(p: Path):
    text = p.read_text(encoding="utf-8", errors="replace")
    f = []
    if p.suffix in (".html", ".htm"):
        pg = Page()
        pg.feed(text)
        full = bool(re.search(r"<html|<!doctype", text, re.I))
        pg.finish(full)
        f += pg.f
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", text, re.S | re.I):
            f += css_checks(m.group(1), text[: m.start(1)].count("\n") + 1)
        if len(text) > 200_000:
            f.append((1, "size", f"HTML is {len(text)//1000} KB: move data/assets out"))
    elif p.suffix == ".css":
        f += css_checks(text)
    return sorted(set(f))


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    files = []
    for a in argv:
        p = Path(a)
        if p.is_dir():
            files += [x for x in p.rglob("*") if x.suffix in (".html", ".htm", ".css")
                      and not {"node_modules", ".git", "dist"} & set(x.parts)]
        elif p.exists():
            files.append(p)
        else:
            print(f"not found: {a}")
            return 2
    n = 0
    for p in files:
        for line, rule, msg in check_file(p):
            print(f"{p}:{line}: [{rule}] {msg}")
            n += 1
    print(f"{n} finding(s) in {len(files)} file(s)")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
