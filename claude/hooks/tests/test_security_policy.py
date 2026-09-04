import json
from pathlib import Path
import subprocess
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
SETTINGS = REPO_ROOT / "claude" / "settings.json"
CANARY = REPO_ROOT / "claude" / "sandbox-canary.json"
VALIDATE_BASH = REPO_ROOT / "claude" / "hooks" / "validate-bash.sh"
DENY_CHECK = REPO_ROOT / "claude" / "hooks" / "deny-check.sh"


class SecurityPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.settings = json.loads(SETTINGS.read_text())
        cls.canary = json.loads(CANARY.read_text())

    def test_canary_keeps_only_the_macOS_trial_boundary(self) -> None:
        sandbox = self.canary["sandbox"]
        self.assertEqual(
            set(sandbox),
            {
                "enabled",
                "failIfUnavailable",
                "excludedCommands",
                "network",
                "credentials",
            },
        )
        self.assertTrue(sandbox["enabled"])
        self.assertFalse(sandbox["failIfUnavailable"])
        self.assertEqual(
            sandbox["excludedCommands"], ["docker *", "docker-compose *", "gh *"]
        )
        self.assertEqual(sandbox["network"], {"allowLocalBinding": True})

        credential_files = {
            entry["path"]
            for entry in sandbox["credentials"]["files"]
            if entry["mode"] == "deny"
        }
        credential_env_vars = {
            entry["name"]
            for entry in sandbox["credentials"]["envVars"]
            if entry["mode"] == "deny"
        }
        self.assertTrue(
            {"~/.ssh", "~/.config/gh/hosts.yml", "~/.claude/.credentials.json"}
            <= credential_files
        )
        self.assertTrue(
            {"ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GH_TOKEN"}
            <= credential_env_vars
        )

    def test_default_settings_do_not_enable_sandbox_during_canary(self) -> None:
        self.assertNotIn("sandbox", self.settings)

    def test_auto_mode_keeps_bypass_permissions_disabled(self) -> None:
        permissions = self.settings["permissions"]
        self.assertEqual(permissions["defaultMode"], "auto")
        self.assertEqual(permissions["disableBypassPermissionsMode"], "disable")
        self.assertTrue(self.settings["skipAutoPermissionPrompt"])
        self.assertNotIn("skipDangerousModePermissionPrompt", self.settings)
        self.assertEqual(
            self.canary["permissions"]["disableBypassPermissionsMode"], "disable"
        )

    def test_standard_permissions_own_allow_ask_and_deny_decisions(self) -> None:
        permissions = self.settings["permissions"]
        self.assertIn("Bash(gh pr view:*)", permissions["allow"])
        self.assertIn("Bash(gh api:*)", permissions["ask"])
        self.assertIn("Bash(dangerouslyDisableSandbox:true)", permissions["ask"])
        self.assertIn("Bash(rm -f *)", permissions["deny"])
        self.assertIn("Read(**/*.env)", permissions["deny"])

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
        cases = [
            ("git add src/app.ts", "allow"),
            ("git add -A", "deny"),
            ("git add . && git status", "deny"),
        ]
        for command, expected in cases:
            payload = {
                "tool_name": "Bash",
                "tool_input": {"command": command},
            }
            result = subprocess.run(
                [str(VALIDATE_BASH)],
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                check=False,
            )

            with self.subTest(command=command):
                self.assertEqual(result.returncode, 0, result.stderr)
                if expected == "allow":
                    self.assertEqual(result.stdout, "")
                else:
                    output = json.loads(result.stdout)
                    decision = output["hookSpecificOutput"]["permissionDecision"]
                    self.assertEqual(decision, "deny")


if __name__ == "__main__":
    unittest.main()
