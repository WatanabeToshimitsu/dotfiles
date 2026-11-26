"""Check that the Claude Code CLI writes claude/settings.json back unchanged (#360).

~/.claude/settings.json links to this file, and the CLI rewrites the whole file
in its own key order on any user-settings write. A file in another order leaves
a diff that stops `git pull`. Needs the local CLI and plugin registry, so CI
skips it.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SETTINGS = Path(__file__).resolve().parents[1] / "claude" / "settings.json"
REGISTRY = Path.home() / ".claude" / "plugins"
REGISTRY_FILES = ["installed_plugins.json", "known_marketplaces.json"]


@unittest.skipUnless(shutil.which("claude") and all((REGISTRY / name).is_file() for name in REGISTRY_FILES),
                     "needs the claude CLI and a local plugin registry")
class SettingsCliOrderTest(unittest.TestCase):
    def test_a_plugin_disable_and_enable_round_trip_leaves_the_file_byte_identical(self):
        original = SETTINGS.read_bytes()
        plugin = next(name for name, on in json.loads(original)["enabledPlugins"].items() if on)
        with tempfile.TemporaryDirectory() as home:
            config = Path(home) / ".claude"
            (config / "plugins").mkdir(parents=True)
            # Why not a symlink: the CLI would rewrite the tracked file itself.
            (config / "settings.json").write_bytes(original)
            for name in REGISTRY_FILES:
                shutil.copy(REGISTRY / name, config / "plugins" / name)
            environment = {key: value for key, value in os.environ.items() if key != "CLAUDE_CONFIG_DIR"}
            environment["HOME"] = home
            for action in ("disable", "enable"):
                subprocess.run(["claude", "plugin", action, plugin, "--scope", "user"], env=environment,
                               capture_output=True, text=True, timeout=120, check=True)
            self.assertEqual((config / "settings.json").read_text(), original.decode())
        self.assertEqual(SETTINGS.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
