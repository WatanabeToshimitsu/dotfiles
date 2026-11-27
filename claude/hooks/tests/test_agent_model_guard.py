import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "agent-model-guard.py"
SETTINGS = Path(__file__).resolve().parents[2] / "settings.json"


def matcher_selects(matcher, value):
    """Apply the hooks matcher rules in https://code.claude.com/docs/en/hooks."""
    if matcher in (None, "", "*"):
        return True
    if re.fullmatch(r"[A-Za-z0-9_\- ,|]*", matcher):
        return value in {part.strip() for part in re.split(r"[|,]", matcher)}
    # Why not Python's re: matchers are JavaScript regular expressions, and some syntax differs.
    test = "process.exit(new RegExp(process.argv[1]).test(process.argv[2]) ? 0 : 1)"
    return subprocess.run(["node", "-e", test, "--", matcher, value]).returncode == 0


def decide(command, tool_input, tool_name="Agent", env=None):
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}
    result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True,
                            env=env, timeout=10, check=True)
    if not result.stdout.strip():
        return None
    return json.loads(result.stdout)["hookSpecificOutput"].get("permissionDecision")


class AgentModelGuardTest(unittest.TestCase):
    run_guard = staticmethod(lambda tool_input, **kw: decide([sys.executable, str(SCRIPT)], tool_input, **kw))

    def test_denies_a_subagent_call_without_a_model(self):
        self.assertEqual(self.run_guard({"subagent_type": "general-purpose", "prompt": "x"}), "deny")

    def test_denies_an_empty_model(self):
        self.assertEqual(self.run_guard({"subagent_type": "Explore", "prompt": "x", "model": ""}), "deny")

    def test_denies_a_defined_agent_without_a_call_time_model(self):
        self.assertEqual(self.run_guard({"subagent_type": "fable-deep", "prompt": "x"}), "deny")

    def test_allows_a_call_that_names_a_model(self):
        self.assertIsNone(self.run_guard({"subagent_type": "general-purpose", "prompt": "x", "model": "sonnet"}))

    def test_allows_a_fork_which_cannot_take_a_model(self):
        self.assertIsNone(self.run_guard({"subagent_type": "fork", "prompt": "x"}))

    def test_ignores_other_tools(self):
        self.assertIsNone(self.run_guard({"command": "ls"}, tool_name="Bash"))

    def test_settings_register_the_guard_for_agent_calls(self):
        hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
        wired = [hook["command"] for group in hooks.get("PreToolUse", [])
                 if matcher_selects(group.get("matcher"), "Agent")
                 for hook in group["hooks"] if SCRIPT.name in hook["command"]]
        self.assertEqual(len(wired), 1)
        with tempfile.TemporaryDirectory() as home:
            (Path(home) / ".claude").mkdir()
            (Path(home) / ".claude" / "hooks").symlink_to(SCRIPT.parent)
            env = {**os.environ, "HOME": home}
            command = ["bash", "-c", wired[0]]
            self.assertEqual(decide(command, {"subagent_type": "general-purpose", "prompt": "x"}, env=env), "deny")
            self.assertIsNone(decide(command, {"subagent_type": "general-purpose", "prompt": "x", "model": "haiku"},
                                     env=env))


if __name__ == "__main__":
    unittest.main()
