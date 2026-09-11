#!/usr/bin/env python3
"""Check sync mechanics in disposable directories, without installing anything."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading


ROOT = Path(__file__).resolve().parents[2]
BEGIN = "<!-- BEGIN dotfiles Claude sync -->"
END = "<!-- END dotfiles Claude sync -->"


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True)


def render(source):
    prompt = (source / "CLAUDE.md").read_text()
    rules = sorted((source / "rules").rglob("*.md"))
    index = []
    for path in rules:
        text = path.read_text()
        frontmatter = text.split("---", 2)[1]
        scopes = re.findall(r'^  - "(.+)"$', frontmatter, re.MULTILINE)
        if not scopes:
            raise ValueError(f"Unsupported rule frontmatter: {path.name}")
        index.append({"path": path.relative_to(source).as_posix(), "paths": scopes})
    body = prompt.rstrip() + "\n\n# Shared rule index\n\n"
    body += "Before editing, read the rules whose listed paths match the files.\n"
    body += "Resolve paths below relative to the sibling claude-source directory.\n"
    body += "These are prompt instructions, not native Codex path-rule enforcement.\n\n"
    for entry in index:
        body += f"- {entry['path']}: " + ", ".join(entry["paths"]) + "\n"
    body += "\n# Portability boundary for this spike\n\n"
    body += "This output has not received model, tool, or memory adaptations.\n"
    body += "Do not install it as a production agent configuration.\n"
    return body, index


def merge_block(existing, generated):
    block = f"{BEGIN}\n{generated.rstrip()}\n{END}"
    if BEGIN in existing or END in existing:
        if existing.count(BEGIN) != 1 or existing.count(END) != 1:
            raise ValueError("Ambiguous managed block")
        start, end = existing.index(BEGIN), existing.index(END)
        if end < start:
            raise ValueError("Reversed managed block")
        return existing[:start] + block + existing[end + len(END):]
    return block + "\n\n" + existing


def link_without_replacement(source, target):
    if target.is_symlink() and target.resolve() == source.resolve():
        return
    if target.exists() or target.is_symlink():
        raise FileExistsError(target.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source, target_is_directory=True)


class Rpc:
    def __init__(self, state_dir):
        state_dir.mkdir()
        (state_dir / "config.toml").write_text(
            '[features]\nhooks = true\n[analytics]\nenabled = false\n'
        )
        # Only this disposable child receives Codex's documented home override.
        probe_env = {k: os.environ[k] for k in ("PATH", "LANG", "TMPDIR") if k in os.environ}
        probe_env["CODEX_HOME"] = str(state_dir)
        self.stderr = tempfile.TemporaryFile(mode="w+")
        self.proc = subprocess.Popen(
            ["codex", "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            cwd=state_dir, env=probe_env, text=True, bufsize=1,
        )
        self.messages = queue.Queue()
        self.sequence = 0
        threading.Thread(target=self.read, daemon=True).start()
        self.call("initialize", {
            "clientInfo": {"name": "dotfiles_sync_probe", "version": "0.1.0"},
            "capabilities": {"experimentalApi": True},
        })
        self.send({"method": "initialized", "params": {}})

    def read(self):
        for line in self.proc.stdout:
            self.messages.put(json.loads(line))
        self.messages.put(None)

    def send(self, value):
        self.proc.stdin.write(json.dumps(value) + "\n")
        self.proc.stdin.flush()

    def call(self, method, params):
        self.sequence += 1
        expected = self.sequence
        self.send({"id": expected, "method": method, "params": params})
        while True:
            message = self.messages.get(timeout=30)
            if message is None:
                raise RuntimeError("App-server closed before returning a response")
            if message.get("id") == expected:
                if "error" in message:
                    raise RuntimeError(message["error"])
                return message["result"]

    def close(self):
        self.proc.stdin.close()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        self.proc.stdout.close()
        self.stderr.close()


def run(runtime):
    report = {"base_commit": git("rev-parse", "HEAD").strip(), "checks": []}

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        report["checks"].append(name)

    with tempfile.TemporaryDirectory(prefix="dotfiles-sync-probe-") as temporary:
        workspace = Path(temporary)
        source = workspace / "claude-source"
        tracked = git("ls-files", "-z", "claude/CLAUDE.md", "claude/rules", "claude/skills")
        for name in filter(None, tracked.split("\0")):
            original = ROOT / name
            if original.is_symlink():
                raise ValueError("The spike only exports tracked regular files")
            target = workspace / "claude-source" / Path(name).relative_to("claude")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, target)
        check("private_ticket_reference_not_exported", not (source / "skills/ticket/reference.md").exists())

        first, index = render(source)
        second, _ = render(source)
        check("generation_is_deterministic", first == second)
        original_rules = list((ROOT / "claude/rules").rglob("*.md"))
        scope_count = sum(
            line.startswith("  - ")
            for path in original_rules
            for line in path.read_text().split("---", 2)[1].splitlines()
        )
        check("rule_index_preserves_all_scopes", len(index) == len(original_rules) and sum(len(p["paths"]) for p in index) == scope_count)
        check("claude_prompt_preserved_verbatim", first.startswith((source / "CLAUDE.md").read_text().rstrip()))

        original_prompt = (source / "CLAUDE.md").read_text()
        (source / "CLAUDE.md").write_text(original_prompt + "\nSYNC_PROBE_REVISION\n")
        changed, _ = render(source)
        check("source_edit_changes_generated_output", changed != first and "SYNC_PROBE_REVISION" in changed)
        check("stale_output_is_detectable", hashlib.sha256(first.encode()).digest() != hashlib.sha256(changed.encode()).digest())
        (source / "CLAUDE.md").write_text(original_prompt)

        original_local = "# Existing Codex instructions\nKeep local review preferences.\n"
        installed = merge_block(original_local, first)
        check("local_instructions_are_preserved_last", installed.endswith(original_local))
        check("managed_block_is_idempotent", merge_block(installed, first) == installed)
        check("managed_block_updates_once", merge_block(installed, changed).count(BEGIN) == 1)

        skills = sorted((source / "skills").glob("*/SKILL.md"))
        project = workspace / "project"
        (project / ".git").mkdir(parents=True)
        links = project / ".agents/skills"
        for skill in skills:
            link_without_replacement(skill.parent, links / skill.parent.name)
            link_without_replacement(skill.parent, links / skill.parent.name)
        check("skill_links_preserve_original_bytes", all((links / p.parent.name / "SKILL.md").read_bytes() == p.read_bytes() for p in skills))
        collision = links / "existing-user-skill"
        collision.mkdir()
        try:
            link_without_replacement(skills[0].parent, collision)
        except FileExistsError:
            check("existing_skill_directory_is_not_replaced", collision.is_dir() and not collision.is_symlink())
        else:
            raise AssertionError("Collision unexpectedly replaced user files")

        report.update({
            "rule_count": len(index), "rule_scope_count": scope_count, "skill_count": len(skills),
            "generated_prompt_bytes": len(first.encode()),
            "settings_keys_requiring_explicit_policy": sorted(json.loads((ROOT / "claude/settings.json").read_text())),
            "runtime": "not_requested", "model_turns": 0,
        })
        if runtime:
            rpc = Rpc(workspace / "runtime-state")
            try:
                params = {"cwds": [str(project)], "forceReload": True}
                listed = rpc.call("skills/list", params)["data"][0]
                discovered = {p["name"]: p for p in listed["skills"]}
                expected = {p.parent.name for p in skills}
                check("codex_discovers_all_six_linked_skills", expected <= discovered.keys())
                check("codex_reports_no_skill_parse_errors", not listed["errors"])
                target = source / "skills/code-review/SKILL.md"
                target.write_text(target.read_text().replace("description: ", "description: SYNC_PROBE_REVISION ", 1))
                refreshed = rpc.call("skills/list", params)["data"][0]
                description = next(p["description"] for p in refreshed["skills"] if p["name"] == "code-review")
                check("codex_force_reload_observes_source_edit", description.startswith("SYNC_PROBE_REVISION "))
                config = rpc.call("config/read", {"includeLayers": False})
                check("isolated_codex_config_is_loaded", config["config"].get("features", {}).get("hooks") is True)
                report["runtime"] = subprocess.check_output(["codex", "--version"], text=True, stderr=subprocess.DEVNULL).strip()
                report["discovered_skills"] = sorted(expected)
            finally:
                rpc.close()
    report["result"] = "passed"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", action="store_true", help="Also test the local Codex app-server without model turns")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run(args.runtime)
    output = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(output)
    print(output, end="")


if __name__ == "__main__":
    main()
