# Running the crew in other AI tools

The idea needs only markdown files and an assistant that can either start sub-tasks or take turns as roles. `crew.py init <dir> --target portable` writes `AGENTS.md` (read by Codex, Cursor and many others) plus `crew/planner.md`, `crew/worker.md`, `crew/verifier.md`, `crew/plan-template.md`, `crew/lessons.md`.

## Mapping

| Need | Claude Code | Tool that can start agents (Codex, Cursor, Gemini CLI, custom) | Chat-only tool |
|---|---|---|---|
| Planner role | `.claude/agents/planner.md` | paste `crew/planner.md` as the lead's instructions | one chat, you paste `planner.md` |
| Workers | subagents, `model: haiku` | start a sub-agent per task with `crew/worker.md` + the brief; choose the cheapest model that passes the done-check | a fresh chat per task, brief pasted in |
| Verifier | subagent, read-only | a separate sub-agent that did not write the code | another fresh chat |
| Plan file | `plans/<task>.md` | same | same, saved by you |
| Compaction | settings | tool-specific; the fallback is the same: state lives in the plan file, start a fresh session between plans | fresh chat |
| Lessons | `memory/lessons.md` | same, user reviews | same |

## What does not carry over

- Choosing a different model per agent only works where the tool lets you (many do per sub-agent or per API call; some do not). If it cannot, the crew still works but loses the cost split, so use it only for the quality gain.
- Automatic parallel spawning is tool-specific. Without it, run tasks one at a time; the plan file and done-checks keep working.
- The thresholds in `settings.json` are Claude Code only.

## Fully manual protocol (works anywhere)

1. Open one session with `planner.md` + your goal. It writes the plan file; save it.
2. For each task: new session, paste `worker.md` and that task's brief. Save its report.
3. New session, paste `verifier.md`, the brief, and the report. Re-run the done-check yourself if you can.
4. Failures: back to step 2 with the findings. Two rounds, then return to the planner.
5. Planner session: paste the plan file and reports, ask for the close-out and lessons.

Keep the plan file as the only memory between sessions. That is also what makes the crew resumable by a different assistant (see the handoff skill).
