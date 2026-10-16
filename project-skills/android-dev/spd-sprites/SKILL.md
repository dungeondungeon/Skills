---
name: spd-sprites
description: Inspect, diff, merge and port item sprites between Pixel Dungeon sprite sheets (Deepest / SPD / EPD items.png and ItemSpriteSheet.java). Use when adding sprites for new items, porting items from Experienced Pixel Dungeon or another fork, finding free sprite cells, or previewing sprites. Not for mob, hero or UI sprite sheets.
---

# Pixel Dungeon sprite sheets

Item sprites live in `core/src/main/assets/sprites/items.png`: a 256x512 grid of 16x16 cells (16 wide, 32 tall).
`sprites/ItemSpriteSheet.java` names each cell with a constant (`xy(x, y)` is **1-based**) and gives its
visible size with `assignItemRect(NAME, w, h)`. Small 8x8 overlay icons (potion/scroll/ring marks) are in
`item_icons.png` / the `Icons` inner class.

Forks drift: EPD's sheet is laid out differently from SPD v4's, so **never copy cells by position between
forks**. Port by constant name instead.

## Tool

`python .claude/skills/spd-sprites/sprite_tool.py <command>` (run from `android-dev/`; needs Pillow:
`python -m pip install pillow`). Cells in the tool are **0-based** `x,y`.

| Command | Use |
|---|---|
| `diff A.png B.png` | per-cell differences: safe (A empty), conflict, removed |
| `free SHEET.png` | list empty cells |
| `consts ItemSpriteSheet.java` | every constant as `NAME x,y` |
| `find ItemSpriteSheet.java NAME...` | cells of given constants |
| `copy SRC.png DST.png SX,SY[:DX,DY]...` | copy cells (refuses to overwrite drawn cells without `--force`) |
| `preview SHEET.png OUT.png X,Y...` | 8x enlarged strip of cells; open it with the Read tool to look at it |
| `port SRC_JAVA SRC.png DST.png NAME... [--start-row N]` | copy named constants' sprites into free cells of DST and print Java constants + `assignItemRect` lines |

## Porting sprites from another fork

1. List the source fork's constants that ours lacks:
   `python sprite_tool.py consts <ours>.java` and `... consts <theirs>.java`, then compare names.
2. Back up `items.png`, then `port` the names you need (`--start-row 28` fills the empty bottom rows first).
3. `port` defaults sizes to 16x16 when the source sets them in a loop (wands 14x14, stones 14x12,
   EPD fishing hooks 14x13): fix those lines.
4. Paste the printed block into `ItemSpriteSheet.java` (Deepest keeps ported ones in a marked
   "ported from Experienced Pixel Dungeon" section, before the `Icons` class).
5. `preview` the new cells and look at the image to confirm they're the right sprites.
6. Compile (`./gradlew desktop:compileJava` in `shattered-pixel-dungeon/`).

Section-marker constants (e.g. `TREASURE_BAGS`, `FISHING_HOOKS`) share a cell with their first item: don't port them.

## Drawing new sprites

`assignItemRect(NAME, w, h)` crops from the cell's **top-left corner**, so a sprite must be drawn flush top-left
in its 16x16 cell, not centred. Draw with Pillow, paste into a free cell (`free`), add the constant and its rect, then
`preview` it to check.
