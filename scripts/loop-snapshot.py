#!/usr/bin/env python3
"""Collect one read-only discovery packet; never select or execute work."""

import argparse
import json
import os
import re
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COMMAND_TIMEOUT = 8
ITEM_LIMIT = 50
CHECK_LIMIT = 20
ISSUE_FIELDS = "number,title,url,labels,assignees,updatedAt"
PR_FIELDS = (
    "number,title,url,headRefName,isDraft,mergeable,reviewDecision,"
    "statusCheckRollup,updatedAt"
)


class CollectionError(Exception):
    pass


def validate_repository(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_][A-Za-z0-9_.-]*", value):
        raise ValueError("expected a GitHub OWNER/REPO name")
    return value


def execute(command: list[str], directory: Path) -> str:
    env = {**os.environ, "GH_PROMPT_DISABLED": "1", "GIT_TERMINAL_PROMPT": "0"}
    try:
        process = subprocess.Popen(
            command,
            cwd=directory,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
    except FileNotFoundError as error:
        raise CollectionError("missing_command") from error
    except OSError as error:
        raise CollectionError("command_unavailable") from error
    try:
        output, _ = process.communicate(timeout=COMMAND_TIMEOUT)
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
        process.stdout.close()
        process.stderr.close()
        raise CollectionError("timeout") from error
    if process.returncode:
        raise CollectionError("command_failed")
    try:
        return output.decode("utf-8")
    except UnicodeError as error:
        raise CollectionError("invalid_encoding") from error


def require_fields(item: dict, fields: dict[str, type]) -> None:
    if not isinstance(item, dict) or any(
        type(item.get(key)) is not kind for key, kind in fields.items()
    ):
        raise CollectionError("invalid_schema")


def summarize_item(item: dict, repository: str, kind: str) -> dict[str, Any]:
    require_fields(item, {"number": int, "title": str, "url": str, "updatedAt": str})
    route = "issues" if kind == "issue" else "pull"
    expected_url = f"https://github.com/{repository}/{route}/{item['number']}"
    if item["number"] <= 0 or item["url"].lower() != expected_url.lower():
        raise CollectionError("invalid_schema")
    result = {key: item[key] for key in ("number", "title", "url", "updatedAt")}
    if kind == "issue":
        require_fields(item, {"labels": list, "assignees": list})
        for label in item["labels"]:
            require_fields(label, {"name": str})
        for assignee in item["assignees"]:
            require_fields(assignee, {"login": str})
        result.update(
            labels=[label["name"] for label in item["labels"]],
            assigned=bool(item["assignees"]),
        )
        return result
    require_fields(item, {"headRefName": str, "isDraft": bool, "mergeable": str})
    if "reviewDecision" not in item or (
        item["reviewDecision"] is not None
        and not isinstance(item["reviewDecision"], str)
    ):
        raise CollectionError("invalid_schema")
    result.update({
        key: item[key]
        for key in ("headRefName", "isDraft", "mergeable", "reviewDecision")
    })
    if "statusCheckRollup" not in item:
        raise CollectionError("invalid_schema")
    checks = item["statusCheckRollup"]
    result.update(checks=None, checks_truncated=False)
    if checks is None:
        return result
    if not isinstance(checks, list):
        raise CollectionError("invalid_schema")
    result["checks"] = []
    for check in checks[:CHECK_LIMIT]:
        require_fields(check, {"__typename": str})
        fields = {
            "CheckRun": ("name", "status", "conclusion", "detailsUrl"),
            "StatusContext": ("context", "state", "targetUrl"),
        }.get(check["__typename"])
        if fields is None:
            raise CollectionError("invalid_schema")
        nullable = {"conclusion", "detailsUrl", "targetUrl"}
        require_fields(check, {key: str for key in fields if key not in nullable})
        if any(
            key not in check
            or (check[key] is not None and not isinstance(check[key], str))
            for key in fields if key in nullable
        ):
            raise CollectionError("invalid_schema")
        result["checks"].append({key: check[key] for key in ("__typename", *fields)})
    result["checks_truncated"] = len(checks) > CHECK_LIMIT
    return result


def github_source(repository: str, directory: Path, kind: str) -> dict[str, Any]:
    fields = ISSUE_FIELDS if kind == "issue" else PR_FIELDS
    command = [
        "gh", kind, "list", "--repo", repository, "--state", "open",
        "--limit", str(ITEM_LIMIT + 1), "--json", fields,
    ]
    try:
        raw = execute(command, directory)
        try:
            items = json.loads(raw)
        except ValueError as error:
            raise CollectionError("invalid_json") from error
        if not isinstance(items, list):
            raise CollectionError("invalid_schema")
        summarized = [
            summarize_item(item, repository, kind) for item in items[:ITEM_LIMIT]
        ]
        truncated = len(items) > ITEM_LIMIT or any(
            item.get("checks_truncated") for item in summarized
        )
        return {
            "status": "partial" if truncated else "ok",
            "truncated": truncated,
            "items": summarized,
        }
    except CollectionError as error:
        return {"status": "unavailable", "error": str(error)}


def collect(repository: str, directory: Path) -> dict[str, Any]:
    validate_repository(repository)
    started = time.monotonic()
    result: dict[str, Any] = {
        "schema_version": 1,
        "repository": repository,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }
    sources = result["sources"]
    verified = False
    git = ["git", "--no-optional-locks"]
    try:
        origin = execute([*git, "remote", "get-url", "origin"], directory).strip()
        match = re.fullmatch(
            r"(?:git@github\.com:|https://github\.com/|ssh://git@github\.com/)"
            r"([^/]+/[^/]+?)(?:\.git)?",
            origin,
        )
        if not match or match[1].lower() != repository.lower():
            raise CollectionError("repository_mismatch")
        verified = True
        head = execute([*git, "rev-parse", "HEAD"], directory).strip()
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", head):
            raise CollectionError("invalid_head")
        dirty = bool(execute(
            [*git, "status", "--porcelain=v1", "--untracked-files=normal"], directory,
        ).strip())
        sources["local"] = {"status": "ok", "head": head, "dirty": dirty}
    except CollectionError as error:
        sources["local"] = {"status": "unavailable", "error": str(error)}
    for name, kind in (("issues", "issue"), ("pull_requests", "pr")):
        if verified:
            sources[name] = github_source(repository, directory, kind)
        else:
            sources[name] = {
                "status": "unavailable", "error": "local_repository_unverified",
            }
    result.update(
        complete=all(source["status"] == "ok" for source in sources.values()),
        finished_at=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=round(time.monotonic() - started, 3),
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", required=True, help="GitHub OWNER/REPO; must match local origin",
    )
    parser.add_argument("--directory", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = collect(args.repo, args.directory)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
