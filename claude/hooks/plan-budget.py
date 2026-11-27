#!/usr/bin/env python3
"""Pace Claude subscription usage against the 5-hour and weekly limits.

`record` reads the status line JSON on stdin and logs rate limits and session cost.
`check [--usd N]` reports how far each window is ahead of an even pace and,
for an API-equivalent estimate, its share of each limit and whether to ask first.
"""
import argparse
from datetime import date, datetime, time, timedelta
import json
import os
from pathlib import Path
import sys
import time as clock

H5 = 5 * 3600
D7 = 7 * 86400
H5_FLOOR = 10.0
RECORD_INTERVAL = 60
KEEP = 8 * 86400
PRUNE_BYTES = 8 << 20
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def state_dir() -> Path:
    return Path(os.environ.get("CLAUDE_PLAN_BUDGET_DIR") or Path.home() / ".claude" / "plan-budget")


def now() -> float:
    return float(os.environ.get("CLAUDE_PLAN_BUDGET_NOW") or clock.time())


def read_samples(path: Path) -> list:
    if not path.exists():
        return []
    samples = []
    for line in path.read_text().splitlines():
        try:
            samples.append(json.loads(line))
        except ValueError:
            continue
    return samples


def record(raw: str) -> None:
    try:
        data = json.loads(raw)
        limits = data.get("rate_limits") or {}
        h5, d7 = limits.get("five_hour") or {}, limits.get("seven_day") or {}
        entry = {"ts": now(), "session": data["session_id"],
                 "cost": float((data.get("cost") or {}).get("total_cost_usd") or 0),
                 "h5": h5.get("used_percentage"), "h5_reset": h5.get("resets_at"),
                 "d7": d7.get("used_percentage"), "d7_reset": d7.get("resets_at")}
    except (ValueError, KeyError, TypeError, AttributeError):
        return
    path = state_dir() / "samples.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    tail = b""
    if path.exists():
        with path.open("rb") as f:
            f.seek(max(0, path.stat().st_size - 32768))
            tail = f.read()
    for line in reversed(tail.decode(errors="ignore").splitlines()):
        try:
            last = json.loads(line)
        except ValueError:
            continue
        if last.get("session") == entry["session"]:
            if entry["ts"] - last["ts"] < RECORD_INTERVAL and (last["h5"], last["d7"]) == (entry["h5"], entry["d7"]):
                return
            break
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    if path.stat().st_size > PRUNE_BYTES:
        # shortcut: a line another session appends during this rewrite is lost; lock the file if that matters.
        kept = [s for s in read_samples(path) if s["ts"] >= entry["ts"] - KEEP]
        tmp = path.with_suffix(".tmp")
        tmp.write_text("".join(json.dumps(s) + "\n" for s in kept))
        tmp.replace(path)


def load_schedule():
    path = state_dir() / "schedule.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text())
    return ({DAYS.index(d) for d in raw["days"]},
            time.fromisoformat(raw["start"]), time.fromisoformat(raw["end"]))


def active_seconds(start: float, end: float, schedule) -> float:
    if end <= start:
        return 0.0
    if schedule is None:
        return end - start
    days, open_at, close_at = schedule
    total, day = 0.0, date.fromtimestamp(start)
    while day <= date.fromtimestamp(end):
        if day.weekday() in days:
            lo = datetime.combine(day, open_at).timestamp()
            hi = datetime.combine(day, close_at).timestamp()
            total += max(0.0, min(end, hi) - max(start, lo))
        day += timedelta(days=1)
    return total


def window_cost(samples: list, start: float) -> float:
    by_session: dict = {}
    for s in sorted(samples, key=lambda s: s["ts"]):
        first, last = by_session.get(s["session"], (None, None))
        if s["ts"] <= start or first is None:
            first = s["cost"]
        by_session[s["session"]] = (first, s["cost"])
    return sum(last - first for first, last in by_session.values())


def window(name, used, reset, length, schedule, samples, t):
    if t >= reset:
        # Why not reuse the sampled window: it already reset to 0, and a new 5-hour window opens only at the next request.
        start = t if length == H5 else reset
        reset, used = start + length, 0.0
    start = reset - length
    total, elapsed = active_seconds(start, reset, schedule), active_seconds(start, t, schedule)
    allowed = 100.0 * elapsed / total if total else 100.0
    if length == H5:
        allowed = max(H5_FLOOR, allowed)
    cost = window_cost([s for s in samples if s["ts"] <= t], start)
    rate = used / cost if cost > 0 and used > 0 else None
    return {"name": name, "used": used, "allowed": allowed, "reset": reset, "total": total,
            "elapsed": elapsed, "left": total - elapsed, "cost": cost, "rate": rate}


def check(usd) -> int:
    t = now()
    samples = read_samples(state_dir() / "samples.jsonl")
    limited = [s for s in samples if s.get("h5") is not None and s.get("d7") is not None]
    if not limited:
        print("no rate-limit sample yet: the status line logs one after a session's first response")
        return 0
    latest = max(limited, key=lambda s: s["ts"])
    try:
        schedule = load_schedule()
    except (ValueError, KeyError, TypeError) as error:
        print(f"invalid {state_dir() / 'schedule.json'}: {error!r}", file=sys.stderr)
        return 2
    h5 = window("5h", float(latest["h5"]), latest["h5_reset"], H5, None, samples, t)
    d7 = window("weekly", float(latest["d7"]), latest["d7_reset"], D7, schedule, samples, t)
    unit = "work-hour" if schedule else "h"
    print(f"sample: {(t - latest['ts']) / 60:.0f} min old")
    print(f"5h: {h5['used']:.0f}% used, pace allows {h5['allowed']:.1f}% (floor {H5_FLOOR:.0f}%); "
          f"resets {datetime.fromtimestamp(h5['reset']):%H:%M} ({h5['left'] / 3600:.1f} h left)")
    hours = f"{d7['elapsed'] / 3600:.1f} of {d7['total'] / 3600:.1f} {'work hours' if schedule else 'hours'}"
    print(f"weekly: {d7['used']:.0f}% used, pace allows {d7['allowed']:.1f}% ({hours}); "
          f"resets {datetime.fromtimestamp(d7['reset']):%m/%d %H:%M} ({d7['left'] / 3600:.1f} {'work hours' if schedule else 'h'} left)")
    if h5["rate"] and d7["rate"]:
        print(f"$1 API-equivalent = {h5['rate']:.2f}% of 5h, {d7['rate']:.2f}% of weekly "
              f"(from ${h5['cost']:.2f} and ${d7['cost']:.2f} logged; unlogged usage makes these high)")
    if usd is None:
        return 0
    if not (h5["rate"] and d7["rate"]):
        print("no conversion yet: too little logged cost in a window; judge the share yourself")
        return 0
    over = []
    for w in (h5, d7):
        w["est"] = usd * w["rate"]
        if w["est"] > w["allowed"] - w["used"]:
            over.append(w["name"])
    print(f"estimate ${usd:.2f}: 5h +{h5['est']:.1f}% -> {h5['used'] + h5['est']:.1f}%, "
          f"weekly +{d7['est']:.1f}% -> {d7['used'] + d7['est']:.1f}%")

    def pace(w, per):
        after = (100 - w["used"] - w["est"]) / (w["left"] / 3600) if w["left"] else 0.0
        so_far = w["used"] / (w["elapsed"] / 3600) if w["elapsed"] else 0.0
        return f"{after:.1f}%/{per} for {w['name']} (so far {so_far:.1f}%/{per})"

    print(f"after it, staying under the limit needs at most {pace(h5, 'h')} and {pace(d7, unit)}")
    print(f"verdict: ask (over pace: {', '.join(over)})" if over else "verdict: ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("record")
    checker = sub.add_parser("check")
    checker.add_argument("--usd", type=float, help="API-equivalent estimate of the planned work")
    args = parser.parse_args()
    if args.command == "record":
        record(sys.stdin.read())
        return 0
    return check(args.usd)


if __name__ == "__main__":
    sys.exit(main())
