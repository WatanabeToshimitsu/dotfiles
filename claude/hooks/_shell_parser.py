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


REDIRECT = re.compile(r"<<<|<<-|<<|<>|<&|<|>>|>&|>")
ANSI_C = re.compile(r"'((?:[^'\\]|\\.)*)'?", re.S)
UNMODELED_SHELL = re.compile(r"=~|\(\(|\$\{#?(?!#)[^}#]*(?:[#\s'\"<>()`;&|\\]|\$\{)")


class LenientParser(ShellParser):
    """Locate simple commands in text ShellParser rejects; expansions stay literal.

    Quoted text, comments, and heredoc bodies never start a command, except
    the $( ) substitutions inside them. Syntax whose boundaries this scanner
    does not model, such as backquote substitution, raises UnsupportedShell.
    """

    def substitution(self, char):
        if char == "$" and self.source.startswith("(", self.index):
            self.index += 1
            self.parse(")")
        elif char == "`":
            raise UnsupportedShell()
        else:
            return False
        return True

    def expansions(self, stop):
        value = []
        while self.index < len(self.source) and self.source[self.index] != stop:
            char = self.source[self.index]
            self.index += 1
            following = self.source[self.index:self.index + 1]
            if char == "\\" and following and following in "$`\\\n" + ('"' if stop == '"' else ""):
                if following != "\n":
                    value.append(following)
                self.index += 1
            elif self.substitution(char):
                value.append("<substitution>")
            else:
                value.append(char)
        self.index += 1
        return "".join(value)

    def word(self, closer=None):
        value = []
        quoted = False
        while self.index < len(self.source):
            char = self.source[self.index]
            if char in " \t\r\n;&|()<>" or char == closer:
                break
            self.index += 1
            if char == "'":
                end = self.source.find("'", self.index)
                end = len(self.source) if end < 0 else end
                value.append(self.source[self.index:end])
                self.index = end + 1
                quoted = True
            elif char == '"':
                value.append(self.expansions('"'))
                quoted = True
            elif char == "$" and self.source.startswith("'", self.index):
                match = ANSI_C.match(self.source, self.index)
                if "\\" in match.group(1):
                    raise UnsupportedShell()
                value.append(match.group(1))
                self.index = match.end()
                quoted = True
            elif char == "\\":
                if self.source[self.index:self.index + 1] != "\n":
                    value.append(self.source[self.index:self.index + 1])
                    quoted = True
                self.index += 1
            elif self.substitution(char):
                value.append("<substitution>")
            else:
                value.append(char)
        return "".join(value), quoted

    def heredocs(self, pending):
        for delimiter, strip_tabs, quoted in pending:
            while self.index < len(self.source):
                end = self.source.find("\n", self.index)
                end = len(self.source) if end < 0 else end
                line = self.source[self.index:end]
                if (line.lstrip("\t") if strip_tabs else line) == delimiter or quoted:
                    self.index = end + 1
                    if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                        break
                else:
                    self.expansions("\n")

    def parse(self, closer=None):
        arguments = []
        pending = []
        while self.index < len(self.source):
            char = self.source[self.index]
            if char == closer:
                self.index += 1
                break
            if char in " \t\r":
                self.index += 1
            elif self.source.startswith("\\\n", self.index):
                self.index += 2
            elif char == "#":
                end = self.source.find("\n", self.index)
                self.index = end if end >= 0 else len(self.source)
            elif char in "<>":
                operator = REDIRECT.match(self.source, self.index).group()
                self.index += len(operator)
                if operator in {"<", ">"} and self.source.startswith("(", self.index):
                    self.index += 1
                    self.parse(")")
                    continue
                while self.index < len(self.source) and self.source[self.index] in " \t":
                    self.index += 1
                target, quoted = self.word(closer)
                if operator in {"<<", "<<-"} and target:
                    pending.append((target, operator == "<<-", quoted))
            elif char in ";&|()\n":
                self.finish(arguments)
                arguments = []
                self.index += 1
                if char == "(":
                    self.parse(")")
                elif char == "\n":
                    self.heredocs(pending)
                    pending = []
            else:
                word, quoted = self.word(closer)
                if quoted or not word.isdigit() or self.source[self.index:self.index + 1] not in {"<", ">"}:
                    arguments.append(word)
        self.finish(arguments)
