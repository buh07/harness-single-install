"""NFS cache commit protocol; portable owned fixtures, no providers/services."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from orchestrator_harness import bootstrap, mutation, setup
from orchestrator_harness.tests.test_v2_materialization import MaterializationFixture


class CacheGenerationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = MaterializationFixture()
        self.addCleanup(self.fixture.close)
        self.rt = self.fixture.root_workspace / '.harness-runtime'
        self.source = self.fixture.harness / 'super-cache/custom/README.md'
        self.real_replace = setup.replace

    def install(self, *, overwrite=False):
        catalog = setup._capture_cache_catalog(self.fixture.harness)
        plan = setup._plan_active_cache(self.fixture.harness, catalog=catalog)
        # Test the generation path on every POSIX filesystem, not only NFS.
        with patch.object(setup, '_cache_directory_rename_supported', return_value=False):
            setup._install_active_cache(self.fixture.harness, self.rt, plan=plan,
                                        catalog=catalog, overwrite=overwrite)
        return setup._validated_cache_for_dispatch(self.fixture.harness, self.rt)

    def selection(self):
        return json.loads(mutation.read_bytes(self.rt, setup.CACHE_SELECTION_NAME))

    def test_first_commit_is_exact_pinned_and_idempotent(self):
        generation = self.install()
        self.assertTrue(generation.name.startswith(setup.CACHE_GENERATION_PREFIX))
        self.assertFalse((self.rt / 'super-cache').exists())
        self.assertFalse((self.rt / setup.CACHE_TRANSACTION_NAME).exists())
        self.assertEqual(generation, self.install())
        self.assertEqual(1, len(list(self.rt.glob(setup.CACHE_GENERATION_PREFIX + '*'))))
        self.assertEqual(generation / 'composed-payloads/codex',
                         bootstrap._managed_payload(self.fixture.harness, self.rt, 'codex'))
        self.assertEqual(Path(generation.name), bootstrap._validated_cache_reference(self.fixture.harness, self.rt))
        boundary = setup._capture_cache_boundary(self.rt)
        self.assertEqual(self.selection(), setup._validate_cache_selection(boundary))

    def test_overwrite_commits_new_generation_and_retains_previous_bytes(self):
        old = self.install()
        original = (old / 'custom/README.md').read_bytes()
        self.source.write_bytes(b'new shipped bytes\n')
        with self.assertRaises(setup.SetupError):
            self.install()
        new = self.install(overwrite=True)
        self.assertNotEqual(old, new)
        self.assertEqual(original, (old / 'custom/README.md').read_bytes())
        self.assertEqual(b'new shipped bytes\n', (new / 'custom/README.md').read_bytes())

    def test_failure_before_commit_retains_prior_selection_and_incomplete_evidence(self):
        old = self.install()
        prior = (self.rt / setup.CACHE_SELECTION_NAME).read_bytes()
        self.source.write_bytes(b'changed\n')
        def fail_commit(root, relative, data, **kwargs):
            if Path(relative) == Path(setup.CACHE_SELECTION_NAME):
                raise OSError('injected precommit crash boundary')
            return self.real_replace(root, relative, data, **kwargs)
        with patch.object(setup, 'replace', side_effect=fail_commit), self.assertRaises(setup.SetupError):
            self.install(overwrite=True)
        self.assertEqual(prior, (self.rt / setup.CACHE_SELECTION_NAME).read_bytes())
        self.assertTrue(old.exists())
        self.assertEqual(2, len(list(self.rt.glob(setup.CACHE_GENERATION_PREFIX + '*'))))
        # A separately requested later setup creates a fresh generation; no
        # guessed ownership recovery or abandoned-generation deletion occurs.
        self.install(overwrite=True)
        self.assertEqual(3, len(list(self.rt.glob(setup.CACHE_GENERATION_PREFIX + '*'))))

    def test_failure_after_commit_is_resolved_by_record_not_republication(self):
        def commit_then_fail(root, relative, data, **kwargs):
            result = self.real_replace(root, relative, data, **kwargs)
            if Path(relative) == Path(setup.CACHE_SELECTION_NAME):
                raise OSError('injected postcommit crash boundary')
            return result
        with patch.object(setup, 'replace', side_effect=commit_then_fail), self.assertRaises(setup.SetupError):
            self.install()
        committed = self.selection()['generation']
        self.assertEqual(self.rt / committed, self.install())
        self.assertEqual(1, len(list(self.rt.glob(setup.CACHE_GENERATION_PREFIX + '*'))))

    def test_generation_native_identity_not_only_bytes_is_bound(self):
        generation = self.install()
        file = generation / 'custom/README.md'
        content = file.read_bytes()
        file.unlink()
        file.write_bytes(content)
        with self.assertRaises(setup.SetupError):
            setup._validated_cache_for_dispatch(self.fixture.harness, self.rt)
        self.assertTrue(generation.exists())

    def test_changed_unknown_or_redirected_generation_is_preserved_and_refused(self):
        generation = self.install()
        extra = generation / 'foreign-note'
        extra.write_bytes(b'preserve me')
        with self.assertRaises(setup.SetupError):
            setup._validated_cache_for_dispatch(self.fixture.harness, self.rt)
        self.assertEqual(b'preserve me', extra.read_bytes())

    def test_invalid_or_escaping_selector_never_reads_external_tree(self):
        self.install()
        selection = self.selection()
        selection['generation'] = '../outside'
        (self.rt / setup.CACHE_SELECTION_NAME).write_text(json.dumps(selection))
        with self.assertRaises(setup.SetupError):
            setup._validated_cache_for_dispatch(self.fixture.harness, self.rt)

    def test_concurrent_selector_change_is_not_overwritten(self):
        old = self.install()
        self.source.write_bytes(b'new source\n')
        prior = self.selection()
        prior['config_identity'] += '-foreign'
        foreign = json.dumps(prior).encode()
        def foreign_commit(root, relative, data, **kwargs):
            if Path(relative) == Path(setup.CACHE_SELECTION_NAME):
                (self.rt / setup.CACHE_SELECTION_NAME).write_bytes(foreign)
            return self.real_replace(root, relative, data, **kwargs)
        with patch.object(setup, 'replace', side_effect=foreign_commit), self.assertRaises(setup.SetupError):
            self.install(overwrite=True)
        self.assertEqual(foreign, (self.rt / setup.CACHE_SELECTION_NAME).read_bytes())
        self.assertTrue(old.exists())

    def test_unselected_foreign_generation_is_never_adopted_or_deleted(self):
        self.rt.mkdir()
        foreign = self.rt / (setup.CACHE_GENERATION_PREFIX + 'f' * 32)
        foreign.mkdir()
        (foreign / 'important').write_bytes(b'preserve')
        selected = self.install()
        self.assertNotEqual(selected, foreign)
        self.assertEqual(b'preserve', (foreign / 'important').read_bytes())

    @unittest.skipUnless(os.name == 'posix', 'POSIX capability discovery')
    def test_real_capability_probe_leaves_no_names_and_generic_rename_unchanged(self):
        self.rt.mkdir()
        info = self.rt.stat()
        root = mutation.TargetState(True, 'directory', (info.st_dev, info.st_ino), None, None)
        supported = setup._cache_directory_rename_supported(self.rt, root)
        self.assertEqual([], list(self.rt.iterdir()))
        if not supported:
            (self.rt / 'source').mkdir()
            with self.assertRaises(mutation.MutationUnsupported):
                mutation.rename(self.rt, 'source', 'target')
            self.assertTrue((self.rt / 'source').is_dir())
            self.assertFalse((self.rt / 'target').exists())


@unittest.skipUnless(os.name == 'posix', 'POSIX shared admission read lock')
class PublicationReaderTests(unittest.TestCase):
    def test_readonly_lock_missing_or_foreign_is_refused_without_writes(self):
        from orchestrator_harness.records import runtime_read_lock
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with self.assertRaises(OSError):
                with runtime_read_lock(root):
                    self.fail('missing admission lock was accepted')
            self.assertEqual([], list(root.iterdir()))
            protected = root / 'protected'
            protected.write_bytes(b'preserve')
            (root / '.RUNTIME_STATE.json.lock').symlink_to(protected)
            with self.assertRaises(OSError):
                with runtime_read_lock(root):
                    self.fail('redirected admission lock was accepted')
            self.assertEqual(b'preserve', protected.read_bytes())

    def test_actual_readonly_scan_waits_for_first_epoch_marker_publication(self):
        self._assert_diagnostic_waits("scan")

    def test_actual_plain_watch_waits_for_first_epoch_marker_publication(self):
        self._assert_diagnostic_waits("plain-watch")

    def test_nested_reader_reuses_same_thread_admission_without_deadlock(self):
        from orchestrator_harness.records import runtime_admission_lock, runtime_read_lock
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with runtime_admission_lock(root), runtime_read_lock(root):
                self.assertEqual(['.RUNTIME_STATE.json.lock'], os.listdir(root))

    def _assert_diagnostic_waits(self, kind):
        from types import SimpleNamespace
        from orchestrator_harness import scan_watch
        from orchestrator_harness.records import runtime_admission_lock
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            epoch = root / 'epochs/fixture-epoch'
            epoch.mkdir(parents=True)
            (epoch / 'epoch-state.json').write_text(json.dumps({
                'schema': 'epoch-state/v1', 'epoch_id': 'fixture-epoch',
                'lifecycle': 'active', 'lane_mode': 'plain' if kind == 'plain-watch' else 'managed'}))
            (epoch / 'active-lanes.json').write_text(json.dumps({
                'schema': 'active-lanes/v1', 'epoch_id': 'fixture-epoch', 'lanes': []}))
            linked, release, started = threading.Event(), threading.Event(), threading.Event()
            errors, results = [], []
            real_link = os.link
            def link(*args, **kwargs):
                real_link(*args, **kwargs)
                linked.set()
                if not release.wait(10):
                    raise RuntimeError('fixture publication was not released')
            def writer():
                try:
                    with runtime_admission_lock(root):
                        mutation.replace(root, 'CURRENT_EPOCH.json', json.dumps({
                            'schema': 'current-epoch/v1', 'epoch_id': 'fixture-epoch'}).encode())
                except BaseException as exc:
                    errors.append(exc)
            def reader():
                started.set()
                try:
                    if kind == "scan":
                        results.append(scan_watch.build_snapshot(root))
                    else:
                        with patch.object(scan_watch, "find_harness_root", return_value=root), \
                             patch.object(scan_watch, "load_config", return_value=SimpleNamespace(runtime_root=root, profile="plain")):
                            results.append(scan_watch.run_watch(timeout="0s"))
                except BaseException as exc:
                    errors.append(exc)
            with patch.object(mutation, '_posix_rename', side_effect=mutation.MutationUnsupported('fixture')), \
                 patch.object(os, 'link', side_effect=link) as seam, \
                 patch.object(os, 'supports_dir_fd', os.supports_dir_fd | {seam}), \
                 patch.object(os, 'supports_follow_symlinks', os.supports_follow_symlinks | {seam}):
                publishing = threading.Thread(target=writer)
                publishing.start()
                self.assertTrue(linked.wait(10))
                reading = threading.Thread(target=reader)
                reading.start()
                self.assertTrue(started.wait(10))
                time.sleep(.05)
                self.assertTrue(reading.is_alive())
                release.set()
                publishing.join(10)
                reading.join(10)
                self.assertFalse(publishing.is_alive())
                self.assertFalse(reading.is_alive())
            self.assertEqual([], errors)
            if kind == "scan":
                self.assertEqual('fixture-epoch', results[0]['epoch_id'])
                self.assertEqual([], results[0]['lanes'])
            else:
                self.assertEqual("WATCH_TIMEOUT", results[0]["code"])
                self.assertNotIn("plain regular", results[0]["summary"])
            self.assertEqual({'CURRENT_EPOCH.json', '.RUNTIME_STATE.json.lock',
                              'epochs/fixture-epoch/epoch-state.json',
                              'epochs/fixture-epoch/active-lanes.json'},
                             {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()})
