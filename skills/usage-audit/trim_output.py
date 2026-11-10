"""Claude Code PreToolUse hook: keep build and test output short before Claude reads it.

A Gradle build or test run can print thousands of lines, and every line stays in context for the
rest of the session. This hook rewrites matching Bash commands so Claude sees only error, failure
and warning lines (with a little context) plus the last 25 lines. The exit code is kept.

  hook   : read the PreToolUse JSON on stdin, print the rewrite (Claude Code calls this)
  filter : filter stdin to stdout (the rewritten command pipes through this)

Opt out for one command by adding  # full-output  to it.
"""
import json
import re
import sys

# Only a plain build/test call is rewritten (and so auto-allowed): no chaining, pipes, redirects or substitution.
MATCH = re.compile(r"^\s*(\./|\.\\)?(gradlew(\.bat)?|gradle|pytest|python -m pytest|npm (run )?test|yarn test|pnpm test|go test|cargo (test|build)|mvn|dotnet (build|test))(\s|$)")
UNSAFE = re.compile(r"[;&|<>`\n]|\$\(")
KEEP = re.compile(r"error|exception|fail|warning: |what went wrong|caused by|^\s+at |BUILD (SUCCESSFUL|FAILED)|^e: |^w: |tests? (passed|failed)|\d+ (passed|failed)", re.I)
TAIL, CONTEXT, MAX_KEPT = 25, 2, 200


def hook():
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not MATCH.match(cmd) or UNSAFE.search(cmd) or "full-output" in cmd:
        print("{}")
        return
    me = __file__.replace("\\", "/")
    new = f'set -o pipefail; ( {cmd} ) 2>&1 | python "{me}" filter'
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                             "updatedInput": {**data["tool_input"], "command": new}}}))


def filt():
    lines = sys.stdin.read().splitlines()
    if len(lines) <= TAIL + 40:
        print("\n".join(lines))
        return
    keep = set()
    for i, line in enumerate(lines[:-TAIL]):
        if KEEP.search(line):
            keep.update(range(max(0, i - CONTEXT), min(len(lines) - TAIL, i + CONTEXT + 1)))
    kept = sorted(keep)[:MAX_KEPT]
    out, prev = [], -1
    for i in kept:
        if i != prev + 1:
            out.append("  ...")
        out.append(lines[i])
        prev = i
    print(f"[trim_output: {len(lines)} lines, showing {len(kept)} matching + last {TAIL}. Add '# full-output' to see all.]")
    print("\n".join(out + ["  ..."] + lines[-TAIL:]))


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    {"hook": hook, "filter": filt}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
