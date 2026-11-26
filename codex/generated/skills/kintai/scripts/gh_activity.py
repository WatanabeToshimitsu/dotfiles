#!/usr/bin/env python3
"""Print GitHub work evidence per JST day: PRs the user opened, and their reviews or comments on others' PRs.

Usage: gh_activity.py START END   (inclusive YYYY-MM-DD dates)
Output: tab-separated date, kind, PR, title; repositories under the user's own account are left out.
"""
import datetime as dt
import json
import subprocess
import sys

JST = dt.timezone(dt.timedelta(hours=9))
LIMIT = 1000


def gh(*args):
    # gh prints a hint on stderr for every PR it reads, so stderr is shown only when a call fails.
    done = subprocess.run(["gh", *args], capture_output=True, text=True)
    if done.returncode:
        sys.exit(f"gh {' '.join(args)} failed: {done.stderr.strip()}")
    return json.loads(done.stdout)


def day(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(JST).date().isoformat()


def rows(me, start, end, authored, activity):
    out = set()
    for p in authored:
        repo = p["repository"]["nameWithOwner"]
        if not repo.startswith(me + "/") and start <= day(p["createdAt"]) <= end:
            out.add((day(p["createdAt"]), "PR", f"{repo}#{p['number']}", p["title"]))
    for ts, p in activity:
        repo = p["repository"]["nameWithOwner"]
        if not repo.startswith(me + "/") and start <= day(ts) <= end:
            out.add((day(ts), "REVIEW", f"{repo}#{p['number']} ({p['author']['login']})", p["title"]))
    return sorted(out)


def search(*qualifiers):
    found = gh("search", "prs", *qualifiers, "--json", "repository,number,title,author,createdAt", "--limit", str(LIMIT))
    if len(found) >= LIMIT:
        sys.exit(f"gh search returned {LIMIT} results, its maximum; use a shorter range")
    return found


def main(start, end):
    me = gh("api", "user")["login"]
    authored = search("--author=@me", f"--created={start}T00:00:00+09:00..{end}T23:59:59+09:00")
    others = {}
    # Reviews of PRs updated after END still count, so the update range stays open-ended.
    for flag in ("--reviewed-by=@me", "--commenter=@me"):
        for p in search(flag, f"--updated=>={start}T00:00:00+09:00"):
            if p["author"]["login"] != me:
                others[(p["repository"]["nameWithOwner"], p["number"])] = p
    activity = []
    for (repo, number), p in others.items():
        for path, key in (("pulls/{}/reviews", "submitted_at"), ("pulls/{}/comments", "created_at"), ("issues/{}/comments", "created_at")):
            for page in gh("api", "--paginate", "--slurp", f"repos/{repo}/" + path.format(number)):
                activity += [(it[key], p) for it in page if (it.get("user") or {}).get("login") == me and it.get(key)]
    for row in rows(me, start, end, authored, activity):
        print("\t".join(row))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    start, end = (dt.date.fromisoformat(a) for a in sys.argv[1:])
    if start > end:
        sys.exit(__doc__)
    main(start.isoformat(), end.isoformat())
