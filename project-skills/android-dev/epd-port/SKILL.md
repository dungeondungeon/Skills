---
name: epd-port
description: Port a system, item or mob from Experienced Pixel Dungeon Redone (EPD) into Deepest Pixel Dungeon (an SPD v4.0.2 fork). Use when bringing over any EPD class, recipe, loot bag, quest, level or mechanic, or when asked to "add the EPD stuff".
---

# Porting from EPD into Deepest Pixel Dungeon

- **Source (read only):** `Experienced-Pixel-Dungeon-Redone/` (EPD v2.19, built on an older SPD).
- **Target:** `shattered-pixel-dungeon/` (Deepest, SPD v4.0.2 base). Read `CLAUDE.md` first.
- **Scope and order:** "EPD scope" in `design/23-18-decisions-log.md` and the roadmap in `design/22-17-implementation-roadmap.md`
  (batches: sprites → loot/spells → Arena → portal items → quests/fishing/weapons). Check what's already
  ported in `shattered-pixel-dungeon/CHANGELOG.md` before starting.

## Finding what to port

```bash
# EPD-only files (relative paths), with line counts
E=Experienced-Pixel-Dungeon-Redone/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon
S=shattered-pixel-dungeon/core/src/main/java/com/shatteredpixel/shatteredpixeldungeon
comm -23 <(cd $E && find . -name "*.java" | sort) <(cd $S && find . -name "*.java" | sort)
# where an EPD class is created or used (its drop sources and hooks)
grep -rn "new GambleBag()" --include=*.java $E
# how EPD changed an existing SPD method
diff <(sed 's/\r//' $S/actors/mobs/Goo.java | sed -n '/public void die/,/^	}/p') \
     <(sed 's/\r//' $E/actors/mobs/Goo.java | sed -n '/public void die/,/^	}/p')
```

Port the whole feature: the class, **its drop sources and hooks** (shops, bosses, ring of wealth...),
its recipes, text, sprites, and journal entries.

## Translation rules (EPD → Deepest)

| EPD | Deepest |
|---|---|
| `long` gold, HP, damage, levels, `value()`, `energyVal()` | `int` (SPD types). `Random.Long`/`NormalLongRange` → `Random.IntRange`/`NormalIntRange` |
| `Random.Int(a, b)` (EPD's inclusive helper) | `Random.IntRange(a, b)` |
| `Dungeon.Int(...)`, `Dungeon.Float(...)`, `Dungeon.chances(...)` | `Random.Int`, `Random.Float`, `Random.chances` |
| `item.doPickUp(hero, pos, 0f)` | `item.collect()` (no time cost), else `Dungeon.level.drop(...)` |
| `Dungeon.hero.perks` / `Perks.Perk.*` | drop it: EPD perks are **not** ported |
| `Dungeon.cycle` content (`if (Dungeon.cycle > 0)`) | the reset loop is Phase 7; `Dungeon.cycle` exists and is always 0. Leave a comment noting the cycle rewards come later; don't port them early |
| `Dungeon.escalatingDepth()` | exists in our `Dungeon` (EPD's formula) |
| `Badges.isObtainedLocally` | exists (added for boss treasure bags) |
| EPD's self-cast `Spell.onCast` that just `detach`es | also do the talent/Catalog bookkeeping: see `items/spells/FireBooster.java`'s `used(hero)` |
| `TargetedSpell.affectTarget` | must end with `onSpellused()` (SPD v4) |
| `Flashbang`, `ShockBomb` (old SPD names) | use SPD v4's `FlashBangBomb`; shock bombs no longer exist |

- Before porting an EPD helper method, grep our code for it: SPD v4 already has some (e.g. `Level.spawnMob(int)`),
  and a duplicate won't compile.
- New side areas (arena, portal worlds) use the portal system: a `PortalItem` subclass with its own
  `Dungeon.BRANCH_*` and level class (see `items/portals/TicketToArena.java` and `levels/ArenaLevel.java`).
  Restocking shop heaps can use a respawning `FOR_SALE` heap instead of EPD's `FOR_ARENA_SALE` heap type.
- Assets (tilesets, music) are copied from EPD's `core/src/main/assets/`; note any whose author isn't
  credited, for the credits pass.
- Keep SPD's weapon balance: EPD-**added** weapons come over rebalanced to SPD tiers. Don't port EPD's
  changes to existing SPD weapons, its subclass upgrades, or Bbat.
- Ported files get both copyright lines (SPD's header plus `Experienced Pixel Dungeon / Copyright (C)
  2019-2024 Trashbox Bobylev`). Add a short `//EPD: ...` comment saying what the class is or does.

## Checklist per item

1. **Sprite:** use the `spd-sprites` skill (`port` command). EPD's sheet layout differs from ours, so never copy by position.
   Text icons (`effects/text_icons.png`, 7x8 cells) use `--cell 7x8`.
2. **Class** in the matching package, following the rules above.
3. **Recipes** registered in `items/Recipe.java` (one/two/three-ingredient arrays).
4. **Drop sources and hooks** (shops `levels/rooms/special/ShopRoom.java`, bosses' `die()`,
   `RingOfWealth`, etc.).
5. **Journal:** add the class to a `journal/Catalog.java` category. The Training Room only lays out
   catalogued items the player has seen.
6. **Dev World:** add new items to `levels/DevWorldLevel.java` (`ALCHEMY_ITEMS` or a new row).
7. **Text:** `core/src/main/assets/messages/<area>/<area>.properties`, with keys like `items.treasurebags.gamblebag.name`.
   Escape a literal percent sign as `%%` in descriptions, and run `python check_messages.py` (it must print nothing).
8. `./gradlew desktop:compileJava -q` from `shattered-pixel-dungeon/`.
9. **Docs:** add a changelog entry, update those two design files, run `python design-doc-page/build.py`, and
   republish the artifact (see CLAUDE.md). Then commit.

## Gotchas found in play-testing

- **Windows from game logic crash** (`Text measured from the actor thread!`). Code run by actors, such as `doPickUp`, `act()` or
  `execute()` during a turn, must open windows inside `Game.runOnRenderThread(new Callback(){...})`.
- **There are two inventory UIs:** `windows/WndBag.java` (mobile, and the bag window) and `ui/InventoryPane.java` (desktop and
  large screens). Inventory changes such as EPD's 55-slot backpack must be made in both.
- **Gold and energy crystals** must never be `collect()`ed into the bag. Both override `collect` to go to the purse.
  Keep that in mind when porting EPD loot code, which often uses `doPickUp`.
- **`%%` only when the text takes values.** `Messages.get` only formats a value when arguments are passed, so `%%` in a
  value with no `%s`/`%d` shows up literally as `%%`. Item `desc`, `stats_desc` and `ability_desc` values usually take no
  arguments, so write a plain `%` there.
- **SPD v4 API drift:** `TargetedCell` is no longer a `(cell, color)` effect (use `CellEmitter` bursts), `Item.cast` only
  takes a `Hero` (for catches or trades, drop at the hero's feet with `sprite.drop(fromCell)`), and `abilityChargeUse` is final
  (override `baseChargeUse` instead).
- **Extra exotics:** add them to `exoToReg` only (not `regToExo`), so they get their regular counterpart's colour without
  replacing SPD's own exotic, then offer them as alternatives where SPD's exotic drops.
