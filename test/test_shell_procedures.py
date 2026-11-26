"""Run the shell procedures written in Markdown under both bash and zsh.

The Bash tool runs zsh, while checks were often run with `bash -c` (#357).
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SHELLS = {"bash": ["bash", "-c"], "zsh": ["zsh", "-f", "-c"]}
FENCE = re.compile(r"^```(?:bash|sh|zsh|shell)\n(.*?)^```", re.M | re.S)
# zsh reads `$name:x` as a history modifier on the variable, bash as text.
ZSH_MODIFIER = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*:[A-Za-z&]")


def shell_blocks():
    files = subprocess.run(["git", "-C", str(ROOT), "ls-files", "*.md"],
                           capture_output=True, text=True, check=True).stdout.split()
    for name in files:
        for block in FENCE.findall((ROOT / name).read_text(encoding="utf-8")):
            yield name, block


class ShellProcedureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [shell for shell in SHELLS if not shutil.which(shell)]
        if missing:
            raise AssertionError(f"both shells are required, missing: {missing}")

    def test_markdown_shell_blocks_avoid_zsh_variable_modifiers(self):
        found = [(name, match) for name, block in shell_blocks()
                 for match in ZSH_MODIFIER.findall(block)]
        self.assertEqual(found, [])

    def git(self, *args, cwd=None):
        return subprocess.run(["git", *args], cwd=cwd, env=self.env, capture_output=True,
                              text=True, check=True).stdout.strip()

    def test_main_sync_chain_merges_and_keeps_local_edits_in_both_shells(self):
        text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        chain = next(block for block in FENCE.findall(text) if "merge --ff-only --autostash" in block)
        results = {}
        for shell, command in SHELLS.items():
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "gitconfig").write_text(
                    "[user]\n\tname = t\n\temail = t@example.com\n[commit]\n\tgpgsign = false\n"
                    "[init]\n\tdefaultBranch = main\n")
                self.env = {"PATH": os.environ["PATH"], "HOME": directory, "LC_ALL": "C",
                            "GIT_CONFIG_GLOBAL": str(root / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1"}
                main, upstream = root / "main", root / "upstream"
                self.git("init", "-q", "--bare", str(root / "origin.git"))
                self.git("clone", "-q", str(root / "origin.git"), str(upstream))
                settings = upstream / "claude" / "settings.json"
                settings.parent.mkdir()
                lines = {"merged": 1, "x1": 0, "x2": 0, "x3": 0, "x4": 0, "local": 1}
                settings.write_text(json.dumps(lines, indent=2) + "\n")
                self.git("add", "claude/settings.json", cwd=upstream)
                self.git("commit", "-q", "-m", "seed", cwd=upstream)
                self.git("push", "-q", "origin", "HEAD:main", cwd=upstream)
                self.git("clone", "-q", str(root / "origin.git"), str(main))
                settings.write_text(json.dumps(dict(lines, merged=2), indent=2) + "\n")
                self.git("commit", "-q", "-am", "merged change", cwd=upstream)
                self.git("push", "-q", "origin", "HEAD:main", cwd=upstream)
                local = main / "claude" / "settings.json"
                local.write_text(json.dumps(dict(lines, local=2), indent=2) + "\n")

                run = subprocess.run([*command, chain.replace("<main>", f"'{main}'")], env=self.env,
                                     capture_output=True, text=True, timeout=60)
                results[shell] = (run.returncode,
                                  self.git("rev-parse", "HEAD", cwd=main) ==
                                  self.git("rev-parse", "origin/main", cwd=main),
                                  json.loads(local.read_text()))
                with self.subTest(shell=shell):
                    self.assertEqual(results[shell], (0, True, dict(lines, merged=2, local=2)),
                                     run.stderr)
        self.assertEqual(results["bash"], results["zsh"])


if __name__ == "__main__":
    unittest.main()
