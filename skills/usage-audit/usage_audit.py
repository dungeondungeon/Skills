"""Find what is using up your Claude Code limits, from the local transcripts.

  python usage_audit.py [--days 7] [--match android-dev] [--top 8] [--projects ~/.claude/projects] [--json out.json]

Reads ~/.claude/projects/**/*.jsonl (main sessions and their subagents), keeps sessions active in the
last --days, optionally only those whose working folder contains --match, and reports:
  - where the usage went: model, main vs subagent, cache reads vs writes vs output
  - the costliest sessions, with peak context and cache misses
  - the tool results that sat in context longest ("context rent"), and files read again and again
  - flags, each with the habit or setting that fixes it

Weights are API list prices, used only to compare one kind of usage with another. Anthropic does not
publish how plan limits weigh tokens, so treat the dollar figures as relative, not as your bill.
Token counts are real (from the API's usage fields); tool-result sizes are estimates (characters / 4).
"""
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

# USD per million tokens: input, 5m cache write, 1h cache write, cache read, output (list prices, Oct 2026)
PRICES = [
    ("fable-5-1", (10, 12.5, 20, 0.25, 50)), ("mythos-5-1", (10, 12.5, 20, 0.25, 50)),
    ("fable", (10, 12.5, 20, 1.0, 50)), ("mythos", (10, 12.5, 20, 1.0, 50)),
    ("opus-5-5", (4, 5, 8, 0.2, 20)), ("opus", (5, 6.25, 10, 0.5, 25)),
    ("sonnet-5-5", (2, 2.5, 4, 0.1, 10)), ("sonnet-5", (2, 2.5, 4, 0.2, 10)), ("sonnet", (3, 3.75, 6, 0.3, 15)),
    ("haiku-5-5", (0.1, 0.125, 0.2, 0.01, 0.5)), ("haiku", (1, 1.25, 2, 0.1, 5)),
]
HAIKU55_LONG = (0.5, 0.625, 1.0, 0.05, 2.5)  # Haiku 5.5 when the prompt is over 100k tokens


def family(model):
    m = (model or "").lower()
    for f in ("fable", "mythos", "opus", "sonnet", "haiku"):
        if f in m:
            return f
    return "other"


def cost(model, u):
    m = (model or "").lower()
    p = next((p for k, p in PRICES if k in m), PRICES[4][1])
    inp, cr, cw = u.get("input_tokens", 0), u.get("cache_read_input_tokens", 0), u.get("cache_creation_input_tokens", 0)
    if "haiku-5-5" in m and inp + cr + cw > 100_000:
        p = HAIKU55_LONG
    cc = u.get("cache_creation") or {}
    w5, w1 = cc.get("ephemeral_5m_input_tokens"), cc.get("ephemeral_1h_input_tokens")
    if w5 is None and w1 is None:
        w5, w1 = 0, cw  # older transcripts: assume the 1h cache a subscription uses
    parts = {"uncached input": inp * p[0], "cache write": (w5 or 0) * p[1] + (w1 or 0) * p[2],
             "cache read": cr * p[3], "output": u.get("output_tokens", 0) * p[4]}
    return {k: v / 1e6 for k, v in parts.items()}


def text_len(content):
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(text_len(b.get("text", "") if isinstance(b, dict) and b.get("type") == "text"
                            else b.get("content", "") if isinstance(b, dict) else "") for b in content)
    return 0


def describe(name, inp):
    inp = inp or {}
    for k in ("file_path", "path", "command", "pattern", "url", "query", "description", "prompt"):
        if inp.get(k):
            return f"{name} {str(inp[k]).splitlines()[0][:70]}"
    return name


def ts(e):
    t = e.get("timestamp")
    try:
        return datetime.fromisoformat(t.replace("Z", "+00:00")) if t else None
    except ValueError:
        return None


def load(projects, since, match):
    sessions = defaultdict(lambda: {"reqs": {}, "results": [], "reads": Counter(), "title": "", "prompt": "", "cwd": "",
                                    "start": None, "end": None, "order": []})
    for f in glob.glob(os.path.join(os.path.expanduser(projects), "**", "*.jsonl"), recursive=True):
        sub_file = "subagents" in f.replace("\\", "/").split("/")
        tools = {}
        for line in open(f, encoding="utf-8", errors="ignore"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            sid = e.get("sessionId") or os.path.basename(f)
            s = sessions[sid]
            if e.get("type") == "ai-title" and e.get("aiTitle"):
                s["title"] = e["aiTitle"]
            if e.get("cwd") and not sub_file:
                s["cwd"] = s["cwd"] or e["cwd"]
            t = ts(e)
            if t:
                s["start"] = min(s["start"] or t, t)
                s["end"] = max(s["end"] or t, t)
            m = e.get("message") if isinstance(e.get("message"), dict) else {}
            side = sub_file or bool(e.get("isSidechain"))
            if e.get("type") == "assistant":
                if m.get("usage"):
                    rid = e.get("requestId") or e.get("uuid")
                    if rid not in s["reqs"] and not side:
                        s["order"].append(("req", rid))
                    s["reqs"][rid] = (m.get("model"), m["usage"], side)  # repeated per content block; keep one
                for b in m.get("content") or []:
                    if isinstance(b, dict) and b.get("type") == "tool_use":
                        tools[b.get("id")] = describe(b.get("name", "?"), b.get("input"))
                        if b.get("name") == "Read" and not side:
                            s["reads"][(b.get("input") or {}).get("file_path", "?")] += 1
            elif e.get("type") == "user" and not side:
                c = m.get("content")
                texts = [c] if isinstance(c, str) else [b.get("text", "") for b in c or [] if isinstance(b, dict) and b.get("type") == "text"]
                for t in texts if not s["prompt"] else []:
                    t = re.sub(r"<([\w-]+)[^>]*>.*?</\1>", " ", t, flags=re.S)  # drop harness-added tagged blocks
                    if t.strip() and not t.lstrip().startswith("<"):
                        s["prompt"] = " ".join(t.split())[:60]  # names the session when it has no title
                        break
                for b in m.get("content") if isinstance(m.get("content"), list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_result":
                        s["order"].append(("res", (tools.get(b.get("tool_use_id"), "tool"), text_len(b.get("content")) // 4)))
    out = {}
    for sid, s in sessions.items():
        if not s["reqs"] or not s["end"] or s["end"] < since:
            continue
        if match and match.lower() not in s["cwd"].lower():
            continue
        out[sid] = s
    return out


def main(a):
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    days, top = float(opt("--days", 7)), int(opt("--top", 8))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    S = load(opt("--projects", "~/.claude/projects"), since, opt("--match"))
    if not S:
        sys.exit(f"No sessions in the last {days:g} days" + (f" under a folder matching {opt('--match')!r}" if opt("--match") else ""))

    by_model, by_part, main_sub = Counter(), Counter(), Counter()
    rows, rent, flags = [], [], Counter()
    for sid, s in S.items():
        total = sub = opus = 0.0
        ctx, misses = [], 0
        for model, u, side in s["reqs"].values():
            c = cost(model, u)
            v = sum(c.values())
            total += v
            by_model[family(model)] += v
            for k, x in c.items():
                by_part[k] += x
            main_sub["subagents" if side else "main"] += v
            sub += v if side else 0
            opus += v if family(model) in ("opus", "fable", "mythos") else 0
            if not side:
                ctx.append(u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0) + u.get("cache_creation_input_tokens", 0))
                if len(ctx) > 1 and u.get("cache_creation_input_tokens", 0) > 20_000:
                    misses += 1  # big re-write after the first request: break past the cache lifetime, compaction, or changed tools
        later = 0
        for kind, val in reversed(s["order"]):
            if kind == "req":
                later += 1
            elif val[1] >= 500:
                rent.append((val[1] * later, val[1], later, val[0], s["title"] or sid[:8]))
        peak = max(ctx) if ctx else 0
        rereads = sum(n - 1 for n in s["reads"].values() if n > 1)
        s["title"] = s["title"] or s["prompt"]
        rows.append({"session": sid, "title": s["title"], "cwd": s["cwd"], "start": s["start"].isoformat()[:16],
                     "requests": len(ctx), "peak_ctx": peak, "cost": round(total, 3), "subagent_share": round(sub / total, 2) if total else 0,
                     "opus_share": round(opus / total, 2) if total else 0, "cache_misses": misses, "rereads": rereads,
                     "top_rereads": [(os.path.basename(k), n) for k, n in s["reads"].most_common(3) if n > 2]})
        flags["long"] += peak > 150_000
        flags["huge"] += peak > 400_000
        flags["misses"] += misses >= 3
        flags["rereads"] += rereads >= 5
        flags["subagents"] += total and sub / total > 0.4

    grand = sum(by_model.values())
    pct = lambda x: f"{x / grand:.0%}" if grand else "-"
    print(f"{len(S)} sessions in the last {days:g} days, ${grand:,.2f} at API list price (relative weight, not your bill)\n")
    print("By model:      " + ", ".join(f"{k} {pct(v)}" for k, v in by_model.most_common()))
    print("Main/subagent: " + ", ".join(f"{k} {pct(v)}" for k, v in main_sub.most_common()))
    print("By kind:       " + ", ".join(f"{k} {pct(v)}" for k, v in by_part.most_common()))

    rows.sort(key=lambda r: -r["cost"])
    print(f"\nCostliest sessions (share of total, requests, peak context, cache misses, subagent share):")
    for r in rows[:top]:
        name = (r["title"] or r["session"][:8])[:44]
        print(f"  {pct(r['cost']):>4}  {r['start']}  {name:<44} {r['requests']:>4} req  peak {r['peak_ctx'] // 1000:>4}k"
              f"  misses {r['cache_misses']:>2}  sub {r['subagent_share']:.0%}" + (f"  re-read {r['top_rereads']}" if r["top_rereads"] else ""))

    rent.sort(key=lambda x: -x[0])
    if rent:
        print("\nTool results that stayed in context longest (est. tokens x later requests that re-sent them):")
        for score, t, n, what, title in rent[:top]:
            print(f"  {t:>7,} tok x {n:>3} req  {what[:70]}  [{title[:30]}]")

    n = len(S)
    tips = []
    if by_model["opus"] + by_model["fable"] + by_model["mythos"] > 0.5 * grand:
        tips.append("Most usage is Opus/Fable. Default to Sonnet (/model), keep Opus for planning and hard bugs.")
    if flags["long"]:
        tips.append(f"{flags['long']}/{n} sessions passed 150k context. /clear between tasks; start each feature from its plans/ file.")
    if flags["huge"]:
        tips.append(f"{flags['huge']}/{n} sessions passed 400k context (the 1M window). Set \"autoCompactWindow\": 200000 in ~/.claude/settings.json so they compact at 200k.")
    if flags["misses"]:
        tips.append(f"{flags['misses']}/{n} sessions had 3+ cache misses. After a break of an hour or more, /clear and resume from HANDOFF.md instead of continuing.")
    if flags["rereads"]:
        tips.append(f"{flags['rereads']}/{n} sessions re-read the same files 5+ times. Point CLAUDE.md or the plan at the exact section to read.")
    if flags["subagents"]:
        tips.append(f"{flags['subagents']}/{n} sessions spent over 40% in subagents. Ask for fewer parallel agents, or set model: haiku on simple ones.")
    if by_part["output"] > 0.4 * grand:
        tips.append("Output (including thinking) is over 40% of usage. Lower /effort for routine edits; ask for diffs, not full files.")
    if rent and rent[0][1] > 5_000:
        tips.append("Big tool results ride along in every later request. Read files by line range, filter build/test output, and /clear after a big one.")
    print("\nWhat to change first:" if tips else "\nNo flags raised.")
    for i, t in enumerate(tips, 1):
        print(f"  {i}. {t}")
    if opt("--json"):
        json.dump({"by_model": by_model, "by_kind": by_part, "main_subagent": main_sub, "sessions": rows,
                   "rent": rent[:50]}, open(opt("--json"), "w", encoding="utf-8"), indent=1)
        print(f"\nsaved {opt('--json')}")


if __name__ == "__main__":
    if "-h" in sys.argv or "--help" in sys.argv:
        sys.exit(__doc__)
    sys.stdout.reconfigure(errors="replace")  # session titles can hold characters a Windows console can't print
    main(sys.argv[1:])
