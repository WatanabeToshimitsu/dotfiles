#!/bin/bash
# Keep stdin for the hook payload; never evaluate the supplied shell command.
exec python3 /dev/fd/3 "${BASH_SOURCE[0]}" 3<<'PY'
import json
import os
from pathlib import Path
import re
import shlex
import sys


LEGACY_PATTERN = re.compile(r"\bgit add (-A|--all|\.($|[ ;|&]))", re.MULTILINE)
TICKET_STATE = re.compile(r"profiles/ticket\b|ticket-browser\.json|(^|[ =])(--session|AGENT_BROWSER_SESSION)[ =][\"']?ticket\b")
HOME = os.path.expanduser("~")
TICKET_PROFILE = os.path.realpath(os.path.join(HOME, ".agent-browser", "profiles", "ticket"))
AGENT_BROWSER = re.compile(r"^agent-browser(@[^/]*)?$")
PATH_OPTIONS = {"--profile", "--config", "AGENT_BROWSER_PROFILE", "AGENT_BROWSER_CONFIG"}
DIRECTORY_CHANGE = re.compile(r"(^|[;&|(\n]\s*)(cd|pushd|popd)\b")
RELATIVE_PATH_OPTION = re.compile(
    r"(--profile|--config|AGENT_BROWSER_PROFILE|AGENT_BROWSER_CONFIG)[ =]+(?![\"']?(/|~|\$HOME\b|\$\{HOME\}))")
NODE_LAUNCHERS = {"node", "npm", "npx", "pnpm", "pnpx", "yarn", "bun", "bunx", "deno", "tsx",
                  "vite", "next", "storybook", "vitest", "jest", "playwright"}
WRAPPERS = {"env": {"-u", "--unset", "-C", "--chdir"}, "exec": {"-a"},
            "nohup": set(), "time": set(), "command": set()}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
working_directory = os.getcwd()


def launched_program(arguments):
    words = list(arguments)
    while words:
        if ASSIGNMENT.match(words[0]):
            words.pop(0)
        elif words[0] == "rtk":
            words = words[2:] if words[1:2] == ["proxy"] else words[1:]
        elif words[0] in WRAPPERS:
            wrapper = words.pop(0)
            while words and words[0].startswith("-"):
                option = words.pop(0)
                if option == "--":
                    break
                if wrapper == "env" and option.startswith("-S"):
                    try:
                        words = shlex.split(option[2:] or (words.pop(0) if words else "")) + words
                    except ValueError:
                        return None
                    break
                if option in WRAPPERS[wrapper] and words:
                    words.pop(0)
        else:
            return Path(words[0]).name
    return None


def names_ticket_path(word, bare=False):
    for value in (word, word.split("=", 1)[-1]):
        value = re.sub(r"^~(?=/|$)|\$\{HOME\}|\$HOME\b", lambda _: HOME, value)
        if not value or ("/" not in value and not bare):
            continue
        resolved = os.path.realpath(os.path.join(working_directory, os.path.normpath(value)))
        if resolved == TICKET_PROFILE or resolved.startswith(TICKET_PROFILE + os.sep) or \
                os.path.basename(resolved) == "ticket-browser.json":
            return True
    return False


sys.dont_write_bytecode = True
parser_dir = Path(sys.argv[1]).resolve().parent
sys.path.insert(0, str(parser_dir))
try:
    if not (parser_dir / "_shell_parser.py").is_file():
        raise ImportError
    from _shell_parser import ShellParser, UnsupportedShell
except ImportError:
    print("Required shell parser is unavailable", file=sys.stderr)
    raise SystemExit(2)


class Commands(ShellParser):
    """Recognize simple data commands; retain the old check for other syntax."""

    def __init__(self, source):
        super().__init__(source)
        self.forbidden = False
        self.ticket_state = False
        self.changes_directory = False
        self.relative_agent_browser_path = False
        self.unknown = False
        self.node_launch = False

    def finish(self, arguments):
        if not arguments:
            return
        if launched_program(arguments) in NODE_LAUNCHERS:
            self.node_launch = True
        if arguments[0] in {"cd", "pushd", "popd"}:
            self.changes_directory = True
        bare = [value for option, value in zip(arguments, arguments[1:]) if option in PATH_OPTIONS]
        bare += [word.split("=", 1)[1] for word in arguments
                 if "=" in word and word.split("=", 1)[0] in PATH_OPTIONS]
        runs_agent_browser = any(AGENT_BROWSER.match(Path(word).name) for word in arguments)
        if runs_agent_browser and any(
                not re.match(r"^(/|~(/|$)|\$HOME\b|\$\{HOME\})", value) for value in bare):
            self.relative_agent_browser_path = True
        if runs_agent_browser and (
                TICKET_STATE.search(" ".join(arguments)) or
                any(names_ticket_path(word) for word in arguments) or
                any(names_ticket_path(value, bare=True) for value in bare)):
            self.ticket_state = True
            return
        if arguments[0] == "rtk":
            arguments = arguments[1:]
            if arguments[:1] == ["proxy"]:
                arguments = arguments[1:]
        while len(arguments) > 1 and arguments[0] == "git":
            option = arguments[1]
            if (option not in {"--no-optional-locks", "--literal-pathspecs"}
                    and not option.startswith(("-C", "-c"))):
                break
            # New options must not suppress the fallback over executable config.
            if option == "--literal-pathspecs" or option.startswith("-c"):
                self.unknown = True
            arguments = ["git", *arguments[3 if option in {"-C", "-c"} else 2:]]
        if arguments[:2] == ["git", "add"]:
            options = True
            for argument in arguments[2:]:
                if argument == "--" and options:
                    options = False
                elif argument == "." or (options and (
                    argument == "--all" or
                    (argument.startswith("-") and not argument.startswith("--")
                     and "A" in argument)
                )):
                    self.forbidden = True
            return
        # Only these commands are known to treat their arguments/stdin as data.
        # An interpreter, eval, unknown wrapper, or pipeline consumer retains
        # the legacy check over the entire original command, including heredocs.
        if arguments[:1] in [["cat"], ["echo"], ["printf"]]:
            return
        if len(arguments) >= 2 and arguments[0] == "git" and arguments[1] in {
            "commit", "status", "diff", "log", "show", "rev-parse",
        }:
            return
        if len(arguments) >= 3 and arguments[0] == "gh" and (
            arguments[1] in {"pr", "issue"} and
            arguments[2] in {"create", "edit", "comment", "view", "list"}
        ):
            return
        self.unknown = True


try:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") != "Bash":
        sys.exit(0)
    command = payload.get("tool_input", {}).get("command", "")
    background = payload.get("tool_input", {}).get("run_in_background") is True
    if isinstance(payload.get("cwd"), str) and os.path.isabs(payload["cwd"]):
        working_directory = payload["cwd"]
    if not isinstance(command, str):
        sys.exit(0)
except (ValueError, AttributeError):
    sys.exit(0)

commands = Commands(command)
try:
    commands.parse()
except (UnsupportedShell, RecursionError):
    commands.unknown = True

reason = None
# Why not track cd targets: the hook never evaluates the command, so a relative
# agent-browser path after a directory change cannot be resolved; refuse it.
if commands.ticket_state or (
        commands.changes_directory and commands.relative_agent_browser_path) or (
        commands.unknown and "agent-browser" in command and (
            TICKET_STATE.search(command) or
            (DIRECTORY_CHANGE.search(command) and RELATIVE_PATH_OPTION.search(command)))):
    reason = "Use ticket-browser for the ticket browser session and profile."
elif commands.forbidden or (commands.unknown and LEGACY_PATTERN.search(command)):
    reason = "Do not git-add all files. Specify the file name(s) to add."
elif background and commands.node_launch:
    reason = "Start long-running Node processes through the memory gate: memgate run -- <command>"
if reason:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
PY
