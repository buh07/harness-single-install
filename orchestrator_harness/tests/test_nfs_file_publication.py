"""Focused regular-file fallback checks; all fixtures honor TMPDIR."""
from __future__ import annotations

import errno
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from orchestrator_harness import mutation


@unittest.skipUnless(os.name == "posix", "POSIX exclusive-link publication")
class ExclusiveLinkPublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="exclusive-file-")
        self.addCleanup(temporary.cleanup)
        self.fixture = Path(temporary.name).resolve()
        self.root = self.fixture / "owned"
        self.root.mkdir()
        self.target = self.root / "record"
        self.real_link = os.link
        # Keep the real link callable in capability sets when mocking its seam.
        self.addCleanup(patch.stopall)
        patch.object(os, "supports_dir_fd", os.supports_dir_fd | {self.real_link}).start()
        self.unsupported = patch.object(mutation, "_posix_rename", side_effect=mutation.MutationUnsupported("fixture"))

    def link_seam(self, callback):
        seam = patch.object(os, "link", side_effect=callback).start()
        patch.object(os, "supports_dir_fd", os.supports_dir_fd | {seam}).start()
        patch.object(os, "supports_follow_symlinks", os.supports_follow_symlinks | {seam}).start()
        return seam

    def publish(self, data=b"complete record\n"):
        return mutation.replace(self.root, "record", data, expected=mutation.TargetState.absent())

    def after_proof_close(self, callback):
        """Inject changes exactly after the linked proof descriptor closes."""
        real_fdopen = os.fdopen
        target = self.target

        def fdopen(descriptor, mode, *args, **kwargs):
            handle = real_fdopen(descriptor, mode, *args, **kwargs)
            if mode != "rb":
                return handle

            class ObserveClose:
                def __enter__(self):
                    return handle.__enter__()

                def __exit__(self, kind, value, traceback):
                    info = os.fstat(handle.fileno())
                    linked_proof = (target.exists() and info.st_nlink == 2
                        and (info.st_dev, info.st_ino)
                        == (target.stat().st_dev, target.stat().st_ino))
                    result = handle.__exit__(kind, value, traceback)
                    if kind is None and linked_proof:
                        callback()
                    return result

            return ObserveClose()

        return patch.object(os, "fdopen", side_effect=fdopen)

    def test_staging_unlink_has_no_open_owned_inode_descriptor(self):
        # Deterministic Linux-NFS regression: an open proof descriptor at this
        # point causes silly-rename, whose deferred REMOVE can outlive close().
        real_fdopen, real_unlink = os.fdopen, os.unlink
        opened, removed = [], []

        def fdopen(*args, **kwargs):
            handle = real_fdopen(*args, **kwargs)
            opened.append(handle)
            return handle

        def unlink(name, **kwargs):
            if str(name).endswith(".tmp") and self.target.exists():
                info = self.target.stat()
                matching = [handle for handle in opened if not handle.closed
                    and (os.fstat(handle.fileno()).st_dev, os.fstat(handle.fileno()).st_ino)
                    == (info.st_dev, info.st_ino)]
                self.assertEqual([], matching, "unlink would silly-rename our open staging inode")
                removed.append(name)
            return real_unlink(name, **kwargs)

        with self.unsupported, patch.object(os, "fdopen", side_effect=fdopen), \
             patch.object(os, "unlink", side_effect=unlink) as seam, \
             patch.object(os, "supports_dir_fd", os.supports_dir_fd | {seam}):
            self.publish()
        self.assertEqual(1, len(removed))
        self.assertEqual(1, self.target.stat().st_nlink)
        self.assertEqual(["record"], os.listdir(self.root))

    def pending_removal(self):
        """Model deferred kernel REMOVE; only this fixture removes its alias."""
        real_unlink = os.unlink
        pending = self.root / ".pending-fixture-alias"
        attempts = []

        def unlink(name, **kwargs):
            if str(name).endswith(".tmp") and self.target.exists():
                attempts.append(name)
                os.rename(name, pending.name, src_dir_fd=kwargs["dir_fd"],
                          dst_dir_fd=kwargs["dir_fd"])
                return None
            return real_unlink(name, **kwargs)

        seam = patch.object(os, "unlink", side_effect=unlink).start()
        patch.object(os, "supports_dir_fd", os.supports_dir_fd | {seam}).start()
        return pending, attempts, real_unlink

    def test_deferred_removal_completes_one_publication_without_exempting_readers(self):
        pending, attempts, real_unlink = self.pending_removal()
        link = self.link_seam(self.real_link)
        observations = []

        def complete(delay):
            observations.append(delay)
            self.assertGreater(delay, 0)
            self.assertLessEqual(delay, .01)
            self.assertEqual(2, self.target.stat().st_nlink)
            with self.assertRaises(mutation.MutationConflict):
                mutation.read_bytes(self.root, "record")
            self.assertTrue(pending.exists())
            real_unlink(pending)  # fixture's asynchronous REMOVE, not publisher cleanup

        with self.unsupported, patch.object(mutation.time, "sleep", side_effect=complete):
            receipt = self.publish()
        self.assertEqual(1, link.call_count)
        self.assertEqual(1, len(attempts))
        self.assertEqual(1, len(observations))
        self.assertEqual(1, self.target.stat().st_nlink)
        self.assertEqual(receipt.resulting, mutation.capture_target(self.root, "record"))
        self.assertEqual(["record"], os.listdir(self.root))

    def test_persistent_foreign_link_times_out_without_retry_or_cleanup(self):
        pending, attempts, _ = self.pending_removal()
        link = self.link_seam(self.real_link)
        with self.unsupported, patch.object(mutation.time, "monotonic", side_effect=[0., 6.]), \
             patch.object(mutation.time, "sleep") as sleep, \
             self.assertRaisesRegex(mutation.MutationConflict, "completion timed out"):
            self.publish()
        self.assertEqual(1, link.call_count)
        self.assertEqual(1, len(attempts))
        sleep.assert_not_called()
        self.assertTrue(pending.exists())
        self.assertEqual(b"complete record\n", self.target.read_bytes())
        with self.assertRaises(mutation.MutationConflict):
            mutation.read_bytes(self.root, "record")

    def test_more_than_two_links_during_completion_fails_without_wait(self):
        pending, attempts, _ = self.pending_removal()
        real_rename = os.rename
        extra = self.fixture / "unknown-extra"

        def rename(*args, **kwargs):
            result = real_rename(*args, **kwargs)
            self.real_link(self.target, extra)
            return result

        with self.unsupported, patch.object(os, "rename", side_effect=rename) as seam, \
             patch.object(os, "supports_dir_fd", os.supports_dir_fd | {seam}), \
             patch.object(mutation.time, "sleep") as sleep, \
             self.assertRaisesRegex(mutation.MutationConflict, "unexpected link count"):
            self.publish()
        sleep.assert_not_called()
        self.assertEqual(1, len(attempts))
        self.assertTrue(pending.exists())
        self.assertTrue(extra.exists())
        self.assertEqual(3, self.target.stat().st_nlink)

    def test_destination_substitution_while_completion_waits_is_preserved(self):
        pending, attempts, _ = self.pending_removal()
        foreign = self.fixture / "foreign-after-unlink"
        foreign.write_bytes(b"preserve foreign destination")

        def substitute(delay):
            os.replace(foreign, self.target)

        with self.unsupported, patch.object(mutation.time, "sleep", side_effect=substitute), \
             self.assertRaisesRegex(mutation.MutationConflict, "result changed during completion"):
            self.publish()
        self.assertEqual(1, len(attempts))
        self.assertEqual(b"preserve foreign destination", self.target.read_bytes())
        self.assertEqual(b"complete record\n", pending.read_bytes())

    def test_destination_metadata_change_while_completion_waits_fails(self):
        pending, attempts, _ = self.pending_removal()
        with self.unsupported, patch.object(mutation.time, "sleep", side_effect=lambda delay: self.target.chmod(0o400)), \
             self.assertRaisesRegex(mutation.MutationConflict, "result changed during completion"):
            self.publish()
        self.assertEqual(1, len(attempts))
        self.assertTrue(pending.exists())
        self.assertEqual(0o400, stat.S_IMODE(self.target.stat().st_mode))

    def test_reappearing_staging_name_while_completion_waits_is_preserved(self):
        pending, attempts, _ = self.pending_removal()

        def appear(delay):
            (self.root / attempts[0]).write_bytes(b"preserve foreign staging")

        with self.unsupported, patch.object(mutation.time, "sleep", side_effect=appear), \
             self.assertRaisesRegex(mutation.MutationConflict, "staging name reappeared"):
            self.publish()
        self.assertEqual(1, len(attempts))
        self.assertEqual(b"preserve foreign staging", (self.root / attempts[0]).read_bytes())
        self.assertTrue(pending.exists())

    def test_completed_result_still_requires_exact_bytes_after_wait(self):
        pending, attempts, real_unlink = self.pending_removal()

        def corrupt(delay):
            before = self.target.stat()
            self.target.write_bytes(b"different bytes\n")
            os.utime(self.target, ns=(before.st_atime_ns, before.st_mtime_ns))
            real_unlink(pending)

        with self.unsupported, patch.object(mutation.time, "sleep", side_effect=corrupt), \
             self.assertRaisesRegex(mutation.MutationConflict, "result identity or bytes changed"):
            self.publish()
        self.assertEqual(1, len(attempts))
        self.assertEqual(1, self.target.stat().st_nlink)
        self.assertEqual(b"different bytes\n", self.target.read_bytes())

    def _assert_post_close_substitution_refused(self, entry):
        foreign = self.fixture / "foreign"
        foreign.write_bytes(b"preserve foreign inode")
        staging, changed = [], []

        def linked(source, target, **kwargs):
            staging.append(self.root / source)
            return self.real_link(source, target, **kwargs)

        def substitute():
            changed.append(entry)
            os.replace(foreign, staging[0] if entry == "staging" else self.target)

        self.link_seam(linked)
        with self.unsupported, self.after_proof_close(substitute), \
             self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual([entry], changed)
        substituted = staging[0] if entry == "staging" else self.target
        self.assertEqual(b"preserve foreign inode", substituted.read_bytes())
        self.assertEqual(b"complete record\n" if entry == "staging" else b"preserve foreign inode",
                         self.target.read_bytes())
        self.assertEqual({"record", staging[0].name} if entry == "staging" else {"record"},
                         set(os.listdir(self.root)))

    def test_postclose_staging_substitution_preserves_foreign_name(self):
        self._assert_post_close_substitution_refused("staging")

    def test_postclose_destination_substitution_preserves_foreign_name(self):
        self._assert_post_close_substitution_refused("destination")

    def test_postclose_metadata_change_is_not_accepted(self):
        changed = []

        def change_mode():
            changed.append(True)
            self.target.chmod(0o400)

        with self.unsupported, self.after_proof_close(change_mode), \
             self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual([True], changed)
        self.assertEqual(b"complete record\n", self.target.read_bytes())
        self.assertEqual(["record"], os.listdir(self.root))

    def test_real_filesystem_publication_preserves_single_inode_content_and_metadata(self):
        metadata = mutation.FileMetadata(0o440, 1600000000000000000, 1600000001000000000)
        with self.unsupported:
            receipt = mutation.replace(self.root, "record", b"complete record\n",
                expected=mutation.TargetState.absent(), metadata=metadata)
        info = self.target.stat()
        self.assertEqual(receipt.resulting.identity, (info.st_dev, info.st_ino))
        self.assertEqual(1, info.st_nlink)
        self.assertEqual(0o440, stat.S_IMODE(info.st_mode))
        self.assertEqual(metadata.mtime_ns, info.st_mtime_ns)
        self.assertEqual(b"complete record\n", mutation.read_bytes(self.root, "record"))
        self.assertEqual(["record"], os.listdir(self.root))

    def test_unmocked_filesystem_can_publish_new_file(self):
        self.publish()
        self.assertEqual(b"complete record\n", mutation.read_bytes(self.root, "record"))
        self.assertEqual(1, self.target.stat().st_nlink)

    def test_supported_native_path_never_uses_link(self):
        def native(source_fd, source, target_fd, target, **kwargs):
            self.assertFalse(kwargs["replace_existing"])
            os.rename(source, target, src_dir_fd=source_fd, dst_dir_fd=target_fd)
        seam = self.link_seam(lambda *args, **kwargs: self.fail("native path used link"))
        with patch.object(mutation, "_posix_rename", side_effect=native):
            self.publish()
        seam.assert_not_called()

    def test_existing_file_replacement_does_not_use_fallback(self):
        self.target.write_bytes(b"old")
        seam = self.link_seam(lambda *args, **kwargs: self.fail("replacement used link"))
        mutation.replace(self.root, "record", b"new", expected=mutation.capture_target(self.root, "record"))
        seam.assert_not_called()
        self.assertEqual(b"new", self.target.read_bytes())

    def test_noncapability_native_error_does_not_use_fallback(self):
        seam = self.link_seam(lambda *args, **kwargs: self.fail("I/O error used link"))
        with patch.object(mutation, "_posix_rename", side_effect=OSError(errno.EIO, "fixture")):
            with self.assertRaises(OSError):
                self.publish()
        seam.assert_not_called()
        self.assertEqual([], os.listdir(self.root))

    def test_general_file_and_directory_rename_remain_unsupported(self):
        for name, directory in (("file", False), ("directory", True)):
            source = self.root / name
            source.mkdir() if directory else source.write_bytes(b"preserve source")
            with self.unsupported, self.assertRaises(mutation.MutationUnsupported):
                mutation.rename(self.root, name, "destination")
            self.assertTrue(source.exists())
            self.assertFalse((self.root / "destination").exists())

    def test_late_destination_file_symlink_or_directory_is_never_overwritten(self):
        protected = self.fixture / "protected"
        protected.write_bytes(b"retain")
        for kind in ("file", "symlink", "directory"):
            with self.subTest(kind=kind):
                def appear(source, target, **kwargs):
                    if kind == "file":
                        self.target.write_bytes(b"foreign")
                    elif kind == "symlink":
                        self.target.symlink_to(protected)
                    else:
                        self.target.mkdir()
                    return self.real_link(source, target, **kwargs)
                with self.unsupported:
                    self.link_seam(appear)
                    with self.assertRaises(mutation.MutationConflict):
                        self.publish()
                self.assertEqual(b"retain", protected.read_bytes())
                self.assertEqual(["record"], os.listdir(self.root))
                if kind == "directory":
                    self.target.rmdir()
                else:
                    self.target.unlink()

    def test_server_committed_link_then_error_requires_exact_two_name_proof(self):
        for error in (errno.EIO, errno.EEXIST):
            with self.subTest(error=error):
                def committed(source, target, **kwargs):
                    self.real_link(source, target, **kwargs)
                    raise OSError(error, "simulated lost LINK response")
                self.link_seam(committed)
                with self.unsupported:
                    self.publish()
                self.assertEqual(b"complete record\n", mutation.read_bytes(self.root, "record"))
                self.assertEqual(["record"], os.listdir(self.root))
                self.target.unlink()

    def test_link_error_without_commit_fails_closed(self):
        self.link_seam(lambda *args, **kwargs: (_ for _ in ()).throw(OSError(errno.EIO, "fixture")))
        with self.unsupported, self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual([], os.listdir(self.root))

    def test_link_error_with_foreign_same_bytes_is_not_success(self):
        def foreign(source, target, **kwargs):
            self.target.write_bytes(b"complete record\n")
            raise OSError(errno.EIO, "fixture")
        self.link_seam(foreign)
        with self.unsupported, self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual(b"complete record\n", self.target.read_bytes())
        self.assertEqual(["record"], os.listdir(self.root))

    def test_source_substitution_is_detected_without_deleting_foreign_names(self):
        foreign = self.fixture / "foreign"
        foreign.write_bytes(b"foreign content")
        def substitute(source, target, **kwargs):
            os.replace(foreign, self.root / source)
            return self.real_link(source, target, **kwargs)
        self.link_seam(substitute)
        with self.unsupported, self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual(b"foreign content", self.target.read_bytes())
        self.assertEqual(2, self.target.stat().st_nlink)
        self.assertEqual(2, len(os.listdir(self.root)))

    def test_source_symlink_substitution_is_not_followed(self):
        protected = self.fixture / "protected"
        protected.write_bytes(b"retain")
        def substitute(source, target, **kwargs):
            (self.root / source).unlink()
            (self.root / source).symlink_to(protected)
            return self.real_link(source, target, **kwargs)
        self.link_seam(substitute)
        with self.unsupported, self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertTrue(self.target.is_symlink())
        self.assertEqual(b"retain", protected.read_bytes())

    def test_postlink_content_change_fails_without_rolling_back_destination(self):
        def corrupt(source, target, **kwargs):
            self.real_link(source, target, **kwargs)
            self.target.write_bytes(b"foreign mutation")
        self.link_seam(corrupt)
        with self.unsupported, self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual(b"foreign mutation", self.target.read_bytes())
        self.assertEqual(["record"], os.listdir(self.root))

    def test_postlink_destination_substitution_preserves_foreign_destination(self):
        foreign = self.fixture / "foreign"
        foreign.write_bytes(b"foreign destination")
        def substitute(source, target, **kwargs):
            self.real_link(source, target, **kwargs)
            os.replace(foreign, self.target)
        self.link_seam(substitute)
        with self.unsupported, self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual(b"foreign destination", self.target.read_bytes())
        self.assertEqual(["record"], os.listdir(self.root))

    def test_postlink_mode_or_mtime_change_is_not_accepted(self):
        for field in ("mode", "mtime"):
            with self.subTest(field=field):
                def change(source, target, **kwargs):
                    self.real_link(source, target, **kwargs)
                    if field == "mode":
                        self.target.chmod(0o400)
                    else:
                        info = self.target.stat()
                        os.utime(self.target, ns=(info.st_atime_ns, info.st_mtime_ns - 1000000000))
                self.link_seam(change)
                with self.unsupported, self.assertRaises(mutation.MutationConflict):
                    self.publish()
                self.assertEqual(b"complete record\n", self.target.read_bytes())
                self.target.unlink()

    def test_extra_hardlink_fails_without_weakening_normal_readers(self):
        extra = self.fixture / "extra"
        def link_extra(source, target, **kwargs):
            self.real_link(source, target, **kwargs)
            self.real_link(self.target, extra)
        self.link_seam(link_extra)
        with self.unsupported, self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual(b"complete record\n", self.target.read_bytes())
        with self.assertRaises(mutation.MutationConflict):
            mutation.read_bytes(self.root, "record")

    def test_parent_substitution_never_follows_replacement_symlink(self):
        moved = self.fixture / "moved"
        protected = self.fixture / "protected"
        protected.mkdir()
        (protected / "sentinel").write_bytes(b"retain")
        def substitute(source, target, **kwargs):
            self.root.rename(moved)
            self.root.symlink_to(protected, target_is_directory=True)
            return self.real_link(source, target, **kwargs)
        self.link_seam(substitute)
        with self.unsupported, self.assertRaises(mutation.MutationConflict):
            self.publish()
        self.assertEqual(["sentinel"], os.listdir(protected))
        self.assertEqual(b"retain", (protected / "sentinel").read_bytes())
        self.assertEqual(b"complete record\n", (moved / "record").read_bytes())

    def test_fsync_error_after_link_never_rolls_back_destination(self):
        real_fsync = os.fsync
        def fail_directory_sync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode) and self.target.exists():
                raise OSError(errno.EIO, "fixture directory fsync failure")
            return real_fsync(fd)
        with self.unsupported, patch.object(os, "fsync", side_effect=fail_directory_sync):
            with self.assertRaises(OSError):
                self.publish()
        self.assertEqual(b"complete record\n", self.target.read_bytes())

    def test_unlink_error_before_or_after_commit_never_rolls_back_destination(self):
        real_unlink = os.unlink
        for committed in (False, True):
            with self.subTest(committed=committed):
                attempted = []
                def unlink_error(path, **kwargs):
                    if str(path).endswith(".tmp") and not attempted:
                        attempted.append(path)
                        if committed:
                            real_unlink(path, **kwargs)
                        raise OSError(errno.EIO, "simulated unlink response loss")
                    return real_unlink(path, **kwargs)
                with patch.object(os, "unlink", side_effect=unlink_error) as seam:
                    with patch.object(os, "supports_dir_fd", os.supports_dir_fd | {seam}):
                        with self.unsupported, self.assertRaises(OSError):
                            self.publish()
                self.assertTrue(attempted)
                self.assertEqual(b"complete record\n", self.target.read_bytes())
                self.assertEqual(["record"], os.listdir(self.root))
                self.target.unlink()

    def test_crash_after_link_leaves_two_link_evidence_and_readers_fail_closed(self):
        code = '''
import os, sys
from pathlib import Path
from unittest.mock import patch
from orchestrator_harness import mutation
real_link = os.link
def crash(*args, **kwargs):
    real_link(*args, **kwargs)
    os._exit(73)
with patch.object(mutation, "_posix_rename", side_effect=mutation.MutationUnsupported("fixture")):
    with patch.object(os, "link", side_effect=crash) as seam:
        os.supports_dir_fd = os.supports_dir_fd | {seam}
        os.supports_follow_symlinks = os.supports_follow_symlinks | {seam}
        mutation.replace(Path(sys.argv[1]), "record", b"complete record\\n", expected=mutation.TargetState.absent())
'''
        result = subprocess.run([sys.executable, "-B", "-c", code, str(self.root)], capture_output=True)
        self.assertEqual(73, result.returncode, result.stderr.decode())
        self.assertEqual(2, self.target.stat().st_nlink)
        self.assertEqual(b"complete record\n", self.target.read_bytes())
        self.assertEqual(2, len(os.listdir(self.root)))
        with self.assertRaises(mutation.MutationConflict):
            mutation.read_bytes(self.root, "record")


if __name__ == "__main__":
    unittest.main()
