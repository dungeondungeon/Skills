"""Scaffold and lint a planner/worker crew.

  python crew.py init <dir> [--target claude|portable|both]   copy templates, never overwrite
  python crew.py check <dir>                                  lint agent files and settings

Standard library only. Exit code 1 when check finds errors.
"""
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TPL = HERE / "templates"
KNOWN = {"name", "description", "tools", "disallowedTools", "model", "permissionMode", "mcpServers", "hooks",
         "maxTurns", "autoCompactWindow", "skills", "initialPrompt", "memory", "effort", "background",
         "isolation", "color", "omitClaudeMd"}
MODELS = {"sonnet", "opus", "haiku", "fable", "inherit"}
EFFORT = {"low", "medium", "high", "xhigh", "max"}
# settings keys people expect (from videos) that Claude Code does not have
FAKE = {"autoCompactPercent", "autoCompactThreshold", "compactAt", "compactThreshold", "plannerModel",
        "workerModel", "autoCompactPct"}


def init(dest: Path, target: str) -> int:
    n = 0
    for t in ("claude", "portable") if target == "both" else (target,):
        src = TPL / t
        for f in sorted(src.rglob("*")):
            if f.is_dir():
                continue
            out = dest / f.relative_to(src)
            if out.exists():
                print(f"skip   {out} (exists)")
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, out)
            print(f"create {out}")
            n += 1
    print(f"{n} file(s) created. Next: python crew.py check {dest}")
    return 0


def frontmatter(text: str):
    m = re.match(r"---\r?\n(.*?)\r?\n---", text, re.S)
    if not m:
        return None
    d = {}
    for line in m.group(1).splitlines():
        k = re.match(r"^([A-Za-z]\w*):\s*(.*)$", line)
        if k:
            d[k.group(1)] = k.group(2).strip()
    return d


def check(root: Path) -> int:
    errs, warns = [], []
    agents = root / ".claude" / "agents"
    if agents.is_dir():
        files = sorted(agents.glob("*.md"))
        names = set()
        for f in files:
            fm = frontmatter(f.read_text(encoding="utf-8"))
            if fm is None:
                errs.append(f"{f.name}: no YAML frontmatter")
                continue
            for k in ("name", "description"):
                if not fm.get(k):
                    errs.append(f"{f.name}: missing {k}")
            names.add(fm.get("name"))
            for k in fm:
                if k not in KNOWN:
                    warns.append(f"{f.name}: unknown frontmatter key '{k}' (ignored by Claude Code?)")
            m = fm.get("model")
            if m and m not in MODELS and not m.startswith("claude-"):
                errs.append(f"{f.name}: model '{m}' is not an alias or a full model id")
            if not m:
                warns.append(f"{f.name}: no model; it inherits the parent's, so a worker would run on Opus")
            e = fm.get("effort")
            if e and e not in EFFORT:
                errs.append(f"{f.name}: effort '{e}' not in {sorted(EFFORT)}")
            if "autoCompactWindow" in fm and not fm["autoCompactWindow"].isdigit():
                errs.append(f"{f.name}: autoCompactWindow must be a plain integer, not '{fm['autoCompactWindow']}'")
            if f.stem == "worker" and "Agent" in fm.get("tools", ""):
                warns.append("worker.md: workers that can spawn agents multiply cost; remove Agent from tools")
            if f.stem == "verifier" and "Write" in fm.get("tools", "") and "disallowedTools" not in fm:
                warns.append("verifier.md: verifier should be read-only")
        for need in ("planner", "worker", "verifier"):
            if need not in names:
                warns.append(f"no agent named '{need}' in .claude/agents")
    s = root / ".claude" / "settings.json"
    if s.is_file():
        try:
            cfg = json.loads(s.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errs.append(f"settings.json: invalid JSON ({e})")
            cfg = {}
        for k in cfg:
            if k in FAKE:
                errs.append(f"settings.json: '{k}' is not a Claude Code setting; use autoCompactWindow and env CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")
        w = cfg.get("autoCompactWindow")
        if w is not None and not (isinstance(w, int) and w >= 100000):
            errs.append("settings.json: autoCompactWindow must be an integer >= 100000")
        p = cfg.get("env", {}).get("CLAUDE_AUTOCOMPACT_PCT_OVERRIDE")
        if p is not None and not (str(p).isdigit() and 1 <= int(p) <= 100):
            errs.append("settings.json: CLAUDE_AUTOCOMPACT_PCT_OVERRIDE must be 1-100")
        a = cfg.get("agent")
        if a and not (agents / f"{a}.md").is_file():
            errs.append(f"settings.json: agent '{a}' has no .claude/agents/{a}.md")
    elif agents.is_dir():
        warns.append("no .claude/settings.json (planner will not start as the main session unless you pass --agent)")
    cm = root / "CLAUDE.md"
    if cm.is_file() and len(cm.read_text(encoding="utf-8").splitlines()) > 150:
        warns.append("CLAUDE.md is over 150 lines; move detail out")
    port = (root / "crew").is_dir()
    if not agents.is_dir() and not port:
        errs.append("no .claude/agents and no crew/ folder; run init first")
    if port:
        for f in ("planner.md", "worker.md", "verifier.md", "plan-template.md"):
            if not (root / "crew" / f).is_file():
                warns.append(f"crew/{f} missing")
        if not (root / "AGENTS.md").is_file():
            warns.append("AGENTS.md missing")
    for w_ in warns:
        print("warn ", w_)
    for e_ in errs:
        print("ERROR", e_)
    print(f"{len(errs)} error(s), {len(warns)} warning(s)")
    return 1 if errs else 0


def main(argv):
    if len(argv) < 3 or argv[1] not in ("init", "check"):
        print(__doc__)
        return 2
    root = Path(argv[2])
    if argv[1] == "check":
        return check(root)
    target = "claude"
    if "--target" in argv:
        target = argv[argv.index("--target") + 1]
    if target not in ("claude", "portable", "both"):
        print("target must be claude, portable or both")
        return 2
    return init(root, target)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
