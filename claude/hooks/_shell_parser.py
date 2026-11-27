"""Parse hook command text without executing it; callers supply finish policy."""

import ast
from pathlib import Path
import re
import shlex


class UnsupportedShell(ValueError):
    pass


class ShellParser:
    def __init__(self, source):
        self.source = source
        self.index = 0
        self.heredoc_bodies = []
        self.writes = []

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
            elif char == "`":
                self.backquote()
            elif char == "$":
                raise UnsupportedShell()
            else:
                value.append(char)
        if quote or self.index == start:
            raise UnsupportedShell()
        return "".join(value), quoted

    def backquote(self):
        """Report the commands in a backquote substitution, then refuse it as unmodeled syntax."""
        end = self.index
        while end < len(self.source) and self.source[end] != "`":
            end += 2 if self.source[end] == "\\" else 1
        if end < len(self.source):
            self.source, self.index = re.sub(r"\\([$`\\])", r"\1", self.source[self.index:end]), 0
            self.parse()
        # Why not resume after the body: callers fall back to pattern checks on
        # unmodeled syntax, and reading the body must only add findings.
        raise UnsupportedShell()

    def record_heredoc(self, owner, start, end, strip_tabs):
        body = self.source[start:end]
        self.heredoc_bodies.append((owner, re.sub(r"(?m)^\t+", "", body) if strip_tabs else body))

    def heredocs(self, pending):
        for delimiter, strip_tabs, quoted, owner in pending:
            start = self.index
            while self.index < len(self.source):
                line_start = self.index
                end = self.source.find("\n", self.index)
                if end < 0:
                    end = len(self.source)
                line = self.source[self.index:end]
                self.index = min(end + 1, len(self.source))
                candidate = line.lstrip("\t") if strip_tabs else line
                if candidate == delimiter:
                    self.record_heredoc(owner, start, line_start, strip_tabs)
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
                    pending.append((target, operator == "<<-", quoted, arguments))
                elif operator in {">", ">>"}:
                    self.writes.append((arguments, target, operator))
            else:
                argument, _ = self.word()
                arguments.append(argument)
        if nested or pending:
            raise UnsupportedShell()
        self.finish(arguments)


REDIRECT = re.compile(r"<<<|<<-|<<|<>|<&|<|>>|>&|>")
ANSI_C = re.compile(r"'((?:[^'\\]|\\.)*)'?", re.S)
UNMODELED_SHELL = re.compile(r"=~|\(\(|\$\{#?(?!#)[^}#]*(?:[#\s'\"<>()`;&|\\]|\$\{)")
PYTHON = re.compile(r"python[0-9.]*$")
LAUNCHERS = {"env", "command", "exec", "nohup", "time", "timeout", "nice", "sudo", "rtk", "proxy", "uv", "run"}
RESERVED_WORDS = {"!", "{", "}", "do", "done", "then", "else", "elif", "fi", "if", "while", "until"}
ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
WRAPPER_VALUE_OPTIONS = {
    "env": {"-u", "--unset", "-C", "--chdir"}, "exec": {"-a"},
    **dict.fromkeys(["time", "nohup", "nice", "timeout", "stdbuf"],
                    {"-n", "-k", "-s", "--adjustment", "--kill-after", "--signal", "-i", "-o", "-e"}),
}
SHELL_PROGRAMS = {"bash", "sh", "zsh", "dash", "ksh"}
SPAWNS = {"subprocess": {"run", "call", "check_call", "check_output", "Popen", "getoutput", "getstatusoutput"},
          "os": {"system", "popen"}}


def command_words(words):
    """The words from the command name on, past reserved words, assignments, and wrapper programs."""
    words = list(words)
    while words:
        program = Path(words[0]).name
        if words[0] in RESERVED_WORDS or ASSIGNMENT.match(words[0]):
            words = words[1:]
        elif program == "rtk":
            words = words[2:] if words[1:2] == ["proxy"] else words[1:]
        elif program in {"command", "builtin", "noglob"}:
            words = words[2:] if words[1:2] == ["--"] else words[1:]
        elif program in WRAPPER_VALUE_OPTIONS:
            values = WRAPPER_VALUE_OPTIONS[program]
            words = words[1:]
            # Why not stop at -- or an env assignment: the guards before this skipped
            # both and kept reading options, and a shorter skip would drop their denials.
            while words and (words[0].startswith("-") or program == "env" and ASSIGNMENT.match(words[0])):
                if words.pop(0) in values:
                    words = words[1:]
            if program == "timeout":
                words = words[1:]
        else:
            break
    return words


def shell_script(words):
    """The text eval or a shell's -c option runs, and whether reading it met only modeled options.

    The text is None when the words run none. A shell reading a file or stdin,
    or given --rcfile, also gives False; an -o value or an option after -c
    still gives the text, with False.
    """
    program = Path(words[0]).name if words else ""
    if program == "eval":
        return " ".join(words[1:]), True
    if program not in SHELL_PROGRAMS:
        return None, True
    modeled, reads_text, rest = True, False, iter(words[1:])
    for word in rest:
        if word in {"--", "-"}:
            word = next(rest, None)
            break
        if word in {"--rcfile", "--init-file"}:
            return None, False
        if not word.startswith(("-", "+")):
            break
        if word.startswith("--"):
            continue
        modeled = modeled and not reads_text
        if re.search(r"[oO]", word[1:]):
            modeled = False
            next(rest, None)
        reads_text = reads_text or (word[0] == "-" and "c" in word[1:])
    else:
        word = None
    if not reads_text or word is None:
        return None, False
    return word, modeled


def python_sources(parser, argvs):
    """Yield the Python source each python command in argvs runs: its -c text, a script this text writes, or its stdin heredoc."""
    files = {}
    for writer, target, operator in parser.writes:
        body = "".join(body for owner, body in parser.heredoc_bodies if owner is writer)
        files[Path(target)] = (files.get(Path(target), "") if operator == ">>" else "") + body
    for argv in argvs:
        words = list(argv)
        if re.match(r"command -\w*[vV]", " ".join(words[:2])):
            continue
        while words and (words[0] in LAUNCHERS or "=" in words[0] or re.match(r"[-\d]", words[0])):
            words.pop(0)
        if not words or not PYTHON.match(Path(words[0]).name):
            continue
        mode, rest = "stdin", iter(words[1:])
        for word in rest:
            if re.fullmatch(r"-\w*[cm]", word):
                mode = word[-1]
                break
            if word in {"-W", "-X"}:
                next(rest, None)
            elif word == "-" or not word.startswith("-"):
                mode = "stdin" if word == "-" else word
                break
        if mode == "c":
            yield next(rest, "")
        elif mode == "stdin":
            yield from (body for owner, body in parser.heredoc_bodies if owner is argv)
        elif mode != "m" and Path(mode) in files:
            yield files[Path(mode)]


def spawned_commands(source):
    """Yield the shell text of each subprocess or os call in Python source that has a literal first argument."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError, RecursionError):
        return
    modules, functions, shadowed = {}, set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update((alias.asname or alias.name, alias.name) for alias in node.names if alias.name in SPAWNS)
        elif isinstance(node, ast.ImportFrom):
            names = {alias.asname or alias.name: alias.name for alias in node.names}
            if node.module in SPAWNS:
                functions.update(name for name, original in names.items() if original in SPAWNS[node.module])
            else:
                shadowed.update(names)
    # Why not resolve scopes: a name also imported from another module is ambiguous, so skip it.
    functions -= shadowed
    for node in ast.walk(tree):
        func = getattr(node, "func", None)
        if not isinstance(node, ast.Call) or not node.args or not (
                isinstance(func, ast.Name) and func.id in functions or
                isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and
                func.attr in SPAWNS.get(modules.get(func.value.id), ())):
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            yield first.value
        elif isinstance(first, (ast.List, ast.Tuple)):
            argv = [element.value if isinstance(element, ast.Constant) and isinstance(element.value, str)
                    else "<expression>" for element in first.elts]
            shell = any(keyword.arg == "shell" and getattr(keyword.value, "value", None) is True
                        for keyword in node.keywords)
            # Why not join a shell=True sequence: sh runs only its first item; the rest become $0, $1, ...
            yield argv[0] if shell and argv else shlex.join(argv)


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
            self.backquote()
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
        for delimiter, strip_tabs, quoted, owner in pending:
            start = self.index
            while self.index < len(self.source):
                line_start = self.index
                end = self.source.find("\n", self.index)
                end = len(self.source) if end < 0 else end
                line = self.source[self.index:end]
                if (line.lstrip("\t") if strip_tabs else line) == delimiter or quoted:
                    self.index = end + 1
                    if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                        self.record_heredoc(owner, start, line_start, strip_tabs)
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
                    pending.append((target, operator == "<<-", quoted, arguments))
                elif operator in {">", ">>"} and target:
                    self.writes.append((arguments, target, operator))
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
