import json
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_DIR = REPO_ROOT / "claude"
LOCK = json.loads((CLAUDE_DIR / "dependencies.lock.json").read_text())
SETTINGS = json.loads((CLAUDE_DIR / "settings.json").read_text())
PINNED_MARKETPLACES = {
    name: entry["source"]
    for name, entry in SETTINGS["extraKnownMarketplaces"].items()
    if entry["source"]["source"] == "settings"
}


class DependencyLockTest(unittest.TestCase):
    def test_every_source_is_immutable(self) -> None:
        self.assertRegex(LOCK["claudeCode"], r"^\d+\.\d+\.\d+$")
        self.assertRegex(LOCK["statusLine"]["version"], r"^\d+\.\d+\.\d+$")
        self.assertRegex(LOCK["skillsCli"]["version"], r"^\d+\.\d+\.\d+$")
        for skill_source in LOCK["skills"]:
            self.assertRegex(skill_source["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(len(PINNED_MARKETPLACES), 1)
        marketplace = next(iter(PINNED_MARKETPLACES.values()))
        for plugin in marketplace["plugins"]:
            self.assertRegex(plugin["source"]["sha"], r"^[0-9a-f]{40}$")

    def test_status_line_uses_the_locked_version(self) -> None:
        package = LOCK["statusLine"]["package"]
        version = LOCK["statusLine"]["version"]
        command = SETTINGS["statusLine"]["command"]

        self.assertEqual(command, f"npx -y {package}@{version}")
        self.assertNotIn("@latest", command)

    def test_only_pinned_plugin_ids_are_enabled(self) -> None:
        marketplace = next(iter(PINNED_MARKETPLACES.values()))
        expected = {
            f"{plugin['name']}@{marketplace['name']}"
            for plugin in marketplace["plugins"]
        }
        actual = {
            plugin_id
            for plugin_id, enabled in SETTINGS["enabledPlugins"].items()
            if enabled
        }

        self.assertEqual(actual, expected)

    def test_settings_marketplace_name_matches_its_key(self) -> None:
        key, marketplace = next(iter(PINNED_MARKETPLACES.items()))
        self.assertEqual(key, marketplace["name"])

    def test_manifestless_lsp_plugin_keeps_its_inline_definition(self) -> None:
        marketplace = next(iter(PINNED_MARKETPLACES.values()))
        typescript_lsp = next(
            plugin
            for plugin in marketplace["plugins"]
            if plugin["name"] == "typescript-lsp"
        )

        self.assertFalse(typescript_lsp["strict"])
        self.assertEqual(
            typescript_lsp["lspServers"]["typescript"]["command"],
            "typescript-language-server",
        )

    def test_third_party_marketplaces_do_not_auto_update(self) -> None:
        for name, marketplace in SETTINGS.get("extraKnownMarketplaces", {}).items():
            with self.subTest(marketplace=name):
                self.assertFalse(marketplace.get("autoUpdate", False))

    def test_skill_names_are_unique(self) -> None:
        names = [name for source in LOCK["skills"] for name in source["names"]]
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main()
