---
name: memory
description: Save and recall durable project facts (decisions, user preferences, corrections, gotchas) as plain files with a small index, in a format both Claude and Codex can read, and audit that memory for bloat, duplicates and staleness. Use when the user says "remember", "don't forget", "what did we decide", asks how to get memory like Claude-mem, or when a session ends with decisions that a future session would have to ask again. Not for task state mid-work (use handoff), project docs (CLAUDE.md or design docs), or secrets.
---

# Memory

Plain-file memory: one fact per file in `.memory/`, plus `MEMORY.md`, a one-line-per-fact index. No daemon, no hooks, no
database. `mem.py` (stdlib Python) saves, searches and audits it. Codex and ChatGPT can use it too: they only need to
run the script or read the files.

## Is this worth the tokens? (honest answer)

Memory costs tokens every session it is read, and saves them only when it prevents re-asking or re-exploring.

- This skill: the index is capped at about 1,500 tokens (`audit` enforces it) and is read **on demand**, not injected
  automatically. The pointer in CLAUDE.md costs about 60 tokens per session. Typical cost: 60 to 700 tokens.
- Claude Code's built-in auto memory already does the same job for one machine (first 200 lines or 25 KB of its
  `MEMORY.md` load every session; topic files on demand). Use it. This skill adds what it lacks: it travels with the
  repo, works in Codex, is searchable, and is audited.
- Claude-mem (the plugin) injects about 50 observation titles each session and compresses every tool call with a
  background model. Its author estimates about 16.5k tokens per session at 30 observations; that is the author's figure,
  not measured here. It also runs a local worker with an unauthenticated HTTP API (reported in a Feb 2026 community audit,
  not verified here) and is Claude-Code-only. For a user who hits limits fast, it is the wrong trade. Its one real strength
  is automatic capture of what happened, which this skill replaces with deliberate saves.
- Break-even: a memory saves tokens only if it stops a question or a re-read of more than about 1,000 tokens. Save facts
  that are expensive to re-derive (a decision and its reason, a user correction, a non-obvious gotcha). Do not save what
  the code, git log or CLAUDE.md already say.

## First time in a project

```bash
python <skill-dir>/mem.py init        # creates .memory/, prints the 3-line CLAUDE.md / AGENTS.md snippet
```
Paste the snippet into CLAUDE.md or AGENTS.md. If the project already uses Claude's auto memory, keep that and skip
`init`; use only `audit` and the rules below.

## Recall

Read memory only when the task may depend on a past decision. Otherwise do not touch it.
```bash
python <skill-dir>/mem.py brief "keywords from the task"    # index + top 2 matching files in full
python <skill-dir>/mem.py search deploy netlify --full      # ranked by name/description match
```
Before acting on a memory that names a file, function or flag, check it still exists. Memories are observations from
a past date, not live state.

## Save

Save when the user says remember, corrects you, or a decision with a reason is made. One fact per file:
```bash
python <skill-dir>/mem.py add --name deploy-target --type project \
  --desc "Site deploys to Netlify from main" \
  --body "Deploy: Netlify, branch main. **Why:** user choice 2026-11-24. **How to apply:** never suggest Vercel."
```
Types: `user` (who they are, preferences), `feedback` (corrections and confirmed approaches), `project` (goals,
constraints, decisions not visible in code), `reference` (where things live outside the repo).

Rules the script enforces: refuses a body that looks like a credential, refuses over 4 KB, warns on near-duplicates
(then use `--update`), writes the date. Rules it cannot enforce: write absolute dates, include the **Why**, one fact
per file, and never save something the repo already records.

## Keep it small

```bash
python <skill-dir>/mem.py audit       # index tokens vs budget, orphans, dangling entries, stale, duplicates
python <skill-dir>/mem.py forget old-fact
```
Run `audit` at the end of any session that saved more than two memories, and when the index feels long. A wrong memory
is worse than none: delete or fix it as soon as you see it is wrong.

## Optional: automatic recall (not recommended by default)

A SessionStart hook can print `mem.py brief` so the index loads without being asked. That makes the cost fixed
(index tokens every session, even for a one-line question). Only worth it if the index stays under about 500 tokens and
the user keeps forgetting to ask. Never add a hook that records every tool call: that is Claude-mem's cost model.

## Moving between assistants

`.memory/` is plain Markdown. Tell Codex in AGENTS.md to run `mem.py brief` and `mem.py add` as above. Memory is for
facts that last; use the handoff skill for "where I stopped".
