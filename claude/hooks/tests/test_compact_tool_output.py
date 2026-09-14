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
LARGE = "detail line\n" * 300


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
        self.addCleanup(self.temp_dir.cleanup)
        self.cache_dir = Path(self.temp_dir.name) / "cache"
        self.env = {
            **os.environ,
            "CLAUDE_TOOL_OUTPUT_CACHE_DIR": str(self.cache_dir),
            "CLAUDE_TOOL_OUTPUT_MAX_CHARS": "1000",
            "CLAUDE_TOOL_OUTPUT_PREVIEW_CHARS": "500",
            "CLAUDE_TOOL_OUTPUT_RETENTION_DAYS": "7",
        }

    def run_script(
        self, *args: str, input_text: str = "", expected_status: int = 0
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=input_text,
            text=True,
            capture_output=True,
            env=self.env,
            check=False,
        )
        self.assertEqual(result.returncode, expected_status, result.stderr)
        return result

    def run_hook(self, tool: str, response: object) -> subprocess.CompletedProcess[str]:
        return self.run_script(
            input_text=json.dumps({"tool_name": tool, "tool_response": response})
        )

    def test_read_metadata_and_archive_commands_preserve_original(self) -> None:
        legacy = [
            self.cache_dir / name
            for name in (".last-invoked", ".last-error", ".errors/old.json")
        ]
        for path in legacy:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}")
        self.assertIn("archives: 0", self.run_script("stats").stdout)
        original = read_response("alpha\n" + LARGE + "TARGET value\nomega\n")
        original["artifactRead"] = {"slug": "example", "ver": "version-123"}

        result = self.run_hook("Read", original)
        updated = json.loads(result.stdout)["hookSpecificOutput"]["updatedToolOutput"]
        preview = updated["file"]["content"]
        self.assertLess(len(preview), len(original["file"]["content"]))
        match = re.search(r"archive ([a-f0-9]{20})", preview)
        self.assertIsNotNone(match)
        archive_id = match.group(1)
        updated["file"]["content"] = original["file"]["content"]
        self.assertEqual(updated, original)

        archive_path = self.cache_dir / f"{archive_id}.json"
        self.assertEqual(json.loads(archive_path.read_text())["tool_response"], original)
        self.assertEqual(stat.S_IMODE(archive_path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.cache_dir.stat().st_mode), 0o700)
        self.assertEqual(json.loads(self.run_script("expand", archive_id).stdout), original)
        focused = self.run_script("expand", archive_id, "--grep", "target", "--context", "1")
        self.assertIn("TARGET value", focused.stdout)
        self.assertLess(len(focused.stdout), 500)
        stats = self.run_script("stats").stdout
        self.assertIn("archives: 1", stats)
        self.assertRegex(stats, r"saved: [1-9][0-9,]* chars")
        for absent in ("tokens", "hook active", "hook failures"):
            self.assertNotIn(absent, stats)
        for path in legacy:
            self.assertEqual(path.read_text(), "{}")

    def test_grep_and_webfetch_preserve_metadata(self) -> None:
        cases = [
            ("Grep", "content", {
                "mode": "content", "numFiles": 1, "filenames": ["src/example.txt"],
                "content": LARGE, "numLines": 300, "appliedLimit": 300, "appliedOffset": 1,
            }),
            ("WebFetch", "result", {
                "bytes": 4000, "code": 200, "codeText": "OK", "result": LARGE,
                "durationMs": 12, "url": "https://example.com/page",
            }),
        ]
        for tool, field, original in cases:
            with self.subTest(tool=tool):
                result = self.run_hook(tool, original)
                updated = json.loads(result.stdout)["hookSpecificOutput"]["updatedToolOutput"]
                self.assertLess(len(updated[field]), len(original[field]))
                self.assertIn("archive ", updated[field])
                updated[field] = original[field]
                self.assertEqual(updated, original)

    def test_mcp_preserves_all_blocks_except_long_nondiagnostic_text(self) -> None:
        self.env["CLAUDE_TOOL_OUTPUT_MAX_CHARS"] = "40000"
        self.env["CLAUDE_TOOL_OUTPUT_PREVIEW_CHARS"] = "20000"
        blocks = [
            {"type": "text", "text": "short context"},
            {"type": "text", "text": LARGE * 20},
            {"type": "text", "text": LARGE * 30},
            {"type": "text", "text": "WARNING: " + "cause" * 800 + "\n  at worker\n"},
            {"type": "image", "mimeType": "image/png", "data": "aGVsbG8="},
            {"type": "resource", "resource": {"uri": "file:///example", "text": "opaque"}},
            {"type": "future", "id": "record-123", "status": "failed",
             "error": {"message": "unchanged"}},
            *[{"type": "text", "text": f"item-{index}"} for index in range(205)],
        ]
        wrapped = {
            "content": blocks, "isError": False,
            "structuredContent": {"id": "record-123", "status": "failed"},
            "_meta": {"cursor": "next-page-123"},
        }
        for original in (blocks, wrapped):
            with self.subTest(wrapped=isinstance(original, dict)):
                result = self.run_hook("mcp__example__query", original)
                updated = json.loads(result.stdout)["hookSpecificOutput"]["updatedMCPToolOutput"]
                self.assertEqual(json.dumps(updated).count("Claude tool output compacted"), 1)
                updated_blocks = updated["content"] if isinstance(updated, dict) else updated
                self.assertEqual(len(updated_blocks), len(blocks))
                for index in (1, 2):
                    self.assertLess(len(updated_blocks[index]["text"]), len(blocks[index]["text"]))
                    updated_blocks[index]["text"] = blocks[index]["text"]
                self.assertEqual(updated, original)

    def test_passthrough_does_not_rewrite_or_archive(self) -> None:
        paths = [f"src/file-{index}.txt" for index in range(300)]
        diagnostic = LARGE + "CRITICAL failure: " + "cause" * 1000 + "\nstack frame\n"
        cases = [
            ("small", "Read", read_response("small")),
            ("unknown Read", "Read", {"content": LARGE, "lineCount": 300}),
            ("Read image", "Read", {
                "type": "image", "file": {"base64": LARGE, "type": "image/png"},
            }),
            ("Read pdf", "Read", {
                "type": "pdf", "file": {"base64": LARGE, "filePath": "example.pdf"},
            }),
            ("Read notebook", "Read", {
                "type": "notebook", "file": {"cells": [{"source": LARGE}]},
            }),
            ("Read parts", "Read", {
                "type": "parts", "pages": [{"base64": LARGE, "mediaType": "image/png"}],
            }),
            ("Grep filenames", "Grep", {
                "mode": "files_with_matches", "numFiles": 300, "filenames": paths,
            }),
            ("Grep counts", "Grep", {
                "mode": "count", "content": LARGE, "filenames": [], "numFiles": 0,
            }),
            ("Glob", "Glob", {
                "filenames": paths, "numFiles": 300, "durationMs": 1, "truncated": False,
            }),
            ("WebSearch", "WebSearch", {"query": "example", "results": [LARGE]}),
            ("malformed HTTP code", "WebFetch", {"code": "200", "result": LARGE}),
            ("HTTP error", "WebFetch", {
                "bytes": 4000, "code": 500, "codeText": "Unavailable", "result": LARGE,
                "durationMs": 1, "url": "https://example.com",
            }),
            ("MCP string", "mcp__example__query", LARGE),
            ("MCP record", "mcp__example__query", {
                "content": LARGE, "id": "record-123", "status": "failed",
            }),
            ("MCP records", "mcp__example__query", [
                {"id": "record-123", "status": "failed", "body": LARGE},
            ]),
            ("MCP error", "mcp__example__query", {
                "content": [{"type": "text", "text": LARGE}], "isError": True,
            }),
            ("MCP diagnostic", "mcp__example__query", [
                {"type": "text", "text": LARGE}, {"type": "text", "text": diagnostic},
            ]),
            ("Read diagnostic", "Read", read_response(diagnostic)),
            ("protected data fills budget", "mcp__example__query", [
                {"type": "text", "text": LARGE},
                {"type": "image", "mimeType": "image/png", "data": "aGVsbG8=" * 1000},
            ]),
            ("unsupported tool", "Bash", {"content": LARGE}),
        ]
        for name, tool, original in cases:
            with self.subTest(case=name):
                cache = self.cache_dir / name
                self.env["CLAUDE_TOOL_OUTPUT_CACHE_DIR"] = str(cache)
                result = self.run_hook(tool, original)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "")
                self.assertFalse(cache.exists())

    def test_malformed_input_fails_open_without_retaining_payload(self) -> None:
        secret = "credential-do-not-log"
        result = self.run_script(input_text="{" + secret)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(secret, result.stderr)
        self.assertFalse(self.cache_dir.exists())

    def test_expand_rejects_an_invalid_archive_id(self) -> None:
        result = self.run_script("expand", "../settings", expected_status=1)
        self.assertIn("archive ID must be", result.stderr)


if __name__ == "__main__":
    unittest.main()
