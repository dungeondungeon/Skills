---
name: crew
description: Set up and run a planner-and-workers crew, where one strong model plans and checks and cheaper models do the bounded work, with a run-check-fix loop, a written plan file, lessons that carry over, and a compaction setting. Works as Claude Code subagents or as a plain-markdown protocol for Codex, Cursor, Gemini CLI or any tool that can start agents. Use when the user says "crew", "planner and workers", "orchestrator", "Opus plans Haiku does the work", or wants a big task split across agents, or asks to scaffold the .claude/agents folder. Not for small or tightly coupled edits, and not for finding where usage goes (use usage-audit).
---

# Crew: planner, workers, verifier

One agent that thinks (planner), cheaper agents that do (workers), and a check that does not trust the workers (verifier). The aim is better results on big, splittable tasks. It is **not** a guaranteed token saver; read `reference/claims-check.md` before promising savings.

## When to use it

Use it when the task splits into 3+ pieces that are independent and each has a checkable result (migrate 20 files, port 8 items, research 5 sources, write tests for 6 modules).

Do it yourself, with no crew, when:
- the task is small or one coherent edit (a crew costs more than it saves),
- pieces depend on each other's output or share many files,
- "done" cannot be checked by a command or a short rubric.

## Setup (once per project)

Scaffold the files, then check them:

```
python crew.py init <project-dir> --target claude     # .claude/agents + settings + memory/
python crew.py init <project-dir> --target portable   # AGENTS.md + crew/ prompts, no vendor features
python crew.py check <project-dir>                    # lints the files and flags unsupported settings
```

`init` never overwrites a file that exists. Claude Code layout, from the screenshots that prompted this skill, plus a verifier:

```
CLAUDE.md                 lean: the loop and the rules below (@-imports crew rules if long)
.claude/agents/planner.md model opus, effort xhigh; plans, briefs, reviews, never edits files
.claude/agents/worker.md  model haiku; one brief in, one short report out
.claude/agents/verifier.md model sonnet; read-only; judges worker output against the brief
.claude/settings.json     agent=planner, autoCompactWindow, CLAUDE_AUTOCOMPACT_PCT_OVERRIDE
memory/lessons.md         what the crew learned; the planner proposes, the user approves
```

Start with `claude --agent planner` (or the `agent` setting, already in the template). The planner is then the main session and spawns workers; it is the one running at xhigh.

## The loop

1. **Plan.** Planner writes `plans/<task>.md`: goal, a task list where each task has files, constraints, and a **done-check** (a command that exits 0, or a 3-line rubric), and what is out of scope. Ask the user via grill-me if the goal is vague.
2. **Run.** Planner sends each worker a brief (template in `reference/brief.md`): goal, exact files, constraints, done-check, report format of at most 15 lines. Independent tasks go in parallel; the limit is cost, not capability (see caps below).
3. **Check.** The worker runs the done-check itself and reports the real output. Then the verifier, a different agent, re-runs it and reads the diff against the brief. A deterministic command beats a model opinion; use the verifier for what commands cannot see.
4. **Fix.** Failures go back to the same worker with the verifier's exact findings, at most **2 rounds**. After that the planner decides: reword the brief, split the task, upgrade that one task to a stronger model, or do it itself. Never loop a third time on the same brief.
5. **Close.** Planner re-runs the full done-check once, writes the result into the plan file, and appends 0-3 lines to `memory/lessons.md`.

## Rules that keep it cheap

- Cap: at most 5 workers in flight and about 10 per task unless the user raises it. Every subagent starts with its own context and sends its own requests.
- Workers get briefs, not the conversation. Pass paths, not file contents.
- Reports are short and structured; the planner reads reports, not transcripts.
- Stop and tell the user when the crew is costing more than the task is worth: more than 2 fix rounds on over a third of tasks means the briefs or the model tier is wrong.
- Measure, don't guess: compare `/usage` (or the usage-audit skill) for a crew run against the same task done single-agent once. Report what was measured versus inferred.

## Compaction

Claude Code has no "40% / 60%" menu. The real knobs: `autoCompactWindow` (tokens, min 100000) sets the window; `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1-100) compacts earlier at that percent of it and can only lower the threshold. The template uses 200000 and 60. For a long or messy task lower the percent in the launch environment (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=40 claude --agent planner`). It is not switched per task automatically. Better than compacting: write state to the plan file and `/clear` between plans.

## Skills that improve themselves

The honest version: after each run the planner appends lessons to `memory/lessons.md` (what failed, which brief wording worked, which tasks need a stronger tier). The user reads that file and promotes good lessons into the worker/planner prompts or a skill (skill-creator helps). Do not let agents edit their own prompts unreviewed; it drifts and nobody can see why behavior changed. `memory: project` in an agent's frontmatter gives a subagent its own persistent notes folder if wanted.

## Other tools

`reference/portable.md` runs the same loop with plain markdown in Codex, Cursor, Gemini CLI, or the API. What carries over (roles, briefs, done-checks, plan file, fix cap) and what does not (model per agent, automatic spawning, compaction settings) is listed there.
