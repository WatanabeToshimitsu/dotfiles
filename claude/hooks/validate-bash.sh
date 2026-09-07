#!/bin/bash
# Keep stdin for the hook payload; never evaluate the supplied shell command.
exec python3 /dev/fd/3 3<<'PY'
import json
import re
import sys


LEGACY_PATTERN = re.compile(r"\bgit add (-A|--all|\.($|[ ;|&]))", re.MULTILINE)


class UnsupportedShell(ValueError):
    pass


class Commands:
    """Recognize simple data commands; retain the old check for other syntax."""

    def __init__(self, source):
        self.source = source
        self.index = 0
        self.forbidden = False
        self.unknown = False

    def word(self):
        value = []
        quote = None
        quoted = False
        start = self.index
        while self.index < len(self.source):
            char = self.source[self.index]
            if quote is None and char in " \t\r\n;&|()<>":
                break
            self.index += 1
            if char == quote:
                quote = None
            elif quote == "'":
                value.append(char)
            elif char in "'\"" and quote is None:
                quote = char
                quoted = True
            elif char == "\\":
                if self.index == len(self.source):
                    raise UnsupportedShell()
                escaped = self.source[self.index]
                self.index += 1
                if escaped == "\n":
                    continue
                if quote == '"' and escaped not in '$`"\\':
                    value.append("\\")
                value.append(escaped)
                quoted = True
            elif char == "$" and self.source[self.index:self.index + 1] == "(":
                self.index += 1
                self.parse(nested=True)
                value.append("<substitution>")
            elif char in "$`":
                raise UnsupportedShell()
            else:
                value.append(char)
        if quote or self.index == start:
            raise UnsupportedShell()
        return "".join(value), quoted

    def finish(self, arguments):
        if not arguments:
            return
        if arguments[0] == "rtk":
            arguments = arguments[1:]
            if arguments[:1] == ["proxy"]:
                arguments = arguments[1:]
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

    def heredocs(self, pending):
        for delimiter, strip_tabs, quoted in pending:
            while self.index < len(self.source):
                end = self.source.find("\n", self.index)
                if end < 0:
                    end = len(self.source)
                line = self.source[self.index:end]
                self.index = min(end + 1, len(self.source))
                candidate = line.lstrip("\t") if strip_tabs else line
                if candidate == delimiter:
                    break
                # Unquoted heredocs can execute substitutions, even for cat.
                if not quoted and ("$" in line or "`" in line or "\\" in line):
                    raise UnsupportedShell()
            else:
                raise UnsupportedShell()

    def parse(self, nested=False):
        arguments = []
        pending = []
        while self.index < len(self.source):
            char = self.source[self.index]
            if char in " \t\r":
                self.index += 1
            elif self.source.startswith("\\\n", self.index):
                self.index += 2
            elif char == "#":
                end = self.source.find("\n", self.index)
                self.index = end if end >= 0 else len(self.source)
            elif char == ")":
                if not nested or pending:
                    raise UnsupportedShell()
                self.finish(arguments)
                self.index += 1
                return
            elif char == "(":
                if arguments:
                    raise UnsupportedShell()
                self.index += 1
                self.parse(nested=True)
            elif char in ";&|\n":
                self.finish(arguments)
                arguments = []
                self.index += 1
                if char == "\n":
                    self.heredocs(pending)
                    pending = []
            elif char in "<>":
                match = re.match(r"<<<|<<-|<<|>>|<>|[<>][&|]?", self.source[self.index:])
                operator = match.group()
                self.index += len(operator)
                while self.index < len(self.source) and self.source[self.index] in " \t":
                    self.index += 1
                target, quoted = self.word()
                if operator in {"<<", "<<-"}:
                    pending.append((target, operator == "<<-", quoted))
            else:
                argument, _ = self.word()
                arguments.append(argument)
        if nested or pending:
            raise UnsupportedShell()
        self.finish(arguments)


try:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") != "Bash":
        sys.exit(0)
    command = payload.get("tool_input", {}).get("command", "")
    if not isinstance(command, str):
        sys.exit(0)
except (ValueError, AttributeError):
    sys.exit(0)

commands = Commands(command)
try:
    commands.parse()
except (UnsupportedShell, RecursionError):
    commands.unknown = True

if commands.forbidden or (commands.unknown and LEGACY_PATTERN.search(command)):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Do not git-add all files. Specify the file name(s) to add.",
    }}))
PY
