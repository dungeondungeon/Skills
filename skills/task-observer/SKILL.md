---
name: task-observer
description: Look back over the user's recent Claude Code sessions for work they keep repeating (the same requests, corrections, commands, files read), then draft a skill, CLAUDE.md rule or script for the best one or two and install it only after approval. Use when the user asks what to turn into a skill, wants Claude to learn from how they work, or after a stretch of similar tasks. Not for always-on background watching, for installing anything without approval, or for judging one session (use usage-audit for cost).
---

# Task observer

This is a review you run on demand, not a watcher. Claude cannot see across sessions on its own; the only record is the
transcripts Claude Code keeps on the user's machine. `observe.py` counts repeats in them. Claude then drafts, the user
approves. Nothing is installed silently, and nothing costs tokens between runs.

## Cost and limits (say these up front)

- The scan is a local script. It sends nothing anywhere and uses no tokens. Reading its report costs about 1-2k tokens.
- Drafting one skill costs a normal short session. Hooks that observe every session would add cost to each one, so this skill has none.
- It finds repeats, not value. A pattern in 3 sessions can still be a bad skill. It sees only this machine's transcripts (a cloud session can't run it), and only as far back as Claude Code keeps them.
- It reads prompts, which can contain secrets. The report masks common key formats and truncates quotes, but the user should skim it before pasting it anywhere.

## 1. Scan

On the user's machine, from this skill's folder:

```bash
python observe.py scan --days 30            # all projects
python observe.py scan --match android-dev  # one project
```

It lists, by distinct sessions: repeated request phrases, repeated corrections, repeated shell commands, and files read
in many sessions, each marked "covered" when an installed skill's description already shares most of its words.
Add `--min-sessions 2` for a short history.

## 2. Choose, at most two

Sort each finding into the smallest thing that fixes it:

| Pattern | Build |
|---|---|
| Repeated correction ("don't touch X", "always do Y") | One line in CLAUDE.md. Not a skill. |
| Same file read at the start of many sessions | A pointer in CLAUDE.md, or a short reference file. |
| Same command or script rewritten | A script (check the script-library skill first), possibly inside a skill. |
| Same kind of request, multi-step, with judgment | A skill. |
| Already "covered" | Improve that skill's description or body; do not add a second. |

Skip anything one-off, and anything where the saving is under a minute. Show the user the two best candidates with the
evidence (session counts and example prompts) and a one-line reason for each, and say which you would build and why.
If the data is thin, say so; do not invent a pattern.

## 3. Draft, don't install

Write the draft to `proposed-skills/<name>/` (outside the skills folder), not into `~/.claude/skills`.
Follow the repo conventions: `name` and a `description` that says when to use it and ends with a "Not for ..." line;
body short and imperative; scripts in the folder instead of long inline code; no facts that belong in CLAUDE.md.
Base the steps on the example prompts and on what the sessions actually did, and mark anything guessed.

Check it: `python <repo>/skills/script-library/library.py audit <folder>` (when the library skill is installed).

## 4. Approve, then install

Show the draft and wait for the user's yes. Then:

```bash
python observe.py install proposed-skills/<name>            # dry run, lists files
python observe.py install proposed-skills/<name> --yes      # copies to ~/.claude/skills
```

It refuses to overwrite an existing skill. The skill loads in the next session. Re-run the scan in a few weeks: the
finding should stop appearing (and the phrase should show as "covered"); if it still does, the skill's description
isn't triggering and needs rewording.
