---
name: squeeze
description: Shrink big files, JSON, logs and HTML pages before reading them into context, with the full original kept on disk and retrievable by line range. Use when about to read or print something large (API or tool JSON, long logs, command output, a big HTML artifact or page) or when a session keeps re-reading the same large file. Not for source code you will edit (read it normally), build and test output (usage-audit's trim_output hook), project docs (project-context-optimizer) or reducing Claude's own output (ponytail).
---

# Squeeze

Every token that enters a session is re-sent on each later request, so a 10k-token log read once costs 10k tokens times every request after it. This skill puts a filter in front of the biggest, least informative inputs. It is a manual tool, not a proxy: nothing sits between Claude Code and Anthropic.

Script: `squeeze.py` next to this file (standard library only). The skill folder path is wherever it is installed, for example `~/.claude/skills/squeeze/squeeze.py`.

## Use it

```
python squeeze.py show FILE            # compact view of a file
some-command 2>&1 | python squeeze.py filter
python squeeze.py get ID               # the exact original
python squeeze.py get ID 120-160       # only those lines, numbered
python squeeze.py stats                # what has been saved
```

What `show` and `filter` do, by content type:

| Input | Result |
|---|---|
| JSON | Arrays of same-shaped objects become a table: column names, first 3 rows, total row count. Long strings are cut. Other arrays keep 5 items. |
| HTML | An outline: title, headings and ids of sections, script and style spots, each with its original line number. Use `get ID A-B` to read just the section needed. |
| Logs and long text (40+ lines) | Repeated lines (ignoring numbers and timestamps) collapse to "repeated Nx"; errors, warnings and tracebacks are kept with one line of context, plus the first 10 and last 25 lines. |
| Under 1500 chars, short or prose-like text, or less than 10% saved | Passed through unchanged. |

Every squeezed result ends with `[squeezed kind: ~A -> ~B tokens. Full original: squeeze.py get ID]`. The original is stashed in `~/.claude/squeeze/` (set `SQUEEZE_DIR` to move it), so squeezing is reversible: if the compact view lacks something, `get` returns it exactly.

## When to reach for it

1. Before `Read` or `cat` on a file that is clearly large and not code you will edit: JSON dumps, API responses, exports, logs.
2. Before printing a long command's output into the session: pipe it through `filter`.
3. An HTML artifact or design page that gets re-read after each edit: run `show` once to get the outline, then `get ID A-B` for only the section being changed, and edit by line range. This targets the repeated whole-page reads that show up in `usage_audit.py`.
4. Do not squeeze what you are about to edit exactly (code, config), or anything where one dropped line could change the answer. If an error is reported but its cause isn't in the compact view, `get` the range before guessing.

## What it will and will not do (measured, not claimed)

Test inputs, sizes estimated as chars/4, compact view only (the first read):

| Input | Before | After | Note |
|---|---|---|---|
| JSON list of 400 user records | ~9,100 | ~54 | Synthetic and very uniform. Real API data varies more, so expect less. |
| 600-line log, one error | ~6,000 | ~48 | Synthetic: nearly every line a repeat. |
| Real `git log --stat`, 300 commits | ~2,240 | ~460 | Mostly lines dropped, not rewritten. |
| Real file listing, 2,000 paths | ~27,000 | ~1,900 | The same: head, tail and any error-like lines. |
| Real `pip list -v` table | ~2,120 | unchanged | No safe cut, passed through. |
| Synthetic multi-line HTML page, 25 sections | ~7,550 | ~420 | Outline only. Reading a section costs a `get`. |
| One-line prose paragraph set | ~3,080 | unchanged | Prose is not compressed. |

Read these carefully. The big percentages come from hiding content, not from clever compression, and they are the best case. If Claude then needs the hidden part, `get` adds it back, so a net saving needs most squeezed inputs to be skimmable. None of this has been measured on real Claude Code sessions yet. To check, run `usage_audit.py` (usage-audit skill) for a week before and a week after and compare "tool results that stayed in context longest" and total cache reads.

## Compared with Headroom, and what is deliberately left out

Headroom (headroom-ai, Apache 2.0) does similar things automatically: JSON and AST code compression, a prose model, and a local store with a retrieve tool. Per its README its own benchmarks show 21 to 57% on four scenarios built from tool-output formats and over 90% on repeated JSON and logs, little on prose. Those are the project's own numbers, not independent. This skill borrows two ideas (table-ifying JSON, reversible retrieval by id) and skips the rest:

- No proxy. `headroom wrap claude` routes Claude Code through a local proxy. A proxy can change what is sent upstream and may affect prompt caching, which is half of this user's usage. Whether that is allowed on a Pro or Max login is not something to assume (routing a plan login through third-party tools has already been judged a terms problem for OmniRoute), so it is left for the user to check against Anthropic's current terms before trying it.
- No AST code compression and no prose model. Compressing code you are about to edit risks wrong edits, and prose barely shrinks.
- No hook that rewrites Read results. As far as is known, Claude Code hooks can't replace the output of the built-in Read tool, so this stays a deliberate step Claude takes.
- No telemetry, and nothing leaves the machine.

Related skills do the other jobs: usage-audit measures where usage goes and trims build and test output; ponytail shortens Claude's output; project-context-optimizer shrinks project docs.
