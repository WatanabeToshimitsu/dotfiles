import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "instruction-eval.py"
spec = importlib.util.spec_from_file_location("instruction_eval", SCRIPT)
instruction_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(instruction_eval)


class RemoveOnceTest(unittest.TestCase):
    def test_removes_the_only_occurrence(self):
        self.assertEqual(instruction_eval.remove_once("a\n- rule\nb\n", "- rule\n"), "a\nb\n")

    def test_refuses_text_that_is_missing(self):
        with self.assertRaises(SystemExit):
            instruction_eval.remove_once("a\nb\n", "- rule\n")

    def test_refuses_text_that_appears_twice(self):
        with self.assertRaises(SystemExit):
            instruction_eval.remove_once("- rule\n- rule\n", "- rule\n")


class BuildPluginTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root = base / "repo"
        (self.root / "claude" / "skills" / "flow").mkdir(parents=True)
        (self.root / "claude" / "settings.json").write_text('{"language": "日本語"}')
        (self.root / "claude" / "CLAUDE.md").write_text("global\n- report state after a check\n")
        (self.root / "CLAUDE.md").write_text("project\n")
        (self.root / "claude" / "skills" / "flow" / "SKILL.md").write_text("skill\n- ask in the session\n")
        self.case = base / "cases" / "state"
        (self.case / "graders").mkdir(parents=True)
        (self.case / "prompt.md").write_text("---\nmax_turns: 3\n---\n\nhi\n")
        (self.case / "graders" / "g.md").write_text("---\ntype: regex\npattern: x\n---\n")
        self.out = base / "out"

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, ablation, ablate):
        (self.case / "ablation.json").write_text(json.dumps(ablation))
        return instruction_eval.build_plugin(self.root, self.case, self.out / ("off" if ablate else "on"), ablate)

    def test_prompt_opens_with_both_instruction_files_and_keeps_the_case_prompt(self):
        plugin = self.build({"file": "claude/CLAUDE.md", "remove": "- report state after a check\n"}, False)
        prompt = (plugin / "evals" / "state" / "prompt.md").read_text()
        front, body = prompt.split("\n---\n", 1)
        self.assertIn("max_turns: 3", front)
        self.assertTrue(body.lstrip().startswith("<system-reminder>"))
        self.assertIn("- report state after a check", body)
        self.assertIn("project", body)
        self.assertTrue(body.endswith("hi\n"))
        self.assertTrue((plugin / "skills" / "flow" / "SKILL.md").is_file())
        self.assertTrue((plugin / ".claude-plugin" / "plugin.json").is_file())

    def test_system_prompt_carries_the_language_setting(self):
        plugin = self.build({"file": "claude/CLAUDE.md", "remove": "- report state after a check\n"}, False)
        front = (plugin / "evals" / "state" / "prompt.md").read_text().split("\n---\n", 1)[0]
        line = next(l for l in front.splitlines() if l.startswith("append_system_prompt: "))
        self.assertIn("Always respond in 日本語.", json.loads(line.split(": ", 1)[1]))

    def test_global_instructions_sit_beside_the_skills_their_links_name(self):
        plugin = self.build({"file": "claude/CLAUDE.md", "remove": "- report state after a check\n"}, False)
        body = (plugin / "evals" / "state" / "prompt.md").read_text()
        self.assertIn(f"Contents of {plugin}/CLAUDE.md (user's private global instructions", body)

    def test_ablated_plugin_differs_only_by_the_removed_text(self):
        ablation = {"file": "claude/CLAUDE.md", "remove": "- report state after a check\n"}
        on_plugin, off_plugin = self.build(ablation, False), self.build(ablation, True)
        on = (on_plugin / "evals" / "state" / "prompt.md").read_text().replace(str(on_plugin), "<plugin>")
        off = (off_plugin / "evals" / "state" / "prompt.md").read_text().replace(str(off_plugin), "<plugin>")
        self.assertEqual(on.replace("- report state after a check\n", "", 1), off)

    def test_ablation_can_remove_several_passages(self):
        (self.root / "claude" / "CLAUDE.md").write_text("global\n- one\n- two\n")
        plugin = self.build({"file": "claude/CLAUDE.md", "remove": ["- one\n", "- two\n"]}, True)
        body = (plugin / "evals" / "state" / "prompt.md").read_text()
        self.assertNotIn("- one", body)
        self.assertNotIn("- two", body)

    def test_ablation_reaches_skill_files(self):
        plugin = self.build({"file": "claude/skills/flow/SKILL.md", "remove": "- ask in the session\n"}, True)
        self.assertEqual((plugin / "skills" / "flow" / "SKILL.md").read_text(), "skill\n")
        self.assertEqual((self.root / "claude" / "skills" / "flow" / "SKILL.md").read_text(),
                         "skill\n- ask in the session\n")


class VerdictTest(unittest.TestCase):
    def test_passes_when_every_current_run_passes_and_most_ablated_runs_fail(self):
        self.assertTrue(instruction_eval.verdict([1, 1, 1], [0, 0, 1]))

    def test_fails_when_a_current_run_fails(self):
        self.assertFalse(instruction_eval.verdict([1, 0.5, 1], [0, 0, 0]))

    def test_fails_when_the_ablated_version_mostly_passes(self):
        self.assertFalse(instruction_eval.verdict([1, 1, 1], [1, 1, 0]))


if __name__ == "__main__":
    unittest.main()
