import importlib.util
import json
import os
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

    def test_duplicate_remote_settings_keep_scalar_and_multivalue_semantics(self):
        for setting, values, blocked in [
            ("mirror", ["false", "true"], True),
            ("mirror", ["true", "false"], False),
            ("push", ["+HEAD:main", "HEAD:topic"], True),
            ("push", ["HEAD:topic", "+HEAD:main"], True),
        ]:
            with tempfile.TemporaryDirectory() as directory:
                git = self.topic_repo(directory)
                for value in values:
                    git("config", "--add", "remote.origin." + setting, value)

                for client in ["claude", "codex"]:
                    with self.subTest(setting=setting, values=values, client=client):
                        output = self.run_hook({
                            "tool_name": "Bash", "cwd": directory,
                            "tool_input": {"command": "git push origin"},
                        }, client)

                        if blocked:
                            detail = output.get("hookSpecificOutput", {})
                            self.assertEqual(detail.get("permissionDecision"), "deny")
                            self.assertEqual(detail["permissionDecisionReason"], self.guard.FORCE_REASON)
                        else:
                            self.assertEqual(output, {})

    def test_remote_mirror_uses_git_boolean_semantics(self):
        for value, normalized in [
            (None, "true"), ("2", "true"), ("-1", "true"), ("true", "true"),
            ("false", "false"), ("0", "false"), ("", "false"),
        ]:
            with tempfile.TemporaryDirectory() as directory:
                git = self.topic_repo(directory, origin="https://example.invalid/o/r.git")
                if value is None:
                    with (Path(directory) / ".git/config").open("a") as config:
                        config.write('\n[remote "origin"]\n\tmirror\n')
                else:
                    git("config", "remote.origin.mirror", value)
                self.assertEqual(git("config", "--bool", "--get", "remote.origin.mirror"), normalized)

                for client in ["claude", "codex"]:
                    with self.subTest(value=value, client=client):
                        output = self.run_hook({
                            "tool_name": "Bash", "cwd": directory,
                            "tool_input": {"command": "git push origin"},
                        }, client)
                        if normalized == "true":
                            detail = output.get("hookSpecificOutput", {})
                            self.assertEqual(detail.get("permissionDecision"), "deny",
                                             "Git-true mirror must be denied")
                            self.assertEqual(detail["permissionDecisionReason"], self.guard.FORCE_REASON)
                        else:
                            self.assertEqual(output, {})

    def test_inline_git_config_cannot_hide_forced_push(self):
        for command in [
            "git -c remote.origin.push=+HEAD:main push origin",
            "git -cremote.origin.push=+HEAD:main push origin",
        ]:
            output = self.run_hook({
                "tool_name": "Bash", "cwd": "/tmp", "tool_input": {"command": command},
            }, "codex")
            self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def run_hook(self, payload, client, env=None):
        clean_env = {key: value for key, value in os.environ.items() if key not in {"GH_HOST", "GH_REPO"}}
        result = subprocess.run(
            ["python3", str(HOOK), "--client", client],
            input=json.dumps(payload), text=True, capture_output=True, check=True,
            env={**clean_env, **(env or {})},
        )
        self.assertEqual(result.stderr, "")
        return json.loads(result.stdout) if result.stdout else {}

    def topic_repo(self, directory, *, pushed=True, origin="https://github.com/o/r.git"):
        def git(*args):
            return subprocess.run(
                ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                 "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "-C", directory, *args], check=True, capture_output=True, text=True,
            ).stdout.strip()
        git("init", "-b", "main")
        git("commit", "--allow-empty", "-m", "base")
        git("switch", "-c", "topic")
        (Path(directory) / "app.txt").write_text("clean\n")
        git("add", "app.txt")
        git("commit", "-m", "change")
        git("remote", "add", "origin", origin)
        git("update-ref", "refs/remotes/origin/main", git("rev-parse", "main"))
        if pushed:
            git("update-ref", "refs/remotes/origin/topic", git("rev-parse", "topic"))
        return git

    def assert_claude_pr_prompts(self, directory, command, env=None):
        output = self.run_hook({
            "tool_name": "Bash", "cwd": directory,
            "tool_input": {"command": command},
        }, "claude", env)["hookSpecificOutput"]
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertIn("未検査", output["permissionDecisionReason"])

    def test_codex_pr_decisions_ignore_the_origin_target_check(self):
        cases = [
            ({"pushed": False}, "gh pr create --base main --head topic --title Test --body Clean", None),
            ({"origin": "https://git.example.invalid/o/r.git"}, "gh pr create --repo o/r --base main --title Test --body Clean", None),
            ({}, "GH_REPO=u/r gh pr create --base main --title Test --body Clean", None),
            ({}, "gh pr create --base main --title Test --body Clean", {"GH_HOST": "git.example.invalid"}),
        ]
        for options, command, env in cases:
            with self.subTest(command=command, env=env), tempfile.TemporaryDirectory() as directory:
                self.topic_repo(directory, **options)
                output = self.run_hook({
                    "tool_name": "Bash", "cwd": directory,
                    "tool_input": {"command": command},
                }, "codex", env)["hookSpecificOutput"]
                self.assertNotIn("permissionDecision", output)
                self.assertIn("既存の明示的な許可", output["additionalContext"])
                self.assertIn("未検査の範囲が残っています", output["additionalContext"])

    def test_claude_pr_with_uninspected_range_still_prompts_in_auto_mode(self):
        output = self.run_hook({
            "tool_name": "Bash", "permission_mode": "auto", "cwd": "/tmp",
            "tool_input": {"command": "gh pr create --title Test --body Clean"},
        }, "claude")
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("未検査", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_claude_clean_fully_inspected_pr_proceeds_without_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            self.topic_repo(directory)
            for command in [
                "gh pr create --base main --head topic --title Test --body Clean",
                "rtk proxy gh pr create --repo o/r --base main --title Test --body Clean",
                "gh pr create --repo github.com/o/r --base main --title Test --body Clean",
            ]:
                with self.subTest(command=command):
                    output = self.run_hook({
                        "tool_name": "Bash", "permission_mode": "auto", "cwd": directory,
                        "tool_input": {"command": command},
                    }, "claude")["hookSpecificOutput"]
                    self.assertNotIn("permissionDecision", output)
                    self.assertIn("1 コミット", output["additionalContext"])

    def test_claude_pr_prompts_when_head_is_not_pushed(self):
        with tempfile.TemporaryDirectory() as directory:
            self.topic_repo(directory, pushed=False)
            self.assert_claude_pr_prompts(directory, "gh pr create --base main --head topic --title Test --body Clean")

    def test_claude_pr_prompts_when_local_head_is_ahead_of_its_pushed_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            git = self.topic_repo(directory)
            git("commit", "--allow-empty", "-m", "unpushed")
            self.assert_claude_pr_prompts(directory, "gh pr create --base main --head topic --title Test --body Clean")

    def test_claude_pr_prompts_when_a_same_named_tag_hides_the_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            git = self.topic_repo(directory)
            git("tag", "topic")
            git("commit", "--allow-empty", "-m", "unpushed")
            self.assert_claude_pr_prompts(directory, "gh pr create --base main --head topic --title Test --body Clean")
        with tempfile.TemporaryDirectory() as directory:
            git = self.topic_repo(directory)
            git("tag", "topic", "main")
            self.assert_claude_pr_prompts(directory, "gh pr create --base main --head topic --title Test --body Clean")

    def test_claude_pr_text_mentioning_gh_variables_does_not_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            self.topic_repo(directory)
            output = self.run_hook({
                "tool_name": "Bash", "cwd": directory,
                "tool_input": {"command": "gh pr create --base main --title 'GH_HOST=example' --body 'GH_REPO=o/r'"},
            }, "claude")["hookSpecificOutput"]
            self.assertNotIn("permissionDecision", output)

    def test_claude_pr_prompts_when_target_may_not_be_origin(self):
        with tempfile.TemporaryDirectory() as directory:
            git = self.topic_repo(directory)
            git("remote", "add", "upstream", "https://github.com/u/r.git")
            self.assert_claude_pr_prompts(directory, "gh pr create --base main --title Test --body Clean")
        with tempfile.TemporaryDirectory() as directory:
            self.topic_repo(directory, origin="https://git.example.invalid/o/r.git")
            self.assert_claude_pr_prompts(directory, "gh pr create --repo o/r --base main --title Test --body Clean")
        with tempfile.TemporaryDirectory() as directory:
            self.topic_repo(directory)
            self.assert_claude_pr_prompts(
                directory, "gh pr create --repo https://git.example.invalid/o/r --base main --title Test --body Clean")
        with tempfile.TemporaryDirectory() as directory:
            self.topic_repo(directory)
            self.assert_claude_pr_prompts(directory, "gh pr create --base main --head someone:topic --title Test --body Clean")
            for command in [
                "GH_HOST=git.example.invalid gh pr create --repo o/r --base main --title Test --body Clean",
                "env GH_REPO=u/r gh pr create --base main --title Test --body Clean",
                "GH_REPO=o/gh gh pr create --base main --head topic --title Test --body Clean",
                "env GH_REPO=o/gh rtk proxy gh pr create --base main --head topic --title Test --body Clean",
            ]:
                with self.subTest(command=command):
                    self.assert_claude_pr_prompts(directory, command)
            for variable, value in [("GH_HOST", "git.example.invalid"), ("GH_REPO", "u/r")]:
                with self.subTest(variable=variable):
                    self.assert_claude_pr_prompts(
                        directory, "gh pr create --repo o/r --base main --title Test --body Clean", {variable: value})

    def test_claude_pr_prompts_when_text_is_generated_after_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            self.topic_repo(directory)
            for command in [
                "gh pr create --base main --head topic --fill",
                "gh pr create --base main --head topic --title Test",
                "gh pr create --base main --head topic --title Test --body Clean --web",
                "gh pr create --base main --head topic --title Test --body Clean --editor",
                "gh pr create --base main --head topic --title Test --template template.md",
                "gh pr create --base main --head topic --body Clean",
            ]:
                with self.subTest(command=command):
                    output = self.run_hook({
                        "tool_name": "Bash", "cwd": directory,
                        "tool_input": {"command": command},
                    }, "claude")["hookSpecificOutput"]
                    self.assertEqual(output["permissionDecision"], "ask")
                    self.assertIn("未検査", output["permissionDecisionReason"])

    def test_codex_cli_preserves_scoped_authorization_and_inspection(self):
        for tool, key, command in [
            ("Bash", "command", "gh pr create --title Test --body Clean"),
            ("exec_command", "cmd", "rtk gh pr create --draft --title Test --body Clean"),
            ("shell_command", "command", "rtk proxy gh pr create --title Test --body Clean"),
        ]:
            with self.subTest(tool=tool):
                output = self.run_hook({
                    "tool_name": tool, "cwd": "/tmp",
                    "tool_input": {key: command},
                }, "codex")["hookSpecificOutput"]
                self.assertNotIn("permissionDecision", output)
                self.assertIn("未検査", output["additionalContext"])
                self.assertIn("既存の明示的な許可", output["additionalContext"])
                self.assertIn("未検査の範囲が残っています", output["additionalContext"])
                self.assertIn("ユーザーの個別確認", output["additionalContext"])
                self.assertIn("自動審査", output["additionalContext"])
                self.assertNotIn("確認を恒久許可に保存しない", output["additionalContext"])

    def test_codex_cli_secret_scan_still_blocks_before_review(self):
        secret = "gh" + "p_" + "aB7cD9" * 6
        for command in [
            "gh pr create --title Test --body " + secret,
            "rtk proxy gh pr create --draft --title " + secret + " --body Clean",
        ]:
            with self.subTest(command_type=command.split()[0]):
                output = self.run_hook({
                    "tool_name": "Bash", "cwd": "/tmp",
                    "tool_input": {"command": command},
                }, "codex")
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertNotIn(secret, json.dumps(output))

    def test_codex_uninspected_api_pr_creation_remains_blocked(self):
        for command in [
            "gh api repos/o/r/pulls -X POST -f title=Test",
            "rtk proxy gh api -X POST /repos/o/r/pulls -f title=Test",
            "gh api graphql -f 'query=mutation { createPullRequest(input: {}) { id } }'",
        ]:
            with self.subTest(command=command):
                output = self.run_hook({
                    "tool_name": "Bash", "cwd": "/tmp",
                    "tool_input": {"command": command},
                }, "codex")["hookSpecificOutput"]
                self.assertEqual(output.get("permissionDecision"), "deny")
                self.assertIn("gh pr create", output["permissionDecisionReason"])
        self.assertEqual(self.run_hook({
            "tool_name": "Bash", "cwd": "/tmp",
            "tool_input": {"command": "gh api repos/o/r/pulls"},
        }, "codex"), {})

    def test_codex_cli_requires_explicit_inspectable_text(self):
        with tempfile.TemporaryDirectory() as directory:
            oversized = Path(directory) / "large.md"
            oversized.write_bytes(b"x" * (self.guard.MAX_BYTES + 1))
            for command in [
                "gh pr create --title Test",
                "gh pr create --body Clean",
                "gh pr create --title '' --body Clean",
                "gh pr create --title Test --body-file ''",
                "gh pr create --fill",
                "gh pr create --title Test --body Clean --fill-first",
                "gh pr create --title Test --body Clean --fill-verbose",
                "gh pr create --title Test --body Clean -f",
                "gh pr create --title Test --body Clean --editor",
                "gh pr create --title Test --body Clean --web",
                "gh pr create --title Test --body Clean -de",
                "gh pr create --title Test --body Clean -dbXYZ",
                "gh pr create --title Test --body Clean -w",
                "gh pr create --title Test --body Clean --recover old-state",
                "gh pr create --title Test --body Clean --template template.md",
                "gh pr create --title Test --body Clean --attach=private.png",
                "gh pr create --title Test --body-file missing.md",
                "gh pr create --title Test --body-file large.md",
                "gh pr create --title Test --body-file - <<'EOF'\nClean\nEOF\n",
            ]:
                with self.subTest(command=command):
                    output = self.run_hook({
                        "tool_name": "Bash", "cwd": directory,
                        "tool_input": {"command": command},
                    }, "codex")["hookSpecificOutput"]
                    self.assertEqual(output.get("permissionDecision"), "deny")
                    self.assertIn("--body", output["permissionDecisionReason"])

    def test_codex_cli_accepts_readable_files_and_explicit_empty_bodies(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "body.md").write_text("変更内容を確認しました。\n", encoding="utf-8")
            for command in [
                "gh pr create --title Test --body-file body.md",
                "gh pr create --title Test --body ''",
                "gh pr create -tTest -bClean --label bug --label docs",
                "gh pr create --title Test --body '--web'",
            ]:
                with self.subTest(command=command):
                    output = self.run_hook({
                        "tool_name": "Bash", "cwd": directory,
                        "tool_input": {"command": command},
                    }, "codex")["hookSpecificOutput"]
                    self.assertNotIn("permissionDecision", output)

    def test_codex_cli_scans_the_last_repeated_text_option(self):
        secret = "gh" + "p_" + "aB7cD9" * 6
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "clean.md").write_text("Clean\n")
            (Path(directory) / "secret.md").write_text(secret)
            for command in [
                "gh pr create --title Test --body Clean --body " + secret,
                "gh pr create --title Test --body Clean -b" + secret,
                "gh pr create --title Test --body Clean -t" + secret,
                "gh pr create --title Test --body-file clean.md -Fsecret.md",
            ]:
                with self.subTest(option=command.rsplit(' ', 1)[0]):
                    output = self.run_hook({
                        "tool_name": "Bash", "cwd": directory,
                        "tool_input": {"command": command},
                    }, "codex")["hookSpecificOutput"]
                    self.assertEqual(output.get("permissionDecision"), "deny")
                    self.assertIn("秘密情報", output["permissionDecisionReason"])
                    self.assertNotIn(secret, json.dumps(output))

    def test_codex_cli_scans_a_complete_clean_commit_range(self):
        with tempfile.TemporaryDirectory() as directory:
            self.topic_repo(directory)
            output = self.run_hook({
                "tool_name": "Bash", "cwd": directory,
                "tool_input": {"command": "gh pr create --repo o/r --base main --head topic --title Test --body Clean"},
            }, "codex")["hookSpecificOutput"]
            self.assertNotIn("permissionDecision", output)
            self.assertIn("1 コミット", output["additionalContext"])
            self.assertNotIn("未検査。", output["additionalContext"])
            self.assertIn("既存の明示的な許可", output["additionalContext"])
            self.assertIn("再確認せず", output["additionalContext"])
            self.assertNotIn("未検査の範囲が残っています", output["additionalContext"])

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
            for client in ["claude", "codex"]:
                output = self.run_hook({
                    "tool_name": "Bash", "cwd": directory,
                    "tool_input": {"command": "gh pr create --base main --head topic --title Test"},
                }, client)
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertIn("秘密情報の疑い", output["hookSpecificOutput"]["permissionDecisionReason"])
                output = self.run_hook({
                    "tool_name": "Bash", "cwd": directory,
                    "tool_input": {"command": "git push -u origin topic"},
                }, client)
                self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertIn("push 前", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_codex_connector_preserves_scoped_authorization_and_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.run_hook({
                "tool_name": "mcp__codex_apps__github_create_pull_request", "cwd": directory,
                "tool_input": {"repository_full_name": "o/r", "base_branch": "main",
                               "head_branch": "topic", "title": "Test", "body": "Clean"},
            }, "codex")
            self.assertNotIn("permissionDecision", output["hookSpecificOutput"])
            self.assertIn("未検査", output["hookSpecificOutput"]["additionalContext"])
            self.assertIn("既存の明示的な許可", output["hookSpecificOutput"]["additionalContext"])
            self.assertIn("未検査の範囲が残っています", output["hookSpecificOutput"]["additionalContext"])
            self.assertIn("ユーザーの個別確認", output["hookSpecificOutput"]["additionalContext"])
            self.assertIn("自動審査", output["hookSpecificOutput"]["additionalContext"])
            self.assertNotIn("確認を恒久許可に保存しない", output["hookSpecificOutput"]["additionalContext"])

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
            blocked, report, _ = self.guard.inspect_pr(directory, {"base": "main", "head": "topic"})
            self.assertTrue(blocked)
            self.assertNotIn(secret, report)


class RemoteMutationGuardSpellingTest(unittest.TestCase):
    """Spellings of guarded operations measured for issue #310.

    Each expectedFailure records one spelling the guard lets through today;
    fixing the guard turns that test into an unexpected success.
    """

    FORCE = "git push --force origin main"
    REF = "repos/o/r/git/refs/heads/main"

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("remote_guard", HOOK)
        cls.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.guard)
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", directory], check=True, capture_output=True)
            subprocess.run(["git", "-C", directory, "config", "alias.publish", "push --force"], check=True)
            result = subprocess.run(
                ["python3", str(HOOK), "--client", "claude"],
                input=json.dumps({"tool_name": "Bash", "cwd": directory,
                                  "tool_input": {"command": "git publish origin main"}}),
                text=True, capture_output=True, check=True,
            )
        cls.config_alias_output = json.loads(result.stdout) if result.stdout else {}

    def assert_decisions(self, cases):
        for command, decision in cases:
            with self.subTest(command=command):
                self.assertEqual(self.guard.classify_shell(command)[0], decision)

    def assert_decision(self, command, decision):
        self.assertEqual(self.guard.classify_shell(command)[0], decision)

    def test_spellings_from_the_issue_table_keep_their_measured_decisions(self):
        self.assert_decisions([
            (self.FORCE, "deny"),
            ("env " + self.FORCE, "deny"),
            ("\\" + self.FORCE, "deny"),
            ("sh -c '" + self.FORCE + "'", "deny"),
            ("git -c alias.publish='push --force' publish origin main", "deny"),
            ("echo '" + self.FORCE + "'", "continue"),
        ])

    def test_wrappers_absolute_paths_and_ref_api_updates_are_blocked(self):
        self.assert_decisions([
            ("builtin " + self.FORCE, "deny"),
            ("exec " + self.FORCE, "deny"),
            ("nohup " + self.FORCE, "deny"),
            ("/usr/bin/" + self.FORCE, "deny"),
            ("gh api -X PATCH " + self.REF + " -f sha=abc -F force=true", "deny"),
            ("gh api -X DELETE " + self.REF, "deny"),
            ("/opt/homebrew/bin/gh pr create --title T --body B", "pr"),
        ])

    @unittest.expectedFailure
    def test_command_p_push_is_blocked(self):
        self.assert_decision("command -p " + self.FORCE, "deny")

    @unittest.expectedFailure
    def test_command_p_pr_create_requires_review(self):
        self.assert_decision("command -p gh pr create --title T --body B", "pr")

    @unittest.expectedFailure
    def test_exec_with_argv0_option_push_is_blocked(self):
        self.assert_decision("exec -a name " + self.FORCE, "deny")

    @unittest.expectedFailure
    def test_xargs_push_is_blocked(self):
        self.assert_decision("xargs " + self.FORCE + " < /dev/null", "deny")

    @unittest.expectedFailure
    def test_xargs_push_with_refs_from_stdin_is_blocked(self):
        self.assert_decision("echo main | xargs git push --force origin", "deny")

    @unittest.expectedFailure
    def test_xargs_pr_create_requires_review(self):
        self.assert_decision("xargs gh pr create --title T --body B < /dev/null", "pr")

    @unittest.expectedFailure
    def test_sudo_push_is_blocked(self):
        self.assert_decision("sudo " + self.FORCE, "deny")

    @unittest.expectedFailure
    def test_eval_push_is_blocked(self):
        self.assert_decision("eval '" + self.FORCE + "'", "deny")

    @unittest.expectedFailure
    def test_brace_group_push_is_blocked(self):
        self.assert_decision("{ " + self.FORCE + "; }", "deny")

    @unittest.expectedFailure
    def test_graphql_update_ref_with_force_is_blocked(self):
        self.assert_decision("gh api graphql -f query='mutation { updateRef(input: {refId: \"R\", oid: \"O\", force: true}) { clientMutationId } }'", "deny")

    @unittest.expectedFailure
    def test_graphql_delete_ref_is_blocked(self):
        self.assert_decision("gh api graphql -f query='mutation { deleteRef(input: {refId: \"R\"}) { clientMutationId } }'", "deny")

    @unittest.expectedFailure
    def test_pr_new_alias_requires_review(self):
        self.assert_decision("gh pr new --title T --body B", "pr")

    @unittest.expectedFailure
    def test_push_alias_from_repository_config_is_blocked(self):
        self.assertEqual(self.config_alias_output.get("hookSpecificOutput", {}).get("permissionDecision"), "deny")


class RemoteMutationGuardFallbackTest(unittest.TestCase):
    """Commands the shell parser rejects, as measured for issues #310 and #317."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("remote_guard", HOOK)
        cls.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.guard)

    def assert_decisions(self, commands, decision):
        for command in commands:
            with self.subTest(command=command):
                with self.assertRaises(self.guard.UnsupportedShell):
                    self.guard.ShellWords(command).parse()
                self.assertEqual(self.guard.classify_shell(command)[0], decision)

    def test_publication_calls_in_command_position_stay_blocked(self):
        self.assert_decisions([
            'branch=$(git branch --show-current); git push origin --delete "$branch"',
            'git commit -m "fix $ticket" && git push origin HEAD',
            'git add -- "$file" && rtk git -C "$dir" push -u origin topic',
            'body=$(cat "$draft"); gh pr create --title T --body "$body"',
            'gh pr new --title "$title" --body B',
            'gh api repos/o/r/issues/1/comments -F body=@"$file"',
            'jq -n "$payload" | gh api graphql --input -',
            'gh api -X "$method" repos/o/r/issues/1',
            'gh api --method=PATCH "repos/o/r/issues/$n" -f state=closed',
            'gh api graphql -f query="mutation { addComment(input: {subjectId: \\"$id\\"}) { clientMutationId } }"',
            'if [ -n "$b" ]; then git push origin "$b"; fi',
            'for b in $branches; do timeout 30 git push origin "$b"; done',
            'echo "$(git push origin "$b")"',
            'echo `git push origin $b`',
            'x=$y; bash -c \'git push origin main\'',
            'x=$y; bash -c \'gh api -X POST repos/o/r/issues/1/comments -f body=B\'',
            'x=$y; bash --norc -c \'git push origin main\'',
            'x=$y; sh -e -c \'git push origin main\'',
            'x=$y; cat <<EO\\\nF\n$(git push origin main)\nEOF\n',
            'x=$y; echo "$(case x in x) git push origin main;; esac)"',
            'x=$y; echo `echo \\`git push origin main\\``',
            'echo $\'don\\\'t\' "$x"; git push origin main',
            'x=$((1<<2))\ngit push origin main\n',
            'echo ${x:- #}; git push origin main',
            'x=$y; git > >(cat) push origin main',
            'time { git push origin "$b"; }',
            'diff <(git push origin main) "$x"',
            'title=${title:-${tag} #317}; gh pr create --title "$title" --body B',
            'x=$y; bash -c "git \\\n  push origin main"',
            "x=$y; bash -c $'echo ready\\n  git push origin main'",
            'cmd="git push origin main"; bash -c "$cmd"',
            'cmd="git push origin $b"; $cmd',
            "x=$y; bash <<'EOF'\ngit push origin main\nEOF\n",
            'echo "git push origin $b" | sh',
            'x=$y; bash -c "echo It\\\'s ready; git push origin main"',
            "x=$y; bash -c -o pipefail 'git push origin main'",
            "x=$y; bash -co pipefail 'git push origin main'",
            "x=$y; bash -s -- -c config <<'EOF'\ngit push origin main\nEOF\n",
            "x=$y; bash -o pipefail -c 'git push origin main'",
            'cat <<EOF\n$(echo "$x"\nEOF\ngit push origin main\n)\n',
            "x=$y; cat <<!\nIt's ready.\n!\ngit push origin main\n",
            'x=$y; a+=b git push origin main',
            'message=ready; [[ "$message" =~ ready|# ]] && git push origin main',
            "x=$y; /bin/sh -c 'gh api -X POST repos/o/r/issues/1/comments -f body=B'",
            'gh api -XDELETE "repos/o/r/git/refs/heads/$b"',
            'x=$y; time git push origin main',
            'x=$y; (git push origin main)',
            'cat <<EOF\n$(git push origin main)\nEOF\n',
            'cat <<EOF\n"$(git push origin main)"\nEOF\n',
            'cat <<-EOF\n\tbody\n\tEOF\ngit push origin "$b"\n',
            'cat "$x" <<\'A\' <<\'B\'\nA-body\nA\nB-body\nB\ngit push origin main\n',
            'gi\\\nt push origin "$b"',
            'git 2>/dev/null push origin "$b"',
            '>"$log" git push origin main',
            'git push "$b" --repo',
            'x=$y; gh pr create --title',
        ], "deny")

    def test_words_outside_command_position_do_not_block(self):
        self.assert_decisions([
            'cat > "$file" <<\'EOF\'\nRun git push origin main, then gh pr create.\nEOF\n',
            'git commit -F - <<EOF\nNever git push from $HOME; gh api is read-only here.\nEOF\n',
            'git stash push -m "wip $ticket"',
            'git log --oneline | grep -c "api" ; echo $?',
            'gh pr view "$n" --json body --jq .body | grep -n "git push"',
            'echo "$1: run gh pr create later"',
            'for n in 1 2 3; do gh api "repos/o/r/issues/$n" --jq .title; done',
            'gh api -X GET "repos/o/r/pulls/$n" | jq .head',
            'git -C "$dir" log --grep push',
            'echo "\\$(git push origin main) $x"',
            'cat "$x" <<\'A\' <<\'B\'\ngit push origin main\nA\ngh pr create\nB\n',
            'cat <<-EOF\n\tgit push origin main\n\tEOF\necho "$x"\n',
            'gh issue list --search "$q" --label',
            'echo "${#items[@]} items"; git stash push',
            'gh issue comment 1 --body "Run \\`git push\\` after $step"',
            'cat > "$f" <<\'EOF\'\nRun `git push` later.\nEOF\n',
            "x=$y; bash --norc -lc 'git status; echo \"git push later\"'",
        ], "continue")


class RemoteMutationGuardFallbackMissTest(unittest.TestCase):
    """Spellings the narrowed fallback lets through, recorded for issue #317.

    Each one either never occurs as shell syntax in the records measured for
    issue #310, or belongs to the forms the #317 review criterion leaves out of
    scope: zsh-only syntax, brace groups, nested heredocs, and options or
    scripts injected through expansions. Fixing the guard turns the test into
    an unexpected success.
    """

    MISSES = (
        ('line_continuation_between_dollar_and_paren', 'x=$y; echo "$\\\n(git push origin main)"'),
        ('legacy_arithmetic_expansion', 'echo "$x"; n=$[1<<2]\ngit push origin main\n'),
        ('heredoc_delimiter_with_substitution', 'x=$y; cat <<"$(true)"\nbody\n$(true)\ngit push origin main\n'),
        ('heredoc_delimiter_split_by_line_continuation', 'cat <<EOF\nEO\\\nF\ngit push origin "$b"\n'),
        ('empty_heredoc_delimiter', "x=$y; cat <<''\n'\n\ngit push origin main\n"),
        ('crlf_heredoc', "x=$y; cat <<'EOF'\r\nEOF\r\ngit push origin main # publish\r\n"),
        ('heredoc_closed_by_paren_inside_substitution', 'x=$y; git commit -m "$(cat <<\'EOF\'\nmsg\nEOF)" && git push origin main'),
        ('heredoc_started_inside_parentheses', "x=$y; (cat <<'EOF')\n'\nEOF\ngit push origin main\n"),
        ('heredoc_read_in_piped_subshell', 'x=$y; cat <<EOF | (\npayload\nEOF\ncat\n)\ngit push origin main\n'),
        ('two_pending_heredocs_in_nested_frames', "x=$y; cat <<'OUT' | (cat <<'IN'\nouter\nOUT\ninner\nIN\n)\ngit push origin main\n"),
        ('tab_stripped_heredoc_with_nested_heredoc', "x=$y; cat <<-OUT\n$(cat <<'IN'\n\tIN\n\tgit push origin main\n)\nOUT\n"),
        ('heredoc_operator_split_by_line_continuation', "x=$y; cat <\\\n<'EOF'\n'\nEOF\ngit push origin main\n"),
        ('heredoc_operator_in_array_subscript', 'a[1<<n ]=3\ngit push origin "$b"\nn'),
        ('ampersand_redirect_before_subcommand', 'git &>/dev/null push origin "$b"'),
        ('named_descriptor_redirect', 'git {fd}>/dev/null push origin "$b"'),
        ('redirect_target_after_line_continuation', 'x=$y; > \\\n  publish.log git push origin main'),
        ('noclobber_override_redirect', 'x=$y; >| publish.log git push origin main'),
        ('zsh_clobber_redirect', 'x=$y; >! publish.log git push origin main'),
        ('zsh_append_both_redirect', 'x=$y; >>&publish.log git push origin main'),
        ('comment_after_process_substitution', 'cat <(echo a)# ; git push origin "$b"'),
        ('comment_inside_substitution_in_bash_3_2', 'y=$v; x=$(echo a # ) ; git push origin main\n)'),
        ('ansi_c_quote_after_line_continuation', 'echo $\\\n\'a\\\'\' ; git push origin "$b" #\''),
        ('coproc', 'coproc git push origin "$b"'),
        ('for_without_in', 'x=$y; set -- main; for branch do git push origin "$branch"; done'),
        ('env_with_directory_option', 'x=$y; env -C repo git push origin main'),
        ('zsh_repeat', "x=$y; zsh -c 'repeat 1 git push origin main'"),
        ('zsh_nocorrect', 'x=$y; nocorrect git push origin main'),
        ('zsh_brace_loop', 'while [[ -n $b ]] { git push origin "$b"; break; }'),
        ('zsh_short_if', 'x=$y; if [[ -n $b ]] git push origin $b'),
        ('zsh_brace_group_without_space', 'x=$y; {git push origin main}'),
        ('zsh_glob_flag', 'x=$y; print -r -- (#i)readme*; git push origin main'),
        ('zsh_pattern_with_hash', 'x=$y; ls (a|#b); git push origin main'),
        ('shell_script_built_by_substitution', 'x=$y; bash -c "echo $(printf \'ready; git push origin main\')"'),
        ('git_subcommand_from_variable', 'x=$y; git "$sub" origin main # push'),
        ('gh_subcommand_from_variable', 'x=$y; gh "$cmd" create --title T --body B'),
        ('api_option_from_variable', 'api_flag=-f; gh api repos/o/r/issues/1/comments $api_flag body=B'),
        ('api_argument_word_splitting', 'request="1/comments -f body=B"; gh api repos/o/r/issues/$request'),
        ('quoted_at_expansion_in_api_argument', 'set -- "" -f body=B; gh api "repos/o/r/issues/1/comments$@"'),
        ('api_field_in_short_option_cluster', 'x=$y; gh api -if body=B repos/o/r/issues/1/comments'),
        ('api_method_in_short_option_cluster', 'x=$y; gh api -iXPOST repos/o/r/issues/1/comments'),
        ('pr_create_after_option', 'x=$y; gh pr -R o/r create --title T --body B'),
    )

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("remote_guard", HOOK)
        cls.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.guard)

    def test_recorded_misses_reach_the_fallback(self):
        for name, command in self.MISSES:
            with self.subTest(name=name):
                with self.assertRaises(self.guard.UnsupportedShell):
                    self.guard.ShellWords(command).parse()


for _name, _command in RemoteMutationGuardFallbackMissTest.MISSES:
    setattr(RemoteMutationGuardFallbackMissTest, f"test_{_name}_is_blocked", unittest.expectedFailure(
        lambda self, command=_command: self.assertEqual(self.guard.classify_shell(command)[0], "deny")))


if __name__ == "__main__":
    unittest.main()
