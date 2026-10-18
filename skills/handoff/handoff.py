"""Gather git repo state for a handoff file, and check a handoff against the repo as it is now.

  python handoff.py state [repo]              print branch, commits, uncommitted/untracked files, stashes as Markdown
  python handoff.py check HANDOFF.md [repo]   list what changed since the handoff's "Repo state" was written

Standard library only. Read-only: never changes the repo.
"""
import os
import re
import subprocess
import sys


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def numstat(repo, *args):
    out = {}
    for line in (git(repo, "diff", "--numstat", *args) or "").splitlines():
        a, d, path = line.split("\t", 2)
        out[path] = f"+{a} -{d}" if a != "-" else "binary"
    return out


def state(repo):
    if git(repo, "rev-parse", "--is-inside-work-tree") != "true":
        return None
    s = {
        "branch": git(repo, "branch", "--show-current") or "(detached)",
        "head": git(repo, "rev-parse", "--short", "HEAD") or "(no commits)",
        "commits": (git(repo, "log", "--oneline", "-8") or "").splitlines(),
        "staged": numstat(repo, "--cached"),
        "unstaged": numstat(repo),
        "untracked": (git(repo, "ls-files", "--others", "--exclude-standard") or "").splitlines(),
        "stashes": (git(repo, "stash", "list") or "").splitlines(),
    }
    upstream = git(repo, "rev-list", "--left-right", "--count", "@{u}...HEAD")
    s["upstream"] = "no upstream" if upstream is None else "behind {} / ahead {}".format(*upstream.split())
    return s


def render(s):
    lines = [f"- Branch: `{s['branch']}` at `{s['head']}` ({s['upstream']})", "- Last commits:"]
    lines += [f"  - {c}" for c in s["commits"]] or ["  - none"]
    for key, label in (("staged", "Staged"), ("unstaged", "Uncommitted")):
        lines.append(f"- {label} changes: {len(s[key])} file(s)")
        lines += [f"  - `{p}` {n}" for p, n in sorted(s[key].items())]
    lines.append(f"- Untracked files: {len(s['untracked'])}")
    lines += [f"  - `{p}`" for p in s["untracked"][:40]]
    if len(s["untracked"]) > 40:
        lines.append(f"  - ...and {len(s['untracked']) - 40} more")
    lines.append(f"- Stashes: {len(s['stashes'])}")
    lines += [f"  - {x}" for x in s["stashes"]]
    return "\n".join(lines)


def check(handoff, repo):
    text = open(handoff, encoding="utf-8").read()
    now = state(repo)
    if now is None:
        print("Not a git repo: compare the handoff with the files by hand.")
        return 0
    old_head = re.search(r"Branch: `([^`]*)` at `([0-9a-f]{4,40})`", text)
    old_files = set(re.findall(r"^\s+- `([^`]+)`", text, re.M))
    notes = []
    if not old_head:
        notes.append("The handoff has no Repo state block from `handoff.py state`, so drift can't be checked.")
    else:
        branch, head = old_head.groups()
        if branch != now["branch"]:
            notes.append(f"Branch changed: handoff says `{branch}`, now `{now['branch']}`.")
        if git(repo, "cat-file", "-e", head + "^{commit}") is None:
            notes.append(f"Handoff commit `{head}` no longer exists here (rebased, reset, or another clone).")
        elif head != now["head"]:
            new = (git(repo, "log", "--oneline", f"{head}..HEAD") or "").splitlines()
            notes.append(f"{len(new)} commit(s) since the handoff:")
            notes += [f"  - {c}" for c in new[:20]]
    now_files = set(now["staged"]) | set(now["unstaged"]) | set(now["untracked"])
    if old_head:
        for p in sorted(old_files - now_files):
            notes.append(f"`{p}` was uncommitted in the handoff and is not now (committed, reverted or lost?).")
        for p in sorted(now_files - old_files):
            notes.append(f"`{p}` is uncommitted now but not in the handoff (changed after it was written).")
    print("\n".join(notes) if notes else "No drift: the repo matches the handoff's Repo state.")
    return 1 if notes else 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "state":
        s = state(argv[2] if len(argv) > 2 else ".")
        print(render(s) if s else "Not a git repo: list the files you changed instead.")
        return 0
    if len(argv) >= 3 and argv[1] == "check":
        return check(argv[2], argv[3] if len(argv) > 3 else os.path.dirname(os.path.abspath(argv[2])))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
