#!/usr/bin/env python3
"""Run each instruction eval case with today's instructions and with the case's instruction removed.

A case is a `claude plugin eval` case in test/instruction-evals/<case>/ plus an
ablation.json naming the instruction file, the exact text to remove, and any
tools to grant. `claude plugin eval` loads no CLAUDE.md or user settings, so
each run gets a generated plugin: its skills are a copy of claude/skills, the
case prompt opens with both CLAUDE.md files in a system reminder as a real
session's first turn does, and the system prompt gets the language setting.
"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "test" / "instruction-evals"
INSTRUCTION_FILES = {
    "claude/CLAUDE.md": "{plugin}/CLAUDE.md (user's private global instructions for all projects)",
    "CLAUDE.md": "dotfiles/CLAUDE.md (project instructions, checked into the codebase)",
}
HEADER = ("As you answer the user's questions, you can use the following context:\n# claudeMd\n"
          "Codebase and user instructions are shown below. Be sure to adhere to these instructions. "
          "IMPORTANT: These instructions OVERRIDE any default behavior and you MUST follow them exactly as written.")
LANGUAGE = ("# Language\nAlways respond in {0}. Use {0} for all explanations, comments, and communications "
            "with the user. Technical terms and code identifiers should remain in their original form.")


def remove_once(text, needle):
    count = text.count(needle)
    if count != 1:
        raise SystemExit(f"text to remove appears {count} times, expected once: {needle[:60]!r}")
    return text.replace(needle, "", 1)


def build_plugin(root, case, target, ablate):
    """A plugin that shows the instructions, optionally without the case's removed text, and holds the case.

    The global CLAUDE.md is shown at the plugin root, beside skills/, as ~/.claude
    holds it, so its relative skill links resolve.
    """
    ablation = json.loads((case / "ablation.json").read_text())
    removals = ablation["remove"] if isinstance(ablation["remove"], list) else [ablation["remove"]]
    shutil.copytree(root / "claude" / "skills", target / "skills",
                    ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    shutil.copytree(case, target / "evals" / case.name)
    texts = {path: (root / path).read_text() for path in INSTRUCTION_FILES}
    if ablate:
        path = ablation["file"]
        if path in texts:
            for removal in removals:
                texts[path] = remove_once(texts[path], removal)
        elif path.startswith("claude/skills/"):
            skill = target / Path(path).relative_to("claude")
            for removal in removals:
                skill.write_text(remove_once(skill.read_text(), removal))
        else:
            raise SystemExit(f"{case.name}: cannot ablate {path}")
    sections = [f"Contents of {label.format(plugin=target)}:\n\n{texts[path]}"
                for path, label in INSTRUCTION_FILES.items()]
    reminder = "<system-reminder>\n" + HEADER + "\n\n" + "\n\n".join(sections) + "\n</system-reminder>\n\n"
    language = json.loads((root / "claude" / "settings.json").read_text())["language"]
    prompt = target / "evals" / case.name / "prompt.md"
    front, body = prompt.read_text().split("\n---\n", 1)
    system = json.dumps(LANGUAGE.format(language), ensure_ascii=False)
    prompt.write_text(f"{front}\nappend_system_prompt: {system}\n---\n\n{reminder}{body.lstrip()}")
    (target / ".claude-plugin").mkdir()
    (target / ".claude-plugin" / "plugin.json").write_text(json.dumps(
        {"name": "harness", "version": "0.0.0", "description": "dotfiles instructions under test"}))
    return target


def verdict(current, ablated):
    """Today's version passes every run; the ablated version fails most runs."""
    return all(score == 1 for score in current) and 2 * sum(score < 1 for score in ablated) > len(ablated)


def run_arm(case, arm, out, args):
    ablation = json.loads((case / "ablation.json").read_text())
    plugin = build_plugin(ROOT, case, out / case.name / arm / "plugin", arm == "ablated")
    result = out / case.name / arm / "result.json"
    command = ["claude", "plugin", "eval", str(plugin), "--case", case.name, "--ablation", "none",
               "--no-publish", "--trust-plugin", "--threshold", "0", "--runs", str(args.runs),
               "--model", args.model, "--judge-model", args.judge_model, "-j", str(args.concurrency),
               "--output-dir", str(out / case.name / arm / "results")]
    command += ["--allow-tools", f"Read(/{plugin}/**)", *ablation.get("allow_tools", []), "--json", str(result)]
    subprocess.run(command, stdout=subprocess.DEVNULL, check=False)
    if not result.is_file():
        raise SystemExit(f"{case.name} {arm}: no result; rerun the command by hand to see why: {command}")
    data = json.loads(result.read_text())
    runs = data["cases"][0]["arms"]["with"]
    return [run["score"] for run in runs], [run["error"] for run in runs if run["error"]], data["costUsd"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cases", nargs="*", help="case directory names; default: all")
    parser.add_argument("--arm", choices=["both", "current", "ablated"], default="both")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--model", default="opus")
    parser.add_argument("--judge-model", default="sonnet")
    parser.add_argument("-j", "--concurrency", type=int, default=3)
    parser.add_argument("--out", type=Path, help="where plugins and results go; default: a new temp directory")
    args = parser.parse_args()
    out = args.out or Path(tempfile.mkdtemp(prefix="instruction-eval-"))
    names = args.cases or sorted(p.name for p in CASES.iterdir() if (p / "ablation.json").is_file())
    arms = ["current", "ablated"] if args.arm == "both" else [args.arm]
    print(f"results: {out}")
    ok = True
    for name in names:
        scores, cost = {}, 0.0
        for arm in arms:
            scores[arm], errors, arm_cost = run_arm(CASES / name, arm, out, args)
            cost += arm_cost
            if errors:
                ok = False
                print(f"{name} {arm}: run errors: {errors}")
        line = "  ".join(f"{arm}={scores[arm]}" for arm in arms)
        if args.arm == "both":
            passed = verdict(scores["current"], scores["ablated"])
            ok &= passed
            line += "  " + ("PASS" if passed else "FAIL")
        print(f"{name}  {line}  cost=${cost:.2f}", flush=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
