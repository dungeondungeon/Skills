# Review rubric: what breaks in production

Single source of truth for both local reviews (SKILL.md) and the CI reviewer (templates/claude-review.yml copies this file into
the repo as `.github/claude-review-rubric.md`).

## Stance
Review **architecture and behaviour, not syntax**. The question for every hunk: *what happens in production when this runs on
real data, real users and real failures?* Read the code around the diff (callers, callees, the data it touches), not just the
changed lines. A compiler, linter or formatter already catches syntax; don't duplicate them.

## Look for
1. **Logic correctness (business or otherwise).** Wrong conditions, inverted checks, off-by-one, wrong units, state that can't
   reach (or can't leave) a state, invariants the change breaks, behaviour that contradicts the spec/design doc, error paths that
   swallow failures or leave half-written state, races and ordering assumptions, retries that aren't idempotent.
2. **Injection vectors.** SQL built by string concatenation or formatting (including ORM raw/`extra`/`whereRaw` calls), plus the
   same pattern elsewhere: shell commands, file paths (traversal), template rendering, deserialisation of untrusted data, URLs
   built from user input (SSRF).
3. **Unhandled edge cases.** null/None/undefined, empty collections, zero, negative, max values and overflow, very large inputs,
   unicode, time zones and DST, missing config, partial network/disk failure, concurrent edits, first run and upgrade from old
   data (save/schema migrations).
4. **N+1 queries and performance.** Queries, network or disk I/O inside loops; lazy-loaded relations iterated; unbounded fetches
   without pagination or limits; missing indexes on new filter columns; O(n²) work on hot paths; allocation or heavy work inside
   per-frame/render/request loops.
5. **Sensitive areas: always flag.** Anything touching **authentication/authorization** (sessions, tokens, permissions, role
   checks), **payments/money** (amounts, currency, rounding, billing, refunds), or **data deletion** (deletes, truncation,
   cascades, cleanup jobs, migrations that drop data, overwriting user files/saves). A change here is at least a WARNING
   ("sensitive area: needs a human reviewer"); a defect here is CRITICAL.

## Ignore
Formatting, naming, style preferences, comment wording, import order, "I'd have written it differently", and anything a linter
enforces. Do not pad the review: no praise, no restating what the code does.

## Severity
- **CRITICAL (blocks merge):** will break in production or is exploitable: wrong results on a normal path, data loss or
  corruption, security hole (injection, auth bypass, secret exposure), money calculated or moved wrongly, crash on a realistic
  input, a destructive operation without a guard.
- **WARNING (informational):** a real risk that is unlikely, unproven, or bounded: an edge case that degrades rather than breaks,
  a performance problem that bites at scale, any change to a sensitive area that looks correct but needs a human eye.

## Evidence rule
Every finding needs a **concrete failure scenario**: the input or state, and what goes wrong. If you can't name one, drop it.
Prefer three verified findings to twenty guesses. When unsure between CRITICAL and WARNING, pick WARNING and say what would
confirm it.

## Comment format (one per finding, anchored to the line)
`**[CRITICAL|WARNING] <category>** — <one-sentence defect>. **Breaks when:** <scenario>. **Fix:** <direction, not a full patch>.`

Categories: `logic`, `injection`, `edge-case`, `performance`, `n+1`, `sensitive-auth`, `sensitive-payments`, `sensitive-deletion`.

## Summary and verdict
End with a short summary: counts by severity, the sensitive areas touched, and **VERDICT: BLOCK** if there is at least one
CRITICAL, otherwise **VERDICT: PASS**.
