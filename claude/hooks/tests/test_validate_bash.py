import json
from pathlib import Path
import subprocess
import unittest


HOOK = Path(__file__).resolve().parents[1] / "validate-bash.sh"


class ValidateBashTests(unittest.TestCase):
    def decision(self, command):
        result = subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
            text=True,
            capture_output=True,
            timeout=5,
            check=True,
        )
        if not result.stdout:
            return "allow"
        return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]

    def test_literal_prose_is_not_a_command(self):
        cases = [
            "git commit -m 'Keep git add -A blocked'",
            'git commit --message="Keep git add --all blocked"',
            "gh pr create --body 'git add -A remains denied' --title 'git add . policy'",
            "gh pr edit 111 --body 'Do not run git add -A'",
            "git status # do not run git add -A",
            "# don't run git add -A\ngit status",
            "printf '%s\\n' 'git add -A'",
            "git commit -m 'literal $(git add -A) and `git add --all`'",
        ]
        for command in cases:
            with self.subTest(command=command):
                self.assertEqual(self.decision(command), "allow")

    def test_heredoc_prose_is_not_a_command(self):
        cases = [
            "git commit -F - <<'EOF'\nKeep git add -A blocked\nEOF\n",
            'gh pr create --body-file - <<"EOF"\nDo not git add --all\nEOF\n',
            "cat <<EOF\ngit add -A\nEOF\n",
            "cat <<-'EOF'\n\tgit add -A\n\tEOF\n",
            "cat <<'FIRST' <<'SECOND'\ngit add -A\nFIRST\ngit add --all\nSECOND\n",
            'git commit -F "$(cat <<\'EOF\'\nKeep git add -A blocked\nEOF\n)"',
            'gh pr create --body "$(cat <<\'EOF\'\ngit add -A remains denied\nEOF\n)"',
        ]
        for command in cases:
            with self.subTest(command=command):
                self.assertEqual(self.decision(command), "allow")

    def test_executable_staging_is_still_denied(self):
        cases = [
            "git add -A", "git add --all", "git add .",
            "git add . && git status",
            "git status; git add -A", "git status\ngit add --all",
            "git status # harmless\ngit add -A",
            "git commit -m 'git add -A is prohibited'; git add -A",
            "cat <<'EOF'\nmessage\nEOF\ngit add -A",
            "cat <<'EOF'; git add -A\nmessage\nEOF\n",
            "bash -c 'git add -A'", "eval 'git add -A'",
            "bash <<'EOF'\ngit add -A\nEOF\n",
            "cat <<'EOF' | bash\ngit add -A\nEOF\n",
            'git commit -m "$(git add -A)"',
            'git commit -m "`git add -A`"',
            "cat <<EOF\n$(git add -A)\nEOF\n",
            "cat <<EOF\n`git add -A`\nEOF\n",
            "git add README.md -A", "git add '-A'", "git add \".\"",
            "rtk git add -A", "rtk proxy git add -A",
            'echo "$HOME"\ngit add .\ngit status',
            "git \\\n add -A",
            "git add \\\n -A",
        ]
        for command in cases:
            with self.subTest(command=command):
                self.assertEqual(self.decision(command), "deny")

    def test_explicit_paths_and_non_bash_input_are_preserved(self):
        for command in ["git add README.md", "git add ./src/main.ts", "git add -- -A"]:
            with self.subTest(command=command):
                self.assertEqual(self.decision(command), "allow")
        for payload in ["not json", '{"tool_name":"Read","tool_input":{}}']:
            result = subprocess.run(["bash", str(HOOK)], input=payload, text=True,
                                    capture_output=True, timeout=5, check=True)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
