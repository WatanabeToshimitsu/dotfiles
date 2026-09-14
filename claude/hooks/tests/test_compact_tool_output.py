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


def read_response(content: str) -> dict:
    return {
        "type": "text",
        "file": {
            "filePath": "src/example.txt",
            "content": content,
            "numLines": len(content.splitlines()),
            "startLine": 1,
            "totalLines": len(content.splitlines()),
        },
    }


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
                "tool_response": read_response("small result"),
            }
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.cache_dir.exists())

    def test_compacts_large_output_and_archives_the_original(self) -> None:
        original_response = read_response("start\n" + "detail line\n" * 300 + "end\n")
        original_response["artifactRead"] = {"slug": "example", "ver": "version-123"}
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
        self.assertNotEqual(updated["file"]["content"], original_response["file"]["content"])
        self.assertLess(len(json.dumps(updated)), 1000)
        archive_id = self.archive_id_from(output)
        updated["file"]["content"] = original_response["file"]["content"]
        self.assertEqual(updated, original_response)

        archive_path = self.cache_dir / f"{archive_id}.json"
        archive = json.loads(archive_path.read_text())
        self.assertEqual(archive["tool_response"], original_response)
        self.assertEqual(stat.S_IMODE(archive_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.cache_dir.stat().st_mode), 0o700)

        expanded = subprocess.run(
            [sys.executable, str(SCRIPT), "expand", archive_id],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(expanded.returncode, 0, expanded.stderr)
        self.assertEqual(json.loads(expanded.stdout), original_response)

    def test_compacts_mcp_text_without_changing_blocks_or_metadata(self) -> None:
        self.env["CLAUDE_TOOL_OUTPUT_MAX_CHARS"] = "40000"
        self.env["CLAUDE_TOOL_OUTPUT_PREVIEW_CHARS"] = "20000"
        blocks = [
            {"type": "text", "text": "detail\n" * 20000},
            {"type": "image", "mimeType": "image/png", "data": "aGVsbG8="},
            {"type": "resource", "resource": {"uri": "file:///example", "text": "opaque"}},
            {"type": "future", "id": "record-12345678", "status": "failed"},
            *[{"type": "text", "text": f"item-{index}"} for index in range(205)],
        ]
        for original in [blocks, {"content": blocks, "isError": False,
                                 "structuredContent": {"id": "record-123", "status": "failed"},
                                 "_meta": {"cursor": "next-page-123"}}]:
            with self.subTest(wrapped=isinstance(original, dict)):
                result = self.run_hook({"tool_name": "mcp__example__query",
                                        "tool_response": original})
                self.assertEqual(result.returncode, 0, result.stderr)
                output = json.loads(result.stdout)
                updated = output["hookSpecificOutput"]["updatedMCPToolOutput"]
                updated_blocks = updated["content"] if isinstance(updated, dict) else updated
                self.assertLess(len(json.dumps(updated)), len(json.dumps(original)))
                self.assertIn("archive ", updated_blocks[0]["text"])
                updated_blocks[0]["text"] = blocks[0]["text"]
                self.assertEqual(updated, original)

    def test_compacts_known_grep_and_webfetch_bodies(self) -> None:
        cases = [
            ("Grep", {"mode": "content", "numFiles": 1, "filenames": ["src/example.txt"],
                      "content": "src/example.txt:1: detail\n" * 300, "numLines": 300,
                      "appliedLimit": 300, "appliedOffset": 1}, "content"),
            ("WebFetch", {"bytes": 4000, "code": 200, "codeText": "OK",
                          "result": "detail line\n" * 300, "durationMs": 12,
                          "url": "https://example.com/page"}, "result"),
        ]
        for tool, original, field in cases:
            with self.subTest(tool=tool):
                result = self.run_hook({"tool_name": tool, "tool_response": original})
                self.assertEqual(result.returncode, 0, result.stderr)
                updated = json.loads(result.stdout)["hookSpecificOutput"]["updatedToolOutput"]
                self.assertLess(len(updated[field]), len(original[field]))
                self.assertIn("archive ", updated[field])
                updated[field] = original[field]
                self.assertEqual(updated, original)

    def test_leaves_unknown_shapes_and_nontext_results_unchanged(self) -> None:
        large = "detail" * 1000
        cases = [
            ("Read", {"content": large, "lineCount": 1}),
            ("Read", {"type": "image", "file": {"base64": large, "type": "image/png"}}),
            ("Read", {"type": "pdf", "file": {"base64": large, "filePath": "example.pdf"}}),
            ("Read", {"type": "notebook", "file": {"cells": [{"source": large}]}}),
            ("Read", {"type": "parts", "pages": [{"base64": large, "mediaType": "image/png"}]}),
            ("Grep", {"mode": "files_with_matches", "numFiles": 300,
                      "filenames": [f"src/file-{index}.txt" for index in range(300)]}),
            ("Grep", {"mode": "count", "content": large, "filenames": [], "numFiles": 0}),
            ("Glob", {"filenames": [f"src/file-{index}.txt" for index in range(300)],
                      "numFiles": 300, "durationMs": 1, "truncated": False}),
            ("WebSearch", {"query": "example", "results": [large]}),
            ("WebFetch", {"code": "200", "result": large}),
            ("mcp__example__query", large),
            ("mcp__example__query", {"content": large, "id": "record-123", "status": "failed"}),
            ("mcp__example__query", [{"id": "record-123", "status": "failed", "body": large}]),
        ]
        for tool, original in cases:
            with self.subTest(tool=tool, shape=str(original)[:80]):
                result = self.run_hook({"tool_name": tool, "tool_response": original})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertFalse(self.cache_dir.exists())

    def test_leaves_error_results_and_diagnostic_bodies_unchanged(self) -> None:
        diagnostic = "detail\n" * 300 + "CRITICAL failure: " + "cause" * 1000 + "\nstack frame\n"
        cases = [
            ("mcp__example__query", {"content": [{"type": "text", "text": "cause" * 1000}],
                                   "isError": True}),
            ("mcp__example__query", [{"type": "text", "text": diagnostic}]),
            ("Read", read_response(diagnostic)),
            ("WebFetch", {"bytes": 5000, "code": 500, "codeText": "Unavailable",
                          "result": "cause" * 1000, "durationMs": 1, "url": "https://example.com"}),
        ]
        for tool, original in cases:
            with self.subTest(tool=tool, shape=type(original).__name__):
                result = self.run_hook({"tool_name": tool, "tool_response": original})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertFalse(self.cache_dir.exists())

    def test_preserves_full_diagnostics_while_compacting_another_body(self) -> None:
        self.env["CLAUDE_TOOL_OUTPUT_MAX_CHARS"] = "10000"
        self.env["CLAUDE_TOOL_OUTPUT_PREVIEW_CHARS"] = "6000"
        original = [{"type": "text", "text": "detail\n" * 20000},
                    {"type": "text", "text": "WARNING: " + "cause" * 800 + "\n  at worker\n"}]
        result = self.run_hook({"tool_name": "mcp__example__query", "tool_response": original})
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = json.loads(result.stdout)["hookSpecificOutput"]["updatedMCPToolOutput"]
        self.assertEqual(updated[1], original[1])
        self.assertLess(len(updated[0]["text"]), len(original[0]["text"]))

    def test_compacts_multiple_long_text_blocks_and_keeps_short_text(self) -> None:
        original = [
            {"type": "text", "text": "short context"},
            {"type": "text", "text": "large body" * 1000},
            {"type": "text", "text": "more context" * 2000},
        ]
        result = self.run_hook({"tool_name": "mcp__example__query", "tool_response": original})
        self.assertEqual(result.returncode, 0, result.stderr)
        updated = json.loads(result.stdout)["hookSpecificOutput"]["updatedMCPToolOutput"]
        self.assertEqual(updated[0], original[0])
        for before, after in zip(original[1:], updated[1:]):
            self.assertEqual(after["type"], "text")
            self.assertLess(len(after["text"]), len(before["text"]))
        self.assertEqual(json.dumps(updated).count("Claude tool output compacted"), 1)

    def test_leaves_output_when_protected_data_exhausts_preview_budget(self) -> None:
        result = self.run_hook({"tool_name": "mcp__example__query", "tool_response": [
            {"type": "text", "text": "detail" * 1000},
            {"type": "image", "mimeType": "image/png", "data": "aGVsbG8=" * 1000},
        ]})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.cache_dir.exists())

    def test_expand_can_filter_an_archived_result(self) -> None:
        original_response = read_response(
            "alpha\n" + "noise\n" * 250 + "TARGET value\n" + "omega\n"
        )
        hook_result = self.run_hook(
            {
                "session_id": "session-3",
                "tool_use_id": "tool-4",
                "tool_name": "Read",
                "tool_input": {"file_path": "/tmp/example"},
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

    def test_malformed_input_fails_open_without_retaining_payload(self) -> None:
        secret = "credential-do-not-log"
        result = self.run_raw_hook("{" + secret)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(secret, result.stderr)
        self.assertFalse(self.cache_dir.exists())

    def test_stats_reports_saved_output(self) -> None:
        hook_result = self.run_hook(
            {
                "session_id": "session-5",
                "tool_use_id": "tool-6",
                "tool_name": "Read",
                "tool_response": read_response("detail\n" * 500),
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
        self.assertNotIn("tokens", stats_result.stdout)
        self.assertNotIn("hook active", stats_result.stdout)
        self.assertNotIn("hook failures", stats_result.stdout)

    def test_retired_health_markers_do_not_affect_stats_or_hook(self) -> None:
        self.cache_dir.mkdir(parents=True)
        (self.cache_dir / ".last-invoked").touch()
        (self.cache_dir / ".last-error").write_text("retired", encoding="utf-8")
        legacy_errors = self.cache_dir / ".errors"
        legacy_errors.mkdir()
        (legacy_errors / "old.json").write_text(
            json.dumps({"error_type": "ValueError"}), encoding="utf-8"
        )

        stats_result = subprocess.run(
            [sys.executable, str(SCRIPT), "stats"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(stats_result.returncode, 0, stats_result.stderr)
        self.assertIn("archives: 0", stats_result.stdout)

        hook_result = self.run_hook(
            {
                "session_id": "session-6",
                "tool_use_id": "tool-7",
                "tool_name": "Read",
                "tool_response": read_response("retained line\n" * 300),
            }
        )
        self.assertEqual(hook_result.returncode, 0, hook_result.stderr)
        archive_id = self.archive_id_from(json.loads(hook_result.stdout))
        expand_result = subprocess.run(
            [sys.executable, str(SCRIPT), "expand", archive_id, "--grep", "retained"],
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(expand_result.returncode, 0, expand_result.stderr)
        self.assertIn("retained line", expand_result.stdout)
        self.assertTrue((self.cache_dir / ".last-invoked").exists())
        self.assertTrue((self.cache_dir / ".last-error").exists())
        self.assertTrue(legacy_errors.exists())

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
