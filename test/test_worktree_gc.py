import importlib.machinery
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / ".shell-utils" / "worktree-gc"
LOADER = importlib.machinery.SourceFileLoader("worktree_gc", str(SCRIPT))
SPEC = importlib.util.spec_from_loader("worktree_gc", LOADER)
gc = importlib.util.module_from_spec(SPEC)
sys.modules["worktree_gc"] = gc
LOADER.exec_module(gc)

DAY = 86400


def git(cwd, *args):
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


class FakeTools:
    def __init__(self):
        self.ghq = []
        self.pr_heads = {}
        self.cwd_paths = []
        self.lsof_ok = True
        self.lsof_calls = 0
        self.on_lsof = None

    def repos(self):
        return [str(repo) for repo in self.ghq]

    def merged_pr_heads(self, repo, branch):
        return self.pr_heads.get(branch, set())

    def cwds(self):
        self.lsof_calls += 1
        if self.on_lsof:
            self.on_lsof(self.lsof_calls)
        return [str(path) for path in self.cwd_paths] if self.lsof_ok else None


class WorktreeGcTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        config = self.root / "gitconfig"
        config.write_text(
            "[user]\n\tname = Test\n\temail = test@example.com\n"
            "[init]\n\tdefaultBranch = main\n"
            "[commit]\n\tgpgsign = false\n"
        )
        patcher = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tools = FakeTools()
        self.main = self.root / "repo"
        remote = self.root / "repo.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        subprocess.run(["git", "init", "-q", str(self.main)], check=True)
        (self.main / ".gitignore").write_text(".claude/\n")
        git(self.main, "add", ".")
        git(self.main, "commit", "-qm", "init")
        git(self.main, "remote", "add", "origin", str(remote))
        git(self.main, "push", "-q", "origin", "main")
        git(self.main, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")

    def worktree(self, name="feat", merge=True, days=10, path=None):
        tree = path or self.root / "wt" / name
        git(self.main, "worktree", "add", "-q", "-b", name, str(tree), "main")
        (tree / f"{name}.txt").write_text("change\n")
        git(tree, "add", ".")
        git(tree, "commit", "-qm", name)
        if merge:
            git(self.main, "merge", "-q", "--no-ff", name, "-m", f"Merge {name}")
            git(self.main, "push", "-q", "origin", "main")
        self.age(tree, days)
        return tree

    def age(self, tree, days):
        admin = Path(git(tree, "rev-parse", "--absolute-git-dir"))
        stamp = time.time() - days * DAY
        for path in (tree, admin / "HEAD", admin / "index", admin / "logs" / "HEAD"):
            os.utime(path, (stamp, stamp))

    def run_gc(self, apply=True):
        out = io.StringIO()
        gc.run([str(self.main)], apply, 3, self.tools, out=out)
        return out.getvalue()

    def assert_kept(self, tree, reason):
        output = self.run_gc()
        self.assertIn(f"keep     {reason}", output)
        self.assertTrue(tree.exists())

    def test_removes_a_worktree_merged_with_a_merge_commit_and_keeps_its_branch(self):
        tree = self.worktree()

        self.assertIn("removed", self.run_gc())

        self.assertFalse(tree.exists())
        self.assertTrue(git(self.main, "branch", "--list", "feat"))

    def test_removes_a_squash_merged_worktree_whose_head_matches_the_pr(self):
        tree = self.worktree(merge=False)
        self.tools.pr_heads["feat"] = {git(tree, "rev-parse", "HEAD")}

        self.run_gc()

        self.assertFalse(tree.exists())

    def test_keeps_a_worktree_that_moved_after_its_pr_merged(self):
        tree = self.worktree(merge=False)
        self.tools.pr_heads["feat"] = {"0" * 40}

        self.assert_kept(tree, "not-merged")

    def test_keeps_uncommitted_and_untracked_changes(self):
        git(self.main, "config", "status.showUntrackedFiles", "no")
        tracked = self.worktree("tracked")
        (tracked / "tracked.txt").write_text("edited\n")
        untracked = self.worktree("untracked")
        (untracked / "notes").mkdir()
        (untracked / "notes" / "draft.md").write_text("draft\n")
        for tree in (tracked, untracked):
            self.age(tree, 10)

        output = self.run_gc()

        self.assertEqual(output.count("keep     dirty"), 2)
        self.assertTrue(tracked.exists() and untracked.exists())

    def test_keeps_a_locked_worktree(self):
        tree = self.worktree()
        git(self.main, "worktree", "lock", str(tree))

        self.assert_kept(tree, "locked")

    def test_keeps_a_recently_active_worktree(self):
        tree = self.worktree(days=1)

        self.assert_kept(tree, "recent")

    def test_keeps_a_worktree_a_process_is_working_in(self):
        tree = self.worktree()
        self.tools.cwd_paths = [tree / "src"]

        self.assert_kept(tree, "in-use")

    def test_keeps_everything_when_lsof_fails(self):
        tree = self.worktree()
        self.tools.lsof_ok = False

        self.assert_kept(tree, "cwd-check-failed")

    def test_keeps_a_detached_worktree(self):
        tree = self.root / "wt" / "detached"
        git(self.main, "worktree", "add", "-q", "--detach", str(tree), "main")
        self.age(tree, 10)

        self.assert_kept(tree, "detached")

    def test_keeps_a_worktree_that_contains_another_worktree(self):
        parent = self.worktree("parent")
        child = parent / ".claude" / "worktrees" / "child"
        git(self.main, "worktree", "add", "-q", "-b", "child", str(child), "main")
        (child / "wip.txt").write_text("uncommitted\n")
        self.age(parent, 10)

        self.assert_kept(parent, "contains-worktree")
        self.assertTrue((child / "wip.txt").exists())

    def test_reports_each_worktree_once_when_linked_worktrees_are_listed_as_repositories(self):
        tree = self.worktree(days=1)
        out = io.StringIO()

        gc.run([str(self.main), str(tree)], True, 3, self.tools, out=out)

        self.assertEqual(out.getvalue().count(str(tree)), 1)

    def test_keeps_a_worktree_holding_a_worktree_of_a_repository_not_being_scanned(self):
        other = self.root / "other"
        subprocess.run(["git", "init", "-q", str(other)], check=True)
        git(other, "commit", "-q", "--allow-empty", "-m", "init")
        parent = self.worktree("parent")
        child = parent / ".claude" / "worktrees" / "child"
        git(other, "worktree", "add", "-q", "-b", "child", str(child))
        (child / "wip.txt").write_text("uncommitted\n")
        self.age(parent, 10)
        self.tools.ghq = [self.main, other]

        self.assert_kept(parent, "contains-worktree")
        self.assertTrue((child / "wip.txt").exists())

    def test_keeps_a_worktree_entered_after_the_first_check(self):
        tree = self.worktree()
        self.tools.on_lsof = lambda call: self.tools.cwd_paths.append(tree) if call == 2 else None

        self.assert_kept(tree, "in-use")

    def test_keeps_a_worktree_that_gains_a_nested_worktree_before_removal(self):
        parent = self.worktree("parent")
        child = parent / ".claude" / "worktrees" / "child"
        child.parent.mkdir(parents=True)
        self.age(parent, 10)

        def create_child(call):
            if call == 2:
                git(self.main, "worktree", "add", "-q", "-b", "child", str(child), "main")
                (child / "wip.txt").write_text("uncommitted\n")

        self.tools.ghq = [self.main]
        self.tools.on_lsof = create_child

        self.assert_kept(parent, "contains-worktree")
        self.assertTrue((child / "wip.txt").exists())

    def test_final_cwd_check_comes_after_the_merge_lookup(self):
        tree = self.worktree(merge=False)
        self.tools.pr_heads["feat"] = {git(tree, "rev-parse", "HEAD")}
        lookups = []

        def lookup(repo, branch):
            lookups.append(self.tools.lsof_calls)
            if len(lookups) == 1:
                self.tools.cwd_paths.append(tree)
            return self.tools.pr_heads[branch]

        self.tools.merged_pr_heads = lookup

        self.assert_kept(tree, "in-use")

    def test_keeps_a_worktree_that_moved_to_a_detached_commit_during_the_lookup(self):
        tree = self.worktree(merge=False)
        self.tools.pr_heads["feat"] = {git(tree, "rev-parse", "HEAD")}

        def detach_and_commit(repo, branch):
            git(tree, "checkout", "-q", "--detach")
            git(tree, "commit", "-q", "--allow-empty", "-m", "detached work")
            self.age(tree, 10)
            return self.tools.pr_heads[branch]

        self.tools.merged_pr_heads = detach_and_commit

        self.assert_kept(tree, "changed")

    def test_dry_run_removes_nothing(self):
        tree = self.worktree()

        output = self.run_gc(apply=False)

        self.assertIn("remove   merged", output)
        self.assertTrue(tree.exists())


if __name__ == "__main__":
    unittest.main()
