"""Property tests for the Bash safety guards.

Each rule names an operation the guard must stop wherever a shell would run it.
The tests generate the operation inside wrappers and compositions, ask the hook,
and treat an allowed input as a miss only when running it under zsh with stub
programs shows that the operation really ran.
"""

import contextlib
import hashlib
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


HOOKS = Path(__file__).resolve().parents[1]
VALIDATE_BASH = HOOKS / "validate-bash.sh"
REMOTE_GUARD = HOOKS / "remote-mutation-guard.py"
SEED = 385
SAMPLES = 400

PREFIXES = [
    "", "rtk ", "rtk proxy ", "env ", "env FOO=1 ", "FOO=1 ", "/usr/bin/env ",
    "command ", "exec ", "nohup ", "time ", "nice ", "nice -n 5 ", "timeout 30 ",
    "noglob ",
]
GIT_OPTIONS = [
    "", "-C . ", "-c core.a=b ", "--no-pager ", "-P ", "--no-optional-locks ",
    "--literal-pathspecs ", "--git-dir=.git ",
]
COMPOSITIONS = [
    "{X}",
    "true; {X}",
    "true && {X}",
    "false || {X}",
    "true\n{X}",
    "echo | {X}",
    "{X} | cat",
    "{X} > /dev/null 2>&1",
    "{X} & wait",
    "! {X}",
    "( {X} )",
    "{ {X}; }",
    'echo "$({X})"',
    "echo `{X}`",
    "if true; then {X}; fi",
    "for i in 1; do {X}; done",
    "while true; do {X}; break; done",
    "case x in x) {X};; esac",
    "f() { {X}; }; f",
    "bash -c '{X}'",
    "sh -c '{X}'",
    "zsh -c '{X}'",
    "eval '{X}'",
    "python3 -c \"import subprocess; subprocess.run('{X}', shell=True)\"",
    "python3 - <<'EOF'\nimport os\nos.system('{X}')\nEOF",
]
DATA_CONTEXTS = [
    "echo '{T}'",
    "printf '%s\\n' '{T}'",
    "git commit -m '{T}'",
    "gh pr create --title t --body '{T}'",
    "gh issue comment 1 --body '{T}'",
    "cat <<'EOF'\n{T}\nEOF",
    "cat <<EOF\n{T}\nEOF",
    "true # {T}",
    "git commit -F - <<'EOF'\n{T}\nEOF",
]

STAGE_ALL = ["-A", "--all", ".", "-vA", "./", ":/"]
FORCE_PUSH = [
    "push --force origin main", "push -f origin main", "push origin main --force",
    "push --force-with-lease origin main", "push origin +main", "push origin +HEAD:main",
    "push origin :old", "push --delete origin old", "push -d origin old",
    "push --mirror origin", "push -uf origin main", "push --prune origin",
]
CREATE_PR = [
    "gh pr create --title t --body b", "gh pr new --title t --body b",
    "gh --repo example/repo pr create --title t --body b",
    "gh api repos/example/repo/pulls -f title=t",
    "gh api -X POST repos/example/repo/pulls",
    "gh api graphql -f query=createPullRequest",
]


class Family:
    def __init__(self, name, dimensions, render, program, operation, hook, missed):
        self.name = name
        self.dimensions = dimensions
        self.render = render
        self.program = program
        self.operation = operation
        self.hook = hook
        self.missed = missed
        self.baseline = {dimension: values[0] for dimension, values in dimensions.items()}

    def cases(self):
        unique = {}
        for first, second in itertools.combinations(self.dimensions, 2):
            for pair in itertools.product(self.dimensions[first], self.dimensions[second]):
                case = dict(self.baseline, **dict(zip((first, second), pair)))
                unique[tuple(case.values())] = case
        generator = random.Random(f"{SEED}-{self.name}")
        for _ in range(SAMPLES):
            case = {dimension: generator.choice(values)
                    for dimension, values in self.dimensions.items()}
            unique[tuple(case.values())] = case
        return list(unique.values())

    def command(self, case):
        return case["composition"].replace("{X}", self.render(case))


def validate_bash_program():
    source = VALIDATE_BASH.read_text()
    body = source.split("3<<'PY'\n", 1)[1].rsplit("\nPY\n", 1)[0]
    return compile(body, str(VALIDATE_BASH), "exec")


class GuardPropertyTest(unittest.TestCase):
    """Generate wrapped operations, then confirm each allowed one by running it."""

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        cls.work = root / "work"
        cls.stubs = root / "stubs"
        cls.log = root / "calls.log"
        cls.work.mkdir()
        cls.stubs.mkdir()
        record = ('#!/bin/sh\n{ printf %s "$(basename "$0")"; for a in "$@"; do '
                  "printf '\\037%s' \"$a\"; done; printf '\\n'; } >> \"$GUARD_LOG\"\n")
        launchers = {
            "git": record, "gh": record,
            "rtk": '#!/bin/sh\n[ "$1" = proxy ] && shift\nexec "$@"\n',
            "timeout": '#!/bin/sh\nshift\nexec "$@"\n',
        }
        for name, text in launchers.items():
            path = cls.stubs / name
            path.write_text(text)
            path.chmod(0o755)
        system = [os.path.dirname(sys.executable), "/usr/bin", "/bin"]
        cls.environment = {
            "PATH": os.pathsep.join([str(cls.stubs), *system]),
            "HOME": str(root), "GUARD_LOG": str(cls.log), "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1", "GH_CONFIG_DIR": str(root / "gh"),
        }
        if not shutil.which("zsh"):
            raise AssertionError("zsh is required to confirm misses by running them")
        found = cls.run_shell("for p in git gh rtk timeout; do whence -p $p; done")
        assert found.split() == [str(cls.stubs / name) for name in ("git", "gh", "rtk", "timeout")], found

        spec = importlib.util.spec_from_file_location("remote_guard_properties", REMOTE_GUARD)
        cls.guard = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.guard)
        cls.program = validate_bash_program()
        cls.counts = {}
        cls.found = {}

        cls.families = [
            Family("stage-all", {
                "operation": STAGE_ALL, "git_option": GIT_OPTIONS,
                "prefix": PREFIXES, "composition": COMPOSITIONS,
            }, lambda case: f"{case['prefix']}git {case['git_option']}add {case['operation']}",
                "git", lambda case: ["add", *case["operation"].split()],
                cls.validate_bash, lambda decision: decision != "deny"),
            Family("force-push", {
                "operation": FORCE_PUSH, "git_option": GIT_OPTIONS,
                "prefix": PREFIXES, "composition": COMPOSITIONS,
            }, lambda case: f"{case['prefix']}git {case['git_option']}{case['operation']}",
                "git", lambda case: case["operation"].split(),
                cls.remote, lambda decision: decision != "deny"),
            Family("create-pr", {
                "operation": CREATE_PR, "prefix": PREFIXES, "composition": COMPOSITIONS,
            }, lambda case: f"{case['prefix']}{case['operation']}",
                "gh", lambda case: case["operation"].split()[1:],
                cls.remote, lambda decision: decision == "continue"),
        ]

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()
        if cls.counts:
            summary = ", ".join(f"{name} {count}" for name, count in cls.counts.items())
            print(f"\nguard properties: generated inputs: {summary}", file=sys.stderr)

    @classmethod
    def run_shell(cls, command):
        if cls.log.exists():
            cls.log.unlink()
        result = subprocess.run(["zsh", "-f", "-c", command], cwd=cls.work, env=cls.environment,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20)
        return result.stdout

    @classmethod
    def calls(cls, command):
        cls.run_shell(command)
        if not cls.log.exists():
            return []
        return [line.split("\x1f") for line in cls.log.read_text().splitlines()]

    @classmethod
    def performs(cls, family, case, command):
        expected = family.operation(case)
        return any(call[0] == family.program and call[-len(expected):] == expected
                   for call in cls.calls(command))

    @classmethod
    def validate_bash(cls, command):
        payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command},
                              "cwd": str(cls.work)})
        output = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(payload)), \
                mock.patch.object(sys, "argv", ["validate-bash.sh", str(VALIDATE_BASH)]), \
                contextlib.redirect_stdout(output):
            try:
                exec(cls.program, {"__name__": "__main__"})
            except SystemExit:
                pass
        if not output.getvalue():
            return "allow"
        return json.loads(output.getvalue())["hookSpecificOutput"]["permissionDecision"]

    @classmethod
    def remote(cls, command):
        return cls.guard.classify_shell(command)[0]

    def misses(self, family):
        if family.name not in self.found:
            cases = family.cases()
            self.counts[family.name] = len(cases)
            self.found[family.name] = [
                case for case in cases
                if family.missed(family.hook(family.command(case)))
                and self.performs(family, case, family.command(case))]
        return self.found[family.name]

    def grouped(self, family):
        """Misses by recorded cause, each as a count and a digest of its commands."""
        groups = {cause: [] for cause, _, _ in KNOWN_MISSES.get(family.name, [])}
        groups[None] = []
        for case in self.misses(family):
            cause = next((cause for cause, records, _ in KNOWN_MISSES.get(family.name, [])
                          if any(all(case[dimension] in values for dimension, values in record.items())
                                 for record in records)), None)
            groups[cause].append(family.command(case))
        unexplained = groups.pop(None)
        digest = {cause: f"{len(commands)} {hashlib.sha256(chr(10).join(sorted(commands)).encode()).hexdigest()[:12]}"
                  for cause, commands in groups.items()}
        return unexplained, digest

    def test_in_process_runner_matches_the_hook_script(self):
        for command in ["git add -A", "git add README.md", "bash -c 'git add .'"]:
            with self.subTest(command=command):
                result = subprocess.run(["bash", str(VALIDATE_BASH)], text=True, capture_output=True,
                                        input=json.dumps({"tool_name": "Bash",
                                                          "tool_input": {"command": command},
                                                          "cwd": str(self.work)}),
                                        timeout=10, check=True)
                script = (json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]
                          if result.stdout else "allow")
                self.assertEqual(self.validate_bash(command), script)

    def test_operations_run_by_a_shell_are_stopped_except_recorded_misses(self):
        for family in self.families:
            with self.subTest(family=family.name):
                unexplained, digest = self.grouped(family)
                self.assertEqual(unexplained, [])
                self.assertEqual(digest, {cause: recorded
                                          for cause, _, recorded in KNOWN_MISSES.get(family.name, [])})

    @unittest.expectedFailure
    def test_operations_run_by_a_shell_are_always_stopped(self):
        self.assertEqual({family.name: len(self.misses(family)) for family in self.families},
                         {family.name: 0 for family in self.families})

    def test_operations_quoted_as_data_are_not_stopped(self):
        for family in self.families:
            cases = {family.render(case): case for case in family.cases()
                     if case["composition"] == "{X}"}
            self.counts[f"{family.name} as data"] = len(cases) * len(DATA_CONTEXTS)
            for context in DATA_CONTEXTS:
                for text, case in cases.items():
                    command = context.replace("{T}", text)
                    with self.subTest(family=family.name, command=command):
                        self.assertNotEqual(family.hook(command), "deny")
                text, case = next(iter(cases.items()))
                with self.subTest(family=family.name, context=context, ran=True):
                    self.assertFalse(self.performs(family, case, context.replace("{T}", text)))


WRAPPERS = [prefix for prefix in PREFIXES if prefix and not prefix.startswith("rtk")]
SKIPPED_GIT_OPTIONS = ["-C . ", "-c core.a=b ", "--no-optional-locks ", "--literal-pathspecs "]
RESERVED = ["! {X}", "{ {X}; }", "if true; then {X}; fi", "for i in 1; do {X}; done",
            "while true; do {X}; break; done"]
SHELL_TEXT = ["bash -c '{X}'", "sh -c '{X}'", "zsh -c '{X}'", "eval '{X}'", "echo `{X}`"]

# Each cause lists the generated values that reach it, then the count and
# digest of the misses it explains, so a new, fixed or swapped miss fails.
KNOWN_MISSES = {
    "stage-all": [
        ("all-files pathspec other than '.'", [{"operation": ["./", ":/"]}], "215 2ecca9fd3320"),
        ("git option the parser does not skip", [
            {"git_option": ["--no-pager ", "-P "]},
            {"git_option": ["--git-dir=.git "], "operation": ["-vA"]},
        ], "157 04e6b2cdfb3f"),
        ("wrapper before git", [
            {"prefix": WRAPPERS, "operation": ["-vA"]},
            {"prefix": WRAPPERS, "git_option": SKIPPED_GIT_OPTIONS},
            {"prefix": WRAPPERS, "operation": ["."], "composition": ['echo "$({X})"']},
        ], "173 7f62300b0783"),
        ("reserved word or function around git", [
            {"composition": RESERVED + ["f() { {X}; }; f"], "operation": ["-vA"]},
            {"composition": RESERVED + ["f() { {X}; }; f"], "git_option": SKIPPED_GIT_OPTIONS},
        ], "39 b81da1ec0117"),
        ("text run by another shell", [
            {"composition": SHELL_TEXT, "operation": ["-vA", "."]},
            {"composition": SHELL_TEXT, "git_option": SKIPPED_GIT_OPTIONS},
        ], "39 f7953eb48c1e"),
    ],
    "force-push": [
        ("reserved word before the command", [{"composition": RESERVED}], "240 4326dd5fb4a8"),
        ("eval", [{"composition": ["eval '{X}'"]}], "48 b9d1dc7f759b"),
    ],
    "create-pr": [
        ("gh pr new alias", [{"operation": ["gh pr new --title t --body b"]}], "88 4a4d1f267562"),
        ("reserved word before the command", [{"composition": RESERVED}], "144 d87d63d3c5a8"),
        ("eval", [{"composition": ["eval '{X}'"]}], "28 629d0be39e09"),
    ],
}


if __name__ == "__main__":
    unittest.main()
