import importlib.util
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "claude/skills/evidence-video/scripts/trim_idle.py"
SPEC = importlib.util.spec_from_file_location("trim_idle", SCRIPT)
trim_idle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trim_idle)


class KeepRangesTest(unittest.TestCase):
    def test_keeps_lead_hold_and_tail_of_still_stretches(self):
        stills = [(0.0, 3.0), (5.0, 9.0), (12.0, 15.0)]
        keep = trim_idle.keep_ranges(15.0, stills, hold=1.2, lead=0.5, tail=1.5)
        self.assertEqual([(round(a, 3), round(b, 3)) for a, b in keep], [(2.5, 6.2), (9.0, 13.5)])

    def test_keeps_a_still_shorter_than_hold_whole(self):
        keep = trim_idle.keep_ranges(10.0, [(5.0, 6.22)], hold=1.2, lead=0.5, tail=1.5)
        self.assertEqual(keep, [(0.0, 10.0)])


class StillsTest(unittest.TestCase):
    def test_merges_one_frame_flicker_and_closes_an_open_still_at_the_end(self):
        log = (
            "freeze_start: 1.0\nfreeze_end: 3.0\n"
            "freeze_start: 3.1\nfreeze_end: 5.0\n"
            "freeze_start: 8.0\n"
        )
        result = CompletedProcess([], 0, stdout="", stderr=log)
        with patch.object(trim_idle.subprocess, "run", return_value=result):
            self.assertEqual(trim_idle.stills("raw.mp4", 10.0), [(1.0, 5.0), (8.0, 10.0)])


if __name__ == "__main__":
    unittest.main()
