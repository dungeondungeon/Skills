# Worker brief template

```
GOAL: one sentence, the end state, not the steps.
FILES: exact paths to read and edit. Touch nothing else.
CONSTRAINTS: style, APIs to keep, things not to change.
DONE-CHECK: a command that must exit 0 (paste it), or a rubric of at most 3 yes/no lines.
REPORT (max 15 lines): status DONE|BLOCKED|FAILED; files changed; the done-check's real output (last 20 lines); anything you were unsure about.
IF STUCK: stop and report BLOCKED with what you tried. Do not guess, widen scope, or touch other files.
```

Verifier brief: same GOAL/FILES/DONE-CHECK plus the worker's report. Ask it to re-run the check, read the diff, and answer PASS or FAIL with at most 5 numbered findings, each with file and line.
