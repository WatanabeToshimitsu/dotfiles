import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / ".shell-utils/memgate"
LOADER = importlib.machinery.SourceFileLoader("memgate", str(SCRIPT))
memgate = importlib.util.module_from_spec(importlib.util.spec_from_loader("memgate", LOADER))
LOADER.exec_module(memgate)
GIB = 1 << 30
ME = os.getpid()


class Exec(Exception):
    pass


class MemgateTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.table = {ME: (1, "s-me", "python")}
        self.sizes = {}
        self.free = 0
        self.swapins = 0
        self.patch(memgate, "LEDGER_DIR", self.root / "run")
        self.patch(memgate, "PEAKS", self.root / "state/peaks.json")
        self.patch(memgate, "INTERVAL", 0)
        self.patch(memgate, "ENFORCE", True)
        self.patch(memgate, "SWAP_ALLOWANCE", 0)
        self.patch(memgate, "processes", lambda: dict(self.table))
        self.patch(memgate, "footprint", lambda pid: self.sizes.get(pid, 0))
        self.patch(memgate, "memory", lambda: (self.free, self.swapins))
        self.patch(memgate.subprocess, "Popen", self.spawn)
        (self.root / "run").mkdir(mode=0o700)
        memgate.save(self.root / "run/swapins.json", [[time.time() - 60, 0]])

    def patch(self, target, name, value):
        patcher = patch.object(target, name, value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def spawn(self, argv, **_):
        pid = 900 + len([p for p in self.table if p >= 900])
        self.table[pid] = (ME, f"s-{pid}", "python")
        return SimpleNamespace(pid=pid)

    def ledger(self):
        return json.loads((self.root / "run/ledger.json").read_text())

    def events(self, directory="state"):
        path = self.root / directory / "decisions.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def admit(self, key, wait=0, **options):
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            try:
                memgate.admit(key, wait, **options)
            except SystemExit as error:
                return error.code, stderr.getvalue()
        return 0, stderr.getvalue()

    def test_estimate_is_the_measured_peak_or_the_larger_of_floor_and_the_largest_peak_in_the_repository(self):
        a, b = json.dumps(["/r/.git", "", ["a"]]), json.dumps(["/r/.git", "", ["b"]])
        elsewhere = json.dumps(["/other/.git", "", ["c"]])
        self.assertEqual(memgate.estimate({}, a), 2 * GIB)
        self.assertEqual(memgate.estimate({b: 3 * GIB}, a), 3 * GIB)
        self.assertEqual(memgate.estimate({b: GIB}, a), 2 * GIB)
        self.assertEqual(memgate.estimate({a: GIB // 2, b: 3 * GIB}, a), GIB // 2)
        self.assertEqual(memgate.estimate({elsewhere: 5 * GIB}, a), 2 * GIB)
        self.assertEqual(memgate.estimate({elsewhere: 5 * GIB, "agent-browser": 4 * GIB}, "web"), 2 * GIB)

    def test_swapin_rate_needs_a_baseline_old_enough_and_ignores_a_counter_reset(self):
        now = 1000.0
        self.assertEqual(memgate.swapin_rate([], now, 50), (None, None))
        self.assertEqual(memgate.swapin_rate([[now - 1, 0]], now, 50), (None, None))
        self.assertEqual(memgate.swapin_rate([[now - 10, 100], [now - 5, 150]], now, 600), (50.0, 10.0))
        self.assertEqual(memgate.swapin_rate([[now - 10, 900]], now, 100), (0.0, 10.0))

    def test_samples_are_pruned_to_the_window(self):
        now = time.time()
        memgate.save(self.root / "run/swapins.json", [[now - 500, 0], [now - 100, 1000], [now + 50, 9]])
        self.assertEqual(memgate.add_sample(now, 3000), (20.0, 100.0))
        self.assertEqual(memgate.load(self.root / "run/swapins.json", []), [[now - 100, 1000], [now, 3000]])

    def test_swap_allowance_applies_only_while_swapin_is_slow(self):
        self.patch(memgate, "SWAP_ALLOWANCE", 4 * GIB)
        self.free = 2.5 * GIB
        self.swapins = 60 * memgate.SWAPIN_LIMIT // 2
        self.assertEqual(self.admit("a")[0], 0)
        self.assertEqual(self.events()[-1]["allowance"], 4 * GIB)
        (self.root / "run/ledger.json").unlink()
        self.swapins += 60 * memgate.SWAPIN_LIMIT * 4
        code, stderr = self.admit("b")
        self.assertEqual(code, 75)
        self.assertEqual(self.events()[-1]["allowance"], 0)
        self.assertEqual(self.events()[-1]["verdict"], "timeout")

    def test_first_launch_without_a_recent_sample_waits_once_for_a_baseline(self):
        (self.root / "run/swapins.json").unlink()
        self.patch(memgate, "INTERVAL", 2)
        clock = [1000.0]
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds

        self.patch(memgate, "time", SimpleNamespace(time=lambda: clock[0], monotonic=lambda: clock[0], sleep=sleep))
        self.free = 4 * GIB
        self.swapins = 2 * GIB
        self.assertEqual(self.admit("a")[0], 0)
        self.assertEqual(sleeps, [2])
        self.assertEqual(self.events()[-1]["rate_span"], 2)

    def test_second_launch_cannot_use_headroom_reserved_by_the_first(self):
        self.free = 4.5 * GIB
        self.assertEqual(self.admit("a")[0], 0)
        self.assertEqual(len(self.ledger()), 1)
        code, stderr = self.admit("b")
        self.assertEqual(code, 75)
        self.assertIn("needs 2.0 GiB", stderr)
        self.sizes[ME] = 1.5 * GIB
        self.assertEqual(self.admit("b")[0], 0)
        self.assertEqual([entry["key"] for entry in self.ledger()], ["a", "b"])

    def test_reservation_ends_only_when_watcher_and_target_are_both_gone(self):
        self.free = 3.5 * GIB
        self.table[500] = (1, "s-500", "node")
        stale = {"key": "old", "estimate": 2 * GIB, "pidfile": None}
        entries = [
            {**stale, "target": [500, "s-500"], "watcher": [501, "s-501"]},
            {**stale, "target": [502, "s-502"], "watcher": [500, "reused"]},
        ]
        memgate.save(self.root / "run/ledger.json", entries)
        self.assertEqual(self.admit("a")[0], 75)
        del self.table[500]
        self.assertEqual(self.admit("a")[0], 0)
        self.assertEqual([entry["key"] for entry in self.ledger()], ["a"])

    def test_timeout_lists_reservations_and_largest_processes(self):
        self.free = GIB
        self.table[700] = (1, "s-700", "tsserver")
        self.sizes[700] = 6 * GIB
        memgate.save(self.root / "run/ledger.json", [
            {"key": "dev", "estimate": GIB, "target": [700, "s-700"], "watcher": [0, None], "pidfile": None}])
        code, stderr = self.admit("a", wait=0.05)
        self.assertEqual(code, 75)
        self.assertEqual(stderr.count("waiting up to"), 1)
        self.assertIn("dev", stderr)
        self.assertIn("6.0 GiB pid 700 tsserver", stderr)

    def test_busy_ledger_lock_fails_at_the_deadline_only_when_enforcing(self):
        self.patch(memgate, "LOCK_WAIT", 0)
        with open(self.root / "run/lock", "a") as lock:
            memgate.fcntl.flock(lock, memgate.fcntl.LOCK_EX)
            for enforce, expected in ((True, 75), (False, 0)):
                with self.subTest(enforce=enforce):
                    memgate.ENFORCE = enforce
                    pid = os.fork()
                    if pid == 0:
                        os._exit(self.admit("a")[0])
                    self.assertEqual(os.waitstatus_to_exitcode(os.waitpid(pid, 0)[1]), expected)
        self.assertEqual([(event["event"], event["mode"]) for event in self.events()],
                         [("busy", "enforce"), ("busy", "observe")])
        self.assertTrue(all("id" in event for event in self.events()))

    def test_observe_mode_launches_a_short_command_silently_and_records_the_decision(self):
        self.patch(memgate, "ENFORCE", False)
        self.free = 2.5 * GIB
        self.swapins = 600
        self.assertEqual(self.admit("a", wait=900), (0, ""))
        entry = self.ledger()[0]
        self.assertEqual(entry["probe"], {"need": 2 * GIB, "wait": 900})
        event = self.events()[0]
        self.assertEqual(event["id"], entry["id"])
        self.assertEqual({key: event[key] for key in (
            "event", "mode", "key", "need", "free", "held", "margin", "allowance", "verdict", "short0", "swapins")},
            {"event": "decision", "mode": "observe", "key": "a", "need": 2 * GIB, "free": 2.5 * GIB, "held": 0,
             "margin": GIB, "allowance": 0, "verdict": "short", "short0": True, "swapins": 600})
        self.assertAlmostEqual(event["rate"], 10.0, delta=0.1)
        self.free = 8 * GIB
        self.assertEqual(self.admit("b")[0], 0)
        self.assertNotIn("probe", self.ledger()[1])

    def test_enforce_mode_records_how_long_a_launch_waited(self):
        self.free = GIB
        waits = iter([GIB, 4 * GIB])
        self.patch(memgate, "memory", lambda: (next(waits), 0))
        self.assertEqual(self.admit("a", wait=60)[0], 0)
        event = self.events()[-1]
        self.assertEqual((event["mode"], event["verdict"], event["short0"]), ("enforce", "admit", False))
        self.assertGreaterEqual(event["waited"], 0)

    def test_decisions_fall_back_to_the_ledger_directory_and_never_fail_the_launch(self):
        (self.root / "state").write_text("")
        self.free = 8 * GIB
        self.assertEqual(self.admit("a")[0], 0)
        self.assertEqual(self.events("run")[0]["verdict"], "admit")
        (self.root / "run/decisions.jsonl").unlink()
        (self.root / "run/decisions.jsonl").mkdir()
        self.assertEqual(self.admit("b")[0], 0)

    def test_unwritable_ledger_still_checks_memory(self):
        for name in ("swapins.json", "lock"):
            (self.root / "run" / name).unlink(missing_ok=True)
        (self.root / "run").rmdir()
        (self.root / "run").write_text("")
        self.free = GIB
        code, stderr = self.admit("a")
        self.assertEqual(code, 75)
        self.assertIn("reservations disabled", stderr)
        self.free = 4 * GIB
        self.assertEqual(self.admit("a")[0], 0)
        self.assertEqual(sorted(self.table), [ME])
        self.assertEqual(self.events()[-1]["rate"], None)

    def test_live_browser_session_is_not_gated(self):
        self.free = 4 * GIB
        self.table[300] = (1, "s-300", "agent-browser-d")
        self.assertEqual(self.admit("b", ready=lambda table: 300 in table)[0], 0)
        self.assertFalse((self.root / "run/ledger.json").exists())

    def test_watcher_records_the_peak_follows_orphans_and_releases(self):
        timeline = [
            ({100: (1, "s-100", "npm"), 101: (100, "s-101", "node"), ME: (100, "s-me", "python")},
             {100: GIB, 101: GIB, ME: 10 * GIB}),
            ({101: (1, "s-101", "node"), ME: (1, "s-me", "python")}, {101: 3 * GIB}),
            ({101: (1, "s-101", "node"), ME: (1, "s-me", "python")}, {101: GIB}),
            ({ME: (1, "s-me", "python")}, {}),
        ]
        for preset, expected in ((None, 3 * GIB), (4 * GIB, 4 * GIB)):
            with self.subTest(preset=preset):
                if preset:
                    memgate.save(self.root / "state/peaks.json", {"k": preset})
                entry = {"key": "k", "estimate": 2 * GIB, "target": [100, "s-100"],
                         "watcher": [ME, "s-me"], "pidfile": None, "id": [100, "s-100"]}
                memgate.save(self.root / "run/ledger.json", [entry])
                steps = iter(timeline)
                during = []

                def processes():
                    during.append(memgate.load(self.root / "state/peaks.json", {}).get("k"))
                    table, self.sizes = next(steps)
                    return dict(table)

                with patch.object(memgate, "processes", processes):
                    memgate.watch(entry)
                self.assertEqual(set(during), {preset})
                self.assertEqual(json.loads((self.root / "state/peaks.json").read_text())["k"], expected)
                self.assertEqual(self.ledger(), [])
                self.assertEqual(self.events()[-1], {**self.events()[-1], "event": "end", "id": [100, "s-100"],
                                                     "key": "k", "peak": 3 * GIB})

    def test_short_launch_is_sampled_until_it_would_have_fit(self):
        self.patch(memgate, "SAMPLE_EVERY", 0)
        other = {"key": "o", "estimate": 2 * GIB, "target": [300, "s-300"], "watcher": [301, "s-301"],
                 "pidfile": None, "id": [300, "s-300"]}
        entry = {"key": "k", "estimate": 2 * GIB, "target": [100, "s-100"], "watcher": [ME, "s-me"],
                 "pidfile": None, "id": [100, "s-100"], "probe": {"need": 2 * GIB, "wait": 900}}
        memgate.save(self.root / "run/ledger.json", [other, entry])
        running = {100: (1, "s-100", "node"), 300: (1, "s-300", "node"), 301: (1, "s-301", "python"),
                   ME: (1, "s-me", "python")}
        timeline = [(GIB, {100: GIB}), (2 * GIB, {100: GIB}), (4 * GIB, {100: GIB}), (4 * GIB, {100: GIB})]
        steps = iter(timeline)

        def processes():
            try:
                self.free, self.sizes = next(steps)
            except StopIteration:
                return {ME: (1, "s-me", "python")}
            return dict(running)

        with patch.object(memgate, "processes", processes):
            memgate.watch(entry)
        samples = [event for event in self.events() if event["event"] == "sample"]
        self.assertEqual([(s["free"], s["own"], s["held"], s["met"]) for s in samples],
                         [(GIB, GIB, 2 * GIB, False), (2 * GIB, GIB, 2 * GIB, False), (4 * GIB, GIB, 2 * GIB, True)])
        self.assertEqual({tuple(s["id"]) for s in samples}, {(100, "s-100")})
        self.assertTrue(all("rate" in s and "swapins" in s and "elapsed" in s for s in samples))
        self.assertEqual(self.events()[-1]["event"], "end")

    def test_short_launch_sampling_stops_at_the_wait_limit(self):
        self.patch(memgate, "SAMPLE_EVERY", 0)
        entry = {"key": "k", "estimate": 2 * GIB, "target": [100, "s-100"], "watcher": [ME, "s-me"],
                 "pidfile": None, "id": [100, "s-100"], "probe": {"need": 2 * GIB, "wait": 0}}
        memgate.save(self.root / "run/ledger.json", [entry])
        steps = iter([{100: (1, "s-100", "node"), ME: (1, "s-me", "python")}] * 3 + [{ME: (1, "s-me", "python")}])
        memgate.save(self.root / "run/swapins.json", [])
        with patch.object(memgate, "processes", lambda: dict(next(steps))):
            memgate.watch(entry)
        self.assertEqual([event["event"] for event in self.events()], ["sample", "end"])
        self.assertEqual(len(memgate.load(self.root / "run/swapins.json", [])), 3)

    def test_watcher_follows_children_that_orphans_start_later(self):
        timeline = [
            ({100: (1, "s-100", "sh"), 101: (100, "s-101", "node")}, {}),
            ({101: (1, "s-101", "node"), 102: (101, "s-102", "node")}, {101: GIB, 102: 2 * GIB}),
            ({}, {}),
        ]
        entry = {"key": "k", "estimate": GIB, "target": [100, "s-100"], "watcher": [ME, "s-me"], "pidfile": None,
                 "id": [100, "s-100"]}
        memgate.save(self.root / "run/ledger.json", [entry])
        steps = iter(timeline)

        def processes():
            table, self.sizes = next(steps)
            return dict(table)

        with patch.object(memgate, "processes", processes):
            memgate.watch(entry)
        self.assertEqual(json.loads((self.root / "state/peaks.json").read_text())["k"], 3 * GIB)

    def test_browser_watcher_follows_the_daemon(self):
        pidfile = self.root / "default.pid"
        entry = {"key": "agent-browser", "estimate": 2 * GIB, "target": [100, "s-100"],
                 "watcher": [ME, "s-me"], "pidfile": str(pidfile), "id": [100, "s-100"]}
        memgate.save(self.root / "run/ledger.json", [entry])
        daemon = {200: (1, "s-200", "agent-browser-d"), 201: (200, "s-201", "Google Chrome")}
        timeline = [
            ({100: (1, "s-100", "agent-browser"), ME: (100, "s-me", "python")}, {100: GIB}),
            ({**daemon, ME: (1, "s-me", "python")}, {200: GIB, 201: 2 * GIB}),
            ({**daemon, ME: (1, "s-me", "python")}, {200: GIB, 201: 2 * GIB}),
            ({ME: (1, "s-me", "python")}, {}),
        ]
        steps = iter(timeline)
        seen = []

        def processes():
            table, self.sizes = next(steps)
            if 200 in table:
                pidfile.write_text("200")
                seen.append([e["target"] for e in self.ledger()])
            return dict(table)

        with patch.object(memgate, "processes", processes):
            memgate.watch(entry)
        self.assertEqual(seen[-1], [[200, "s-200"]])
        self.assertEqual(json.loads((self.root / "state/peaks.json").read_text())["agent-browser"], 3 * GIB)
        self.assertEqual(self.ledger(), [])

    def test_browser_gates_only_commands_that_may_start_a_session(self):
        home = self.root / "home"
        (home / ".agent-browser/namespaces/ns/run").mkdir(parents=True)
        (home / ".agent-browser/default.pid").write_text("300")
        self.table[300] = (1, "s-300", "agent-browser-d")
        calls = []

        def admit(key, wait, ready=None, pidfile=None):
            self.assertEqual(wait, 100)
            calls.append(pidfile)
            if ready(memgate.processes()):
                calls[-1] = "ready"

        def execv(path, argv):
            raise Exec(argv[1:])

        self.patch(memgate, "admit", admit)
        self.patch(memgate.os, "execv", execv)
        self.patch(memgate, "real_browser", lambda: "/bin/agent-browser")
        self.patch(memgate.Path, "home", lambda: home)
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        cases = [
            (["open", "https://example.com"], None),
            (["--session", "foo", "--help"], None),
            (["close"], None),
            (["--session", "s3", "--json", "session", "list"], None),
            (["--session", "s3", "--headed", "close"], None),
            (["--session", "s2", "fill", "@e1", "-h"], str(home / ".agent-browser/s2.pid")),
            (["--session", "close", "open", "https://example.com"],
             str(home / ".agent-browser/close.pid")),
            (["--namespace=ns", "--session", "s", "open", "about:blank"],
             str(home / ".agent-browser/namespaces/ns/run/s.pid")),
        ]
        for args, expected in cases:
            with self.subTest(args=args):
                calls.clear()
                with self.assertRaises(Exec) as ran:
                    memgate.browser(args)
                self.assertEqual(ran.exception.args[0], args)
                self.assertEqual(calls, [expected] if expected else [])

    def test_real_browser_skips_the_shim(self):
        fake = self.root / "bin/agent-browser"
        fake.parent.mkdir()
        fake.write_text("#!/bin/sh\n")
        fake.chmod(0o755)
        with patch.dict(os.environ, {"PATH": f"{SCRIPT.parent}{os.pathsep}{fake.parent}"}):
            self.assertEqual(memgate.real_browser(), str(fake))

    def test_run_admits_the_command_and_execs_it(self):
        calls = []

        def execvp(file, argv):
            raise Exec(argv)

        self.patch(memgate, "admit", lambda key, wait: calls.append((key, wait)))
        self.patch(memgate.os, "execvp", execvp)
        self.patch(memgate, "repository", lambda: ("/r/.git", "web/"))
        for args, key, wait in (
            (["--key", "web", "--wait", "5", "--", "npm", "run", "dev"], "web", 5.0),
            (["--", "npm", "run", "dev"], json.dumps(["/r/.git", "web/", ["npm", "run", "dev"]]), 900.0),
        ):
            with self.subTest(args=args):
                calls.clear()
                with self.assertRaises(Exec) as ran:
                    memgate.run(args)
                self.assertEqual(ran.exception.args[0], ["npm", "run", "dev"])
                self.assertEqual(calls, [(key, wait)])
        for args in ([], ["npm"], ["--key", "web"], ["--"], ["--wait", "soon", "--", "npm"]):
            with self.subTest(args=args), redirect_stderr(io.StringIO()):
                self.assertRaises(SystemExit, memgate.run, args)

    def test_run_reports_a_missing_command_without_a_traceback(self):
        self.patch(memgate, "admit", lambda key, wait: None)
        self.patch(memgate, "repository", lambda: ("/r/.git", ""))
        stderr = io.StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as ran:
            memgate.run(["--", "memgate-test-missing-command"])
        self.assertEqual(ran.exception.code, 127)
        self.assertEqual(stderr.getvalue().count("\n"), 1)


class PlatformTests(unittest.TestCase):
    def test_probes_read_this_process_and_system_memory(self):
        table = memgate.processes()
        self.assertEqual(table[ME][0], os.getppid())
        self.assertGreater(memgate.footprint(ME), 0)
        free, swapins = memgate.memory()
        self.assertGreater(free, 0)
        self.assertGreaterEqual(swapins, 0)

    def test_repository_is_shared_by_worktrees_and_keeps_the_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
                   "-c", "core.hooksPath=/dev/null"]
            subprocess.run([*git, "init", "-q", str(root / "main")], check=True)
            subprocess.run([*git, "-C", str(root / "main"), "commit", "-q", "--allow-empty", "-m", "i"], check=True)
            subprocess.run([*git, "-C", str(root / "main"), "worktree", "add", "-q", str(root / "wt")], check=True)
            (root / "wt/pkg").mkdir()
            seen = []
            for cwd in (root / "main", root / "wt", root / "wt/pkg", root):
                with self.subTest(cwd=cwd):
                    previous = os.getcwd()
                    os.chdir(cwd)
                    try:
                        seen.append(memgate.repository())
                    finally:
                        os.chdir(previous)
        common = str(root / "main/.git")
        self.assertEqual(seen, [(common, ""), (common, ""), (common, "pkg/"), (str(root), "")])


if __name__ == "__main__":
    unittest.main()
