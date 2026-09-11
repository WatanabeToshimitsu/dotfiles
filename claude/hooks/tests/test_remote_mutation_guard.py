import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


HOOK = Path(__file__).resolve().parents[1] / "remote-mutation-guard.py"


class RemoteMutationGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("remote_guard", HOOK)
        cls.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.guard)

    def classify(self, command):
        return self.guard.classify_shell(command)[0]

    def test_normal_push_and_read_commands_continue(self):
        for command in [
            "git push", "git push -u origin topic", "git push origin topic --tags",
            "rtk git push origin topic", "rtk proxy git -C /tmp/repo push origin topic",
            "git push origin feature-force", "git push --force --help",
            "git push --dry-run --force origin main",
            "gh pr view 12", "gh api repos/o/r/pulls", "gh pr create --help",
            "echo 'git push --force origin main'", "printf '%s' 'gh pr create'",
            "cat <<'EOF'\ngit push --force\nEOF\n",
        ]:
            with self.subTest(command=command):
                self.assertEqual(self.classify(command), "continue")

    def test_remote_history_changes_are_blocked_in_all_argument_positions(self):
        for command in [
            "git push --force origin main", "git push origin main --force",
            "git push origin --force-with-lease=main:abc main",
            "git push origin main -f", "git push -uf origin main",
            "git push origin +HEAD:main", "git push -- origin +HEAD:main",
            "git push origin :old-branch", "git push origin main --mirror",
            "git push origin --delete old-branch", "git push -d origin old-branch",
            "git -C /tmp/repo push origin main --force",
            "rtk git push origin main --force", "rtk proxy git push origin main -f",
            "env LANG=C command git push origin main --force",
            "timeout 30 rtk git push origin main --force",
            "env -u TOKEN git push origin main --force",
            "git status && git push origin main --force",
            "bash -lc 'git push origin main --force'",
            "git -c alias.publish='push --force' publish origin main",
            "git -c remote.origin.mirror=true push origin",
        ]:
            with self.subTest(command=command):
                self.assertEqual(self.classify(command), "deny")

    def test_pr_creation_is_detected_without_matching_document_text(self):
        for command in [
            "gh pr create --title 'A change' --body 'Review git push --force behavior'",
            "gh pr create --title '--help' --body Clean",
            "rtk proxy gh pr create --draft --body-file /tmp/body.md",
            "gh --repo o/r pr create --title Test",
            "gh api repos/o/r/pulls --method POST --field title=Test",
            "gh api -X POST /repos/o/r/pulls",
            "gh api repos/o/r/pulls -f title=Test",
            "gh api graphql -f 'query=mutation { createPullRequest(input: {}) { id } }'",
        ]:
            with self.subTest(command=command):
                self.assertEqual(self.classify(command), "pr")

    def test_uninspectable_remote_commands_fail_without_executing(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "never-created"
            self.assertEqual(self.classify(f'git push origin "$(touch {marker})"'), "deny")
            self.assertFalse(marker.exists())
        self.assertEqual(self.classify('git push origin "$branch"'), "deny")

    def test_cancelled_dry_run_and_remote_pruning_are_blocked(self):
        for command in [
            "git push --dry-run --no-dry-run --force origin main",
            "git push -n --no-dry-run origin main --force",
            "git push --prune origin 'refs/heads/*:refs/heads/*'",
            "git push --del origin old", "git push --mir origin", "git push --pru origin",
            "git push --dry-run --no-dry --force origin main",
        ]:
            with self.subTest(command=command):
                self.assertEqual(self.classify(command), "deny")
        self.assertEqual(self.classify("git push --no-dry-run --dry-run --force origin main"), "continue")

    def test_pr_api_urls_and_queries_require_review(self):
        for endpoint in [
            "https://api.github.com/repos/o/r/pulls",
            "https://github.example/api/v3/repos/o/r/pulls",
            "repos/o/r/pulls?state=open",
            "/repos/o/r/pulls/",
        ]:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.classify(f"gh api --method POST '{endpoint}' -f title=Test"), "pr")

    def test_opaque_graphql_inputs_and_git_environment_are_blocked(self):
        for command in [
            "gh api graphql --input /tmp/pr.json",
            "gh api graphql -F query=@/tmp/pr.graphql",
            "gh api graphql --input -",
            "env GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror GIT_CONFIG_VALUE_0=true git push origin",
            "GIT_DIR=/tmp/other.git git push origin main",
        ]:
            with self.subTest(command=command):
                self.assertEqual(self.classify(command), "deny")

    def test_remote_config_is_checked_before_unsupported_push_options(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", directory], check=True, capture_output=True)
            subprocess.run(["git", "-C", directory, "remote", "add", "origin", "https://example.invalid/o/r.git"], check=True)
            for setting, value in [("mirror", "true"), ("push", "+HEAD:main")]:
                subprocess.run(["git", "-C", directory, "config", "remote.origin." + setting, value], check=True)
                for args in ["--no-verify origin main", "-o ci.skip origin main", "--repo origin --no-verify main"]:
                    with self.subTest(setting=setting, args=args):
                        output = self.run_hook({
                            "tool_name": "Bash", "cwd": directory,
                            "tool_input": {"command": "git push " + args},
                        }, "codex")
                        self.assertEqual(output.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")
                subprocess.run(["git", "-C", directory, "config", "--unset", "remote.origin." + setting], check=True)

    def test_normal_push_reaches_the_prepublication_secret_check(self):
        decision, detail = self.guard.classify_shell("rtk git -C /tmp/repo push -u origin topic")
        self.assertEqual(decision, "continue")
        self.assertEqual(detail["pushes"][0]["args"], ["-u", "origin", "topic"])
        self.assertEqual(self.guard.classify_words(["command"]), ("continue", {}))

    def test_inline_git_config_cannot_hide_forced_push(self):
        for command in [
            "git -c remote.origin.push=+HEAD:main push origin",
            "git -cremote.origin.push=+HEAD:main push origin",
        ]:
            output = self.run_hook({
                "tool_name": "Bash", "cwd": "/tmp", "tool_input": {"command": command},
            }, "codex")
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def run_hook(self, payload, client):
        result = subprocess.run(
            ["python3", str(HOOK), "--client", client],
            input=json.dumps(payload), text=True, capture_output=True, check=True,
        )
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout) if result.stdout else {}

    def test_claude_pr_requires_human_even_in_auto_mode(self):
        output = self.run_hook({
            "tool_name": "Bash", "permission_mode": "auto", "cwd": "/tmp",
            "tool_input": {"command": "gh pr create --title Test --body Clean"},
        }, "claude")
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("未検査", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_codex_cli_uses_the_connector_human_approval_path(self):
        output = self.run_hook({
            "tool_name": "Bash", "cwd": "/tmp",
            "tool_input": {"command": "gh pr create --title Test --body Clean"},
        }, "codex")
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("GitHub", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_secret_in_mcp_pr_body_blocks_without_echoing_it(self):
        secret = "gh" + "p_" + "aB7cD9" * 6
        for client in ["claude", "codex"]:
            output = self.run_hook({
                "tool_name": "mcp__github__create_pull_request", "cwd": "/tmp",
                "tool_input": {"title": "Test", "body": secret},
            }, client)
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
            self.assertNotIn(secret, json.dumps(output))

    def test_clean_mcp_pr_still_prompts_in_claude(self):
        output = self.run_hook({
            "tool_name": "mcp__github__create_pull_request", "cwd": "/tmp",
            "tool_input": {"title": "Test", "body": "Clean"},
        }, "claude")
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_body_file_is_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            body = Path(directory) / "body.md"
            body.write_text("-----BEGIN " + "PRIVATE KEY-----\nexample\n")
            output = self.run_hook({
                "tool_name": "Bash", "cwd": directory,
                "tool_input": {"command": f"gh pr create --body-file {body}"},
            }, "claude")
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_intermediate_commits_are_scanned_even_after_secret_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.run(
                    ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                     "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                     "-C", directory, *args], check=True, capture_output=True, text=True,
                ).stdout.strip()
            git("init", "-b", "main")
            file = Path(directory) / "app.txt"
            file.write_text("clean\n")
            git("add", "app.txt"); git("commit", "-m", "base")
            git("switch", "-c", "topic")
            file.write_text("gh" + "p_" + "aB7cD9" * 6 + "\n")
            git("add", "app.txt"); git("commit", "-m", "mistake")
            file.write_text("clean again\n")
            git("add", "app.txt"); git("commit", "-m", "remove")
            git("remote", "add", "origin", "https://example.invalid/o/r.git")
            git("update-ref", "refs/remotes/origin/main", git("rev-parse", "main"))
            git("symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
            output = self.run_hook({
                "tool_name": "Bash", "cwd": directory,
                "tool_input": {"command": "gh pr create --base main --head topic --title Test"},
            }, "claude")
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
            for client in ["claude", "codex"]:
                output = self.run_hook({
                    "tool_name": "Bash", "cwd": directory,
                    "tool_input": {"command": "git push -u origin topic"},
                }, client)
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertIn("push 前", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_real_codex_connector_argument_names_are_used(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.run_hook({
                "tool_name": "mcp__codex_apps__github_create_pull_request", "cwd": directory,
                "tool_input": {"repository_full_name": "o/r", "base_branch": "main",
                               "head_branch": "topic", "title": "Test", "body": "Clean"},
            }, "codex")
            self.assertNotIn("permissionDecision", output["hookSpecificOutput"])
            self.assertIn("未検査", output["hookSpecificOutput"]["additionalContext"])

    def test_secrets_introduced_only_by_a_merge_are_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.run(
                    ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                     "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                     "-C", directory, *args], check=True, capture_output=True, text=True,
                ).stdout.strip()
            git("init", "-b", "main")
            git("commit", "--allow-empty", "-m", "base")
            git("switch", "-c", "topic")
            git("commit", "--allow-empty", "-m", "topic")
            git("switch", "-c", "other", "main")
            git("commit", "--allow-empty", "-m", "other")
            git("switch", "topic")
            git("merge", "--no-ff", "--no-commit", "other")
            secret = "gh" + "p_" + "aB7cD9" * 6
            (Path(directory) / "merge.txt").write_text(secret + "\n")
            git("add", "merge.txt")
            git("commit", "-m", "merge")
            blocked, report = self.guard.inspect_pr(directory, {"base": "main", "head": "topic"})
            self.assertTrue(blocked)
            self.assertNotIn(secret, report)


if __name__ == "__main__":
    unittest.main()
