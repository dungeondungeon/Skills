---
name: project-context-optimizer
description: Audit and restructure a large or long-running project so Claude sessions load less and remember more — lean CLAUDE.md files, design docs split into per-section files with an index, plans/ and tools/ folders, project skills and memory used for the right things. Use when starting work in a big project that lacks this structure (CLAUDE.md over ~150 lines, docs over ~20k tokens, several reference repos, many sessions), or whenever the user asks about saving context through project files, docs, memory or skills. Not for small projects that already load little, for one-off coding tasks, or for finding what uses up usage limits (use usage-audit first).
---

# Project context optimizer

Goal: every session should load only what it needs. Run the audit, propose the changes in one short list, and
**ask before restructuring** (it moves the user's files). Then apply, verify nothing was lost, and report.

## 1. Audit

```bash
python ~/.claude/skills/project-context-optimizer/audit.py <project-root>
```
It prints every CLAUDE.md with its size, the memory index size, project skills with their description lengths,
the largest docs (by tokens), and whether `plans/` and `tools/` exist. Rough cost: tokens ≈ characters / 4.

## 2. What goes where

| Content | Home | Why |
|---|---|---|
| Rules needed in every session (layout, fixed decisions, never-do's) | root `CLAUDE.md`, under ~80 lines | loaded in full every session, re-sent every turn |
| Rules for one area (build commands, code style, message-file rules) | `CLAUDE.md` inside that folder | loads only when working there |
| Repeatable workflows, reference maps, porting rules | a project skill `.claude/skills/<name>/SKILL.md` | only its one-line description loads until used; write a description that says *when* to use it |
| Who the user is, preferences, decisions and *why* | memory (one fact per file, one-line index entry) | the index loads every session, so keep entries one line |
| Big design docs and specs | a folder, **one file per section**, plus a generated `README.md` index with each file's token size | sessions read one section instead of the whole doc |
| Feature work in progress | `plans/<feature>.md`; move to `plans/done/` when shipped | a fresh session starts from the plan, not from a long chat |
| Helper code that keeps being rewritten | `tools/` (importable scripts) | stop regenerating the same code |
| Reference codebases | read-only folders, searched with grep, never read whole | |

Never store in memory what the repo, docs or git history already record.

## 3. Restructure (after the user agrees)

- **Split a big doc:** `python ~/.claude/skills/project-context-optimizer/split_doc.py split <doc> <outdir>`
  splits on `## ` headings into `NN-slug.md` files (order kept by name), **verifies the files join back to the exact
  original**, and writes `<outdir>/README.md`. Back the doc up first; delete the original only after the round trip
  passes and any page/export builder is switched to read the folder (`split_doc.py join <dir> <out>` rebuilds one file,
  `split_doc.py index <dir>` rewrites the index). New sections: name them to sort into place (`18a-...` after `18-...`).
- **Slim CLAUDE.md:** move area-specific rules into that area's own CLAUDE.md; move long workflows into skills;
  fix stale statements you notice (say so). Point to files instead of repeating their content.
- **Update every reference** to moved files (CLAUDE.md files, skills, memory, plans, build scripts): grep for the old names.
- **Verify:** builders still produce identical output (`cmp`), the doc round-trips, the code still compiles.

## 4. Habits to tell the user about (briefly)

- One feature per session, started from its plan file; `/compact` at milestones and `/clear` between unrelated tasks —
  a long conversation is re-sent on every turn and is usually the biggest cost.
- Batch several decisions into one message; match the effort setting to the task.
- Publish or export generated pages once per working block, not after each small edit.
