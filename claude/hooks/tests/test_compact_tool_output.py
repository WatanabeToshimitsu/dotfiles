import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "compact-tool-output.py"


class CompactToolOutputTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.temp_dir.name) / "cache"
        self.env = {
            **os.environ,
            "CLAUDE_TOOL_OUTPUT_CACHE_DIR": str(self.cache_dir),
            "CLAUDE_TOOL_OUTPUT_MAX_CHARS": "1000",
            "CLAUDE_TOOL_OUTPUT_PREVIEW_CHARS": "500",
            "CLAUDE_TOOL_OUTPUT_RETENTION_DAYS": "7",
        }

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_hook(self, payload: dict) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

    def run_raw_hook(self, payload: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=payload,
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

    def archive_id_from(self, output: dict) -> str:
        encoded = json.dumps(output, ensure_ascii=False)
        match = re.search(r"archive ([a-f0-9]{20})", encoded)
        self.assertIsNotNone(match)
        return match.group(1)

    def test_leaves_small_output_unchanged(self) -> None:
        result = self.run_hook(
            {
                "session_id": "session-1",
                "tool_use_id": "tool-1",
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/example"},
                "tool_response": {"content": "small result", "lineCount": 1},
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        marker = self.cache_dir / ".last-invoked"
        self.assertTrue(marker.is_file())
        self.assertEqual(stat.S_IMODE(marker.stat().st_mode), 0o600)
        self.assertEqual(list(self.cache_dir.glob("*.json")), [])

    def test_compacts_large_output_and_archives_the_original(self) -> None:
        original_response = {
            "content": "start\n" + "detail line\n" * 300 + "end\n",
            "lineCount": 302,
        }
        result = self.run_hook(
            {
                "session_id": "session-1",
                "tool_use_id": "tool-2",
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/example"},
                "tool_response": original_response,
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        updated = output["hookSpecificOutput"]["updatedToolOutput"]
        self.assertEqual(set(updated), set(original_response))
        self.assertLess(len(json.dumps(updated)), 1000)
        archive_id = self.archive_id_from(output)

        archive_path = self.cache_dir / f"{archive_id}.json"
        archive = json.loads(archive_path.read_text())
        self.assertEqual(archive["tool_response"], original_response)
        self.assertEqual(stat.S_IMODE(archive_path.stat().st_mode), 0o600)

    def test_preserves_error_evidence_in_compacted_mcp_output(self) -> None:
        original_response = {
            "content": [
                {"type": "text", "text": "normal line\n" * 300},
                {
                    "type": "text",
                    "text": "more detail\n" * 200
                    + "CRITICAL failure: database unavailable\n"
                    + "tail\n" * 100,
                },
            ],
            "isError": True,
        }
        result = self.run_hook(
            {
                "session_id": "session-2",
                "tool_use_id": "tool-3",
                "tool_name": "mcp__example__query",
                "tool_input": {"query": "large"},
                "tool_response": original_response,
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        updated = output["hookSpecificOutput"]["updatedMCPToolOutput"]
        self.assertIs(updated["isError"], True)
        self.assertEqual(len(updated["content"]), 2)
        self.assertIn("CRITICAL failure: database unavailable", json.dumps(updated))

    def test_expand_can_filter_an_archived_result(self) -> None:
        original_response = {
            "content": "alpha\n" + "noise\n" * 250 + "TARGET value\n" + "omega\n"
        }
        hook_result = self.run_hook(
            {
                "session_id": "session-3",
                "tool_use_id": "tool-4",
                "tool_name": "WebFetch",
                "tool_input": {"url": "https://example.com"},
                "tool_response": original_response,
            }
        )
        output = json.loads(hook_result.stdout)
        archive_id = self.archive_id_from(output)

        expand_result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "expand",
                archive_id,
                "--grep",
                "target",
                "--context",
                "1",
            ],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

        self.assertEqual(expand_result.returncode, 0, expand_result.stderr)
        self.assertIn("TARGET value", expand_result.stdout)
        self.assertLess(len(expand_result.stdout), 500)

    def test_ignores_unsupported_tools(self) -> None:
        result = self.run_hook(
            {
                "session_id": "session-4",
                "tool_use_id": "tool-5",
                "tool_name": "Bash",
                "tool_input": {"command": "example"},
                "tool_response": {"content": "large\n" * 1000},
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.cache_dir.exists())

    def test_stats_reports_saved_output(self) -> None:
        hook_result = self.run_hook(
            {
                "session_id": "session-5",
                "tool_use_id": "tool-6",
                "tool_name": "Glob",
                "tool_input": {"pattern": "**/*"},
                "tool_response": {"filenames": "file.txt\n" * 500},
            }
        )
        self.assertEqual(hook_result.returncode, 0, hook_result.stderr)

        stats_result = subprocess.run(
            [sys.executable, str(SCRIPT), "stats"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

        self.assertEqual(stats_result.returncode, 0, stats_result.stderr)
        self.assertIn("archives: 1", stats_result.stdout)
        self.assertRegex(stats_result.stdout, r"saved: [1-9][0-9,]* chars")
        self.assertNotIn("hook active", stats_result.stdout)
        self.assertNotIn("hook failures", stats_result.stdout)

    def test_health_reports_recent_hook_without_compactions(self) -> None:
        hook_result = self.run_hook(
            {
                "session_id": "session-6",
                "tool_use_id": "tool-7",
                "tool_name": "Read",
                "tool_response": {"content": "small"},
            }
        )
        self.assertEqual(hook_result.returncode, 0, hook_result.stderr)

        health_result = subprocess.run(
            [sys.executable, str(SCRIPT), "health", "--days", "7"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

        self.assertEqual(health_result.returncode, 0, health_result.stderr)
        self.assertIn("hook active: yes", health_result.stdout)
        self.assertNotIn("hook last invoked: never", health_result.stdout)
        self.assertIn("hook last error: none", health_result.stdout)
        self.assertNotIn("archives", health_result.stdout)

    def test_records_failure_metadata_without_payload_content(self) -> None:
        secret = "credential-do-not-log"
        result = self.run_raw_hook("{" + secret)

        self.assertEqual(result.returncode, 0)
        self.assertNotIn(secret, result.stderr)
        error_file = self.cache_dir / ".last-error"
        self.assertTrue(error_file.is_file())
        error_record = json.loads(error_file.read_text())
        self.assertEqual(error_record["error_type"], "JSONDecodeError")
        self.assertNotIn(secret, json.dumps(error_record))

        health_result = subprocess.run(
            [sys.executable, str(SCRIPT), "health"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        self.assertIn("hook active: no", health_result.stdout)
        self.assertIn("hook last error: JSONDecodeError at ", health_result.stdout)

        hook_result = self.run_hook(
            {
                "session_id": "session-7",
                "tool_use_id": "tool-8",
                "tool_name": "Read",
                "tool_response": {"content": "small"},
            }
        )
        self.assertEqual(hook_result.returncode, 0, hook_result.stderr)
        self.assertFalse((self.cache_dir / ".last-error").exists())

        health_result = subprocess.run(
            [sys.executable, str(SCRIPT), "health"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(health_result.returncode, 0, health_result.stderr)
        self.assertIn("hook active: yes", health_result.stdout)
        self.assertIn("hook last error: none", health_result.stdout)

    def test_health_marks_old_invocation_inactive(self) -> None:
        hook_result = self.run_hook(
            {
                "session_id": "session-8",
                "tool_use_id": "tool-9",
                "tool_name": "Read",
                "tool_response": {"content": "small"},
            }
        )
        self.assertEqual(hook_result.returncode, 0, hook_result.stderr)
        marker = self.cache_dir / ".last-invoked"
        os.utime(marker, (0, 0))

        health_result = subprocess.run(
            [sys.executable, str(SCRIPT), "health", "--days", "7"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

        self.assertEqual(health_result.returncode, 0, health_result.stderr)
        self.assertIn("hook active: no", health_result.stdout)

    def test_health_reports_and_clears_legacy_error_records(self) -> None:
        legacy_errors = self.cache_dir / ".errors"
        legacy_errors.mkdir(parents=True)
        (legacy_errors / "old.json").write_text(
            json.dumps({"error_type": "ValueError"}), encoding="utf-8"
        )

        health_result = subprocess.run(
            [sys.executable, str(SCRIPT), "health"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(health_result.returncode, 0, health_result.stderr)
        self.assertIn(
            "hook last error: legacy records pending migration",
            health_result.stdout,
        )

        hook_result = self.run_hook(
            {
                "session_id": "session-9",
                "tool_use_id": "tool-10",
                "tool_name": "Read",
                "tool_response": {"content": "small"},
            }
        )
        self.assertEqual(hook_result.returncode, 0, hook_result.stderr)
        self.assertFalse(legacy_errors.exists())

        health_result = subprocess.run(
            [sys.executable, str(SCRIPT), "health"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        self.assertIn("hook last error: none", health_result.stdout)

    def test_expand_rejects_an_invalid_archive_id(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "expand", "../settings"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("archive ID must be", result.stderr)


if __name__ == "__main__":
    unittest.main()
