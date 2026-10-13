"""Parse hook command text without executing it; callers supply finish policy."""

import re


class UnsupportedShell(ValueError):
    pass


class ShellParser:
    def __init__(self, source):
        self.source = source
        self.index = 0

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
