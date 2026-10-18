# Claude skills

My Claude skills, one folder per skill. Each folder holds a `SKILL.md` (name, one-line description, instructions) plus any scripts or templates it uses.

## Index

### Global skills (`skills/`)

| Skill | What it does | Extra files |
|---|---|---|
| [pr-review](skills/pr-review/SKILL.md) | Reviews changes for what breaks in production (logic, injection, edge cases, N+1, auth, payments, deletes), ignoring style. Can install an automatic PR review that gates merges. | `rubric.md`, `templates/claude-review.yml` |
| [user-research](skills/user-research/SKILL.md) | Finds what users or players say online and checks it against the project's design docs: covered, conflicting, or missing. New ideas go to the backlog only. | none |
| [project-context-optimizer](skills/project-context-optimizer/SKILL.md) | Audits a big project and restructures it so sessions load less: lean CLAUDE.md, split docs with an index, plans/ and tools/ folders. | `audit.py`, `split_doc.py` |
| [script-library](skills/script-library/SKILL.md) | Checks for a tested script before Claude writes a new one, logs what was missing and what was reused, shows what to build next, and audits skills for broken, stale, unused or overlapping parts. | `library.py` |
| [handoff](skills/handoff/SKILL.md) | Writes a `HANDOFF.md` checkpoint that another session or assistant (Codex, ChatGPT) can resume from, separating verified from unverified work, and checks a handoff against the repo when resuming. | `handoff.py` |
| [plain-writing](skills/plain-writing/SKILL.md) | Rewrites prose so it sounds human and reads easily (no em dashes or stock AI words, short sentences, active voice), with an optional light Simplified Technical English mode. | `check.py` |
| [grill-me](skills/grill-me/SKILL.md) | Interviews you before a build, asking only questions that change the work, in short batches with recommended answers, then writes a spec. | none |

### Project skills (`project-skills/<project>/`)

These only make sense inside one project, so they install into that project's `.claude/skills/`, not globally.

| Project | Skill | What it does |
|---|---|---|
| android-dev | [spd-sprites](project-skills/android-dev/spd-sprites/SKILL.md) | Inspects, diffs, merges and ports item sprites between Pixel Dungeon sprite sheets, with `sprite_tool.py` (needs Pillow). |
| android-dev | [epd-port](project-skills/android-dev/epd-port/SKILL.md) | Ports systems, items and mobs from Experienced Pixel Dungeon Redone into Deepest Pixel Dungeon, with translation rules and a per-item checklist. |

## Install

### Claude Code on Windows (recommended: link, don't copy)

Linking means an edit in the repo is live in Claude Code immediately, and an edit Claude makes to a skill shows up in `git diff`.

```powershell
git clone https://github.com/<you>/<repo>.git $HOME\code\claude-skills
cd $HOME\code\claude-skills
.\install.ps1                      # links every skills\* folder into ~\.claude\skills
.\install.ps1 -Project C:\path\to\android-dev -ProjectName android-dev   # links project skills into that project
```

If a skill folder already exists in `~\.claude\skills`, the script skips it and tells you. Move or delete the old copy, then run it again.

### Claude Code on macOS / Linux

```bash
git clone https://github.com/<you>/<repo>.git ~/code/claude-skills
cd ~/code/claude-skills && ./install.sh
```

### claude.ai (web, desktop, mobile)

claude.ai takes a skill as a `.zip` of its folder.

```powershell
.\install.ps1 -Zip                 # writes dist\<skill>.zip for every skill
```

Then upload each zip under Settings > Capabilities > Skills. Uploading a skill with an existing name replaces it. Once uploaded, the skill also reaches Claude Code cloud sessions on the same account.

## Adding or changing a skill

1. Create `skills/<name>/SKILL.md` with frontmatter `name` (kebab-case, same as the folder) and `description` (say *when* to use it and end with a "Not for ..." line saying when not to; only this loads until the skill is used).
2. Keep the body short and put long reference material in separate files the skill points to.
3. Run `python skills/script-library/library.py audit .` to catch broken scripts, missing files and overlapping descriptions.
4. Commit, then re-zip and re-upload to claude.ai if you use it there. Claude Code picks up linked changes on its own.
