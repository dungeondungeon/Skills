---
name: pr-review
description: Review code changes for what breaks in production — logic errors, SQL and other injection, unhandled edge cases, N+1 queries and performance, and anything touching auth, payments or data deletion — ignoring style. Use before every commit, push or pull request Claude makes, whenever asked to review a PR, branch, diff or uncommitted changes, and to install the automatic pull-request review that gates merges in a GitHub repo.
---

# PR review: catch what breaks in production

The rubric (what to look for, what to ignore, severities, comment format) is in `rubric.md` next to this file. **Read it
before every review**; it is the single source of truth for local and CI reviews.

## When this runs
- **Always, before Claude commits, pushes or opens a pull request** in any project (user rule, Oct 2026). Review the staged or
  branch diff first. If there is a CRITICAL finding, fix it or tell the user and get their decision before committing.
- When the user asks for a review of a PR, branch, path or the working tree.
- When the user asks to set up or repair the automatic PR reviewer (see "Install the CI gate").

## Local review
1. Get the diff: uncommitted `git diff HEAD`; a branch `git diff <base>...HEAD`; a GitHub PR `gh pr diff <n>`.
2. Read `rubric.md`. For each changed hunk, read enough surrounding code to know the callers, the data and the failure paths.
3. Keep only findings with a concrete failure scenario. Rank CRITICAL first.
4. Report: if the `ReportFindings` tool exists, use it (category, file, line, summary, failure_scenario); otherwise list each
   finding as `file:line` plus the rubric's comment format. Finish with the counts, sensitive areas touched, and the VERDICT.
5. For a GitHub PR the user owns, posting inline comments is an outward action: ask before posting.

Adapt the rubric to the stack rather than skipping it: in a game or app with no SQL, injection means save/file parsing, paths
and shell; "data deletion" includes deleting or overwriting save files, settings and caches; N+1 means work in per-frame or
per-actor loops.

## Install the CI gate in a repo
1. Check the repo has a GitHub remote the user owns (`git remote -v`); if not, say the gate activates once the repo is pushed
   to one. Never install it against an upstream the user doesn't own.
2. Copy `templates/claude-review.yml` to `<repo>/.github/workflows/claude-review.yml` and `rubric.md` to
   `<repo>/.github/claude-review-rubric.md`. If the project has its own risk areas, append a short "Project-specific" section to
   the repo copy of the rubric.
3. Tell the user the two steps only they can do, in GitHub settings: add the `ANTHROPIC_API_KEY` repository secret, and make
   `claude-review` a required status check on the default branch. Never enter keys or change repo settings for them.
4. How the gate works: the reviewer posts inline comments and a summary, writes `PASS` or `BLOCK` to `review-verdict.txt`, and
   the last step fails the check on `BLOCK` or a missing verdict. A required failing check blocks merging; warnings only comment.
5. After the first PR, check the run's log and comments together with the user, and tune the repo's rubric copy if it is noisy.

## Keeping it in sync
If the rubric changes here, re-copy it into each repo that has the gate (`.github/claude-review-rubric.md`).
