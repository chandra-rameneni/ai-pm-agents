#!/usr/bin/env python3
"""Plan My Day helper: deterministic bits the orchestrator shouldn't eyeball.

Subcommands
  init        create run folder, report config/state paths, window start
  merge       combine fetcher outputs, de-duplicate, compare with memory -> merged.json
  slots       free time today inside working hours -> printed JSON
  save        update memory (seen.json), last_plan.json, runs.jsonl
  last-plan   print the latest proposed focus blocks
  mark-booked record booked blocks
  usage       log | summary   token / cost tracking for headless runs

Stdlib only (Python 3.9+). Data lives in $PLAN_MY_DAY_HOME or ~/.plan-my-day.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

SKILL_DIR = Path(__file__).resolve().parent.parent
SOURCE_PRIORITY = ["jira", "aha", "confluence", "email", "calendar", "slack"]
KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}-(?:[A-Z]-)?\d+\b")
FETCH_EXCLUDE = {"meta.json", "seen.json", "config.json"}


# ---------------------------------------------------------------- helpers
def home_dir(arg: str | None) -> Path:
    h = Path(arg or os.environ.get("PLAN_MY_DAY_HOME") or Path.home() / ".plan-my-day")
    return h.expanduser()


def load_json(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text())
    except FileNotFoundError:
        return default


def dump_json(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    tmp.replace(p)


def load_config(home: Path, run_dir: Path | None = None) -> dict:
    example = load_json(SKILL_DIR / "config.example.json", {})
    cfg = None
    if run_dir is not None:
        cfg = load_json(run_dir / "config.json")  # demo fixtures may ship one
    if cfg is None:
        cfg = load_json(home / "config.json")
    merged = dict(example)
    merged.update(cfg or {})
    return merged


def tz_of(cfg: dict):
    name = cfg.get("timezone") or "UTC"
    if ZoneInfo is None:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def now_in(cfg: dict, override: str | None) -> datetime:
    tz = tz_of(cfg)
    if override:
        dt = datetime.fromisoformat(override)
        return dt.astimezone(tz) if dt.tzinfo else dt.replace(tzinfo=tz)
    return datetime.now(tz)


def parse_dt(s, tz) -> datetime | None:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.combine(date.fromisoformat(str(s)[:10]), datetime.min.time())
        except ValueError:
            return None
    return dt.astimezone(tz) if dt.tzinfo else dt.replace(tzinfo=tz)


TRACKING_PARAMS = re.compile(r"[?&](utm_[a-z]+|ref|source|focusedcommentid)=[^&#]*", re.I)


def norm_url(u: str) -> str:
    # Keep query and fragment: many tools put the item id there
    # (Gmail #inbox/<id>, Google Calendar ?eid=, Slack ?thread_ts=). Strip only tracking noise.
    u = TRACKING_PARAMS.sub("", u.strip())
    u = re.sub(r"^https?://(www\.)?", "", u, flags=re.I)
    return u.rstrip("/").lower()


def identity_keys(it: dict) -> set[str]:
    """Keys that *are* this item: its id, its own URL, its own ticket key."""
    keys = {"sid:" + it["source_id"]}
    if it.get("url"):
        keys.add("url:" + norm_url(it["url"]))
    m = re.match(r"^(jira|aha):(.+)$", it["source_id"])
    if m and KEY_RE.fullmatch(m.group(2)):
        keys.add("key:" + m.group(2))
    return keys


def ref_keys(it: dict) -> set[str]:
    """Keys this item points at. They merge only with an item whose identity matches."""
    keys: set[str] = set()
    for r in it.get("refs") or []:
        r = str(r).strip()
        if not r:
            continue
        if r.startswith("http"):
            keys.add("url:" + norm_url(r))
            for k in KEY_RE.findall(r):
                keys.add("key:" + k)
        else:
            for k in KEY_RE.findall(r) or [r.upper()]:
                keys.add("key:" + k)
    return keys


class DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def vip_match(it: dict, vips: list[dict]) -> dict | None:
    fid = (it.get("from_id") or "").lower()
    fem = (it.get("from_email") or "").lower()
    fname = (it.get("from") or "").strip().lower()
    for v in vips or []:
        if fid and fid == str(v.get("slack_id", "")).lower():
            return v
        if fem and fem == str(v.get("email", "")).lower():
            return v
        if fname and v.get("name") and fname == v["name"].strip().lower():
            return v
    return None


# ---------------------------------------------------------------- commands
def cmd_init(a):
    home = home_dir(a.home)
    cfg_path = home / "config.json"
    cfg = load_config(home)
    now = now_in(cfg, a.now)
    run_dir = home / "runs" / now.strftime("%Y-%m-%d-%H%M%S")
    (run_dir / "fetch").mkdir(parents=True, exist_ok=True)
    (home / "state").mkdir(parents=True, exist_ok=True)
    lookback = int(cfg.get("lookback_days", 7))
    out = {
        "home": str(home),
        "config_path": str(cfg_path),
        "config_exists": cfg_path.exists(),
        "config_example": str(SKILL_DIR / "config.example.json"),
        "run_dir": str(run_dir),
        "now": now.isoformat(),
        "today": now.date().isoformat(),
        "window_start": (now - timedelta(days=lookback)).isoformat(),
        "timezone": cfg.get("timezone"),
    }
    print(json.dumps(out, indent=2))


def cmd_merge(a):
    run_dir = Path(a.run_dir)
    home = home_dir(a.home) if a.home else _home_from_run(run_dir)
    cfg = load_config(home, run_dir)
    tz = tz_of(cfg)
    now = now_in(cfg, a.now)
    today = now.date()
    seen = load_json(home / "state" / "seen.json", {"items": {}})
    alias_to_id = {al: pid for pid, rec in seen["items"].items() for al in rec.get("aliases", [])}

    raw, events, ok, failed = [], [], [], []
    expected = [s for s, on in (cfg.get("sources") or {}).items() if on]
    found = set()
    for f in sorted((run_dir / "fetch").glob("*.json")):
        if f.name in FETCH_EXCLUDE:
            continue
        d = load_json(f, {})
        src = d.get("source") or f.stem
        found.add(src)
        if d.get("status") == "error":
            failed.append({"source": src, "error": d.get("error")})
            continue
        ok.append({"source": src, "count": len(d.get("items") or []), "truncated": bool(d.get("truncated"))})
        for it in d.get("items") or []:
            it.setdefault("source", src)
            if not it.get("source_id"):
                continue
            raw.append(it)
        if src == "calendar":
            events = d.get("events") or []
    missing = [s for s in expected if s not in found]

    # union: same identity, or one item references another's identity.
    # Two items that merely reference the same thing (e.g. same epic) stay separate.
    dsu = DSU(len(raw))
    owner: dict[str, int] = {}
    for i, it in enumerate(raw):
        for k in identity_keys(it):
            if k in owner:
                dsu.union(i, owner[k])
            else:
                owner[k] = i
    for i, it in enumerate(raw):
        for k in ref_keys(it):
            if k in owner:
                dsu.union(i, owner[k])
    groups: dict[int, list[dict]] = {}
    for i, it in enumerate(raw):
        groups.setdefault(dsu.find(i), []).append(it)

    items, resolved_ids = [], []
    vips = cfg.get("vips") or []
    for members in groups.values():
        members.sort(key=lambda m: SOURCE_PRIORITY.index(m["source"]) if m["source"] in SOURCE_PRIORITY else 99)
        sids = sorted({m["source_id"] for m in members})
        pid = next((alias_to_id[s] for s in sids if s in alias_to_id), None)
        is_known = pid is not None
        pid = pid or "pmd-" + hashlib.sha1(sids[0].encode()).hexdigest()[:10]
        if all(m.get("resolved") for m in members):
            if is_known:
                resolved_ids.append({"id": pid, "aliases": sids})
            continue
        live = [m for m in members if not m.get("resolved")]
        primary = live[0]
        acts = [parse_dt(m.get("last_activity"), tz) for m in members]
        acts = [x for x in acts if x]
        dues = sorted({str(m["due"])[:10] for m in live if m.get("due")})
        rec = seen["items"].get(pid, {})
        first_seen = rec.get("first_seen")
        earliest = min([d.date() for d in acts] + ([date.fromisoformat(first_seen)] if first_seen else []), default=today)
        vip = None
        for m in sorted(live, key=lambda m: parse_dt(m.get("last_activity"), tz) or now, reverse=True):
            vip = vip_match(m, vips)
            if vip:
                break
        items.append({
            "id": pid,
            "title": primary.get("title"),
            "from": primary.get("from"),
            "sources": [{"source": m["source"], "url": m.get("url"), "my_role": m.get("my_role"),
                         "resolved": bool(m.get("resolved")), "source_id": m["source_id"]} for m in members],
            "aliases": sids,
            "my_roles": sorted({m.get("my_role") for m in live if m.get("my_role")}),
            "last_activity": max(acts).isoformat() if acts else None,
            "due": dues[0] if dues else None,
            "awaiting_me": any(m.get("awaiting_me") for m in live),
            "snippets": [f"[{m['source']}] {m.get('snippet','')}" for m in live if m.get("snippet")][:3],
            "meta": {m["source"]: m.get("meta") for m in members if m.get("meta")},
            "vip": bool(vip),
            "vip_why": (vip or {}).get("why"),
            "status": "carried_over" if is_known else "new",
            "age_days": (today - earliest).days,
            "times_shown": rec.get("times_shown", 0),
            "last_quadrant": rec.get("last_quadrant"),
        })

    items.sort(key=lambda x: (x["due"] or "9999", -(x["age_days"])))
    out = {
        "generated_at": now.isoformat(),
        "today": today.isoformat(),
        "timezone": cfg.get("timezone"),
        "sources_ok": ok,
        "sources_failed": failed,
        "sources_missing": missing,
        "raw_count": len(raw),
        "merged_count": len(items),
        "resolved_cleared": resolved_ids,
        "items": items,
        "events": events,
    }
    dump_json(run_dir / "merged.json", out)
    print(json.dumps({k: out[k] for k in ("sources_ok", "sources_failed", "sources_missing", "raw_count", "merged_count")}
                     | {"new": sum(i["status"] == "new" for i in items),
                        "carried_over": sum(i["status"] == "carried_over" for i in items),
                        "resolved_cleared": len(resolved_ids), "events_today": len(events),
                        "merged_json": str(run_dir / "merged.json")}, indent=2))


def _home_from_run(run_dir: Path) -> Path:
    # run_dir = <home>/runs/<stamp>
    p = run_dir.resolve()
    if p.parent.name == "runs":
        return p.parent.parent
    return home_dir(None)


def _hm(day: date, hm: str, tz) -> datetime:
    h, m = (int(x) for x in hm.split(":"))
    return datetime(day.year, day.month, day.day, h, m, tzinfo=tz)


def cmd_slots(a):
    run_dir = Path(a.run_dir)
    home = home_dir(a.home) if a.home else _home_from_run(run_dir)
    cfg = load_config(home, run_dir)
    tz = tz_of(cfg)
    now = now_in(cfg, a.now)
    merged = load_json(run_dir / "merged.json", {})
    day = date.fromisoformat(merged.get("today") or now.date().isoformat())
    wh = cfg.get("working_hours") or {"start": "09:00", "end": "17:30"}
    start, end = _hm(day, wh["start"], tz), _hm(day, wh["end"], tz)
    if now.date() == day and now > start:
        # round up to next 15 min
        start = now + timedelta(minutes=(15 - now.minute % 15) % 15)
        start = start.replace(second=0, microsecond=0)
    busy = []
    for e in merged.get("events") or []:
        if not e.get("busy", True) or e.get("my_response") == "declined":
            continue
        s, f = parse_dt(e.get("start"), tz), parse_dt(e.get("end"), tz)
        if s and f:
            busy.append((s, f, e.get("title", "")))
    lunch = cfg.get("lunch")
    if lunch:
        busy.append((_hm(day, lunch["start"], tz), _hm(day, lunch["end"], tz), "Lunch"))
    busy.sort()
    free, cur = [], start
    for s, f, _ in busy:
        if f <= cur:
            continue
        if s > cur:
            free.append((cur, min(s, end)))
        cur = max(cur, f)
        if cur >= end:
            break
    if cur < end:
        free.append((cur, end))
    min_m = int(cfg.get("min_block_minutes", 30))
    gaps = [{"start": s.isoformat(), "end": f.isoformat(), "minutes": int((f - s).total_seconds() // 60)}
            for s, f in free if (f - s) >= timedelta(minutes=min_m)]
    print(json.dumps({"day": day.isoformat(), "working_hours": wh, "focus_block_minutes": cfg.get("focus_block_minutes", 90),
                      "free_gaps": gaps,
                      "busy": [{"start": s.isoformat(), "end": f.isoformat(), "title": t} for s, f, t in busy]}, indent=2))


def cmd_save(a):
    run_dir = Path(a.run_dir)
    home = home_dir(a.home) if a.home else _home_from_run(run_dir)
    merged = load_json(run_dir / "merged.json")
    if merged is None:
        sys.exit("merged.json missing; run merge first")
    classified = load_json(run_dir / "classified.json", {"items": [], "proposed_blocks": []})
    quad = {c["id"]: c.get("quadrant") for c in classified.get("items", [])}
    seen_p = home / "state" / "seen.json"
    seen = load_json(seen_p, {"items": {}})
    today = merged["today"]
    for it in merged["items"]:
        rec = seen["items"].setdefault(it["id"], {"first_seen": today, "times_shown": 0})
        rec["aliases"] = sorted(set(rec.get("aliases", [])) | set(it["aliases"]))
        rec["title"] = it["title"]
        if rec.get("last_seen") != today:
            rec["times_shown"] = rec.get("times_shown", 0) + 1
        rec["last_seen"] = today
        rec["last_quadrant"] = quad.get(it["id"], rec.get("last_quadrant"))
        rec.pop("resolved_on", None)
    for r in merged.get("resolved_cleared", []):
        if r["id"] in seen["items"]:
            seen["items"][r["id"]]["resolved_on"] = today
    # forget anything not seen for 30 days
    cutoff = (date.fromisoformat(today) - timedelta(days=30)).isoformat()
    seen["items"] = {k: v for k, v in seen["items"].items() if v.get("last_seen", today) >= cutoff}
    dump_json(seen_p, seen)

    blocks = classified.get("proposed_blocks", [])
    dump_json(home / "state" / "last_plan.json",
              {"date": today, "run_dir": str(run_dir), "proposed_blocks": blocks, "booked": []})
    counts = {q: sum(1 for v in quad.values() if v == q) for q in ("do", "schedule", "delegate", "eliminate")}
    line = {"date": today, "run_dir": str(run_dir), "raw_count": merged["raw_count"],
            "merged_count": merged["merged_count"],
            "per_source": {s["source"]: s["count"] for s in merged["sources_ok"]},
            "failed": [s["source"] for s in merged["sources_failed"]],
            "missing": merged.get("sources_missing", []), "quadrants": counts,
            "proposed_blocks": len(blocks)}
    with open(home / "runs.jsonl", "a") as fh:
        fh.write(json.dumps(line) + "\n")
    print(json.dumps(line, indent=2))


def cmd_last_plan(a):
    home = home_dir(a.home)
    print(json.dumps(load_json(home / "state" / "last_plan.json", {"proposed_blocks": [], "booked": []}), indent=2))


def cmd_mark_booked(a):
    home = home_dir(a.home)
    p = home / "state" / "last_plan.json"
    lp = load_json(p)
    if not lp:
        sys.exit("no last_plan.json")
    ids = a.event_id or []
    for i, n in enumerate(a.n):
        lp["booked"].append({"n": n, "event_id": ids[i] if i < len(ids) else None})
    dump_json(p, lp)
    print(json.dumps(lp["booked"]))


# ---------------------------------------------------------------- usage
def _sum_usage(res: dict) -> dict:
    """Totals across every model used in the run (orchestrator + subagents)."""
    mu = res.get("modelUsage") or {}
    if mu:
        t = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
        for m in mu.values():
            t["input"] += m.get("inputTokens", 0)
            t["output"] += m.get("outputTokens", 0)
            t["cache_read"] += m.get("cacheReadInputTokens", 0)
            t["cache_write"] += m.get("cacheCreationInputTokens", 0)
        t["models"] = {k: v.get("costUSD") for k, v in mu.items()}
        return t
    u = res.get("usage") or {}
    return {"input": u.get("input_tokens", 0), "output": u.get("output_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0),
            "cache_write": u.get("cache_creation_input_tokens", 0)}


def cmd_usage(a):
    home = home_dir(a.home)
    log = home / "usage.jsonl"
    if a.action == "log":
        text = sys.stdin.read().strip()
        try:
            res = json.loads(text)
        except json.JSONDecodeError:
            # stream-json / multiple lines: take last result object
            res = next((json.loads(l) for l in reversed(text.splitlines())
                        if l.strip().startswith("{") and '"result"' in l), {})
        if isinstance(res, list):
            res = next((r for r in reversed(res) if r.get("type") == "result"), {})
        tok = _sum_usage(res)
        runs = (home / "runs.jsonl").read_text().splitlines() if (home / "runs.jsonl").exists() else []
        last = json.loads(runs[-1]) if runs else {}
        entry = {
            "at": datetime.now(timezone.utc).isoformat(),
            "is_error": res.get("is_error", False),
            "duration_s": round(res.get("duration_ms", 0) / 1000, 1),
            "num_turns": res.get("num_turns"),
            "cost_usd": res.get("total_cost_usd"),
            "tokens": tok,
            "total_tokens": tok["input"] + tok["output"] + tok["cache_read"] + tok["cache_write"],
            "items_triaged": last.get("raw_count"),
            "items_after_merge": last.get("merged_count"),
        }
        with open(log, "a") as fh:
            fh.write(json.dumps(entry) + "\n")
        print(json.dumps(entry, indent=2))
        return
    # summary
    if not log.exists():
        sys.exit(f"no usage log yet at {log}; it is written by scripts/run-daily.sh")
    rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if not r.get("is_error")][-a.last:]
    if not rows:
        sys.exit("no successful runs logged")

    def avg(key, sub=None):
        vals = [(r.get(key) or {}).get(sub) if sub else r.get(key) for r in rows]
        vals = [v for v in vals if isinstance(v, (int, float))]
        return sum(vals) / len(vals) if vals else None

    def fmt(v, kind):
        if v is None:
            return "n/a"
        return {"tok": f"{v/1000:,.0f}k", "usd": f"${v:,.2f}", "s": f"{v/60:,.1f} min", "n": f"{v:,.0f}"}[kind]

    summary = [
        ("Runs measured", f"{len(rows)}"),
        ("Avg total tokens / run", fmt(avg("total_tokens"), "tok")),
        ("  of which output", fmt(avg("tokens", "output"), "tok")),
        ("  of which cache reads", fmt(avg("tokens", "cache_read"), "tok")),
        ("Avg cost / run", fmt(avg("cost_usd"), "usd")),
        ("Avg wall-clock / run", fmt(avg("duration_s"), "s")),
        ("Avg items triaged / run", fmt(avg("items_triaged"), "n")),
        ("Avg items after de-dup", fmt(avg("items_after_merge"), "n")),
    ]
    if a.markdown:
        print("| Metric | Value |\n|---|---|")
        for k, v in summary:
            print(f"| {k.strip()} | {v} |")
    else:
        for k, v in summary:
            print(f"{k:<28} {v}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", help="data dir (default $PLAN_MY_DAY_HOME or ~/.plan-my-day)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("--now"); p.set_defaults(f=cmd_init)
    p = sub.add_parser("merge"); p.add_argument("run_dir"); p.add_argument("--now"); p.set_defaults(f=cmd_merge)
    p = sub.add_parser("slots"); p.add_argument("run_dir"); p.add_argument("--now"); p.set_defaults(f=cmd_slots)
    p = sub.add_parser("save"); p.add_argument("run_dir"); p.set_defaults(f=cmd_save)
    p = sub.add_parser("last-plan"); p.set_defaults(f=cmd_last_plan)
    p = sub.add_parser("mark-booked"); p.add_argument("n", type=int, nargs="+"); p.add_argument("--event-id", nargs="*")
    p.set_defaults(f=cmd_mark_booked)
    p = sub.add_parser("usage"); p.add_argument("action", choices=["log", "summary"])
    p.add_argument("--last", type=int, default=30); p.add_argument("--markdown", action="store_true")
    p.set_defaults(f=cmd_usage)

    # allow --home after the subcommand too
    argv = sys.argv[1:]
    if "--home" in argv and argv.index("--home") > 0:
        i = argv.index("--home")
        argv = argv[i:i + 2] + argv[:i] + argv[i + 2:]
    a = ap.parse_args(argv)
    a.f(a)


if __name__ == "__main__":
    main()
