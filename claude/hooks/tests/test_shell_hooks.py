import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS = REPO_ROOT / "claude" / "hooks"
FIXTURES = Path(__file__).parent / "fixtures"


def fixture(hook: str, name: str) -> str:
    return (FIXTURES / hook / name).read_text()


def run_hook(hook: str, payload: str, *, env: dict[str, str] | None = None):
    return subprocess.run(
        ["bash", str(HOOKS / hook)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


class NotificationHookTest(unittest.TestCase):
    def test_waiting_notification_is_translated_and_sent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            capture = root / "curl-args"
            fake_curl = root / "curl"
            fake_curl.write_text(
                "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$HOOK_CAPTURE\"\n"
            )
            fake_curl.chmod(0o755)
            env = {
                **os.environ,
                "PATH": f"{root}:{os.environ['PATH']}",
                "HOOK_CAPTURE": str(capture),
                "PUSHOVER_API_TOKEN": "test-token",
                "PUSHOVER_USER_KEY": "test-user",
            }

            result = run_hook(
                "notification.sh", fixture("notification", "waiting.json"), env=env
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Claudeはあなたの入力を待っています", capture.read_text())

    def test_login_notification_is_ignored(self) -> None:
        result = run_hook("notification.sh", fixture("notification", "login.json"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_invalid_json_fails_open(self) -> None:
        result = run_hook("notification.sh", fixture("notification", "invalid.json"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


class PostTypeScriptLintHookTest(unittest.TestCase):
    def test_typescript_diagnostics_are_returned_as_context(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                ["git", "init", "--quiet", str(root)], check=True, capture_output=True
            )
            oxlint = root / "node_modules" / ".bin" / "oxlint"
            oxlint.parent.mkdir(parents=True)
            oxlint.write_text("#!/usr/bin/env bash\necho 'lint fixture diagnostic'\n")
            oxlint.chmod(0o755)
            payload = json.loads(fixture("post-ts-lint", "typescript.json"))
            payload["cwd"] = str(root)

            result = run_hook("post-ts-lint.sh", json.dumps(payload))

            self.assertEqual(result.returncode, 0, result.stderr)
            output = json.loads(result.stdout)
            self.assertEqual(
                output["hookSpecificOutput"]["hookEventName"], "PostToolUse"
            )
            self.assertIn(
                "lint fixture diagnostic",
                output["hookSpecificOutput"]["additionalContext"],
            )

    def test_unsupported_file_is_ignored(self) -> None:
        result = run_hook(
            "post-ts-lint.sh", fixture("post-ts-lint", "unsupported.json")
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_invalid_json_fails_open(self) -> None:
        result = run_hook("post-ts-lint.sh", fixture("post-ts-lint", "invalid.json"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


class RequireSubagentModelHookTest(unittest.TestCase):
    def test_explicit_model_is_allowed(self) -> None:
        result = run_hook(
            "require-subagent-model.sh",
            fixture("require-subagent-model", "explicit.json"),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_inherited_model_is_denied(self) -> None:
        result = run_hook(
            "require-subagent-model.sh",
            fixture("require-subagent-model", "inherit.json"),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecision"], "deny"
        )

    def test_invalid_json_fails_open(self) -> None:
        result = run_hook(
            "require-subagent-model.sh",
            fixture("require-subagent-model", "invalid.json"),
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


class ValidateBashHookTest(unittest.TestCase):
    def test_scoped_git_add_is_allowed(self) -> None:
        result = run_hook(
            "validate-bash.sh", fixture("validate-bash", "scoped-add.json")
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_git_add_all_is_denied(self) -> None:
        result = run_hook(
            "validate-bash.sh", fixture("validate-bash", "add-all.json")
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(
            output["hookSpecificOutput"]["permissionDecision"], "deny"
        )

    def test_invalid_json_fails_open(self) -> None:
        result = run_hook("validate-bash.sh", fixture("validate-bash", "invalid.json"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
