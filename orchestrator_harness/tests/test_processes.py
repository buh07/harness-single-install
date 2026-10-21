from __future__ import annotations

# pyright: reportImplicitRelativeImport=false
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from orchestrator_harness import processes
from orchestrator_harness.models import ProcessInfo, ProcessQuery, ProcessSnapshot
from orchestrator_harness.processes import (
    WINDOWS_CIM_SCRIPT,
    WINDOWS_CREATE_NO_WINDOW,
    windows_process_query,
    windows_process_snapshot,
)


class DetachedProcessTests(unittest.TestCase):
    def test_detached_session_option_preserves_native_windows_flags(self) -> None:
        argv = ["helper", "--argument"]
        env = {"EXAMPLE": "value"}
        for platform in ("posix", "nt"):
            with self.subTest(platform=platform):
                with (patch.object(processes.os, "name", platform),
                      patch.object(processes.sys, "prefix", sys.base_prefix),
                      patch.object(processes.subprocess, "Popen") as popen):
                    processes.spawn_detached(argv, env=env)
                options = popen.call_args.kwargs
                self.assertEqual(argv, popen.call_args.args[0])
                self.assertIs(env, options["env"])
                self.assertEqual(platform != "nt", options["start_new_session"])
                self.assertEqual(
                    WINDOWS_CREATE_NO_WINDOW if platform == "nt" else 0,
                    options["creationflags"],
                )
                self.assertIs(subprocess.DEVNULL, options["stdin"])
                self.assertIs(options["close_fds"], True)
        self.assertEqual({"EXAMPLE": "value"}, env)

    @unittest.skipUnless(os.name == "posix", "native POSIX process session")
    def test_detached_helper_has_own_session_and_exact_identity_cleanup(self) -> None:
        child = processes.spawn_detached(
            [sys.executable, "-B", "-c", "import time; time.sleep(60)"]
        )
        self.addCleanup(processes.reap_created_process, child)
        identity = processes.process_identity(child.pid)
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(child.pid, os.getpgid(child.pid))
        self.assertEqual(child.pid, os.getsid(child.pid))
        self.assertNotEqual(os.getpgrp(), os.getpgid(child.pid))
        self.assertNotEqual(os.getsid(0), os.getsid(child.pid))
        self.assertTrue(processes.identity_matches(**identity))
        self.assertFalse(processes.terminate_process(child.pid, None, force=True))
        self.assertTrue(processes.identity_matches(**identity))
        self.assertTrue(processes.terminate_process(**identity))
        child.wait(timeout=5)
        self.assertTrue(processes.identity_exit_proven(**identity))


class LinuxInventoryRaceTests(unittest.TestCase):
    """Complete PID absence is benign; unknown owned processes are not."""

    def _inventory(self, queries: dict[int, ProcessQuery]) -> ProcessSnapshot:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for pid in queries:
                (root / str(pid)).mkdir()
            with (
                patch.object(processes, "procfs_root", return_value=root),
                patch.object(processes, "_linux_boot_time", return_value=datetime(2026, 1, 1, tzinfo=timezone.utc)),
                patch.object(processes, "_linux_clock_ticks", return_value=100),
                patch.object(processes, "_linux_process_query", side_effect=lambda pid, **_: queries[pid]),
            ):
                return processes.linux_process_snapshot()

    def test_vanished_inventory_entry_does_not_invalidate_live_process(self) -> None:
        live = ProcessInfo(11, 1, "owned", "owned", datetime(2026, 1, 1, tzinfo=timezone.utc))
        snapshot = self._inventory({11: ProcessQuery(True, live), 22: ProcessQuery(True, None)})
        self.assertTrue(snapshot.complete)
        self.assertEqual((live,), snapshot.processes)
        self.assertEqual((), snapshot.errors)

    def test_all_entries_can_exit_during_inventory(self) -> None:
        snapshot = self._inventory({11: ProcessQuery(True, None), 22: ProcessQuery(True, None)})
        self.assertTrue(snapshot.complete)
        self.assertEqual((), snapshot.processes)
        self.assertEqual((), snapshot.errors)

    def test_permission_malformed_and_unknown_queries_remain_incomplete(self) -> None:
        for error in ("permission denied", "process stat record is incomplete", "identity unavailable"):
            with self.subTest(error=error):
                snapshot = self._inventory({11: ProcessQuery(False, None, (error,)), 22: ProcessQuery(True, None)})
                self.assertFalse(snapshot.complete)
                self.assertEqual((error,), snapshot.errors)

    def test_real_missing_process_query_is_complete_absence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(processes, "procfs_root", return_value=Path(temporary)):
                query = processes._linux_process_query(11, boot=datetime(2026, 1, 1, tzinfo=timezone.utc), ticks=100)
        self.assertTrue(query.complete)
        self.assertIsNone(query.process)
        self.assertEqual((), query.errors)

    def test_real_malformed_process_query_remains_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "11").mkdir()
            (root / "11" / "stat").write_text("invalid stat", encoding="ascii")
            with patch.object(processes, "procfs_root", return_value=root):
                query = processes._linux_process_query(11, boot=datetime(2026, 1, 1, tzinfo=timezone.utc), ticks=100)
        self.assertFalse(query.complete)
        self.assertIsNone(query.process)
        self.assertTrue(query.errors)

    def test_benign_inventory_absence_still_requires_exact_owned_exit(self) -> None:
        snapshot = self._inventory({22: ProcessQuery(True, None)})
        record = {
            "kind": "posix-process-group",
            "root": {"pid": 11, "creation_time": "2026-01-01T00:00:00Z"},
            "process_group_id": 11,
            "session_id": 11,
            "processes": [{"pid": 11, "creation_time": "2026-01-01T00:00:00Z"}],
        }
        for exited, matches, expected in ((True, False, True), (False, True, False), (False, False, False)):
            with self.subTest(exited=exited, matches=matches):
                with (
                    patch.object(processes, "process_snapshot", return_value=snapshot),
                    patch.object(processes, "identity_exit_proven", return_value=exited) as exit_proof,
                    patch.object(processes, "identity_matches", return_value=matches),
                    patch.object(processes, "terminate_process") as terminate,
                ):
                    self.assertEqual(expected, processes.process_boundary_is_gone(record))
                    exit_proof.assert_called_with(11, "2026-01-01T00:00:00Z")
                    terminate.assert_not_called()


class ProcessProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        executable = str(Path(temporary.name) / "tools" / "powershell.exe")
        discovery = patch.object(processes.shutil, "which", return_value=executable)
        discovery.start()
        self.addCleanup(discovery.stop)

    @unittest.skipUnless(os.name == "nt", "Windows venv redirector only")
    def test_detached_venv_python_keeps_identity_and_pid(self) -> None:
        if sys.prefix == sys.base_prefix:
            self.skipTest("requires a Windows virtual environment")
        env = dict(os.environ)
        env.pop("__PYVENV_LAUNCHER__", None)
        original_env = env.copy()
        code = (
            "import json, os, site, sys; "
            "print(json.dumps({'pid': os.getpid(), 'executable': sys.executable, "
            "'prefix': sys.prefix, 'site_packages': site.getsitepackages(), "
            "'path': sys.path}))"
        )
        child = processes.spawn_detached(
            [sys.executable, "-c", code], stdout=subprocess.PIPE, env=env
        )
        output, _ = child.communicate(timeout=10)
        self.assertEqual(0, child.returncode)
        observed = json.loads(output)
        self.assertEqual(child.pid, observed["pid"])
        self.assertEqual(Path(sys.executable), Path(observed["executable"]))
        self.assertEqual(Path(sys.prefix), Path(observed["prefix"]))
        venv_site = str(Path(sys.prefix) / "Lib" / "site-packages")
        self.assertIn(venv_site, observed["site_packages"])
        self.assertIn(venv_site, observed["path"])
        self.assertEqual(original_env, env)

    @unittest.skipUnless(os.name == "nt", "Windows venv redirector only")
    def test_detached_venv_python_passes_private_launcher_environment(self) -> None:
        if sys.prefix == sys.base_prefix:
            self.skipTest("requires a Windows virtual environment")
        env = {"EXAMPLE": "value"}
        with patch.object(processes.subprocess, "Popen") as popen:
            processes.spawn_detached([sys.executable, "-m", "example"], env=env)
        self.assertEqual(
            [sys._base_executable, "-m", "example"], popen.call_args.args[0]
        )
        self.assertEqual(
            {"EXAMPLE": "value", "__PYVENV_LAUNCHER__": sys.executable},
            popen.call_args.kwargs["env"],
        )
        self.assertEqual(
            WINDOWS_CREATE_NO_WINDOW, popen.call_args.kwargs["creationflags"]
        )
        self.assertEqual({"EXAMPLE": "value"}, env)

    @unittest.skipUnless(os.name == "nt", "Windows creation flags only")
    def test_detached_non_python_preserves_argv_env_and_no_window(self) -> None:
        argv = ["other-tool.exe", "--argument"]
        env = {"EXAMPLE": "value"}
        with patch.object(processes.subprocess, "Popen") as popen:
            processes.spawn_detached(argv, env=env)
        self.assertEqual(argv, popen.call_args.args[0])
        self.assertIs(env, popen.call_args.kwargs["env"])
        self.assertEqual(
            WINDOWS_CREATE_NO_WINDOW, popen.call_args.kwargs["creationflags"]
        )
        self.assertEqual({"EXAMPLE": "value"}, env)

    def test_snapshot_indexes_once_and_supports_direct_parent_queries(self) -> None:
        created = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
        snapshot = ProcessSnapshot(
            True,
            (
                ProcessInfo(10, 1, "controller", "controller", created),
                ProcessInfo(11, 10, "child", "child", created),
            ),
            (),
            "fake",
        )

        index = snapshot.by_pid
        self.assertIs(index, snapshot.by_pid)
        self.assertIs(index, snapshot.pid_index)
        self.assertIs(snapshot.process_for(11), index[11])
        self.assertTrue(snapshot.parent_matches(11, 10))
        self.assertFalse(snapshot.parent_matches(11, 1))
        self.assertIsNone(
            ProcessSnapshot(
                False, snapshot.processes, ("partial",), "linux-proc"
            ).parent_matches(99, 10)
        )

    def test_windows_known_pid_query_does_not_use_full_inventory(self) -> None:
        captured = {}

        def runner(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            payload = {
                "pid": 11,
                "ppid": 10,
                "name": "child.exe",
                "command_line": "child",
                "created_utc": "2026-07-30T12:00:00Z",
            }
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")

        query = windows_process_query(11, runner=runner)
        self.assertTrue(query.complete)
        self.assertEqual(11, query.process.pid if query.process else None)
        self.assertIn("ProcessId = 11", captured["argv"][-1])
        self.assertNotIn(
            "Get-CimInstance Win32_Process | ForEach-Object", captured["argv"][-1]
        )
        self.assertEqual(WINDOWS_CREATE_NO_WINDOW, captured["kwargs"]["creationflags"])

    def test_windows_provider_uses_only_fixed_command(self) -> None:
        captured = {}

        def runner(argv, **kwargs):
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            payload = [
                {
                    "pid": 10,
                    "ppid": 1,
                    "name": "python.exe",
                    "command_line": "python worker.py",
                    "created_utc": "2026-07-30T12:00:00Z",
                }
            ]
            return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")

        snapshot = windows_process_snapshot(runner=runner)
        self.assertTrue(snapshot.complete)
        self.assertEqual(10, snapshot.processes[0].pid)
        self.assertEqual(WINDOWS_CIM_SCRIPT, captured["argv"][-1])
        self.assertEqual("-Command", captured["argv"][-2])
        self.assertNotIn("shell", captured["kwargs"])
        self.assertEqual(WINDOWS_CREATE_NO_WINDOW, captured["kwargs"]["creationflags"])

    def test_windows_provider_fails_unknown_on_cim_error(self) -> None:
        def runner(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 7, "", "CIM unavailable")

        snapshot = windows_process_snapshot(runner=runner)
        self.assertFalse(snapshot.complete)
        self.assertIn("CIM returned 7", snapshot.errors[0])

    def test_windows_provider_preserves_missing_creation_time(self) -> None:
        def runner(argv, **kwargs):
            return subprocess.CompletedProcess(
                argv,
                0,
                json.dumps(
                    {
                        "pid": 10,
                        "ppid": 1,
                        "name": "x",
                        "command_line": "",
                        "created_utc": None,
                    }
                ),
                "",
            )

        snapshot = windows_process_snapshot(runner=runner)
        self.assertFalse(snapshot.complete)
        self.assertIsNone(snapshot.processes[0].created_utc)
        self.assertTrue(snapshot.errors)


if __name__ == "__main__":
    unittest.main()
