# Project rules

Large tasks run as a crew: planner (opus, xhigh) plans and reviews, workers (haiku) do bounded tasks, verifier (sonnet) checks. Start with `claude --agent planner`.

- Do small or tightly coupled work directly; use the crew only for 3+ independent, checkable pieces.
- Every task has a done-check (a command that exits 0, or a 3-line rubric). No done-check, no task.
- Plans live in `plans/<task>.md`. State goes there, not in chat, so `/clear` is always safe.
- Max 2 fix rounds per task, then the planner decides. Max 5 workers at once.
- Lessons: planner appends 0-3 lines to `memory/lessons.md` after each plan. Read it before planning. Humans promote lessons into prompts.
