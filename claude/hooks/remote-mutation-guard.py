#!/usr/bin/env python3
"""Guard transparent Git/GitHub publication commands; never execute hook input."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


class UnsupportedShell(ValueError):
    pass


class ShellWords:
    """Tokenize simple shell forms without evaluating expansions or heredocs."""

    def __init__(self, source):
        self.source = source
        self.index = 0
        self.commands = []

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
        if arguments:
            self.commands.append(list(arguments))

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


FORCE_REASON = "強制 push・履歴の上書き・リモート削除は許可していません。通常の push を使用してください。"
OPAQUE_REASON = "公開操作の引数を検査できません。変数・別名・複合処理を避け、対象を明記した単独の git/gh 呼び出しにしてください。"
CONNECTOR_REASON = "Codex の PR 作成は、人の確認が設定された GitHub 連携を使用してください。CLI/API の別経路では作成しないでください。"
MAX_BYTES = 4 * 1024 * 1024


def unwrap(words):
    words = list(words)
    while words:
        program = Path(words[0]).name
        if program == "rtk":
            words = words[1:]
            if words[:1] == ["proxy"]:
                words = words[1:]
        elif program in {"command", "builtin", "noglob", "exec"}:
            words = words[1:]
            if words[:1] == ["--"]:
                words = words[1:]
        elif program == "env":
            words = words[1:]
            while words:
                if words[0] in {"-u", "--unset"}:
                    words = words[2:]
                elif words[0] in {"--", "-i", "--ignore-environment"} or re.match(r"^[A-Za-z_]\w*=", words[0]):
                    words = words[1:]
                else:
                    break
        elif program in {"time", "nohup", "nice", "timeout", "stdbuf"}:
            words = words[1:]
            while words and words[0].startswith("-"):
                option = words.pop(0)
                if option in {"-n", "-k", "-s", "--adjustment", "--kill-after", "--signal", "-i", "-o", "-e"}:
                    words = words[1:]
            if program == "timeout":
                words = words[1:]
        elif re.match(r"^[A-Za-z_]\w*=", words[0]):
            words = words[1:]
        else:
            break
    if words:
        words[0] = Path(words[0]).name
    return words


def argument(words, *names):
    for index, word in enumerate(words):
        if word in names and index + 1 < len(words):
            return words[index + 1]
        for name in names:
            if word.startswith(name + "="):
                return word[len(name) + 1:]
            if len(name) == 2 and name.startswith("-") and word.startswith(name) and word != name:
                return word[2:]
    return None


def option_parts(words, value_options):
    flags = []
    positional = []
    values = {}
    index = 0
    while index < len(words):
        word = words[index]
        if word == "--":
            positional.extend(words[index + 1:])
            break
        if word in value_options:
            if index + 1 >= len(words):
                raise UnsupportedShell()
            values[word] = words[index + 1]
            index += 2
            continue
        name, separator, value = word.partition("=")
        short = next((name for name in value_options if len(name) == 2 and word.startswith(name) and word != name), None)
        if separator and name in value_options:
            values[name] = value
        elif short:
            values[short] = word[2:]
        elif word.startswith("-"):
            flags.append(word)
        else:
            positional.append(word)
        index += 1
    return flags, positional, values


PUSH_VALUE_OPTIONS = {"--repo", "--receive-pack", "--exec", "-o", "--push-option"}


def push_arguments(args):
    flags, positional, values = option_parts(args, PUSH_VALUE_OPTIONS)
    if "--repo" in values:
        return flags, values["--repo"], positional, values
    return flags, positional[0] if positional else None, positional[1:], values


def classify_words(words):
    original = list(words)
    words = unwrap(words)
    if not words:
        return "continue", {}
    if words[0] in {"bash", "sh", "zsh"}:
        for index, word in enumerate(words[1:], 1):
            if word.startswith("-") and "c" in word and index + 1 < len(words):
                return classify_shell(words[index + 1])
    if words[0] == "git":
        index = 1
        configs = []
        while index < len(words) and words[index].startswith("-"):
            option = words[index]
            if option in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}:
                if index + 1 >= len(words):
                    return "deny", {"reason": OPAQUE_REASON}
                if option == "-c":
                    configs.append(words[index + 1])
                index += 2
            elif option.startswith("-c"):
                configs.append(option[2:])
                index += 1
            else:
                index += 1
        subcommand = words[index] if index < len(words) else ""
        for config in configs:
            key, _, value = config.partition("=")
            if key.lower().startswith("alias.") and key[6:] == subcommand:
                if "push" in value:
                    return "deny", {"reason": OPAQUE_REASON}
            if key.lower().endswith(".mirror") and value.lower() in {"true", "1", "yes", "on"}:
                if subcommand == "push":
                    return "deny", {"reason": FORCE_REASON}
        if subcommand != "push":
            return "continue", {}
        environment = original[:len(original) - len(words)]
        if any(re.match(r"^(?:GIT_CONFIG\w*|GIT_DIR|GIT_WORK_TREE|GIT_COMMON_DIR|GIT_NAMESPACE|GIT_REPLACE_REF_BASE)=", word) for word in environment):
            return "deny", {"reason": OPAQUE_REASON}
        args = words[index + 1:]
        flags, _, refs, _ = push_arguments(args)
        dry_run = False
        for flag in flags:
            if flag.startswith("--") and "--no-dry-run".startswith(flag):
                dry_run = False
            elif (flag.startswith("--") and "--dry-run".startswith(flag)) or (flag.startswith("-") and not flag.startswith("--") and "n" in flag[1:]):
                dry_run = True
        if "--help" in flags or "-h" in flags or dry_run:
            return "continue", {}
        if any("<substitution>" in word for word in args):
            return "deny", {"reason": OPAQUE_REASON}
        for flag in flags:
            name = flag.split("=", 1)[0]
            if ((name.startswith("--") and any(option.startswith(name) for option in ["--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete", "--prune"])) or
                (flag.startswith("-") and not flag.startswith("--") and any(letter in flag[1:] for letter in "fd"))):
                return "deny", {"reason": FORCE_REASON}
        if any(ref.startswith(("+", ":")) for ref in refs):
            return "deny", {"reason": FORCE_REASON}
        return "continue", {"pushes": [{"git_options": words[1:index], "args": args}]}
    if words[0] != "gh":
        return "continue", {}
    index = 1
    while index < len(words) and words[index].startswith("-"):
        index += 2 if words[index] in {"-R", "--repo", "--hostname"} else 1
    args = words[index:]
    flags, _, _ = option_parts(args, {"--title", "-t", "--body", "-b", "--body-file", "-F",
                                "--base", "-B", "--head", "-H", "--template", "-T",
                                "--repo", "-R", "--method", "-X", "--field", "-f",
                                "--raw-field", "--input", "--header"})
    if "--help" in flags or "-h" in flags:
        return "continue", {}
    if args[:2] == ["pr", "create"]:
        return "pr", {
            "title": argument(args[2:], "--title", "-t") or "",
            "body": argument(args[2:], "--body", "-b") or "",
            "body_file": argument(args[2:], "--body-file", "-F", "--template", "-T"),
            "base": argument(args[2:], "--base", "-B"),
            "head": argument(args[2:], "--head", "-H"),
            "repo": argument(words[1:], "--repo", "-R"),
        }
    if args[:1] == ["api"]:
        joined = " ".join(args[1:])
        method = argument(args, "--method", "-X")
        _, positional, values = option_parts(args[1:], {"--method", "-X", "--field", "-F", "--raw-field", "-f", "--input", "--header", "-H", "--hostname", "--jq", "-q", "--template", "-t", "--cache"})
        endpoint = unquote(urlsplit(positional[0]).path).rstrip("/") if positional else ""
        fields = any(word in {"-f", "-F", "--field", "--raw-field", "--input"} or
                     word.startswith(("-f", "-F", "--field=", "--raw-field=", "--input=")) for word in args)
        opaque_input = "--input" in values or any(re.search(r"(?:^|=)@", word) for word in args[1:])
        if (endpoint.endswith("graphql") or "/git/refs" in endpoint) and opaque_input:
            return "deny", {"reason": OPAQUE_REASON}
        if "/git/refs" in endpoint and ((method or "").upper() == "DELETE" or re.search(r"\bforce[=:]true\b", joined)):
            return "deny", {"reason": FORCE_REASON}
        if "createPullRequest" in joined or (
            re.search(r"(?:^|/)repos/[^/]+/[^/]+/pulls$", endpoint) and
            ((method or "").upper() == "POST" or (method is None and fields))
        ):
            return "pr", {"body": joined, "uninspected": "GitHub API の本文・対象差分は未検査"}
    return "continue", {}


def classify_shell(command):
    if not isinstance(command, str):
        return "deny", {"reason": OPAQUE_REASON}
    parsed = ShellWords(command)
    try:
        parsed.parse()
    except (UnsupportedShell, RecursionError):
        if re.search(r"\b(?:git|gh)\b[\s\S]*\b(?:push|create|api)\b", command):
            return "deny", {"reason": OPAQUE_REASON}
        return "continue", {}
    result = ("continue", {})
    pushes = []
    for words in parsed.commands:
        decision, detail = classify_words(words)
        pushes.extend(detail.get("pushes", []))
        if decision == "deny":
            return decision, detail
        if decision == "pr":
            result = decision, detail
    if result[0] == "pr" and len(parsed.commands) > 1:
        return "deny", {"reason": OPAQUE_REASON}
    if result[0] == "continue" and pushes:
        result = "continue", {"pushes": pushes}
    return result


SECRET_PATTERNS = {
    "private-key": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
    "github-token": r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b",
    "aws-access-key": r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "api-key": r"\bsk-(?:ant-|proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b",
    "slack-token": r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b",
    "credential-url": r"\b(?:https?|postgres(?:ql)?|mysql)://[^\s/:]+:[^\s/@]{8,}@",
}


def secret_findings(text):
    return {name for name, pattern in SECRET_PATTERNS.items() if re.search(pattern, text)}


def git_output(cwd, *args):
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-c", "log.showSignature=false", "-C", str(cwd), *args],
        text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=5,
    )
    if result.returncode or len(result.stdout.encode()) > MAX_BYTES:
        raise ValueError("Git inspection unavailable")
    return result.stdout.strip()


def commit_text(cwd, detail):
    requested_repo = (detail.get("repo") or detail.get("repository") or
                      detail.get("repo_full_name") or detail.get("repository_full_name"))
    if requested_repo:
        if detail.get("owner") and "/" not in requested_repo:
            requested_repo = detail["owner"] + "/" + requested_repo
        remote = git_output(cwd, "config", "--get", "remote.origin.url")
        if not remote.removesuffix(".git").endswith("/" + requested_repo) and not remote.removesuffix(".git").endswith(":" + requested_repo):
            raise ValueError("PR repository does not match the local repository")
    base = detail.get("base") or detail.get("base_branch")
    head = detail.get("head") or detail.get("head_branch") or "HEAD"
    if base:
        candidates = ["refs/remotes/origin/" + base, base]
    else:
        candidates = ["refs/remotes/origin/HEAD", "refs/remotes/origin/main", "main",
                      "refs/remotes/origin/master", "master"]
    base_oid = None
    for candidate in candidates:
        try:
            base_oid = git_output(cwd, "rev-parse", "--verify", "--end-of-options", candidate + "^{commit}")
            break
        except ValueError:
            continue
    if not base_oid:
        raise ValueError("Base ref unavailable")
    head_oid = git_output(cwd, "rev-parse", "--verify", "--end-of-options", head + "^{commit}")
    revision = base_oid + ".." + head_oid
    count = int(git_output(cwd, "rev-list", "--count", revision, "--"))
    if count > 200:
        raise ValueError("Commit range too large")
    text = git_output(cwd, "log", "--no-ext-diff", "--no-textconv", "--format=%B", "-m", "-p", revision, "--")
    return text, count


def inspect_pr(cwd, detail):
    texts = [str(detail.get("title") or ""), str(detail.get("body") or "")]
    warnings = []
    if detail.get("uninspected"):
        warnings.append(detail["uninspected"])
    if detail.get("issue"):
        warnings.append("既存 Issue から引き継ぐ本文は未検査")
    body_file = detail.get("body_file")
    if body_file:
        try:
            if body_file == "-":
                raise ValueError("stdin unavailable")
            path = Path(body_file).expanduser()
            if not path.is_absolute():
                path = Path(cwd) / path
            if path.stat().st_size > MAX_BYTES or not path.is_file():
                raise ValueError("body unavailable")
            texts.append(path.read_text())
        except (OSError, ValueError):
            warnings.append("PR 本文ファイルは未検査")
    findings = set().union(*(secret_findings(text) for text in texts))
    try:
        history, count = commit_text(cwd, detail)
        findings.update(secret_findings(history))
        summary = f"本文とローカルの {count} コミットを既知の秘密情報パターンで検査しました。"
        if count == 0:
            warnings.append("差分が空のため公開対象との一致を要確認")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        summary = "PR 本文を既知の秘密情報パターンで検査しました。"
        warnings.append("公開対象コミットは未検査")
    if findings:
        return True, "秘密情報の疑いを検出しました: " + ", ".join(sorted(findings)) + "。値は出力していません。公開を止めて内容を確認してください。"
    summary += "検出なしは秘密情報がない保証ではありません。"
    if warnings:
        summary += " " + "。".join(warnings) + "。"
    return False, summary


def inspect_push(cwd, push):
    options = push["git_options"]
    index = 0
    while index < len(options):
        word = options[index]
        if word == "-C":
            cwd = Path(cwd) / options[index + 1]
            index += 2
        elif word.startswith("-C"):
            cwd = Path(cwd) / word[2:]
            index += 1
        elif word.startswith(("--git-dir", "--work-tree", "--config-env", "-c")):
            return True, OPAQUE_REASON
        else:
            index += 1
    args = push["args"]
    flags, remote, refs, values = push_arguments(args)
    refs = refs or ["HEAD"]
    try:
        if not remote:
            branch = git_output(cwd, "symbolic-ref", "--short", "HEAD")
            try:
                remote = git_output(cwd, "config", "--get", "branch." + branch + ".pushRemote")
            except ValueError:
                try:
                    remote = git_output(cwd, "config", "--get", "remote.pushDefault")
                except ValueError:
                    remote = git_output(cwd, "config", "--get", "branch." + branch + ".remote")
        for suffix in ["mirror", "push"]:
            try:
                value = git_output(cwd, "config", "--get-all", "remote." + remote + "." + suffix)
                if (suffix == "mirror" and value.lower() in {"true", "1", "yes", "on"}) or (suffix == "push" and any(line.startswith(("+", ":")) for line in value.splitlines())):
                    return True, FORCE_REASON
            except ValueError:
                pass
        if any(flag not in {"-u", "--set-upstream", "--porcelain", "-v", "--verbose", "-q", "--quiet", "--no-verify"} for flag in flags) or set(values) - {"--repo"}:
            return False, "通常 push は許可されていますが、このオプション構成の公開対象コミットは未検査です。"
        findings = set()
        for ref in refs:
            source, separator, destination = ref.partition(":")
            if not separator:
                destination = source
            if destination == "HEAD":
                destination = git_output(cwd, "symbolic-ref", "--short", "HEAD")
            destination = destination.removeprefix("refs/heads/")
            base = "refs/remotes/" + remote + "/" + destination
            try:
                git_output(cwd, "rev-parse", "--verify", "--end-of-options", base)
            except ValueError:
                base = "refs/remotes/" + remote + "/HEAD"
            history, _ = commit_text(cwd, {"base": base, "head": source})
            findings.update(secret_findings(history))
        if findings:
            return True, "push 前に秘密情報の疑いを検出しました: " + ", ".join(sorted(findings)) + "。値は出力していません。公開を止めて確認してください。"
        return False, ""
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False, "通常 push は許可されていますが、リモート追跡情報が不足しているため公開対象コミットは未検査です。"


def respond(decision=None, reason=""):
    output = {"hookEventName": "PreToolUse"}
    if decision:
        output.update(permissionDecision=decision, permissionDecisionReason=reason)
    if reason:
        output["additionalContext"] = reason
    print(json.dumps({"hookSpecificOutput": output}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=["claude", "codex"], required=True)
    client = parser.parse_args().client
    try:
        payload = json.load(sys.stdin)
        tool = payload.get("tool_name", "")
        data = payload.get("tool_input") or {}
        cwd = payload.get("cwd") or "."
        if not isinstance(data, dict):
            raise ValueError("Invalid tool input")
        if tool in {"Bash", "exec_command", "shell_command"}:
            decision, detail = classify_shell(data.get("command", data.get("cmd", "")))
        elif "github" in tool.lower() and data.get("force") is True:
            decision, detail = "deny", {"reason": FORCE_REASON}
        elif re.search(r"create_?pull_?request|createPullRequest", tool, re.I):
            decision, detail = "pr", data
        elif "pull_request_write" in tool and data.get("method") == "create":
            decision, detail = "pr", data
        else:
            return
        if decision == "deny":
            respond("deny", detail["reason"])
        elif decision == "continue" and detail.get("pushes"):
            warnings = []
            for push in detail["pushes"]:
                blocked, report = inspect_push(cwd, push)
                if blocked:
                    respond("deny", report)
                    return
                if report:
                    warnings.append(report)
            if warnings:
                respond(reason=" ".join(dict.fromkeys(warnings)))
        elif decision == "pr":
            blocked, report = inspect_pr(cwd, detail)
            if blocked:
                respond("deny", report)
            elif client == "codex" and tool in {"Bash", "exec_command", "shell_command"}:
                respond("deny", CONNECTOR_REASON + " " + report)
            elif client == "claude":
                respond("ask", report + " 作成先・タイトル・本文・差分を確認し、この PR の作成を承認してください。")
            else:
                # Codex does not support hook ask decisions. Its connector's
                # prompt + user reviewer settings own the human approval.
                respond(reason=report + " PR 作成前にユーザーの確認が必要です。")
    except (ValueError, TypeError, AttributeError, RecursionError):
        respond("deny", "公開操作の検査入力を解釈できませんでした。設定を確認してください。")


if __name__ == "__main__":
    main()
