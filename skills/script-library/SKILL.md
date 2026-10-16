---
name: script-library
description: Reuse tested helper scripts instead of rewriting them. Use before writing any helper or utility script (file conversion, data cleanup, parsing, batch renames, report generation, build or deploy chores) to check whether one already exists in a skill; after writing a new one that could be needed again; and when the user asks which scripts to build next or to audit their skills for broken, stale or unused parts. Not for one-line commands, or for code that belongs in the project's own source.
---

# Script library

Your skills already are the library: each skill folder holds tested scripts, and its description says when to use
them. This skill closes the loop. Check before writing, log what was missing, and review the log to decide what to
build next. `library.py` sits next to this file and uses only the standard library.

```bash
L=~/.claude/skills/script-library/library.py      # or wherever this skill folder is installed
```

## 1. Before writing a helper script

```bash
python $L find <a few words saying what it must do>
```
It searches every installed skill's scripts by file name, docstring and skill description, and ranks them by how
many of your words match. Read the top match's docstring or `--help` before using it. A high percentage only means
the words overlap, not that the script fits.

- **Fits:** run it, then log the reuse with `python $L log reuse <script-path>`.
- **Nearly fits:** prefer extending that script (add a flag) over writing a second one. Tell the user, because it
  changes their skill.
- **Nothing fits:** write the script, then go to step 2.

## 2. After writing a script you may need again

```bash
python $L log miss "<one line: what the script does, in plain words>" --script <path-to-the-script>
```
Log it when the task is generic enough to come up in another session or project. Skip project-specific code. The
log is `~/.claude/script-library/log.jsonl` and holds only the time, the folder, your one-line task and the script
path, never file contents or secrets. Don't put secrets in the task line.

## 3. Review: what to build next

```bash
python $L review            # or --days 30
```
It groups similar misses. Anything marked **BUILD THIS** (seen two or more times) is a candidate to become a
tested script inside a skill. Propose it to the user: which skill it belongs in (or a new one), the script's
docstring, and a "Not for ..." line for that skill's description. Don't add it without their yes. It also lists
how often each library script was reused, which is the honest measure of what the library saves: runs, not tokens.

## 4. Audit the skills

```bash
python $L audit                       # installed skills
python $L audit <skills-repo-root>    # a skills repo, including project-skills/
```
For each skill it flags:
- a name that doesn't match its folder, or a missing or over-long description;
- a description with no **"Not for ..."** line;
- files named in SKILL.md that don't exist;
- Python scripts that fail to compile, or need a package that isn't installed here;
- scripts with no docstring (so `find` can't match them);
- scripts never logged as reused (once a log exists);
- SKILL.md files unchanged in git for 120+ days;
- pairs of skills with near-identical descriptions.

The audit only reads files. It never runs a skill's scripts, because a script with no arguments may still do
real work. Report the findings as a short list and fix only what the user agrees to.

## Limits

- Logging relies on Claude following this skill, so misses can go unlogged. Treat the counts as a lower bound.
- `find` is word matching, not understanding. Good docstrings make it work: the first line should say what the
  script does in the words someone would use to ask for it.
