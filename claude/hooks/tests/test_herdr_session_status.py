import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "herdr-session-status.py"
SETTINGS = Path(__file__).resolve().parents[2] / "settings.json"

# Stands in for herdr: logs each argv, answers `workspace get` from a fixture, fails on request.
FAKE_HERDR = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["FAKE_HERDR_LOG"], "a") as log:
    log.write(json.dumps(sys.argv[1:], ensure_ascii=False) + "\\n")
if sys.argv[1:3] == ["workspace", "get"]:
    print(json.dumps({"result": {"workspace": json.loads(os.environ["FAKE_HERDR_WORKSPACE"])}}))
sys.exit(int(os.environ.get("FAKE_HERDR_EXIT", "0")))
"""

REPLY = "PR を作成しました。\n\n目的: 状態表示 herdr ─ いま: レビュー待ち\nユーザーのタスク: PR の差分を見て、マージしてよいか返事をする"


def matcher_selects(matcher, value):
    """Apply the hooks matcher rules in https://code.claude.com/docs/en/hooks."""
    if matcher in (None, "", "*"):
        return True
    if re.fullmatch(r"[A-Za-z0-9_\- ,|]*", matcher):
        return value in {part.strip() for part in re.split(r"[|,]", matcher)}
    # Why not Python's re: matchers are JavaScript regular expressions, and some syntax differs.
    test = "process.exit(new RegExp(process.argv[1]).test(process.argv[2]) ? 0 : 1)"
    return subprocess.run(["node", "-e", test, "--", matcher, value]).returncode == 0


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

    def run_hook(self, reply=REPLY, label="dotfiles", tokens=None, pane_count=1, **payload):
        self.env["FAKE_HERDR_WORKSPACE"] = json.dumps(
            {"label": label, "pane_count": pane_count, "tokens": tokens or {}}
        )
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(
                {"hook_event_name": "Stop", "last_assistant_message": reply, "cwd": "/repos/dotfiles", **payload}
            ),
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def status(self, calls, target=("pane", "w1:p1")):
        """The status token values reported to the pane, or to another target, by name."""
        reports = [call for call in calls if (call[0], call[2]) == target and call[1] == "report-metadata"]
        call = next(call for call in reports if any(arg.startswith("task=") for arg in call))
        tokens = dict(arg.split("=", 1) for arg in call if "=" in arg)
        self.project = tokens.pop("project", None)
        return tokens

    def renames(self, calls):
        return [call for call in calls if call[:2] == ["workspace", "rename"]]

    def markers(self, calls):
        """The names each workspace report records as this hook's own."""
        reports = [call for call in calls if call[:2] == ["workspace", "report-metadata"]]
        tokens = [dict(arg.split("=", 1) for arg in call if "=" in arg) for call in reports]
        return [token for token in tokens if "autoname" in token]

    def test_reports_the_users_task_wrapped_to_the_sidebar(self) -> None:
        self.assertEqual(
            self.status(self.run_hook()),
            {
                "task": "PR の差分を見て、マージし",
                "task2": "てよいか返事をする",
                "task3": "",
                "now": "",
                "done": "",
            },
        )

    def test_keeps_the_rest_of_a_long_task_on_the_third_row(self) -> None:
        status = self.status(
            self.run_hook("目的: 状態表示 herdr ─ いま: 確認待ち\nユーザーのタスク: " + "あ" * 13 + "い" * 13 + "う" * 20)
        )

        self.assertEqual((status["task"], status["task2"], status["task3"]), ("あ" * 13, "い" * 13, "う" * 20))

    def test_keeps_a_combining_mark_on_the_row_of_its_base_character(self) -> None:
        status = self.status(
            self.run_hook("目的: 状態表示 herdr ─ いま: 確認待ち\nユーザーのタスク: " + "あ" * 12 + "か\u3099" + "い")
        )

        self.assertEqual((status["task"], status["task2"]), ("あ" * 12 + "か\u3099", "い"))

    def test_reports_the_next_step_when_nothing_is_asked_of_the_user(self) -> None:
        self.assertEqual(
            self.status(self.run_hook("目的: 状態表示 herdr ─ いま: CI の結果待ち\nユーザーのタスク: なし")),
            {"task": "", "task2": "", "task3": "", "now": "CI の結果待ち", "done": ""},
        )

    def test_marks_a_session_whose_goal_is_complete(self) -> None:
        status = self.status(self.run_hook("目的: 状態表示 herdr ─ いま: 完了（後片付け済み）\nユーザーのタスク: なし"))

        self.assertEqual((status["now"], status["done"]), ("完了（後片付け済み）", "✓"))

    def test_does_not_mark_a_complete_step_while_the_user_still_has_a_task(self) -> None:
        status = self.status(self.run_hook("目的: 状態表示 herdr ─ いま: 完了\nユーザーのタスク: PR をマージする"))

        self.assertEqual(status["done"], "")

    def test_reports_a_task_that_only_begins_with_the_reserved_word(self) -> None:
        status = self.status(self.run_hook("目的: 状態表示 herdr ─ いま: 設定待ち\nユーザーのタスク: なしに変更して保存する"))

        self.assertEqual(status["task"], "なしに変更して保存する")

    def test_reads_status_lines_wrapped_in_a_code_fence(self) -> None:
        status = self.status(self.run_hook("```\n目的: 状態表示 herdr ─ いま: 完了\nユーザーのタスク: なし\n```"))

        self.assertEqual(status["now"], "完了")

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

        cleared = {"task": "", "task2": "", "task3": "", "now": "", "done": ""}
        self.assertEqual((self.status(calls), self.status(calls, ("workspace", "w1"))), (cleared, cleared))
        self.assertEqual(len(calls), 2)

    def test_clears_the_previous_sessions_status_when_a_session_starts(self) -> None:
        calls = self.run_hook(hook_event_name="SessionStart", source="startup", last_assistant_message=None)

        cleared = {"task": "", "task2": "", "task3": "", "now": "", "done": ""}
        self.assertEqual((self.status(calls), self.status(calls, ("workspace", "w1"))), (cleared, cleared))
        self.assertEqual(len(calls), 2)

    def test_a_new_session_clears_the_status_through_the_hooks_settings_registers(self) -> None:
        hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
        for source in ("startup", "clear"):
            with self.subTest(source=source):
                wired = [hook["command"] for group in hooks.get("SessionStart", [])
                         if matcher_selects(group.get("matcher"), source)
                         for hook in group["hooks"] if SCRIPT.name in hook["command"]]
                self.assertEqual(len(wired), 1)
                with tempfile.TemporaryDirectory() as home:
                    (Path(home) / ".claude").mkdir()
                    (Path(home) / ".claude" / "hooks").symlink_to(SCRIPT.parent)
                    subprocess.run(["bash", "-c", wired[0]], env={**self.env, "HOME": home}, check=True,
                                   input=json.dumps({"hook_event_name": "SessionStart", "source": source}),
                                   text=True, capture_output=True, timeout=10)
                calls = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
                cleared = {"task": "", "task2": "", "task3": "", "now": "", "done": ""}
                self.assertEqual(self.status(calls), cleared)
                self.log.unlink()

    def test_reports_the_same_status_to_the_workspace(self) -> None:
        calls = self.run_hook()

        self.assertEqual(self.status(calls, ("workspace", "w1")), self.status(calls))

    def git(self, *args):
        identity = ("-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false")
        subprocess.run(["git", *identity, *args], check=True, capture_output=True)

    def test_reports_the_repository_name_as_the_project(self) -> None:
        repo = Path(self.env["FAKE_HERDR_LOG"]).parent / "my-repo"
        self.git("init", "-q", str(repo))
        (repo / "src").mkdir()

        self.status(self.run_hook(cwd=str(repo / "src")))

        self.assertEqual(self.project, "my-repo")

    def test_reports_the_main_repository_name_from_a_worktree(self) -> None:
        root = Path(self.env["FAKE_HERDR_LOG"]).parent
        self.git("init", "-q", str(root / "my-repo"))
        self.git("-C", str(root / "my-repo"), "commit", "-q", "--allow-empty", "-m", "init")
        self.git("-C", str(root / "my-repo"), "worktree", "add", "-q", str(root / "topic-branch"))

        self.status(self.run_hook(cwd=str(root / "topic-branch")))

        self.assertEqual(self.project, "my-repo")

    def test_reports_the_directory_name_as_the_project_outside_a_repository(self) -> None:
        plain = Path(self.env["FAKE_HERDR_LOG"]).parent / "notes"
        plain.mkdir()

        self.status(self.run_hook(cwd=str(plain)))

        self.assertEqual(self.project, "notes")

    def test_reports_the_project_when_the_user_sends_a_prompt(self) -> None:
        self.status(self.run_hook(hook_event_name="UserPromptSubmit", last_assistant_message=None))

        self.assertEqual(self.project, "dotfiles")

    def test_names_a_workspace_that_still_has_its_default_label(self) -> None:
        calls = self.run_hook(label="dotfiles")

        self.assertEqual(self.renames(calls), [["workspace", "rename", "w1", "状態表示 herdr"]])
        self.assertEqual(self.markers(calls), [{"autoname": "状態表示 herdr", "autoname_prev": "dotfiles"}])

    def test_records_its_names_before_it_renames(self) -> None:
        """A rename that fails after the record leaves a label the next stop still recognises."""
        kinds = [call[1] for call in self.run_hook(label="dotfiles") if call[0] == "workspace"]

        self.assertEqual(kinds[-3:], ["get", "report-metadata", "rename"])

    def test_renames_a_workspace_whose_last_rename_failed(self) -> None:
        calls = self.run_hook(label="古い名前", tokens={"autoname": "届かなかった名前", "autoname_prev": "古い名前"})

        self.assertEqual(self.renames(calls), [["workspace", "rename", "w1", "状態表示 herdr"]])

    def test_renames_a_workspace_it_named_before(self) -> None:
        calls = self.run_hook(label="古い名前", tokens={"autoname": "古い名前"})

        self.assertEqual(self.renames(calls), [["workspace", "rename", "w1", "状態表示 herdr"]])

    def test_does_not_adopt_a_typed_label_that_equals_the_goal(self) -> None:
        calls = self.run_hook(label="状態表示 herdr", tokens={})

        self.assertEqual((self.renames(calls), self.markers(calls)), ([], []))

    def test_keeps_a_label_the_user_typed(self) -> None:
        calls = self.run_hook(label="11/27 以降マージ", tokens={"autoname": "古い名前"})

        self.assertEqual((self.renames(calls), self.markers(calls)), ([], []))

    def test_keeps_the_label_of_a_workspace_with_several_panes(self) -> None:
        self.assertEqual(self.renames(self.run_hook(pane_count=2)), [])

    def test_does_not_rename_to_the_label_it_already_has(self) -> None:
        calls = self.run_hook(label="状態表示 herdr", tokens={"autoname": "状態表示 herdr"})

        self.assertEqual(self.renames(calls), [])

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
