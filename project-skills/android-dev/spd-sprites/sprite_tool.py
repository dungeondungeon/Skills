"""Sprite-sheet helper for Pixel Dungeon forks (SPD / EPD / Deepest).

Item sheets are grids of 16x16 cells. Cells are addressed as x,y (0-based).
ItemSpriteSheet.java's xy(x, y) helper is 1-based; this tool converts for you.

Commands:
  diff A.png B.png                 per-cell differences: safe (A empty), conflict (both drawn), removed (B empty)
  free SHEET.png                   list empty cells
  consts ItemSpriteSheet.java      print every constant as NAME x,y
  find SHEET_JAVA NAME [NAME...]   print the cells of given constants
  copy SRC.png DST.png SX,SY[:DX,DY] ...   copy cells from SRC into DST (in place). Refuses to overwrite a drawn cell unless --force
  preview SHEET.png OUT.png X,Y ...        save the given cells side by side, scaled 8x, for viewing
  port SRC_JAVA SRC.png DST.png NAME ... [--start-row N]
                                   copy the named sprite constants from another fork's sheet into free cells
                                   of DST (in place) and print the Java constants + assignItemRect lines

Option --cell WxH: cell size for sheets that aren't 16x16 (text_icons.png is 7x8).
Requires Pillow (python -m pip install pillow).
"""
import re
import sys

CELL = 16
#cell width and height; change with --cell WxH for sheets that aren't 16x16 (e.g. effects/text_icons.png is 7x8)
CW, CH = 16, 16


def load(path):
    from PIL import Image
    return Image.open(path).convert("RGBA")


def box(x, y):
    return (x * CW, y * CH, x * CW + CW, y * CH + CH)


def empty(img, x, y):
    return img.crop(box(x, y)).getextrema()[3][1] == 0


def cells(img):
    return img.width // CW, img.height // CH


def parse_cell(text):
    x, y = text.split(",")
    return int(x), int(y)


def cmd_diff(a_path, b_path):
    a, b = load(a_path), load(b_path)
    w, h = cells(a)
    safe, conflict, removed = [], [], []
    for y in range(h):
        for x in range(w):
            ca, cb = a.crop(box(x, y)), b.crop(box(x, y))
            if ca.tobytes() == cb.tobytes():
                continue
            if empty(b, x, y):
                removed.append((x, y))
            elif empty(a, x, y):
                safe.append((x, y))
            else:
                conflict.append((x, y))
    print("safe (only in B, A empty): %d %s" % (len(safe), safe))
    print("conflict (drawn in both, different): %d %s" % (len(conflict), conflict))
    print("removed (drawn in A, empty in B): %d %s" % (len(removed), removed))


def cmd_free(path):
    img = load(path)
    w, h = cells(img)
    print([(x, y) for y in range(h) for x in range(w) if empty(img, x, y)])


def parse_consts(java_path):
    src = open(java_path, encoding="utf-8").read()
    m = re.search(r"TX_WIDTH\s*=\s*(\d+)", src)
    size = re.search(r"SIZE\s*=\s*(\d+)", src)
    width = int(m.group(1)) // (int(size.group(1)) if size else CELL) if m else CELL
    values = {}
    pat = re.compile(r"(?:public|private)\s+static\s+final\s+int\s+(\w+)\s*=\s*([^;]+);")
    for name, expr in pat.findall(src):
        expr = expr.strip()
        m = re.fullmatch(r"xy\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*(?:([+-])\s*(\d+))?", expr)
        if m:
            v = (int(m.group(1)) - 1) + width * (int(m.group(2)) - 1)
            if m.group(3):
                v += int(m.group(4)) * (1 if m.group(3) == "+" else -1)
            values[name] = v
            continue
        m = re.fullmatch(r"(\w+)\s*(?:([+-])\s*(\d+))?", expr)
        if m and m.group(1) in values:
            v = values[m.group(1)]
            if m.group(2):
                v += int(m.group(3)) * (1 if m.group(2) == "+" else -1)
            values[name] = v
            continue
        if re.fullmatch(r"\d+", expr):
            values[name] = int(expr)
    return width, values


def cmd_consts(java_path):
    width, values = parse_consts(java_path)
    for name, v in values.items():
        if name == "WIDTH":
            continue
        print("%s %d,%d" % (name, v % width, v // width))


def cmd_find(java_path, names):
    width, values = parse_consts(java_path)
    for n in names:
        v = values.get(n)
        print("%s %s" % (n, "?" if v is None else "%d,%d" % (v % width, v // width)))


def cmd_copy(src_path, dst_path, specs, force):
    src, dst = load(src_path), load(dst_path)
    for spec in specs:
        if ":" in spec:
            s, d = spec.split(":")
        else:
            s = d = spec
        sx, sy = parse_cell(s)
        dx, dy = parse_cell(d)
        if not empty(dst, dx, dy) and not force:
            same = dst.crop(box(dx, dy)).tobytes() == src.crop(box(sx, sy)).tobytes()
            if not same:
                sys.exit("refusing to overwrite drawn cell %d,%d in %s (use --force)" % (dx, dy, dst_path))
        dst.paste(src.crop(box(sx, sy)), (dx * CW, dy * CH))
    dst.save(dst_path)
    print("copied %d cells into %s" % (len(specs), dst_path))


def parse_rects(java_path):
    src = open(java_path, encoding="utf-8").read()
    return {n: (int(w), int(h)) for n, w, h in re.findall(r"assignItemRect\(\s*(\w+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", src)}


def cmd_port(src_java, src_png, dst_png, names, start_row):
    """copies the named sprites into free cells of dst (scanning from start_row), prints Java to paste"""
    width, values = parse_consts(src_java)
    rects = parse_rects(src_java)
    src, dst = load(src_png), load(dst_png)
    w, h = cells(dst)
    free = [(x, y) for y in list(range(start_row, h)) + list(range(0, start_row)) for x in range(w) if empty(dst, x, y)]
    decls, rect_lines = [], []
    for n in names:
        if n not in values:
            sys.exit("unknown constant " + n)
        v = values[n]
        sx, sy = v % width, v // width
        if empty(src, sx, sy):
            print("// warning: %s is empty in the source sheet" % n, file=sys.stderr)
        dx, dy = free.pop(0)
        dst.paste(src.crop(box(sx, sy)), (dx * CW, dy * CH))
        decls.append("\tpublic static final int %s = xy(%d, %d);" % (n, dx + 1, dy + 1))
        rw, rh = rects.get(n, (16, 16))
        if n not in rects:
            print("// warning: no assignItemRect for %s, defaulting to 16x16" % n, file=sys.stderr)
        rect_lines.append("\t\tassignItemRect(%s, %d, %d);" % (n, rw, rh))
    dst.save(dst_png)
    print("\n".join(decls))
    print("\tstatic{")
    print("\n".join(rect_lines))
    print("\t}")


def cmd_preview(path, out, specs):
    from PIL import Image
    img = load(path)
    out_img = Image.new("RGBA", (CW * len(specs) + len(specs) - 1, CH), (40, 40, 40, 255))
    for i, spec in enumerate(specs):
        x, y = parse_cell(spec)
        out_img.alpha_composite(img.crop(box(x, y)), (i * (CW + 1), 0))
    out_img = out_img.resize((out_img.width * 8, out_img.height * 8), Image.NEAREST)
    out_img.save(out)
    print("wrote", out)


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    global CW, CH
    cmd, args = argv[1], argv[2:]
    if "--cell" in args:
        i = args.index("--cell")
        CW, CH = (int(v) for v in args[i + 1].lower().split("x"))
        args = args[:i] + args[i + 2:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    if cmd == "diff":
        cmd_diff(*args)
    elif cmd == "free":
        cmd_free(*args)
    elif cmd == "consts":
        cmd_consts(*args)
    elif cmd == "find":
        cmd_find(args[0], args[1:])
    elif cmd == "copy":
        cmd_copy(args[0], args[1], args[2:], force)
    elif cmd == "port":
        start = 0
        if "--start-row" in args:
            i = args.index("--start-row")
            start = int(args[i + 1])
            args = args[:i] + args[i + 2:]
        cmd_port(args[0], args[1], args[2], args[3:], start)
    elif cmd == "preview":
        cmd_preview(args[0], args[1], args[2:])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
