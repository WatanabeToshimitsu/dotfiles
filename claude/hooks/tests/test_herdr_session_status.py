import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "herdr-session-status.py"

# Stands in for herdr: logs each argv, and fails when the test asks it to.
FAKE_HERDR = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_HERDR_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:], ensure_ascii=False) + "\\n")
sys.exit(int(os.environ.get("FAKE_HERDR_EXIT", "0")))
"""

REPLY = "PR を作成しました。\n\n目的: 状態表示 herdr ─ いま: レビュー待ち\nユーザーのタスク: PR の差分を確認する"


class HerdrSessionStatusTest(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        herdr = Path(temp.name) / "herdr"
        herdr.write_text(FAKE_HERDR, encoding="utf-8")
        herdr.chmod(herdr.stat().st_mode | stat.S_IXUSR)
        self.log = Path(temp.name) / "calls.jsonl"
        self.env = {
            **os.environ,
            "HERDR_ENV": "1",
            "HERDR_PANE_ID": "w1:p1",
            "HERDR_WORKSPACE_ID": "w1",
            "HERDR_BIN_PATH": str(herdr),
            "FAKE_HERDR_LOG": str(self.log),
        }

    def run_hook(self, reply=REPLY, **payload):
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps({"hook_event_name": "Stop", "last_assistant_message": reply, **payload}),
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def pane_report(self, calls):
        return next(call for call in calls if call[:3] == ["pane", "report-metadata", "w1:p1"])

    def test_reports_the_name_and_the_users_task_and_clears_the_next_step(self) -> None:
        call = self.pane_report(self.run_hook())

        self.assertIn("name=状態表示 herdr", call)
        self.assertIn("task=PR の差分を確認する", call)
        self.assertEqual(call[call.index("--clear-token") + 1], "now")

    def test_reports_the_next_step_when_nothing_is_asked_of_the_user(self) -> None:
        call = self.pane_report(self.run_hook("目的: 状態表示 herdr ─ いま: CI の結果待ち\nユーザーのタスク: なし"))

        self.assertIn("now=CI の結果待ち", call)
        self.assertEqual(call[call.index("--clear-token") + 1], "task")

    def test_reports_a_task_that_only_begins_with_the_reserved_word(self) -> None:
        call = self.pane_report(self.run_hook("目的: 状態表示 herdr ─ いま: 設定待ち\nユーザーのタスク: なしに変更して保存する"))

        self.assertIn("task=なしに変更して保存する", call)

    def test_reports_the_name_to_the_workspace(self) -> None:
        calls = self.run_hook()

        self.assertIn(
            ["workspace", "report-metadata", "w1", "--source", "claude:session-status", "--token", "name=状態表示 herdr"],
            calls,
        )

    def test_reads_status_lines_wrapped_in_a_code_fence(self) -> None:
        call = self.pane_report(self.run_hook("```\n目的: 状態表示 herdr ─ いま: 完了\nユーザーのタスク: なし\n```"))

        self.assertIn("now=完了", call)

    def test_keeps_the_previous_status_when_the_reply_has_no_status_lines(self) -> None:
        self.assertEqual(self.run_hook("了解です。"), [])

    def test_keeps_the_previous_status_when_only_one_status_line_is_present(self) -> None:
        self.assertEqual(self.run_hook("目的: 状態表示 herdr ─ いま: レビュー待ち"), [])

    def test_keeps_the_previous_status_when_a_blank_line_separates_the_status_lines(self) -> None:
        self.assertEqual(self.run_hook("目的: 状態表示 herdr ─ いま: レビュー待ち\n\nユーザーのタスク: なし"), [])

    def test_keeps_the_previous_status_when_text_follows_the_status_lines(self) -> None:
        self.assertEqual(self.run_hook(REPLY + "\n\n上の 2 行は例です。"), [])

    def test_clears_the_status_when_the_user_sends_a_prompt(self) -> None:
        calls = self.run_hook(hook_event_name="UserPromptSubmit", last_assistant_message=None)

        self.assertEqual(
            calls,
            [
                [
                    "pane",
                    "report-metadata",
                    "w1:p1",
                    "--source",
                    "claude:session-status",
                    "--clear-token",
                    "task",
                    "--clear-token",
                    "now",
                ]
            ],
        )

    def test_does_nothing_outside_herdr(self) -> None:
        del self.env["HERDR_ENV"]

        self.assertEqual(self.run_hook(), [])

    def test_does_nothing_when_a_subagent_stops(self) -> None:
        self.assertEqual(self.run_hook(agent_id="agent-1"), [])

    def test_a_failing_herdr_does_not_fail_the_stop(self) -> None:
        self.env["FAKE_HERDR_EXIT"] = "1"

        self.run_hook()


if __name__ == "__main__":
    unittest.main()
