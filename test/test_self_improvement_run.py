import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/self-improvement-run.py"
SPEC = importlib.util.spec_from_file_location("improvement", SCRIPT)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def wait_for(path, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.02)
    raise AssertionError(f"file was not created: {path.name}")


class CodexProtocolTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sent = []
        self.account = {"account": {"type": "chatgpt", "email": "private@example.invalid"}}
        self.limits = {"ordinaryUsageAllowed": True, "rateLimits": {
            "credits": {"hasCredits": False, "unlimited": False},
            "spendControlReached": False, "rateLimitReachedType": None,
        }}
        self.thread = {"thread": {"id": "thread-1"}, "model": "gpt-6-astra",
                       "modelProvider": "openai", "sandbox": {"type": "readOnly", "networkAccess": False}}

    def run_protocol(self, events=None, before_thread=()):
        replies = [
            {"id": 1, "result": {}}, {"id": 2, "result": self.account},
            {"id": 3, "result": self.limits}, *before_thread,
            {"id": 4, "result": self.thread},
            {"id": 5, "result": {"turn": {"id": "turn-1"}}},
        ]
        replies += events if events is not None else [
            {"method": "item/completed", "params": {
                "threadId": "thread-1", "turnId": "turn-1",
                "item": {"type": "agentMessage", "phase": "final_answer",
                         "text": '{"edits": []}'},
            }},
            {"method": "turn/completed", "params": {
                "threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed"},
            }},
        ]
        stream = iter(replies)
        protocol = runner.CodexProtocol(lambda: next(stream), self.sent.append, self.root)
        return protocol.run("gpt-6-astra", "Complete scoped packet")

    def test_subscription_metadata_and_one_matching_turn_produce_proposal(self):
        result = self.run_protocol()

        self.assertEqual(result["model_metadata"], {"model": "gpt-6-astra",
            "provider": "openai", "source": "thread/start"})
        self.assertEqual(result["result"], '{"edits": []}')
        self.assertEqual(sum(m.get("method") == "turn/start" for m in self.sent), 1)
        self.assertNotIn("private@example.invalid", "".join(
            p.read_text() for p in self.root.iterdir() if p.is_file()
        ))

    def test_unknown_or_paid_usage_stops_before_turn(self):
        for mutate in ("unknown", "credits", "api_key"):
            with self.subTest(mutate=mutate):
                if mutate == "unknown":
                    self.limits["ordinaryUsageAllowed"] = None
                elif mutate == "credits":
                    self.limits["ordinaryUsageAllowed"] = True
                    self.limits["rateLimits"]["credits"]["hasCredits"] = True
                else:
                    self.account["account"]["type"] = "apiKey"
                with self.assertRaises(runner.ProposalStopped):
                    self.run_protocol()
                self.assertFalse(any(m.get("method") == "turn/start" for m in self.sent))

    def test_wrong_effective_model_provider_or_sandbox_stops_before_turn(self):
        for key, value in (("model", "unknown"), ("modelProvider", "other"),
                           ("sandbox", {"type": "workspace-write"})):
            with self.subTest(key=key):
                original = self.thread[key]
                self.thread[key] = value
                with self.assertRaises(runner.ProposalStopped):
                    self.run_protocol()
                self.assertFalse(any(m.get("method") == "turn/start" for m in self.sent))
                self.thread[key] = original

    def test_auth_change_before_thread_response_stops_before_turn(self):
        with self.assertRaises(runner.ProposalStopped):
            self.run_protocol(before_thread=[{
                "method": "account/updated", "params": {"authMode": "apiKey"},
            }])
        self.assertFalse(any(m.get("method") == "turn/start" for m in self.sent))

    def test_missing_reached_limit_field_stops_before_turn(self):
        del self.limits["rateLimits"]["rateLimitReachedType"]
        with self.assertRaises(runner.ProposalStopped):
            self.run_protocol()
        self.assertFalse(any(m.get("method") == "turn/start" for m in self.sent))

    def test_tool_event_or_approval_request_cannot_be_accepted(self):
        for event in (
            {"method": "item/started", "params": {
                "threadId": "thread-1", "turnId": "turn-1",
                "item": {"type": "mcpToolCall"},
            }},
            {"id": 10, "method": "item/commandExecution/requestApproval", "params": {}},
        ):
            with self.subTest(event=event["method"]):
                with self.assertRaises(runner.ProposalStopped):
                    self.run_protocol([event])

    def test_interrupted_or_unmatched_completion_is_incomplete(self):
        for turn_id, status in (("turn-1", "interrupted"), ("other", "completed")):
            with self.subTest(turn_id=turn_id, status=status):
                with self.assertRaises(runner.ProposalStopped):
                    self.run_protocol([{"method": "turn/completed", "params": {
                        "threadId": "thread-1", "turn": {"id": turn_id, "status": status},
                    }}])


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def test_success_keeps_real_exit_code_and_output(self):
        result = runner.bounded(
            [sys.executable, "-c", "print('actual output')"],
            self.root, "", 3, self.root / "call",
        )

        self.assertEqual(result["reason"], "completed")
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(Path(result["stdout"]).read_text().strip(), "actual output")

    def test_lost_watchdog_receipt_never_claims_cleanup(self):
        with patch.object(runner.subprocess, "Popen") as launch:
            launch.return_value.wait.return_value = -signal.SIGKILL
            launch.return_value.poll.return_value = -signal.SIGKILL

            result = runner.bounded(
                [sys.executable, "-c", "pass"], self.root, "", 1, self.root / "call",
            )

        self.assertEqual(result["reason"], "cleanup_unconfirmed")
        self.assertFalse(result["cleanup_confirmed"])

    def test_interrupt_cannot_hide_unconfirmed_cleanup(self):
        directory = self.root / "call"

        def interrupt(*args, **kwargs):
            runner.save(directory / "result.json", {
                "reason": "cleanup_unconfirmed", "cleanup_confirmed": False,
            })
            raise KeyboardInterrupt

        with patch.object(runner.subprocess, "Popen") as launch:
            launch.return_value.wait.side_effect = interrupt
            launch.return_value.poll.return_value = 0

            result = runner.bounded(
                [sys.executable, "-c", "pass"], self.root, "", 1, directory,
            )

        self.assertEqual(result["reason"], "cleanup_unconfirmed")
        self.assertFalse(result["cleanup_confirmed"])

    def test_unavailable_process_observation_stops_before_launch(self):
        directory = self.root / "call"
        directory.mkdir()
        runner.save(directory / "job.json", {
            "argv": [sys.executable, "-c", "pass"], "cwd": str(self.root), "seconds": 2,
        })
        read_end, write_end = os.pipe()
        try:
            with patch.object(runner, "group_running", side_effect=PermissionError(1, "denied")), \
                    patch.object(runner.subprocess, "Popen") as launch, \
                    patch.object(runner.signal, "signal"):
                runner.watchdog(directory / "job.json", read_end)
            result = json.loads((directory / "result.json").read_text())

            launch.assert_not_called()
            self.assertEqual(result["reason"], "runtime_error")
            self.assertTrue(result["cleanup_confirmed"])
            self.assertEqual(result["execution_error"]["errno"], 1)
        finally:
            os.close(write_end)

    def test_deadline_stops_worker_and_its_child(self):
        heartbeat = self.root / "heartbeat"
        child_code = (
            "import pathlib,time; p=pathlib.Path(" + repr(str(heartbeat)) + "); "
            "\nwhile True:\n p.write_text(str(time.monotonic())); time.sleep(.02)"
        )
        worker = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-c'," + repr(child_code) + "]); "
            "time.sleep(60)"
        )

        result = runner.bounded(
            [sys.executable, "-c", worker], self.root, "", 0.6, self.root / "call",
        )

        self.assertEqual(result["reason"], "timed_out")
        self.assertLess(result["elapsed_seconds"], 3)
        self.assertTrue(heartbeat.exists())
        last = heartbeat.read_text()
        time.sleep(0.15)
        self.assertEqual(heartbeat.read_text(), last)

    def test_launcher_death_stops_worker_through_separate_watchdog(self):
        heartbeat = self.root / "heartbeat"
        worker = (
            "import pathlib,time; p=pathlib.Path(" + repr(str(heartbeat)) + "); "
            "\nwhile True:\n p.write_text(str(time.monotonic())); time.sleep(.02)"
        )
        launcher = (
            "import importlib.util; from pathlib import Path; "
            f"s=importlib.util.spec_from_file_location('runner',{str(SCRIPT)!r}); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            f"m.bounded({[sys.executable, '-c', worker]!r}, "
            f"Path({str(self.root)!r}), '', 30, Path({str(self.root / 'call')!r}))"
        )
        owner = subprocess.Popen([sys.executable, "-c", launcher])
        try:
            wait_for(heartbeat)
            owner.kill()
            owner.wait(timeout=3)
            wait_for(self.root / "call/result.json")
            result = json.loads((self.root / "call/result.json").read_text())
            last = heartbeat.read_text()
            time.sleep(0.15)

            self.assertEqual(result["reason"], "owner_lost")
            self.assertEqual(heartbeat.read_text(), last)
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.wait(timeout=3)

    def test_deadline_kills_a_child_that_ignores_term(self):
        heartbeat = self.root / "heartbeat"
        child = (
            "import pathlib,time,signal; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
            "p=pathlib.Path(" + repr(str(heartbeat)) + "); "
            "\nwhile True:\n p.write_text(str(time.monotonic())); time.sleep(.02)"
        )
        worker = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); time.sleep(60)"
        )

        result = runner.bounded(
            [sys.executable, "-c", worker], self.root, "", 0.6, self.root / "call",
        )

        self.assertEqual(result["reason"], "timed_out")
        self.assertTrue(result["cleanup_confirmed"])
        last = heartbeat.read_text()
        time.sleep(0.15)
        self.assertEqual(heartbeat.read_text(), last)

    def test_normal_exit_cleans_lingering_child(self):
        heartbeat = self.root / "heartbeat"
        child = (
            "import pathlib,time; p=pathlib.Path(" + repr(str(heartbeat)) + "); "
            "\nwhile True:\n p.write_text(str(time.monotonic())); time.sleep(.02)"
        )
        worker = (
            "import subprocess,sys,time; "
            "subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); time.sleep(.2)"
        )

        result = runner.bounded(
            [sys.executable, "-c", worker], self.root, "", 3, self.root / "call",
        )

        self.assertEqual(result["reason"], "completed")
        last = heartbeat.read_text()
        time.sleep(0.15)
        self.assertEqual(heartbeat.read_text(), last)


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.worktree = self.root / "worktree"
        self.worktree.mkdir()
        (self.worktree / "value.txt").write_text("broken")
        (self.worktree / "oracle.py").write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "if Path('value.txt').read_text() != 'fixed':\n"
            " print('EXPECTED_REGRESSION'); sys.exit(1)\n"
        )
        self.contract = {
            "version": 1, "case_id": "fixture-case", "repository": "example/dotfiles",
            "source": "task-log:fixture-case", "worktree": str(self.worktree),
            "baseline": "a" * 40, "branch": "codex/fixture",
            "authority": "Synthetic test only; no model or publication",
            "duplicate_check": "Synthetic empty remote snapshot",
            "editable": ["value.txt"],
            "inputs": {
                name: runner.digest(self.worktree / name)
                for name in ("value.txt", "oracle.py")
            },
            "reproduce": [sys.executable, "oracle.py"],
            "red_marker": "EXPECTED_REGRESSION",
            "verify": [[sys.executable, "oracle.py"]],
            "seconds": 20, "max_attempts": 2, "model": "gpt-6-astra",
        }
        self.state = self.root / "state"
        self.calls = []
        self.repo_patch = patch.object(runner, "check_repository")
        self.repo_patch.start()
        self.addCleanup(self.repo_patch.stop)
        self.storage_patch = patch.object(runner, "check_durable_storage")
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def model(self, edits=None, error=False, metadata=True):
        self.calls.append("model")
        return {
            "status": "proposal" if not error else "runtime_error",
            "model_metadata": {"model": "gpt-6-astra", "provider": "openai",
                               "source": "thread/start"} if metadata else {},
            "result": json.dumps({"edits": edits or [
                {"path": "value.txt", "old": "broken", "new": "fixed"},
            ]}),
        }

    def run_case(self, response=None):
        with patch.object(runner, "request_patch", side_effect=response or (lambda *args: self.model())):
            return runner.run_case(self.contract, self.state)

    def test_no_candidate_makes_no_model_call(self):
        with patch.object(runner, "request_patch") as model:
            result = runner.run_case(None, self.state)
        self.assertEqual(result["status"], "no_candidate")
        model.assert_not_called()

    def test_unconfirmed_cleanup_blocks_retry_and_model_dispatch(self):
        with patch.object(runner, "bounded", return_value={
                "reason": "cleanup_unconfirmed", "cleanup_confirmed": False,
                "returncode": None,
        }), patch.object(runner, "request_patch") as model:
            first = runner.run_case(self.contract, self.state)
            second = runner.run_case(self.contract, self.state)

        self.assertEqual(first["status"], "owner_unknown")
        self.assertEqual(second["status"], "owner_unknown")
        self.assertEqual(first["attempts"], 0)
        model.assert_not_called()

    def test_expected_red_then_green_is_only_awaiting_review(self):
        result = self.run_case()

        self.assertEqual(result["status"], "awaiting_review")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual((self.worktree / "value.txt").read_text(), "fixed")
        self.assertEqual(runner.digest(self.worktree / "oracle.py"),
                         self.contract["inputs"]["oracle.py"])
        self.assertEqual(result["red"]["returncode"], 1)
        self.assertEqual(result["verification"][-1]["returncode"], 0)
        self.assertNotIn("success", result)

    def test_duplicate_does_not_restart_or_reset_attempts(self):
        self.run_case()
        self.contract["branch"] = "codex/different-branch"

        result = self.run_case()

        self.assertEqual(result["status"], "duplicate")
        self.assertEqual(len(self.calls), 1)

    def test_duplicate_is_preserved_in_a_fresh_interpreter(self):
        self.run_case()
        contract_path = self.root / "contract.json"
        contract_path.write_text(json.dumps(self.contract))
        code = (
            "import importlib.util,json; from pathlib import Path; "
            f"s=importlib.util.spec_from_file_location('runner',{str(SCRIPT)!r}); "
            "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
            "m.check_durable_storage=lambda *a: None; m.check_repository=lambda *a: None; "
            "m.request_patch=lambda *a: (_ for _ in ()).throw(AssertionError('unexpected model call')); "
            f"print(json.dumps(m.run_case(json.loads(Path({str(contract_path)!r}).read_text()), "
            f"Path({str(self.state)!r}))))"
        )

        result = subprocess.run([sys.executable, "-B", "-c", code],
                                capture_output=True, text=True, timeout=5, check=True)

        self.assertEqual(json.loads(result.stdout)["status"], "duplicate")
        self.assertEqual(json.loads(result.stdout)["attempts"], 1)

    def test_baseline_already_passing_is_unreproduced(self):
        (self.worktree / "value.txt").write_text("fixed")
        self.contract["inputs"]["value.txt"] = runner.digest(self.worktree / "value.txt")

        result = self.run_case()

        self.assertEqual(result["status"], "unreproduced")
        self.assertEqual(self.calls, [])

    def test_unrelated_baseline_failure_does_not_authorize_patch(self):
        (self.worktree / "oracle.py").write_text("raise RuntimeError('environment failure')")
        self.contract["inputs"]["oracle.py"] = runner.digest(self.worktree / "oracle.py")

        result = self.run_case()

        self.assertEqual(result["status"], "reproduction_error")
        self.assertEqual(self.calls, [])

    def test_verification_failure_consumes_cap_without_third_proposal(self):
        def wrong(*args):
            old = (self.worktree / "value.txt").read_text()
            return self.model([{"path": "value.txt", "old": old, "new": old + "!"}])
        result = self.run_case(wrong)
        repeated = self.run_case(wrong)

        self.assertEqual(result["status"], "verification_failed")
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["stop_reason"], "attempt_limit")
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(repeated["status"], "duplicate")

    def test_runtime_error_stops_without_retry(self):
        result = self.run_case(lambda *args: self.model(error=True))

        self.assertEqual(result["status"], "runtime_error")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((self.worktree / "value.txt").read_text(), "broken")

    def test_permission_denial_never_retries(self):
        def denied(*args):
            result = self.model()
            result["controller_error"] = "permission_denied"
            return result
        result = self.run_case(denied)

        self.assertEqual(result["status"], "permission_denied")
        self.assertEqual(len(self.calls), 1)

    def test_unknown_model_cannot_apply_patch(self):
        result = self.run_case(lambda *args: self.model(metadata=False))

        self.assertEqual(result["status"], "unknown_model")
        self.assertEqual((self.worktree / "value.txt").read_text(), "broken")

    def test_unconfirmed_billing_never_applies_a_patch_or_retries(self):
        def limited(*args):
            response = self.model(error=True)
            response["controller_error"] = "billing_unconfirmed"
            return response
        result = self.run_case(limited)

        self.assertEqual(result["status"], "billing_unconfirmed")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual((self.worktree / "value.txt").read_text(), "broken")

    def test_missing_provider_metadata_does_not_apply_patch(self):
        def unknown(*args):
            response = self.model()
            response["model_metadata"]["provider"] = None
            return response
        result = self.run_case(unknown)

        self.assertEqual(result["status"], "unknown_model")
        self.assertEqual((self.worktree / "value.txt").read_text(), "broken")

    def test_malformed_model_patch_cannot_be_success(self):
        def invalid(*args):
            response = self.model()
            response["result"] = "not JSON"
            return response
        result = self.run_case(invalid)

        self.assertEqual(result["status"], "invalid_patch")
        self.assertEqual((self.worktree / "value.txt").read_text(), "broken")

    def test_patch_cannot_edit_protected_test_or_escape_worktree(self):
        for index, path in enumerate(("oracle.py", "../outside", "/tmp/outside")):
            with self.subTest(path=path):
                self.contract["case_id"] = f"invalid-{index}"
                self.contract["source"] = f"task-log:invalid-{index}"
                result = self.run_case(lambda *args: self.model([
                    {"path": path, "old": "broken", "new": "fixed"},
                ]))
                self.assertEqual(result["status"], "invalid_patch")
                self.assertEqual((self.worktree / "value.txt").read_text(), "broken")

    def test_all_edits_are_validated_before_any_write(self):
        result = self.run_case(lambda *args: self.model([
            {"path": "value.txt", "old": "broken", "new": "fixed"},
            {"path": "oracle.py", "old": "unmatched", "new": ""},
        ]))

        self.assertEqual(result["status"], "invalid_patch")
        self.assertEqual((self.worktree / "value.txt").read_text(), "broken")

    def test_changed_protected_input_stops_before_model(self):
        (self.worktree / "oracle.py").write_text("print('changed')")

        result = self.run_case()

        self.assertEqual(result["status"], "input_changed")
        self.assertEqual(self.calls, [])

    def test_invalid_limits_stop_before_model(self):
        for value in (0, -1, True, float("nan"), float("inf")):
            with self.subTest(value=value):
                self.contract["seconds"] = value
                result = self.run_case()
                self.assertEqual(result["status"], "invalid_contract")
        self.assertEqual(self.calls, [])

    def test_repair_deadline_stops_a_slow_reproducer_before_model(self):
        self.contract["seconds"] = 0.1
        self.contract["reproduce"] = [sys.executable, "-c", "import time; time.sleep(60)"]

        result = self.run_case()

        self.assertEqual(result["status"], "timed_out")
        self.assertEqual(result["attempts"], 0)
        self.assertEqual(self.calls, [])

    def test_unfinished_prior_record_does_not_restart_writer(self):
        case_dir = runner.case_directory(self.contract, self.state)
        case_dir.mkdir(parents=True)
        (case_dir / "state.json").write_text(json.dumps({
            "status": "running", "attempts": 1,
        }))

        result = self.run_case()

        self.assertEqual(result["status"], "owner_unknown")
        self.assertEqual(self.calls, [])

    def test_concurrent_lock_is_not_treated_as_finished(self):
        case_dir = runner.case_directory(self.contract, self.state)
        case_dir.mkdir(parents=True)
        with runner.case_lock(case_dir):
            result = self.run_case()

        self.assertEqual(result["status"], "busy")
        self.assertEqual(self.calls, [])

    def test_corrupt_prior_record_never_grants_another_attempt(self):
        case_dir = runner.case_directory(self.contract, self.state)
        case_dir.mkdir(parents=True)
        (case_dir / "state.json").write_text("{truncated")

        result = self.run_case()

        self.assertEqual(result["status"], "owner_unknown")
        self.assertEqual(self.calls, [])

    def test_symlink_input_is_rejected_before_model(self):
        outside = self.root / "outside.txt"
        outside.write_text("broken")
        (self.worktree / "value.txt").unlink()
        (self.worktree / "value.txt").symlink_to(outside)

        result = self.run_case()

        self.assertEqual(result["status"], "invalid_contract")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()

