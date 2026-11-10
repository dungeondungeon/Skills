---
name: usage-audit
description: Find out what is using up Claude Code usage limits and fix the biggest cause first, from the local session transcripts (model mix, long sessions, cache misses, subagents, big tool results, re-read files), plus an optional hook that trims build and test output. Use when the user says they hit limits fast, asks where usage or tokens go, or asks how to make sessions cheaper. Not for API billing questions or for trimming project docs (use project-context-optimizer).
---

# Usage audit

Measure first, then change the one or two things that cost most. Guessing wastes more than it saves.

## 1. Measure

Run both on the user's machine; the transcripts are local and Claude in a cloud session can't see them.

1. In Claude Code, `/usage` on a Pro or Max plan shows the share of recent usage by skill, subagent, plugin and MCP server, and flags any behavior over 10% (long context, cache misses). Press `w` for the last 7 days.
2. `python usage_audit.py --days 7` (add `--match <folder name>` for one project). It reads `~/.claude/projects/**/*.jsonl` and reports usage by model, main vs subagents, cache reads vs writes vs output, the costliest sessions, the tool results that stayed in context longest, and files read over and over. It ends with a ranked "what to change first" list.

Dollar figures in the script are API list prices, used only as relative weights. Anthropic doesn't publish how plan limits weigh tokens, so say "relative" when you report them.

## 2. Fix, biggest lever first

Check each against the measurements; skip what the numbers don't support.

| Lever | When the numbers show | What to do |
|---|---|---|
| Model | Opus or Fable over half of usage | `/model` to Sonnet as the default. Opus 5.5 costs twice Sonnet 5.5 per token at list price; keep it for planning and hard bugs. Simple subagents can use `model: haiku`. |
| Session length | Peak context over ~150k, or many requests per session | `/clear` between unrelated tasks (free); `/compact` is itself a big request. Every request re-sends the whole conversation. One feature per session, started from its plan file. |
| Cache misses | 3+ misses per session | The cache lasts an hour on a subscription (five minutes once on usage credits). After a long break, `/clear` and resume from a handoff note instead of continuing a huge session. |
| Big tool results | One result over ~5k tokens re-sent many times | Read files by line range, grep before reading, and install `trim_output.py` (below) for builds and tests. |
| Subagents and parallel agents | Subagents over ~40% | Ask for fewer parallel agents; each one starts with its own full context. |
| Output and thinking | Output over ~40% | Lower `/effort` for routine edits; ask for diffs, not whole files. A lean-coding skill such as ponytail targets this. |
| MCP servers | One server with a large share in `/usage` | Disable it in `/mcp` when not needed; prefer a CLI (`gh`) where one exists. |
| Background turns | Usage while idle | Stop `/loop` and scheduled tasks you no longer need; each fire re-sends the full context. |

Report what was measured versus inferred, and re-run the audit a week after a change to confirm it helped.

## 3. Optional: trim build and test output

`trim_output.py` is a PreToolUse hook. For a plain build or test command (`./gradlew ...`, `gradle`, `pytest`, `npm test`, `mvn`, `cargo test` and similar, with no `;`, `&&`, pipes or redirects), it pipes the output through a filter that keeps error, failure and warning lines with a little context, plus the last 25 lines. The exit code is kept. Adding `# full-output` to a command skips it. In a test, an 802-line fake Gradle failure came back as 35 lines.

Because the hook rewrites the command, it also approves it, so it only matches commands that are a single build or test call. Install in `~/.claude/settings.json` (use the real path; forward slashes work on Windows):

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [ { "type": "command", "command": "python C:/Users/<you>/Documents/skills/skills/usage-audit/trim_output.py hook" } ] }
    ]
  }
}
```

Check it with `/hooks`. It needs `python` on the PATH of the shell Claude Code uses for Bash.
