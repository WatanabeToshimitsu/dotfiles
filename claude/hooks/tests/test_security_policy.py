import json
from pathlib import Path
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS = REPO_ROOT / "claude" / "settings.json"
CANARY = REPO_ROOT / "claude" / "sandbox-canary.json"
FIXTURE = Path(__file__).parent / "fixtures" / "security-policy.json"
VALIDATE_BASH = REPO_ROOT / "claude" / "hooks" / "validate-bash.sh"
DENY_CHECK = REPO_ROOT / "claude" / "hooks" / "deny-check.sh"


def assert_subset(test: unittest.TestCase, actual, expected, path="sandbox") -> None:
    for key, expected_value in expected.items():
        test.assertIn(key, actual, f"missing {path}.{key}")
        actual_value = actual[key]
        if isinstance(expected_value, dict):
            test.assertIsInstance(actual_value, dict, f"{path}.{key}")
            assert_subset(test, actual_value, expected_value, f"{path}.{key}")
        else:
            test.assertEqual(actual_value, expected_value, f"{path}.{key}")


class SecurityPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = json.loads(SETTINGS.read_text())
        cls.canary = json.loads(CANARY.read_text())
        cls.fixture = json.loads(FIXTURE.read_text())

    def test_canary_matches_declared_sandbox_boundary(self) -> None:
        assert_subset(self, self.canary["sandbox"], self.fixture["sandbox"])

        credential_files = {
            entry["path"]
            for entry in self.canary["sandbox"]["credentials"]["files"]
            if entry["mode"] == "deny"
        }
        credential_env_vars = {
            entry["name"]
            for entry in self.canary["sandbox"]["credentials"]["envVars"]
            if entry["mode"] == "deny"
        }
        self.assertTrue(
            set(self.fixture["requiredCredentialFiles"]) <= credential_files
        )
        self.assertTrue(
            set(self.fixture["requiredCredentialEnvVars"]) <= credential_env_vars
        )

    def test_default_settings_do_not_enable_sandbox_during_canary(self) -> None:
        self.assertNotIn("sandbox", self.settings)

    def test_standard_permissions_own_allow_ask_and_deny_decisions(self) -> None:
        permissions = self.settings["permissions"]
        for case in self.fixture["permissionCases"]:
            with self.subTest(case=case["name"], command=case["command"]):
                decision = case["decision"]
                rule = case["rule"]
                self.assertIn(rule, permissions[decision])
                for other_decision in {"allow", "ask", "deny"} - {decision}:
                    self.assertNotIn(rule, permissions[other_decision])

    def test_incomplete_deny_parser_is_not_wired(self) -> None:
        self.assertFalse(DENY_CHECK.exists())
        self.assertNotIn("deny-check.sh", json.dumps(self.settings["hooks"]))

    def test_home_credentials_do_not_block_project_dotfiles(self) -> None:
        deny_rules = self.settings["permissions"]["deny"]
        self.assertIn("Read(~/.npmrc)", deny_rules)
        self.assertIn("Read(~/.netrc)", deny_rules)
        self.assertNotIn("Read(**/.npmrc)", deny_rules)
        self.assertNotIn("Read(**/.netrc)", deny_rules)

    def test_personal_hook_only_enforces_scoped_git_add_policy(self) -> None:
        for case in self.fixture["personalHookCases"]:
            payload = {
                "tool_name": case["toolName"],
                "tool_input": {"command": case["command"]},
            }
            result = subprocess.run(
                [str(VALIDATE_BASH)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            with self.subTest(case=case["name"]):
                self.assertEqual(result.returncode, 0, result.stderr)
                if case["decision"] == "allow":
                    self.assertEqual(result.stdout, "")
                else:
                    output = json.loads(result.stdout)
                    decision = output["hookSpecificOutput"]["permissionDecision"]
                    self.assertEqual(decision, "deny")


if __name__ == "__main__":
    unittest.main()
