import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "claude/skills/kintai/scripts/gh_activity.py"
SPEC = importlib.util.spec_from_file_location("gh_activity", SCRIPT)
gh_activity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gh_activity)


def pr(repo, number, title="t"):
    return {"repository": {"nameWithOwner": repo}, "number": number, "title": title}


class RowsTest(unittest.TestCase):
    def test_buckets_opened_prs_by_jst_day_and_drops_own_repos_and_other_days(self):
        authored = [
            dict(pr("org/app", 1), createdAt="2026-11-04T15:30:00Z"),
            dict(pr("org/app", 2), createdAt="2026-10-31T14:59:00Z"),
            dict(pr("me/dotfiles", 3), createdAt="2026-11-05T01:00:00Z"),
        ]
        rows = gh_activity.rows("me", "2026-11-01", "2026-11-30", authored, [])
        self.assertEqual(rows, [("2026-11-05", "PR", "org/app#1", "t")])

    def test_keeps_one_review_row_per_pr_and_day_within_the_range(self):
        other = dict(pr("org/app", 9), author={"login": "alice"})
        activity = [
            ("2026-11-10T01:00:00Z", other),
            ("2026-11-10T08:00:00Z", other),
            ("2026-12-01T00:00:00Z", other),
        ]
        rows = gh_activity.rows("me", "2026-11-01", "2026-11-30", [], activity)
        self.assertEqual(rows, [("2026-11-10", "REVIEW", "org/app#9 (alice)", "t")])


if __name__ == "__main__":
    unittest.main()
