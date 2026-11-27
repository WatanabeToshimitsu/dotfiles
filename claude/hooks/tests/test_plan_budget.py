import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "plan-budget.py"
SETTINGS = Path(__file__).resolve().parents[2] / "settings.json"

# Asia/Tokyo: the 5-hour window resets Fri 11/27 13:00, the weekly window Thu 12/03 15:00.
H5_RESET = 1795752000
D7_RESET = 1796277600
NOW = H5_RESET - 41 * 60  # Fri 11/27 12:19
MON_TO_FRI_9_TO_18 = {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "18:00"}


def sample(ts, session, cost, h5=43, d7=30):
    return {"ts": ts, "session": session, "cost": cost,
            "h5": h5, "h5_reset": H5_RESET, "d7": d7, "d7_reset": D7_RESET}


class PlanBudgetTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.env = {**os.environ, "TZ": "Asia/Tokyo", "CLAUDE_PLAN_BUDGET_DIR": str(self.dir),
                    "CLAUDE_PLAN_BUDGET_NOW": str(NOW)}

    def write_samples(self, *samples) -> None:
        (self.dir / "samples.jsonl").write_text("".join(json.dumps(s) + "\n" for s in samples))

    def write_schedule(self, schedule) -> None:
        (self.dir / "schedule.json").write_text(json.dumps(schedule))

    def run_script(self, *args, stdin="", now=NOW):
        env = {**self.env, "CLAUDE_PLAN_BUDGET_NOW": str(now)}
        return subprocess.run(["python3", str(SCRIPT), *args], input=stdin, env=env,
                              capture_output=True, text=True, timeout=10)

    def logged_samples(self):
        path = self.dir / "samples.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_weekly_pace_counts_only_scheduled_work_hours(self):
        self.write_schedule(MON_TO_FRI_9_TO_18)
        self.write_samples(sample(NOW - 60, "a", 1.0))
        out = self.run_script("check").stdout
        self.assertIn("weekly: 30% used, pace allows 14.0% (6.3 of 45.0 work hours)", out)
        self.assertIn("5h: 43% used, pace allows 86.3%", out)

    def test_5h_allowance_has_a_ten_percent_floor_at_window_start(self):
        self.write_samples(sample(NOW - 60, "a", 1.0, h5=2))
        out = self.run_script("check", now=H5_RESET - 5 * 3600 + 6 * 60).stdout
        self.assertIn("5h: 2% used, pace allows 10.0%", out)

    def test_estimate_is_converted_with_logged_costs_and_asks_when_over_pace(self):
        self.write_schedule(MON_TO_FRI_9_TO_18)
        weekly_start = D7_RESET - 7 * 86400
        self.write_samples(
            sample(weekly_start - 3600, "a", 5.0, h5=0, d7=0),
            sample(H5_RESET - 5 * 3600 - 1800, "a", 15.0, h5=0, d7=10),
            sample(NOW - 7200, "b", 1.0),
            sample(NOW - 60, "a", 25.0),
            sample(NOW - 60, "b", 11.0),
        )
        out = self.run_script("check", "--usd", "2").stdout
        self.assertIn("$1 API-equivalent = 2.15% of 5h, 1.00% of weekly", out)
        self.assertIn("weekly +2.0% -> 32.0%", out)
        self.assertIn("1.8%/work-hour for weekly (so far 4.7%/work-hour)", out)
        self.assertIn("verdict: ask (over pace: weekly)", out)

    def test_estimate_within_both_allowances_is_ok(self):
        self.write_samples(sample(NOW - 7200, "a", 0.0, d7=0), sample(NOW - 60, "a", 10.0, h5=43, d7=5))
        out = self.run_script("check", "--usd", "2").stdout
        self.assertIn("verdict: ok", out)

    def test_record_logs_rate_limits_and_throttles_repeats(self):
        def statusline(session, cost, h5):
            return json.dumps({"session_id": session, "cost": {"total_cost_usd": cost}, "rate_limits": {
                "five_hour": {"used_percentage": h5, "resets_at": H5_RESET},
                "seven_day": {"used_percentage": 30, "resets_at": D7_RESET}}})

        self.run_script("record", stdin=statusline("a", 1.0, 43))
        self.run_script("record", stdin=statusline("a", 1.1, 43), now=NOW + 30)
        self.run_script("record", stdin=statusline("a", 1.2, 44), now=NOW + 40)
        self.run_script("record", stdin=statusline("b", 0.1, 44), now=NOW + 50)
        self.assertEqual(
            [(s["session"], s["cost"], s["h5"], s["d7_reset"]) for s in self.logged_samples()],
            [("a", 1.0, 43, D7_RESET), ("a", 1.2, 44, D7_RESET), ("b", 0.1, 44, D7_RESET)])

    def test_record_ignores_input_it_cannot_read(self):
        result = self.run_script("record", stdin="not json")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.logged_samples(), [])

    def test_status_line_logs_a_sample_and_reaches_powerline_with_or_without_the_script(self):
        command = json.loads(SETTINGS.read_text())["statusLine"]["command"]
        stdin = json.dumps({"session_id": "a", "cost": {"total_cost_usd": 1.0}})
        for installed in (True, False):
            with self.subTest(installed=installed):
                home = Path(tempfile.mkdtemp())
                (home / "bin").mkdir()
                (home / "bin" / "npx").write_text("#!/bin/sh\ncat\n")
                (home / "bin" / "npx").chmod(0o755)
                if installed:
                    (home / ".claude" / "hooks").mkdir(parents=True)
                    (home / ".claude" / "hooks" / "plan-budget.py").symlink_to(SCRIPT)
                env = {**self.env, "HOME": str(home), "PATH": f"{home / 'bin'}:{os.environ['PATH']}",
                       "CLAUDE_PLAN_BUDGET_DIR": str(home / "state")}
                result = subprocess.run(["sh", "-c", command], input=stdin, capture_output=True,
                                        text=True, env=env, timeout=10)
                self.assertEqual(result.stdout, stdin)
                self.assertEqual((home / "state" / "samples.jsonl").exists(), installed)


if __name__ == "__main__":
    unittest.main()
