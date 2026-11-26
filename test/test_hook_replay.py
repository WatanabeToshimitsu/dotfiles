import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hook-replay.py"
PRIVATE = "echo private-marker-7f3a"


def transcript_line(command):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "running"},
        {"type": "tool_use", "name": "Bash", "input": {"command": command}},
    ]}})


class HookReplayTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        transcripts = self.root / "projects" / "repo"
        transcripts.mkdir(parents=True)
        recent = ["git add -A", "git add -A", PRIVATE, "git push --force origin main"]
        (transcripts / "recent.jsonl").write_text(
            "\n".join(map(transcript_line, recent)) + "\nnot json\n")
        old = transcripts / "old.jsonl"
        old.write_text(transcript_line("git add --all") + "\n")
        month_ago = time.time() - 30 * 86400
        os.utime(old, (month_ago, month_ago))
        # The old guards allow everything, standing in for a version before a fix.
        self.allow_all = self.root / "allow-all"
        self.allow_all.mkdir()
        for name in ("validate-bash.sh", "remote-mutation-guard.py"):
            (self.allow_all / name).write_text("exit 0\n" if name.endswith(".sh") else "")

    def replay(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--transcripts", str(self.root / "projects"),
                               "--out", str(self.root / "details.jsonl"), *args],
                              capture_output=True, text=True, timeout=120)

    def test_counts_changed_decisions_between_two_hook_versions(self):
        result = self.replay("--before", str(self.allow_all))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("commands replayed: 3", result.stdout)
        self.assertIn("validate-bash: allow -> deny: 1", result.stdout)
        self.assertIn("remote-mutation-guard: allow -> deny: 1", result.stdout)
        details = [json.loads(line) for line in (self.root / "details.jsonl").read_text().splitlines()]
        self.assertEqual(sorted(entry["command"] for entry in details),
                         ["git add -A", "git push --force origin main"])

    def test_the_same_version_on_both_sides_changes_nothing(self):
        result = self.replay("--before", "HEAD", "--after", "HEAD")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("changed decisions: 0", result.stdout)

    def test_commands_stay_out_of_stdout_and_the_repository(self):
        result = self.replay("--before", str(self.allow_all))
        self.assertNotIn("private-marker", result.stdout + result.stderr)
        inside = subprocess.run([sys.executable, str(SCRIPT), "--before", "HEAD",
                                 "--out", str(ROOT / "replay.jsonl")], capture_output=True, text=True)
        self.assertNotEqual(inside.returncode, 0)
        self.assertFalse((ROOT / "replay.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
