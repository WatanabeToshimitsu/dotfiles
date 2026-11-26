#!/usr/bin/env python3
"""Replay past Bash commands through two versions of the Bash guards and count changed decisions.

Commands come from Claude Code transcripts. Only counts reach stdout; the
commands themselves go to a JSONL file outside the repository.
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
HOOK_FILES = ["validate-bash.sh", "remote-mutation-guard.py", "_shell_parser.py"]
HOOKS = {
    "validate-bash": ["bash", "{dir}/validate-bash.sh"],
    "remote-mutation-guard": [sys.executable, "{dir}/remote-mutation-guard.py", "--client", "claude"],
}


def hook_dir(version, target):
    """A directory holding the guards: the path itself, or the files at a git ref."""
    if Path(version).is_dir():
        return str(Path(version).resolve())
    target.mkdir()
    for name in HOOK_FILES:
        shown = subprocess.run(["git", "-C", str(ROOT), "show", f"{version}:claude/hooks/{name}"],
                               capture_output=True)
        if shown.returncode == 0:
            (target / name).write_bytes(shown.stdout)
    if not any(target.iterdir()):
        raise SystemExit(f"no guards at {version}")
    return str(target)


def commands(transcripts, since_days):
    cutoff = time.time() - since_days * 86400
    seen = set()
    for path in sorted(Path(transcripts).rglob("*.jsonl")):
        if path.stat().st_mtime < cutoff:
            continue
        with path.open(encoding="utf-8", errors="replace") as lines:
            for line in lines:
                if '"Bash"' not in line:
                    continue
                try:
                    content = (json.loads(line).get("message") or {}).get("content")
                except ValueError:
                    continue
                for item in content if isinstance(content, list) else []:
                    if not (isinstance(item, dict) and item.get("type") == "tool_use"
                            and item.get("name") == "Bash" and isinstance(item.get("input"), dict)):
                        continue
                    command = item["input"].get("command")
                    if isinstance(command, str) and command not in seen:
                        seen.add(command)
                        yield command


def decision(argv, command, cwd):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}, "cwd": cwd})
    try:
        result = subprocess.run(argv, input=payload, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return "timeout"
    if result.returncode:
        return "error"
    if not result.stdout.strip():
        return "allow"
    try:
        return json.loads(result.stdout)["hookSpecificOutput"].get("permissionDecision", "allow")
    except (ValueError, KeyError):
        return "unparsed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, help="git ref or directory with the old guards")
    parser.add_argument("--after", default=str(ROOT / "claude" / "hooks"),
                        help="git ref or directory with the new guards (default: working tree)")
    parser.add_argument("--transcripts", default=str(Path.home() / ".claude" / "projects"))
    parser.add_argument("--since", type=float, default=14, help="days of transcripts to read")
    parser.add_argument("--limit", type=int, default=0, help="replay at most this many commands")
    parser.add_argument("--out", help="JSONL file for changed commands (default: a new temp file)")
    args = parser.parse_args()

    out = Path(args.out or tempfile.mkstemp(prefix="hook-replay-", suffix=".jsonl")[1]).resolve()
    if out.is_relative_to(ROOT):
        parser.error("--out must be outside the repository; it holds transcript commands")
    found = list(commands(args.transcripts, args.since))
    if args.limit:
        found = found[:args.limit]

    with tempfile.TemporaryDirectory() as workspace:
        cwd = os.path.join(workspace, "cwd")
        os.mkdir(cwd)
        versions = {side: hook_dir(version, Path(workspace) / side)
                    for side, version in (("before", args.before), ("after", args.after))}
        jobs = [(command, hook, side) for command in found for hook in HOOKS for side in versions]

        def run(job):
            command, hook, side = job
            argv = [part.format(dir=versions[side]) for part in HOOKS[hook]]
            return job, decision(argv, command, cwd)

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as pool:
            results = dict(pool.map(run, jobs))

    changes = Counter()
    with out.open("w", encoding="utf-8") as details:
        for command in found:
            for hook in HOOKS:
                before, after = results[command, hook, "before"], results[command, hook, "after"]
                if before != after:
                    changes[f"{hook}: {before} -> {after}"] += 1
                    details.write(json.dumps({"hook": hook, "before": before, "after": after,
                                              "command": command}, ensure_ascii=False) + "\n")
    print(f"commands replayed: {len(found)}")
    for hook in HOOKS:
        for side in ("before", "after"):
            tally = Counter(results[command, hook, side] for command in found)
            print(f"  {hook} {side}: " + ", ".join(f"{name} {count}" for name, count in sorted(tally.items())))
    print(f"changed decisions: {sum(changes.values())}")
    for change, count in sorted(changes.items()):
        print(f"  {change}: {count}")
    print(f"details: {out}")


if __name__ == "__main__":
    main()
