"""Real threaded/process hook-log I/O; identity/readiness doubles, no providers."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orchestrator_harness import mutation, records, root_hook_wrapper as wrapper
from orchestrator_harness import manager_queue as queue
from orchestrator_harness.epochs import current_epoch_path, manager_queue_path


class RootHookAppendLockTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="hook-append-lock-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.repository = Path(__file__).resolve().parents[2]

    @staticmethod
    def rows(path):
        data = path.read_bytes()
        assert data.endswith(b"\n")
        return [json.loads(line) for line in data.splitlines()]

    def processes(self, code, arguments, *, ready=None):
        children = []
        try:
            for args in arguments:
                children.append(subprocess.Popen(
                    [sys.executable, "-B", "-c",
                     "import faulthandler; faulthandler.dump_traceback_later(10, repeat=True)\n" + code,
                     *map(str, args)],
                    cwd=self.repository, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
            if ready is not None:
                deadline = time.monotonic() + 30
                while len(list(self.root.glob("ready-*"))) != len(children):
                    if time.monotonic() >= deadline or any(p.poll() is not None for p in children):
                        self.fail("children did not reach first-creation barrier")
                    time.sleep(0.01)
                ready()
            else:
                for child in children:
                    self.assertEqual("ready", child.stdout.readline().strip())
                for child in children:
                    child.stdin.write("go\n")
                    child.stdin.flush()
            for child in children:
                try:
                    stdout, stderr = child.communicate(timeout=30)
                except subprocess.TimeoutExpired as exc:
                    diagnostic = exc.stderr or b""
                    if isinstance(diagnostic, bytes):
                        diagnostic = diagnostic.decode("utf-8", errors="replace")
                    self.fail(f"owned child {child.pid} exceeded 30s; captured stacks: {diagnostic}")
                self.assertEqual(0, child.returncode, stdout + stderr)
        finally:
            for child in children:
                if child.poll() is None:
                    child.kill()  # Only this fixture's exact original handle.
                child.communicate(timeout=10)

    def test_threads_append_exact_complete_rows_to_fresh_and_existing_logs(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                path = self.root / f"thread-{existing}.jsonl"
                if existing:
                    wrapper._append_jsonl(path, {"seed": True})
                barrier = threading.Barrier(8)
                def writer(number):
                    barrier.wait(timeout=10)
                    for item in range(12):
                        wrapper._append_jsonl(path, {"writer": number, "item": item,
                                                     "payload": "line\n雪" * 128})
                with ThreadPoolExecutor(max_workers=8) as executor:
                    list(executor.map(writer, range(8)))
                rows = self.rows(path)
                self.assertEqual(96 + int(existing), len(rows))
                self.assertEqual({(i, j) for i in range(8) for j in range(12)},
                                 {(r["writer"], r["item"]) for r in rows if "writer" in r})
                self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)

    def test_processes_append_exact_complete_rows_to_fresh_and_existing_logs(self):
        code = '''import sys
from pathlib import Path
from orchestrator_harness.root_hook_wrapper import _append_jsonl
path=Path(sys.argv[1]); number=int(sys.argv[2])
print('ready', flush=True); sys.stdin.readline()
for item in range(12):
 _append_jsonl(path, {'writer':number,'item':item,'payload':'line\\n雪'*128})
'''
        for existing in (False, True):
            with self.subTest(existing=existing):
                path = self.root / f"process-{existing}.jsonl"
                if existing:
                    wrapper._append_jsonl(path, {"seed": True})
                self.processes(code, [(path, i) for i in range(8)])
                rows = self.rows(path)
                self.assertEqual(96 + int(existing), len(rows))
                self.assertEqual({(i, j) for i in range(8) for j in range(12)},
                                 {(r["writer"], r["item"]) for r in rows if "writer" in r})

    def test_process_first_lock_creation_both_absence_windows(self):
        # Actual independent interpreters all authorize an absent lock before
        # one creates it. Cover capture->proof and proof->open, not just EEXIST.
        code = '''import sys,time
from pathlib import Path
from orchestrator_harness import mutation
from orchestrator_harness.records import RecordLock
root=Path(sys.argv[1]); number=sys.argv[2]; seam=sys.argv[3]
def gate():
 (root/('ready-'+number)).touch()
 while not (root/'go').exists(): time.sleep(.005)
if seam=='capture':
 original=mutation._capture_anchored
 def capture(*args, **kwargs):
  value=original(*args, **kwargs)
  if not value.present: gate()
  return value
 mutation._capture_anchored=capture
else: mutation._after_target_proof=gate
with RecordLock(root/'record'): pass
'''
        for seam in ("capture", "proof"):
            with self.subTest(seam=seam):
                for path in self.root.iterdir():
                    path.unlink()
                self.processes(code, [(self.root, i, seam) for i in range(6)],
                               ready=lambda: (self.root / "go").touch())
                self.assertEqual(b"", (self.root / ".record.lock").read_bytes())

    def test_sustained_process_contention_completes_all_rows(self):
        code = '''import sys,faulthandler
from pathlib import Path
from orchestrator_harness.root_hook_wrapper import _append_jsonl
faulthandler.dump_traceback_later(10,repeat=True)
path=Path(sys.argv[1]); number=int(sys.argv[2])
print('ready',flush=True);sys.stdin.readline()
for item in range(100): _append_jsonl(path, {'writer':number,'item':item})
'''
        path = self.root / "sustained.jsonl"
        self.processes(code, [(path, i) for i in range(8)])
        rows = self.rows(path)
        self.assertEqual(800, len(rows))
        self.assertEqual({(i, j) for i in range(8) for j in range(100)},
                         {(r["writer"], r["item"]) for r in rows})

    def test_timed_local_acquisition_releases_registry_without_reentering(self):
        path = self.root / "local-timeout"
        with records.RecordLock(path):
            with self.assertRaisesRegex(records.RecordError, "timed out"):
                with records.RecordLock(path, acquire_timeout=.01):
                    self.fail("same-thread contention must not enter")
        self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)

    @unittest.skipIf(os.name == "nt", "native POSIX flock contention")
    def test_default_acquisition_polls_only_contention_without_a_deadline(self):
        import errno
        import fcntl
        path = self.root / "default-poll"
        native = fcntl.flock
        attempts = []
        def contend(fd, operation):
            if operation & fcntl.LOCK_EX:
                attempts.append(operation)
                if len(attempts) <= 2:
                    raise OSError((errno.EACCES, errno.EAGAIN)[len(attempts) - 1],
                                  "controlled contention")
            return native(fd, operation)
        with patch.object(fcntl, "flock", side_effect=contend), \
                patch.object(records.time, "sleep") as sleep, \
                patch.object(records.RecordLock, "_wait_for_acquisition",
                             side_effect=AssertionError("default must not use a deadline")):
            with records.RecordLock(path):
                self.assertEqual([fcntl.LOCK_EX | fcntl.LOCK_NB] * 3, attempts)
            self.assertEqual([((.005,), {}), ((.005,), {})], sleep.call_args_list)
        self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)

    @unittest.skipIf(os.name == "nt", "native POSIX flock error injection")
    def test_default_acquisition_propagates_noncontention_and_closes_descriptor(self):
        import errno
        path = self.root / "default-error"
        descriptors = []
        def fail(fd, operation):
            descriptors.append(fd)
            raise OSError(errno.EIO, "controlled I/O failure")
        with patch("fcntl.flock", side_effect=fail) as native, \
                patch.object(records.time, "sleep") as sleep:
            with self.assertRaises(OSError) as caught:
                with records.RecordLock(path):
                    self.fail("failed acquisition must not enter")
            self.assertEqual(errno.EIO, caught.exception.errno)
            self.assertEqual(1, native.call_count)
            sleep.assert_not_called()
        self.assertEqual(1, len(descriptors))
        with self.assertRaises(OSError):
            os.fstat(descriptors[0])
        self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)
        self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry_users)
        with records.RecordLock(path):
            pass

    @unittest.skipIf(os.name == "nt", "native POSIX flock contention and identity proof")
    def test_default_waits_for_real_holder_and_rejects_replaced_lock(self):
        import fcntl
        code = '''import sys
from pathlib import Path
from orchestrator_harness.records import RecordLock
with RecordLock(Path(sys.argv[1])):
 print('held',flush=True);sys.stdin.readline()
'''
        for replacement in (False, True):
            with self.subTest(replacement=replacement):
                path = self.root / f"default-held-{replacement}"
                child = subprocess.Popen([sys.executable, "-B", "-c", code, str(path)],
                                         cwd=self.repository, stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                native = fcntl.flock
                attempting = threading.Event()
                done = threading.Event()
                errors = []
                entered = []
                operations = []
                def observe(fd, operation):
                    if operation & fcntl.LOCK_EX:
                        operations.append(operation)
                        attempting.set()
                    return native(fd, operation)
                def acquire():
                    try:
                        with records.RecordLock(path):
                            entered.append(True)
                    except BaseException as exc:
                        errors.append(exc)
                    finally:
                        done.set()
                thread = threading.Thread(target=acquire)
                try:
                    self.assertEqual("held", child.stdout.readline().strip())
                    with patch.object(fcntl, "flock", side_effect=observe), \
                            patch.object(records.RecordLock, "_wait_for_acquisition",
                                         side_effect=AssertionError("default must not use a deadline")):
                        thread.start()
                        self.assertTrue(attempting.wait(10))
                        self.assertFalse(done.wait(.05))
                        if replacement:
                            alternate = self.root / "alternate-lock"
                            alternate.write_bytes(b"")
                            os.replace(alternate, records.RecordLock(path).lock_path)
                        self.release_holder(child)
                        thread.join(timeout=10)
                        self.assertFalse(thread.is_alive())
                finally:
                    if child.poll() is None:
                        child.kill()  # Exact fixture-owned handle only.
                    child.communicate(timeout=10)
                    if thread.ident is not None:
                        thread.join(timeout=10)
                self.assertTrue(operations)
                self.assertEqual({fcntl.LOCK_EX | fcntl.LOCK_NB}, set(operations))
                if replacement:
                    self.assertEqual([], entered)
                    self.assertEqual(1, len(errors), errors)
                    self.assertIsInstance(errors[0], mutation.MutationConflict)
                else:
                    self.assertEqual([True], entered)
                    self.assertEqual([], errors)
                self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)
                self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry_users)

    @unittest.skipIf(os.name == "nt", "native POSIX flock error injection")
    def test_timed_acquisition_does_not_retry_non_contention_failure(self):
        import errno
        path = self.root / "native-error"
        with patch("fcntl.flock", side_effect=OSError(errno.EIO, "controlled I/O failure")) as native:
            with self.assertRaises(OSError):
                with records.RecordLock(path, acquire_timeout=.01):
                    self.fail("failed acquisition must not enter")
        self.assertEqual(1, native.call_count)
        self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)
        with records.RecordLock(path, acquire_timeout=.1):
            pass

    def test_timed_native_contention_fails_closed_and_releases_handles(self):
        path = self.root / "timed.jsonl"
        code = '''import sys
from pathlib import Path
from orchestrator_harness.records import RecordLock
with RecordLock(Path(sys.argv[1])):
 print('held',flush=True);sys.stdin.readline()
'''
        child = subprocess.Popen([sys.executable, "-B", "-c", code, str(path)],
                                 cwd=self.repository, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual("held", child.stdout.readline().strip())
            with self.assertRaisesRegex(records.RecordError, "timed out"):
                with records.RecordLock(path, acquire_timeout=.05):
                    self.fail("held native lock must not enter")
            self.assertFalse(path.exists())
            self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)
            child.stdin.write("release\n")
            child.stdin.flush()
            stdout, stderr = child.communicate(timeout=10)
            self.assertEqual(0, child.returncode, stdout + stderr)
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
        wrapper._append_jsonl(path, {"after_release": True})
        self.assertEqual([{"after_release": True}], self.rows(path))

    @unittest.skipIf(os.name == "nt", "POSIX data-inode NFS synchronization")
    def test_absent_data_synchronization_does_not_create_or_lock_target(self):
        path = self.root / "absent.jsonl"
        with patch("fcntl.flock") as native:
            with mutation.synchronize_append_file(self.root, path.name):
                self.assertFalse(path.exists())
            native.assert_not_called()
        self.assertFalse(path.exists())

    @unittest.skipIf(os.name == "nt", "POSIX data-inode NFS synchronization")
    def test_data_lock_covers_strict_append_close_and_is_then_released(self):
        path = self.root / "close.jsonl"
        path.write_bytes(b"")
        original = wrapper.open_append_file
        observations = []
        code = """import errno,fcntl,os,sys
fd=os.open(sys.argv[1],os.O_RDWR|os.O_NOFOLLOW)
try:
 try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except OSError as exc:
  if exc.errno not in (errno.EACCES,errno.EAGAIN): raise
  print('held')
 else: print('free')
finally: os.close(fd)
"""
        def observe():
            result = subprocess.run([sys.executable, "-B", "-c", code, str(path)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            return result.stdout.strip()
        @contextmanager
        def tracked(*args, **kwargs):
            observations.append(observe())  # Before strict authorization/open.
            with original(*args, **kwargs) as handle:
                yield handle
            self.assertTrue(handle.handle.closed)
            observations.append(observe())  # Strict append descriptor is closed.
        with patch.object(wrapper, "open_append_file", side_effect=tracked):
            wrapper._append_jsonl(path, {"exact": "row"})
        self.assertEqual(["held", "held"], observations)
        self.assertEqual("free", observe())
        self.assertEqual([{"exact": "row"}], self.rows(path))
        self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)

    def data_holder(self, path):
        code = """import fcntl,os,sys
fd=os.open(sys.argv[1],os.O_RDWR|os.O_NOFOLLOW)
try:
 fcntl.flock(fd,fcntl.LOCK_EX)
 print('held',flush=True); sys.stdin.readline()
finally: os.close(fd)
"""
        child = subprocess.Popen([sys.executable, "-B", "-c", code, str(path)],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        def cleanup():
            if child.poll() is None:
                child.kill()  # Exact fixture-owned handle only.
            child.communicate(timeout=10)
        self.addCleanup(cleanup)
        self.assertEqual("held", child.stdout.readline().strip())
        return child

    @staticmethod
    def release_holder(child):
        child.stdin.write("release\n")
        child.stdin.flush()
        stdout, stderr = child.communicate(timeout=10)
        if child.returncode:
            raise AssertionError(stdout + stderr)

    @unittest.skipIf(os.name == "nt", "POSIX data-inode NFS synchronization")
    def test_external_data_holder_blocks_append_until_release(self):
        import fcntl
        path = self.root / "data-contention.jsonl"
        path.write_bytes(b"")
        child = self.data_holder(path)
        identity = path.stat().st_ino
        native = fcntl.flock
        attempting = threading.Event()
        done = threading.Event()
        errors = []
        def observe(fd, operation):
            if operation & fcntl.LOCK_EX and os.fstat(fd).st_ino == identity:
                attempting.set()
            return native(fd, operation)
        def append():
            try:
                wrapper._append_jsonl(path, {"after": "release"})
            except BaseException as exc:
                errors.append(exc)
            finally:
                done.set()
        thread = threading.Thread(target=append)
        try:
            with patch.object(fcntl, "flock", side_effect=observe):
                thread.start()
                self.assertTrue(attempting.wait(10))
                self.assertFalse(done.wait(.05))
                self.assertEqual(b"", path.read_bytes())
                self.release_holder(child)
                thread.join(timeout=10)
                self.assertFalse(thread.is_alive())
        finally:
            if child.poll() is None:
                self.release_holder(child)
            if thread.ident is not None:
                thread.join(timeout=10)
        self.assertEqual([], errors)
        self.assertEqual([{"after": "release"}], self.rows(path))
        self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)

    @unittest.skipIf(os.name == "nt", "POSIX data-inode substitution while waiting")
    def test_data_or_parent_substitution_while_waiting_fails_closed(self):
        import fcntl
        for attack in ("replacement", "symlink", "hardlink", "parent"):
            with self.subTest(attack=attack):
                parent = self.root / attack
                parent.mkdir()
                path = parent / "log.jsonl"
                path.write_bytes(b"original\n")
                outside = self.root / (attack + "-outside")
                outside.write_bytes(b"outside\n")
                child = self.data_holder(path)
                identity = path.stat().st_ino
                native = fcntl.flock
                attempting = threading.Event()
                errors = []
                def observe(fd, operation):
                    if operation & fcntl.LOCK_EX and os.fstat(fd).st_ino == identity:
                        attempting.set()
                    return native(fd, operation)
                def append():
                    try:
                        wrapper._append_jsonl(path, {"must_not_append": True})
                    except BaseException as exc:
                        errors.append(exc)
                thread = threading.Thread(target=append)
                try:
                    with patch.object(fcntl, "flock", side_effect=observe):
                        thread.start()
                        self.assertTrue(attempting.wait(10))
                        if attack == "replacement":
                            replacement = self.root / "replacement-file"
                            replacement.write_bytes(b"replacement\n")
                            os.replace(replacement, path)
                        elif attack == "symlink":
                            path.unlink()
                            path.symlink_to(outside)
                        elif attack == "hardlink":
                            os.link(path, self.root / "extra-link")
                        else:
                            parent.rename(self.root / "retired-parent")
                            parent.mkdir()
                            path.write_bytes(b"replacement parent\n")
                        self.release_holder(child)
                        thread.join(timeout=10)
                        self.assertFalse(thread.is_alive())
                finally:
                    if child.poll() is None:
                        self.release_holder(child)
                    if thread.ident is not None:
                        thread.join(timeout=10)
                self.assertEqual(1, len(errors), errors)
                self.assertIsInstance(errors[0], mutation.MutationConflict)
                self.assertEqual(b"outside\n", outside.read_bytes())
                self.assertNotIn(b"must_not_append", path.read_bytes())
                self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)

    @unittest.skipIf(os.name == "nt", "POSIX data-inode lock timeout/error")
    def test_data_acquisition_timeout_closes_descriptor_and_releases_registry(self):
        import fcntl
        path = self.root / "data-timeout.jsonl"
        path.write_bytes(b"original\n")
        child = self.data_holder(path)
        native = fcntl.flock
        descriptors = set()
        def observe(fd, operation):
            descriptors.add(fd)
            return native(fd, operation)
        try:
            with records.RecordLock(path):
                with patch.object(fcntl, "flock", side_effect=observe):
                    with self.assertRaisesRegex(mutation.MutationError, "timed out"):
                        with mutation.synchronize_append_file(self.root, path.name,
                                                              acquire_timeout=.02):
                            self.fail("held data inode must not enter")
            self.assertEqual(1, len(descriptors))
            for fd in descriptors:
                with self.assertRaises(OSError):
                    os.fstat(fd)
            self.assertEqual(b"original\n", path.read_bytes())
            self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)
        finally:
            self.release_holder(child)
        wrapper._append_jsonl(path, {"after_timeout": True})
        self.assertIn(b'"after_timeout":true', path.read_bytes())

    @unittest.skipIf(os.name == "nt", "POSIX data-inode lock error")
    def test_data_noncontention_error_is_not_retried_and_closes_descriptor(self):
        import errno
        path = self.root / "data-error.jsonl"
        path.write_bytes(b"original\n")
        descriptors = []
        def fail(fd, operation):
            descriptors.append(fd)
            raise OSError(errno.EIO, "controlled data lock failure")
        with records.RecordLock(path):
            with patch("fcntl.flock", side_effect=fail) as native:
                with self.assertRaises(OSError):
                    with mutation.synchronize_append_file(self.root, path.name):
                        self.fail("failed data lock must not enter")
                self.assertEqual(1, native.call_count)
        self.assertEqual(1, len(descriptors))
        with self.assertRaises(OSError):
            os.fstat(descriptors[0])
        self.assertEqual(b"original\n", path.read_bytes())
        self.assertNotIn(os.path.normcase(str(path)), records.RecordLock._registry)

    def hook_fixture(self):
        workspace = self.root / "manager"
        binding_path = workspace / ".codex" / "binding.json"
        binding_path.parent.mkdir(parents=True)
        runtime = self.root / "runtime"
        records.atomic_write_json(current_epoch_path(runtime), {
            "schema": "current-epoch/v1", "epoch_id": "epoch", "queue_id": "queue"})
        records.atomic_write_json(manager_queue_path(runtime), {
            "schema": "manager-queue/v1", "epoch_id": "epoch", "queue_id": "queue", "events": []})
        event = queue.promote_event(runtime, event_type="LANE_STATUS_CHANGED",
                                    lane_id="lane", run_id="run", summary="notice")
        binding = {"harness_root": str(self.root), "runtime_root": str(runtime),
                   "liveness_path": ".agent-workspace/liveness.jsonl",
                   "delivery_receipt_path": ".agent-workspace/delivery.jsonl"}
        config = SimpleNamespace(profile="managed")
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.dict(os.environ, {}, clear=True))
        stack.enter_context(patch.object(wrapper, "_read_binding", return_value=binding))
        stack.enter_context(patch.object(wrapper, "load_config", return_value=config))
        stack.enter_context(patch.object(wrapper, "resolve_root_session", return_value=("session", "codex")))
        stack.enter_context(patch.object(wrapper, "dispatch", return_value={
            "decision": "NOTICE", "notice": {"message": "unresolved"}}))
        return workspace, runtime, event, binding_path

    def test_actual_owned_hook_thread_repeats_no_false_reject_or_repeat_receipt_growth(self):
        workspace, runtime, event, binding = self.hook_fixture()
        barrier = threading.Barrier(8)
        def caller(_):
            barrier.wait(timeout=10)
            return [wrapper._run_owned("codex", "post-tool-use", binding) for _ in range(12)]
        with ThreadPoolExecutor(max_workers=8) as executor:
            outputs = [output for group in executor.map(caller, range(8)) for output in group]
        self.assertTrue(all("hookSpecificOutput" in result for result in outputs), outputs)
        self.assertEqual(96, len(self.rows(workspace / ".agent-workspace/liveness.jsonl")))
        self.assertEqual(1, len(self.rows(workspace / ".agent-workspace/delivery.jsonl")))
        current = queue.read_manager_queue(runtime)["events"][0]
        self.assertEqual(event["event_id"], current["event_id"])
        self.assertEqual(1, len(current["delivery_history"]))
        queue_before = manager_queue_path(runtime).read_bytes()
        delivery_before = (workspace / ".agent-workspace/delivery.jsonl").read_bytes()
        for _ in range(10):
            wrapper._run_owned("codex", "post-tool-use", binding)
        self.assertEqual(queue_before, manager_queue_path(runtime).read_bytes())
        self.assertEqual(delivery_before, (workspace / ".agent-workspace/delivery.jsonl").read_bytes())

    def test_log_lock_is_released_before_dispatch_and_queue_delivery(self):
        workspace, runtime, event, binding = self.hook_fixture()
        def dispatch(*args):
            self.assertNotIn(os.path.normcase(str(workspace / ".agent-workspace/liveness.jsonl")),
                             records.RecordLock._registry)
            return {"decision": "ALLOW"}
        with patch.object(wrapper, "dispatch", side_effect=dispatch):
            self.assertEqual({}, wrapper._run_owned("codex", "post-tool-use", binding))

    def test_actual_owned_hook_processes_concurrent_distinct_scope_deliveries(self):
        workspace, runtime, event, binding_path = self.hook_fixture()
        code = '''import sys,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from orchestrator_harness import root_hook_wrapper as wrapper
root=Path(sys.argv[1]); number=sys.argv[2]; binding=root/'manager/.codex/binding.json'
record={'harness_root':str(root),'runtime_root':str(root/'runtime'),
 'liveness_path':'.agent-workspace/liveness.jsonl','delivery_receipt_path':'.agent-workspace/delivery.jsonl'}
with patch.dict(os.environ,{},clear=True), patch.object(wrapper,'_read_binding',return_value=record), \\
 patch.object(wrapper,'load_config',return_value=SimpleNamespace(profile='managed')), \\
 patch.object(wrapper,'resolve_root_session',return_value=('fixture-session-'+number,'codex')), \\
 patch.object(wrapper,'dispatch',return_value={'decision':'NOTICE','notice':{'message':'unresolved'}}):
 print('ready',flush=True);sys.stdin.readline()
 for item in range(12):
  result=wrapper._run_owned('codex','post-tool-use',binding)
  assert 'hookSpecificOutput' in result,result
'''
        self.processes(code, [(self.root, i) for i in range(8)])
        self.assertEqual(96, len(self.rows(workspace / ".agent-workspace/liveness.jsonl")))
        deliveries = self.rows(workspace / ".agent-workspace/delivery.jsonl")
        self.assertEqual(8, len(deliveries))
        self.assertEqual({f"fixture-session-{i}" for i in range(8)},
                         {row["session_id"] for row in deliveries})
        self.assertEqual({event["event_id"]}, {row["event_id"] for row in deliveries})
        self.assertEqual({"DELIVERED"}, {row["outcome"] for row in deliveries})
        self.assertEqual(8, len(queue.read_manager_queue(runtime)["events"][0]["delivery_history"]))

    def test_strict_log_authorization_still_rejects_change_or_replacement_without_retry(self):
        for replacement in (False, True):
            with self.subTest(replacement=replacement):
                target = self.root / f"strict-{replacement}.jsonl"
                target.write_bytes(b"original\n")
                swap = self.root / "swap"
                swap.write_bytes(b"external\n")
                proofs = []
                def change():
                    # The first proof is for the lock, the second for the log.
                    proofs.append(True)
                    if len(proofs) == 2:
                        if replacement:
                            os.replace(swap, target)
                        else:
                            target.write_bytes(b"external longer content\n")
                with patch.object(mutation, "_after_target_proof", side_effect=change):
                    with self.assertRaises(mutation.MutationConflict):
                        wrapper._append_jsonl(target, {"must_not_append": True})
                self.assertEqual(2, len(proofs))
                self.assertEqual(b"external\n" if replacement else b"external longer content\n", target.read_bytes())

    def test_linked_log_and_lock_targets_fail_closed_without_external_writes(self):
        outside = self.root / "outside"
        outside.write_bytes(b"must remain unchanged\n")
        for target_kind in ("log", "lock"):
            for link_kind in ("symlink", "hardlink", "directory"):
                with self.subTest(target=target_kind, link=link_kind):
                    log = self.root / f"unsafe-{target_kind}-{link_kind}.jsonl"
                    target = log if target_kind == "log" else records.RecordLock(log).lock_path
                    if link_kind == "symlink":
                        try:
                            target.symlink_to(outside)
                        except OSError:
                            if os.name == "nt":
                                continue
                            raise
                    elif link_kind == "hardlink":
                        os.link(outside, target)
                    else:
                        target.mkdir()
                    try:
                        with self.assertRaises(OSError):
                            wrapper._append_jsonl(log, {"must_not_append": True})
                        self.assertEqual(b"must remain unchanged\n", outside.read_bytes())
                    finally:
                        if target.is_dir() and not target.is_symlink():
                            target.rmdir()
                        else:
                            target.unlink()

    @unittest.skipIf(os.name == "nt", "POSIX directory rename attack; Windows denies rename")
    def test_parent_relocation_during_append_proof_fails_closed(self):
        parent = self.root / "parent"
        parent.mkdir()
        target = parent / "log.jsonl"
        target.write_bytes(b"original\n")
        outside = self.root / "outside"
        outside.mkdir()
        (outside / target.name).write_bytes(b"outside\n")
        proofs = []
        def redirect():
            proofs.append(True)
            if len(proofs) == 2:
                parent.rename(self.root / "retired")
                parent.symlink_to(outside, target_is_directory=True)
        with patch.object(mutation, "_after_target_proof", side_effect=redirect):
            with self.assertRaises(OSError):
                wrapper._append_jsonl(target, {"must_not_append": True})
        self.assertEqual(b"outside\n", (outside / target.name).read_bytes())
        self.assertEqual(b"original\n", (self.root / "retired" / target.name).read_bytes())

    @unittest.skipIf(os.name == "nt", "POSIX replacement while flock waits; Windows holds no-delete handle")
    def test_lock_replaced_while_native_acquisition_waits_is_rejected_before_append(self):
        import fcntl
        path = self.root / "log.jsonl"
        lock_path = records.RecordLock(path).lock_path
        replacement = self.root / "replacement"
        replacement.write_bytes(b"")
        code = '''import sys
from pathlib import Path
from orchestrator_harness.records import RecordLock
with RecordLock(Path(sys.argv[1])):
 print('held',flush=True);sys.stdin.readline()
'''
        child = subprocess.Popen([sys.executable, "-B", "-c", code, str(path)],
                                 cwd=self.repository, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        native = fcntl.flock
        attempting = threading.Event()
        done = threading.Event()
        errors = []
        def observed_acquisition(fd, operation):
            if operation & fcntl.LOCK_EX:
                attempting.set()
            return native(fd, operation)
        def append():
            try:
                wrapper._append_jsonl(path, {"must_not_append": True})
            except BaseException as exc:
                errors.append(exc)
            finally:
                done.set()
        thread = threading.Thread(target=append)
        try:
            self.assertEqual("held", child.stdout.readline().strip())
            with patch.object(fcntl, "flock", side_effect=observed_acquisition):
                thread.start()
                self.assertTrue(attempting.wait(10))
                self.assertFalse(done.wait(0.1))
                os.replace(replacement, lock_path)
                child.stdin.write("release\n")
                child.stdin.flush()
                stdout, stderr = child.communicate(timeout=20)
                self.assertEqual(0, child.returncode, stdout + stderr)
                thread.join(timeout=20)
                self.assertFalse(thread.is_alive())
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
            if thread.ident is not None:
                thread.join(timeout=10)
        self.assertEqual(1, len(errors))
        self.assertIsInstance(errors[0], mutation.MutationConflict)
        self.assertIn("lock identity changed", str(errors[0]))
        self.assertFalse(path.exists())
        with records.RecordLock(path):
            pass


if __name__ == "__main__":
    unittest.main()
