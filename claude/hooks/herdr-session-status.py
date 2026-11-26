#!/usr/bin/env python3
"""Claude Code hook: show a session's goal and the user's task in the herdr sidebar.

On Stop, reads the two status lines that end a reply, reports them to the session's herdr pane
and workspace, and names the workspace after the goal. On UserPromptSubmit, clears the status, since the user
has just acted; on SessionStart, clears what the previous session in the pane left.
Try it: echo '{"last_assistant_message": "目的: x ─ いま: y\\nユーザーのタスク: なし"}' | python3 herdr-session-status.py
"""

import json
import os
import re
import subprocess
import sys
import unicodedata

SOURCE = "claude:session-status"
GOAL = re.compile(r"^目的[:：]\s*(.+?)\s+[─—–-]\s+いま[:：]\s*(.+)$")
TASK = re.compile(r"^ユーザーのタスク[:：]\s*(.+)$")
# A Spaces status row holds this many columns at the sidebar width .config/herdr/config.toml pins.
ROW_COLUMNS = 26


def herdr(*args):
    result = subprocess.run(
        [os.environ.get("HERDR_BIN_PATH", "herdr"), *args],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    return json.loads(result.stdout)["result"] if result.stdout.strip() else {}


def report(pane, **tokens):
    # An empty value clears the token, and herdr drops a sidebar row that has no value.
    args = [arg for name, value in tokens.items() for arg in ("--token", f"{name}={value}")]
    # The workspace shows the status in the Spaces panel; the pane copy feeds the agent picker.
    # shortcut: agents sharing a workspace overwrite each other there, report per pane rows if that hurts
    targets = [("pane", pane), ("workspace", os.environ.get("HERDR_WORKSPACE_ID"))]
    for kind, target in targets:
        if target:
            herdr(kind, "report-metadata", target, "--source", SOURCE, *args)


def project(cwd):
    """The repository's name, also from one of its worktrees; the directory name outside git."""
    command = ["git", "-C", cwd, "rev-parse", "--path-format=absolute", "--git-common-dir"]
    common = subprocess.run(command, capture_output=True, text=True, timeout=3).stdout.strip()
    # A worktree's own directory is named after its branch, so the shared .git locates the repo.
    # shortcut: a submodule or a bare repository's worktree shows its directory name, read --show-toplevel if they come up
    return os.path.basename(os.path.dirname(common) if os.path.basename(common) == ".git" else cwd)


def sidebar_rows(text):
    """Wrap to three sidebar rows; the last keeps the rest, which herdr truncates."""
    rows, start, columns = [], 0, 0
    for index, char in enumerate(text):
        # shortcut: an emoji joined by ZWJ can split across rows, upgrade to grapheme clusters if tasks carry them
        wide = unicodedata.east_asian_width(char) in "WF"
        width = 0 if unicodedata.combining(char) else 2 if wide else 1
        if columns + width > ROW_COLUMNS and len(rows) < 2:
            rows.append(text[start:index])
            start, columns = index, 0
        columns += width
    rows.append(text[start:])
    return rows + [""] * (3 - len(rows))


def name_workspace(workspace, name, cwd):
    info = herdr("workspace", "get", workspace)["workspace"]
    label, tokens = info["label"], info.get("tokens") or {}
    # herdr does not record who set a label. Only its default, the directory name, and the
    # names this hook recorded as its own are replaced; any other label is one the user typed.
    own = (os.path.basename(cwd), tokens.get("autoname"), tokens.get("autoname_prev"))
    if info["pane_count"] != 1 or label not in own or label == name:
        return
    # Recorded before the rename, with the label being replaced: if either call then fails,
    # the label is still one of the recorded names and the next stop can finish the job.
    marker = ("--token", f"autoname={name}", "--token", f"autoname_prev={label}")
    herdr("workspace", "report-metadata", workspace, "--source", SOURCE, *marker)
    herdr("workspace", "rename", workspace, name)


def main():
    data = json.load(sys.stdin)
    pane = os.environ.get("HERDR_PANE_ID")
    if os.environ.get("HERDR_ENV") != "1" or not pane or data.get("agent_id"):
        return
    cwd = data.get("cwd") or ""
    if data.get("hook_event_name") in ("UserPromptSubmit", "SessionStart"):
        report(pane, project=project(cwd), task="", task2="", task3="", now="", done="")
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
        # Not 完了 anywhere in いま: "#1 完了、#2 は未着手" is partial; claude/CLAUDE.md leads with 完了 only when done.
        done = "✓" if step.startswith("完了") else ""
        report(pane, project=project(cwd), task="", task2="", task3="", now=step, done=done)
    else:
        first, second, third = sidebar_rows(task)
        report(pane, project=project(cwd), task=first, task2=second, task3=third, now="", done="")
    if workspace := os.environ.get("HERDR_WORKSPACE_ID"):
        name_workspace(workspace, name, cwd)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Not re-raised: a sidebar label must never block or fail a turn.
        pass
