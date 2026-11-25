#!/usr/bin/env python3
"""Claude Code hook: show a session's goal and the user's task in the herdr sidebar.

On Stop, reads the two status lines that end a reply and reports them to the session's herdr pane.
On UserPromptSubmit, clears the task and the next step, since the user has just acted.
Try it: echo '{"last_assistant_message": "目的: x ─ いま: y\\nユーザーのタスク: なし"}' | python3 herdr-session-status.py
"""

import json
import os
import re
import subprocess
import sys

SOURCE = "claude:session-status"
GOAL = re.compile(r"^目的[:：]\s*(.+?)\s+[─—–-]\s+いま[:：]\s*(.+)$")
TASK = re.compile(r"^ユーザーのタスク[:：]\s*(.+)$")


def report(kind, target, *tokens):
    subprocess.run(
        [os.environ.get("HERDR_BIN_PATH", "herdr"), kind, "report-metadata", target, "--source", SOURCE, *tokens],
        capture_output=True,
        timeout=3,
        check=True,
    )


def main():
    data = json.load(sys.stdin)
    pane = os.environ.get("HERDR_PANE_ID")
    if os.environ.get("HERDR_ENV") != "1" or not pane or data.get("agent_id"):
        return
    if data.get("hook_event_name") == "UserPromptSubmit":
        report("pane", pane, "--clear-token", "task", "--clear-token", "now")
        return

    lines = [line.strip() for line in (data.get("last_assistant_message") or "").rstrip().splitlines()]
    if lines and lines[-1].startswith("```"):
        lines.pop()
    # Only the reply's last two lines count: the same lines quoted mid-reply are an example.
    goal, task = (GOAL.match(lines[-2]), TASK.match(lines[-1])) if len(lines) > 1 else (None, None)
    if not (goal and task):
        return
    name, step, task = goal.group(1).strip(), goal.group(2).strip(), task.group(1).strip()

    if task.rstrip("。") == "なし":
        status = ["--clear-token", "task", "--token", f"now={step}"]
    else:
        status = ["--token", f"task={task}", "--clear-token", "now"]
    report("pane", pane, "--token", f"name={name}", *status)
    # The workspace label is left alone: herdr does not record who set it, so a rename
    # could overwrite a name the user typed. The name goes out as a display token instead.
    if workspace := os.environ.get("HERDR_WORKSPACE_ID"):
        report("workspace", workspace, "--token", f"name={name}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Not re-raised: a sidebar label must never block or fail a turn.
        pass
