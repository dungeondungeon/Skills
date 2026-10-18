---
name: handoff
description: Write or resume a handoff checkpoint so another session or another assistant (Codex, ChatGPT) can carry on the work without re-reading the conversation. Use when usage is about to run out, before switching assistants, at the end of a long session, when the user says "handoff", "checkpoint" or "save where we are", and at the start of a session that finds a HANDOFF.md. Not for routine end-of-task summaries, or for facts that belong in memory or CLAUDE.md/AGENTS.md.
---

# Handoff

A handoff is a short file that lets the next worker, which may be a different assistant with no access to this
conversation or to Claude memory, pick up the task cold. Its value is in what it separates: what was checked, what
was guessed, and what is not yet saved anywhere.

If the project already has its own procedure (for example `AI-HANDOFF-PROCEDURE.md`, or a handoff section in
`AGENTS.md`), follow that instead and use this skill only for anything it leaves out.

## Writing a handoff

1. Gather the facts with the script instead of reading files by hand. From the project root:
   ```bash
   python ~/.claude/skills/handoff/handoff.py state      # or wherever this skill folder is installed
   ```
   It prints branch, last commits, uncommitted and untracked files with line counts, and stashes, as Markdown. Paste
   its output under "Repo state". Outside a git repo it says so; describe the files touched instead.
2. Write `HANDOFF.md` at the project root (or the path the project uses) with exactly these sections, plain prose,
   no Claude-only references (no memory paths, no `.claude/` tool names the next assistant can't use):

   ```markdown
   # Handoff (YYYY-MM-DD HH:MM, written by <assistant>)
   ## Goal
   One or two sentences: what the user wants when this is finished, and which plan file defines it.
   ## Done and verified
   Each item with how it was verified (built, test run, user confirmed). Nothing goes here unchecked.
   ## Done but NOT verified
   Written but not compiled, not run, or not seen working. Say why (e.g. sandbox had no network).
   ## In progress
   Exactly where work stopped: file, function, the half-finished change.
   ## Next steps
   Numbered, smallest first. The first one must be doable without asking the user anything.
   ## Decisions and open questions
   Decisions made this session with their reason; questions only the user can answer.
   ## Do not
   Approaches already tried and rejected, and why, so they are not retried.
   ## Repo state
   (output of handoff.py state)
   ```
3. Keep it under about 80 lines. Link to plan files and diffs instead of copying them.
4. Uncommitted work is the main risk. Say plainly in "In progress" whether the next worker must keep it, and never
   tell it to reset, stash or clean the tree.
5. Decide where the file lives. A tracked `HANDOFF.md` shows up as a code change on every checkpoint and becomes
   public if the repo does. Prefer adding it to `.gitignore` unless the user wants it in history.
6. Tell the user in one line where the file is and what the next worker should do first.

## Resuming from a handoff

1. Read `HANDOFF.md`, then run `python <skill>/handoff.py check HANDOFF.md`. It compares the file's "Repo state"
   with the repo now and lists commits, files and branches that changed since it was written.
2. Treat everything under "Done but NOT verified" as unverified: build or test it before building on it.
3. If the drift report shows changes the handoff doesn't explain, tell the user before continuing.
4. When the handoff is consumed, update it rather than leaving a stale one: either rewrite it at the next checkpoint
   or delete it once the goal is done.

## Without a repo (claude.ai chats)

When the work is a long conversation, not code, write the same sections as a Markdown block in the reply so the user
can paste it into a new chat. Drop "Repo state"; under "Done and verified" list facts the user confirmed.

## Using it from Codex

Codex reads `AGENTS.md`, not this folder. To let it write and resume handoffs the same way, copy this folder into the
project's `.agents/skills/` mirror (or point to it from `AGENTS.md`). `handoff.py` uses only the standard library.
