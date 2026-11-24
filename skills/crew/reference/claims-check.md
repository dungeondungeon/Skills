# Claims from the "God mode" video, checked (2026-11-24)

Sources: Claude Code docs (sub-agents, model-config, env-vars, settings-reference, costs) read on 2026-11-24, and Anthropic's engineering post "How we built our multi-agent research system". The video itself was only seen as two screenshots; the rest of its claims are unverified.

| Claim | Verdict | Detail |
|---|---|---|
| Folder: CLAUDE.md, .claude/agents/planner.md + worker.md, .claude/skills/, .claude/settings.json | Real | Agents are markdown files with YAML frontmatter in `.claude/agents/`. |
| A top-level `memory/` folder | Partly | Nothing in Claude Code reads a root `memory/` folder. Real mechanisms: auto memory, and `memory: user\|project\|local` in an agent's frontmatter (stored under `.claude/agent-memory/<name>/`). The template's `memory/lessons.md` is a plain file the planner is told to read. |
| Opus planner on "extra high" effort | Real | `effort: xhigh` works in agent frontmatter or `effortLevel` in settings for Opus 5.5 and other current models. Use `claude --agent planner` or the `agent` setting so the planner is the main session. Opus 5.5 defaults to medium. |
| Haiku workers | Real, but a choice | `model: haiku` in frontmatter, or `CLAUDE_CODE_SUBAGENT_MODEL` (add `_FORCE=1` to override every subagent). Haiku 5.5 exists and supports effort levels. |
| Verification loop run-check-fix | Real and sound | Matches Claude Code's own best-practices advice to give Claude a way to verify its work. Cap the loop. |
| Auto-compact at 40% (60% for big tasks) | Not as stated | No such preset. Real: `autoCompactWindow` (tokens, min 100000), `/autocompact`, `--autocompact`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`, and `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1-100; lower only). On 1M-window models the default compacts near 967K tokens, so "40%" of that is ~390K, which is a very large context. The absolute window matters more than the percent. No automatic switch to 60% for big tasks exists. |
| "Skills that keep improving themselves" | Not a feature | Nothing self-edits skills. A lessons file plus human review is the safe version. |
| "Far fewer tokens" | Unproven, often false | Subagent requests draw on your usage on top of the main session (costs docs). Anthropic's own data: multi-agent systems used about 15x the tokens of chat and agents about 4x. Savings come only if the cheap tier does enough of the token-heavy work correctly the first time. Verification and re-work add tokens. Haiku costs less per token, but no published benchmark shows net savings for this pattern. Measure it. |
| "Better results" | Supported for some tasks | Anthropic found Opus lead + Sonnet subagents beat single-agent Opus by 90.2% on its internal research eval, mostly on breadth-first research. That is Sonnet workers, not Haiku, an internal eval, and research tasks. Not shown for coding. |
| "Anthropic's own engineers work this way" | Partly true, overstated | Anthropic published the planner-plus-subagents pattern for its Research feature and documents subagents. That is not evidence about how its engineers work day to day, and it used Sonnet workers. Unverifiable as stated. |
| "Pay the expensive model only to think" | Reasonable design | Costs docs say to reserve Opus for hard reasoning and pick smaller models for subagents. Opus 5.5 lists at twice Sonnet 5.5 per token. |

## What the build changes because of this

- Worker model is a one-line choice; the default is haiku for mechanical tasks, and the planner may name `sonnet` for a task in its brief.
- Added an independent verifier and a hard 2-round fix cap, since re-work is where savings vanish.
- Compaction uses real settings; the 40% figure is documented as an env override, not a mode.
- Self-improvement is a reviewed lessons file.
- `crew.py check` warns about unsupported keys so copied-from-video config does not silently do nothing.
