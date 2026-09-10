import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/loop-snapshot.py"
SPEC = importlib.util.spec_from_file_location("loop_snapshot", SCRIPT)
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)

REPO = "example/dotfiles"
HEAD = "a" * 40


def issue(number: int = 1) -> dict:
    return {
        "number": number,
        "title": "Fix the failing test",
        "url": f"https://github.com/{REPO}/issues/{number}",
        "labels": [{"name": "priority:P1"}, {"name": "agent:claude"}],
        "assignees": [],
        "updatedAt": "2026-09-10T00:00:00Z",
    }


def pull_request() -> dict:
    return {
        "number": 2,
        "title": "Fix the failing test",
        "url": f"https://github.com/{REPO}/pull/2",
        "headRefName": "fix/issue-1",
        "isDraft": True,
        "mergeable": "UNKNOWN",
        "reviewDecision": "",
        "statusCheckRollup": None,
        "updatedAt": "2026-09-10T00:00:00Z",
    }


class SnapshotTests(unittest.TestCase):
    def run_snapshot(
        self, issues: object = None, prs: object = None,
        failures: dict | None = None,
    ) -> tuple:
        outputs = {
            "origin": "git@github.com:example/dotfiles.git\n",
            "head": HEAD + "\n",
            "dirty": "",
            "issues": json.dumps([] if issues is None else issues),
            "pull_requests": json.dumps([] if prs is None else prs),
        }
        outputs.update(failures or {})
        commands = []

        def execute(command: list[str], directory: Path) -> str:
            commands.append(command)
            if command[:2] == ["gh", "issue"]:
                name = "issues"
            elif command[:2] == ["gh", "pr"]:
                name = "pull_requests"
            elif "get-url" in command:
                name = "origin"
            elif "rev-parse" in command:
                name = "head"
            else:
                name = "dirty"
            value = outputs[name]
            if isinstance(value, Exception):
                raise value
            return value

        with patch.object(snapshot, "execute", side_effect=execute):
            result = snapshot.collect(REPO, Path.cwd())
        return result, commands

    def test_successful_empty_lists_are_complete(self) -> None:
        result, commands = self.run_snapshot()
        self.assertTrue(result["complete"])
        self.assertEqual(result["sources"]["issues"]["items"], [])
        self.assertEqual(result["sources"]["pull_requests"]["items"], [])
        self.assertEqual(len(commands), 5)

    def test_failed_source_is_not_reported_as_empty(self) -> None:
        failure = snapshot.CollectionError("command_failed")
        result, _ = self.run_snapshot(failures={"issues": failure})
        self.assertFalse(result["complete"])
        source = result["sources"]["issues"]
        self.assertEqual(source["status"], "unavailable")
        self.assertNotIn("items", source)
        self.assertEqual(result["sources"]["pull_requests"]["status"], "ok")

    def test_bad_json_and_schema_are_not_empty_results(self) -> None:
        for value in ["not json", "null", "{}", "[null]", "[{}]"]:
            with self.subTest(value=value):
                result, _ = self.run_snapshot(failures={"issues": value})
                self.assertFalse(result["complete"])
                self.assertNotIn("items", result["sources"]["issues"])

    def test_exact_limit_is_known_complete_but_extra_item_marks_partial(self) -> None:
        for count, complete in [(50, True), (51, False)]:
            with self.subTest(count=count):
                result, _ = self.run_snapshot(
                    issues=[issue(n + 1) for n in range(count)],
                )
                self.assertEqual(result["complete"], complete)
                self.assertEqual(len(result["sources"]["issues"]["items"]), 50)
                self.assertEqual(result["sources"]["issues"]["truncated"], not complete)

    def test_dirty_paths_and_unrequested_github_fields_are_not_echoed(self) -> None:
        item = issue()
        item.update(body="PRIVATE CONTENT", comments=[{"body": "PRIVATE COMMENT"}])
        result, _ = self.run_snapshot(
            issues=[item], failures={"dirty": " M private-name\n"},
        )
        encoded = json.dumps(result)
        self.assertNotIn("PRIVATE", encoded)
        self.assertNotIn("private-name", encoded)
        self.assertTrue(result["sources"]["local"]["dirty"])
        self.assertEqual(
            result["sources"]["issues"]["items"][0]["labels"],
            ["priority:P1", "agent:claude"],
        )

    def test_unknown_checks_and_mergeability_stay_unknown(self) -> None:
        result, _ = self.run_snapshot(prs=[pull_request()])
        item = result["sources"]["pull_requests"]["items"][0]
        self.assertIsNone(item["checks"])
        self.assertEqual(item["mergeable"], "UNKNOWN")
        self.assertNotIn("ready", item)

    def test_check_statuses_are_preserved_without_logs(self) -> None:
        pr = pull_request()
        pr["statusCheckRollup"] = [
            {"__typename": "CheckRun", "name": "test", "status": "COMPLETED",
             "conclusion": "FAILURE", "detailsUrl": "https://example.com/check",
             "output": "DO NOT COPY"},
            {"__typename": "StatusContext", "context": "legacy", "state": "PENDING",
             "targetUrl": "https://example.com/status"},
        ]
        result, _ = self.run_snapshot(prs=[pr])
        checks = result["sources"]["pull_requests"]["items"][0]["checks"]
        self.assertEqual(checks[0]["conclusion"], "FAILURE")
        self.assertEqual(checks[1]["state"], "PENDING")
        self.assertNotIn("DO NOT COPY", json.dumps(result))

    def test_repository_mismatch_stops_before_github(self) -> None:
        result, commands = self.run_snapshot(
            failures={"origin": "https://github.com/other/repo.git"},
        )
        self.assertFalse(result["complete"])
        self.assertEqual(result["sources"]["local"]["error"], "repository_mismatch")
        self.assertFalse(any(command[0] == "gh" for command in commands))

    def test_standard_github_origin_formats_are_accepted(self) -> None:
        for origin in [
            f"git@github.com:{REPO}.git",
            f"https://github.com/{REPO}",
            f"https://github.com/{REPO}.git",
            f"ssh://git@github.com/{REPO}.git",
        ]:
            with self.subTest(origin=origin):
                result, _ = self.run_snapshot(failures={"origin": origin})
                self.assertTrue(result["complete"])

    def test_null_check_conclusion_remains_unknown(self) -> None:
        pr = pull_request()
        pr["statusCheckRollup"] = [
            {"__typename": "CheckRun", "name": "test", "status": "IN_PROGRESS",
             "conclusion": None, "detailsUrl": None},
        ]
        result, _ = self.run_snapshot(prs=[pr])
        self.assertTrue(result["complete"])
        check = result["sources"]["pull_requests"]["items"][0]["checks"][0]
        self.assertIsNone(check["conclusion"])

    def test_null_review_decision_remains_unknown(self) -> None:
        pr = pull_request()
        pr["reviewDecision"] = None
        result, _ = self.run_snapshot(prs=[pr])
        self.assertTrue(result["complete"])
        self.assertIsNone(
            result["sources"]["pull_requests"]["items"][0]["reviewDecision"],
        )

    def test_truncated_check_list_makes_packet_incomplete(self) -> None:
        pr = pull_request()
        pr["statusCheckRollup"] = [
            {"__typename": "CheckRun", "name": "test", "status": "COMPLETED",
             "conclusion": "SUCCESS", "detailsUrl": None},
        ] * 21
        result, _ = self.run_snapshot(prs=[pr])
        self.assertFalse(result["complete"])
        self.assertTrue(
            result["sources"]["pull_requests"]["items"][0]["checks_truncated"],
        )

    def test_invalid_head_is_not_accepted_as_evidence(self) -> None:
        result, _ = self.run_snapshot(failures={"head": "unexpected"})
        self.assertFalse(result["complete"])
        self.assertNotIn("head", result["sources"]["local"])

    def test_commands_are_fixed_read_only_calls(self) -> None:
        result, commands = self.run_snapshot(issues=[issue()])
        self.assertTrue(result["complete"])
        self.assertEqual(commands[:3], [
            ["git", "--no-optional-locks", "remote", "get-url", "origin"],
            ["git", "--no-optional-locks", "rev-parse", "HEAD"],
            ["git", "--no-optional-locks", "status",
             "--porcelain=v1", "--untracked-files=normal"],
        ])
        for command in commands[3:]:
            self.assertIn(
                command[:3], [["gh", "issue", "list"], ["gh", "pr", "list"]],
            )
            self.assertIn("51", command)
            self.assertIn(REPO, command)
            self.assertNotIn("--paginate", command)

    def test_repository_argument_rejects_non_github_targets(self) -> None:
        for value in ["https://host/a/b", "../repo", "-x/repo", "a/b/c", "a/b;evil"]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    snapshot.validate_repository(value)

    def test_cli_exit_code_matches_collection_completeness(self) -> None:
        for complete, status in [(True, 0), (False, 1)]:
            output = io.StringIO()
            with patch.object(sys, "argv", [str(SCRIPT), "--repo", REPO]), \
                    patch.object(snapshot, "collect", return_value={"complete": complete}), \
                    redirect_stdout(output):
                self.assertEqual(snapshot.main(), status)
            self.assertEqual(json.loads(output.getvalue()), {"complete": complete})


class ProcessTests(unittest.TestCase):
    def test_child_input_is_closed_and_prompt_flags_are_set(self) -> None:
        code = (
            "import json, os, sys; print(json.dumps([sys.stdin.read(), "
            "os.environ['GH_PROMPT_DISABLED'], os.environ['GIT_TERMINAL_PROMPT']]))"
        )
        result = snapshot.execute([sys.executable, "-B", "-c", code], Path.cwd())
        self.assertEqual(json.loads(result), ["", "1", "0"])

    def test_missing_command_has_no_raw_error_text(self) -> None:
        with self.assertRaises(snapshot.CollectionError) as caught:
            snapshot.execute(["/nonexistent-loop-snapshot-command"], Path.cwd())
        self.assertEqual(str(caught.exception), "missing_command")

    def test_nonzero_command_redacts_stderr(self) -> None:
        with self.assertRaises(snapshot.CollectionError) as caught:
            snapshot.execute(["sh", "-c", "echo PRIVATE >&2; exit 1"], Path.cwd())
        self.assertEqual(str(caught.exception), "command_failed")

    def test_timeout_is_bounded_and_noninteractive(self) -> None:
        with patch.object(snapshot, "COMMAND_TIMEOUT", 0.05):
            with self.assertRaises(snapshot.CollectionError) as caught:
                snapshot.execute(["sleep", "5"], Path.cwd())
        self.assertEqual(str(caught.exception), "timeout")


if __name__ == "__main__":
    unittest.main()
