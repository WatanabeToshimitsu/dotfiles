#!/usr/bin/env python3
"""Compact large non-shell Claude tool results and retain the original locally."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any


SUPPORTED_TOOL = re.compile(r"^(Read|Grep|Glob|WebFetch|WebSearch|mcp__.+)$")
ARCHIVE_ID = re.compile(r"^[a-f0-9]{20}$")
ERROR_LINE = re.compile(
    r"\b(error|critical|fatal|failed|failure|exception|traceback|denied|warning)\b",
    re.IGNORECASE,
)
DEFAULT_MAX_CHARS = 40_000
DEFAULT_PREVIEW_CHARS = 12_000
DEFAULT_RETENTION_DAYS = 7


def env_int(name: str, default: int, minimum: int) -> int:
    try:
        return max(int(os.environ.get(name, default)), minimum)
    except ValueError:
        return default


def cache_dir() -> Path:
    configured = os.environ.get("CLAUDE_TOOL_OUTPUT_CACHE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".claude" / "tool-output-cache"


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_strings(item)


def map_strings(value: Any, transform: Callable[[int, str], str]) -> Any:
    index = 0

    def visit(item: Any) -> Any:
        nonlocal index
        if isinstance(item, str):
            current = index
            index += 1
            return transform(current, item)
        if isinstance(item, list):
            return [visit(child) for child in item]
        if isinstance(item, dict):
            return {key: visit(child) for key, child in item.items()}
        return item

    return visit(value)


def prune_lists(value: Any, max_items: int) -> Any:
    if isinstance(value, list):
        items = value
        if len(items) > max_items:
            head_count = max_items * 2 // 3
            tail_count = max_items - head_count
            items = items[:head_count] + items[-tail_count:]
        return [prune_lists(item, max_items) for item in items]
    if isinstance(value, dict):
        return {key: prune_lists(item, max_items) for key, item in value.items()}
    return value


def allocate_string_budget(strings: list[str], budget: int) -> list[int]:
    remaining_budget = max(budget, 0)
    remaining_chars = sum(len(value) for value in strings)
    allocations: list[int] = []

    for value in strings:
        if remaining_chars == 0 or remaining_budget == 0:
            allocation = 0
        else:
            allocation = min(len(value), remaining_budget * len(value) // remaining_chars)
        allocations.append(allocation)
        remaining_budget -= allocation
        remaining_chars -= len(value)

    return allocations


def truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 1:
        return value[:limit]

    marker = "\n…\n"
    if limit <= len(marker) + 2:
        return value[:limit]
    available = limit - len(marker)
    head = available * 2 // 3
    tail = available - head
    return value[:head] + marker + value[-tail:]


def error_excerpt(strings: list[str], limit: int = 1_500) -> str:
    matches: list[str] = []
    seen: set[str] = set()
    size = 0

    for value in strings:
        for line in value.splitlines():
            stripped = line.strip()
            if not stripped or not ERROR_LINE.search(stripped) or stripped in seen:
                continue
            addition = len(stripped) + 1
            if size + addition > limit:
                return "\n".join(matches)
            matches.append(stripped)
            seen.add(stripped)
            size += addition
    return "\n".join(matches)


def compaction_notice(archive_id: str, original_chars: int, errors: str) -> str:
    notice = (
        "\n\n[Claude tool output compacted from "
        f"{original_chars:,} chars; full result is in archive {archive_id}. "
        f"Use /expand-tool-output {archive_id} with a focus term first.]"
    )
    if errors:
        notice += f"\nImportant diagnostic lines:\n{errors}"
    return notice


def compact_response(response: Any, archive_id: str, preview_chars: int) -> Any | None:
    original_strings = list(iter_strings(response))
    if not original_strings:
        return None

    errors = error_excerpt(original_strings)
    notice = compaction_notice(archive_id, len(encode(response)), errors)
    longest_index = max(range(len(original_strings)), key=lambda item: len(original_strings[item]))

    candidate: Any | None = None
    for list_limit in (200, 50, 10):
        pruned = prune_lists(response, list_limit)
        strings = list(iter_strings(pruned))
        if not strings:
            continue
        structure_chars = len(encode(map_strings(pruned, lambda _index, _value: "")))
        text_budget = max(preview_chars - structure_chars - len(notice), 0)
        allocations = allocate_string_budget(strings, text_budget)

        def transform(index: int, value: str) -> str:
            compacted = truncate_text(value, allocations[index])
            if index == min(longest_index, len(strings) - 1):
                compacted += notice
            return compacted

        candidate = map_strings(pruned, transform)
        if len(encode(candidate)) <= preview_chars:
            return candidate

    return candidate


def make_archive_id(payload: dict[str, Any]) -> str:
    seed = ":".join(
        [
            str(payload.get("session_id", "")),
            str(payload.get("tool_use_id", "")),
            str(time.time_ns()),
            str(os.getpid()),
        ]
    )
    return hashlib.sha256(seed.encode()).hexdigest()[:20]


def prepare_cache(root: Path) -> None:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(root, 0o700)


def clean_expired_archives(root: Path, retention_days: int) -> None:
    cutoff = time.time() - retention_days * 86_400
    for path in root.glob("*.json"):
        try:
            if path.is_file() and not path.is_symlink() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def write_archive(
    root: Path,
    archive_id: str,
    tool_name: str,
    response: Any,
    original_chars: int,
    compacted_chars: int,
) -> None:
    archive = {
        "version": 1,
        "archive_id": archive_id,
        "created_at": datetime.now(UTC).isoformat(),
        "tool_name": tool_name,
        "original_chars": original_chars,
        "compacted_chars": compacted_chars,
        "tool_response": response,
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(root / f"{archive_id}.json", flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(archive, stream, ensure_ascii=False)
        stream.write("\n")


def run_hook() -> int:
    try:
        payload = json.load(sys.stdin)
        tool_name = str(payload.get("tool_name", ""))
        if not SUPPORTED_TOOL.fullmatch(tool_name) or "tool_response" not in payload:
            return 0

        response = payload["tool_response"]
        original_chars = len(encode(response))
        max_chars = env_int("CLAUDE_TOOL_OUTPUT_MAX_CHARS", DEFAULT_MAX_CHARS, 256)
        if original_chars <= max_chars:
            return 0

        preview_chars = min(
            env_int("CLAUDE_TOOL_OUTPUT_PREVIEW_CHARS", DEFAULT_PREVIEW_CHARS, 128),
            max_chars - 1,
        )
        archive_id = make_archive_id(payload)
        compacted = compact_response(response, archive_id, preview_chars)
        if compacted is None:
            return 0
        compacted_chars = len(encode(compacted))
        if compacted_chars >= original_chars:
            return 0

        root = cache_dir()
        prepare_cache(root)
        clean_expired_archives(
            root,
            env_int("CLAUDE_TOOL_OUTPUT_RETENTION_DAYS", DEFAULT_RETENTION_DAYS, 1),
        )
        write_archive(
            root,
            archive_id,
            tool_name,
            response,
            original_chars,
            compacted_chars,
        )
        output_key = "updatedMCPToolOutput" if tool_name.startswith("mcp__") else "updatedToolOutput"
        json.dump(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    output_key: compacted,
                }
            },
            sys.stdout,
            ensure_ascii=False,
        )
        return 0
    except Exception as error:  # Hooks must fail open.
        print(f"compact-tool-output: {error}", file=sys.stderr)
        return 0


def load_archive(archive_id: str) -> dict[str, Any]:
    if not ARCHIVE_ID.fullmatch(archive_id):
        raise ValueError("archive ID must be 20 lowercase hexadecimal characters")
    path = cache_dir() / f"{archive_id}.json"
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, encoding="utf-8") as stream:
        return json.load(stream)


def filter_lines(text: str, term: str, context: int) -> str:
    context = max(context, 0)
    lines = text.splitlines()
    matching = [index for index, line in enumerate(lines) if term.casefold() in line.casefold()]
    if not matching:
        return f"No lines matched {term!r}."

    selected: set[int] = set()
    for index in matching:
        selected.update(range(max(0, index - context), min(len(lines), index + context + 1)))
    return "\n".join(lines[index] for index in sorted(selected))


def slice_lines(text: str, head: int, tail: int) -> str:
    head = max(head, 0)
    tail = max(tail, 0)
    if not head and not tail:
        return text
    lines = text.splitlines()
    selected = lines[:head]
    if tail:
        if head and len(lines) > head + tail:
            selected.append(f"… {len(lines) - head - tail} lines omitted …")
        selected.extend(lines[-tail:])
    return "\n".join(selected)


def expand_archive(args: argparse.Namespace) -> int:
    try:
        archive = load_archive(args.archive_id)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"expand-tool-output: {error}", file=sys.stderr)
        return 1

    response = archive["tool_response"]
    if isinstance(response, str):
        text = response
    elif args.grep or args.head or args.tail:
        text = "\n".join(iter_strings(response))
    else:
        text = json.dumps(response, ensure_ascii=False, indent=2)
    if args.grep:
        text = filter_lines(text, args.grep, args.context)
    print(slice_lines(text, args.head, args.tail))
    return 0


def show_stats() -> int:
    root = cache_dir()
    archives: list[dict[str, Any]] = []
    if root.exists():
        for path in root.glob("*.json"):
            if path.is_symlink():
                continue
            try:
                with path.open(encoding="utf-8") as stream:
                    archives.append(json.load(stream))
            except (OSError, json.JSONDecodeError):
                continue

    original = sum(int(item.get("original_chars", 0)) for item in archives)
    compacted = sum(int(item.get("compacted_chars", 0)) for item in archives)
    saved = max(original - compacted, 0)
    percent = saved * 100 / original if original else 0
    print(f"archives: {len(archives)}")
    print(f"original chars: {original:,}")
    print(f"compacted chars: {compacted:,}")
    print(f"saved: {saved:,} chars ({percent:.1f}%, about {saved // 4:,} tokens)")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    expand = subparsers.add_parser("expand", help="read an archived tool result")
    expand.add_argument("archive_id")
    expand.add_argument("--grep", help="show matching lines, case-insensitively")
    expand.add_argument("--context", type=int, default=2)
    expand.add_argument("--head", type=int, default=0)
    expand.add_argument("--tail", type=int, default=0)
    subparsers.add_parser("stats", help="show local compaction savings")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "expand":
        return expand_archive(args)
    if args.command == "stats":
        return show_stats()
    return run_hook()


if __name__ == "__main__":
    raise SystemExit(main())
