# Crew protocol

For big tasks that split into 3+ independent, checkable pieces, work as a crew: planner, workers, verifier. Prompts are in `crew/`. For anything small, just do it.

- Plan in `plans/<task>.md` (see `crew/plan-template.md`). State lives there, not in chat.
- Every task has a done-check: a command that exits 0, or a rubric of at most 3 yes/no lines.
- Workers get a brief (GOAL, FILES, CONSTRAINTS, DONE-CHECK, REPORT max 15 lines, IF STUCK), not the conversation.
- A different agent verifies. Max 2 fix rounds, then the planner decides. Max 5 workers at once.
- Use the strongest model for planner and verifier and the cheapest that passes the done-check for workers, where the tool allows choosing.
- After each plan, append 0-3 lines to `crew/lessons.md`. A human promotes lessons into prompts.
