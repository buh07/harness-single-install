# Regular-file publication on filesystems without exclusive rename

POSIX publication still prefers native atomic no-replace rename. Only when
that operation reports unsupported, and the authorized destination was absent,
the completed regular-file staging inode may be published using an anchored,
no-follow exclusive hard link. Existing destinations are never overwritten by
this fallback. Existing-file replacement, general file moves, and directory
moves are unchanged. Native cache setup separately supports immutable generations
when a fresh owned empty-directory capability probe reports exclusive rename
unsupported; it does not emulate directory rename.

The publisher holds the staging file open and verifies both names against its
identity, content, mode, size, and modification time. It persists the published
directory entry and completes the held-descriptor proof before closing that
descriptor. Both anchored names must then match the final proof's identity and
metadata, including change time and exactly two links, before only the staging
name is removed. Closing first avoids Linux NFS's asynchronous silly-rename of
an open staging file; otherwise its hidden name can keep the result multiply
linked after publication returns. Holding the descriptor would not make a
pathname unlink atomic against a hostile same-directory writer. The publisher
then completes that one publication before performing the ordinary strict
single-link result capture. After its one successful staging-name unlink, it
checks that the staging name remains absent and the destination retains the
proved device, inode, regular-file mode, size and modification time. Exactly two
links may be observed for at most five monotonic seconds, with short bounded
observation sleeps; the operation succeeds only once the link count becomes one.
Any other link count, substituted name, metadata change or ancestor change is a
conflict. Persistent extra links time out with the complete destination and all
unknown aliases preserved. No open publisher descriptor is held during this
phase, no unknown `.nfs` or foreign name is removed, and neither LINK nor unlink
is repeated. This is a bounded publication-completion observation, not a retry,
automatic repair or orphan-adoption protocol. Another process holding the
staging dentry can cause a genuine Linux NFS silly-rename even after the publisher
closes its own descriptor; force-synchronized attributes cannot remove that
still-open alias. An external hold longer than the deadline still fails clearly.
The caller persists the parent and performs its unchanged strict single-link
byte capture; ordinary readers receive no multi-link exemption. A lost LINK response is
accepted only when the same two-name proof succeeds. Other ambiguous link,
unlink, fsync, ancestor-change, or verification outcomes fail closed and never
remove the destination as rollback. A failed call can therefore leave a complete
destination visible; callers must preserve and diagnose it rather than retrying
blindly.

The brief two-link interval is intentional and private to this publisher's
proof. Ordinary readers retain their single-link requirement. Native setup,
epoch/lane/status creation and managed queue consumers already share runtime
admission. Read-only scan snapshots and plain-watch diagnostic reads now take
a shared admission lock by opening only the already-existing persistent lock
file read-only; they create no lockfiles and cannot overlap admitted first
publication. Before native setup initializes that lock, diagnostics report an
uninitialized runtime without creating it. Outbox/public-check scanners retain
and revisit in-progress refused records through their existing behavior. A
process crash after LINK but before staging-name removal leaves two names;
ordinary readers refuse the complete inode pending explicit diagnosis. This change supplies
no automatic orphan cleanup, retries, lock replacements, or directory-rename
emulation. As with the existing POSIX primitives, held directory descriptors do
not stop hostile processes from renaming ancestors or modifying accessible
inodes; observed changes are conflicts, never permission to follow replacements.

Focused tests live in `orchestrator_harness/tests/test_nfs_file_publication.py`.
Set `TMPDIR` to an owned directory on the filesystem under evaluation before
running them. Real multi-host lock/exclusivity validation and a disposable full
setup check remain necessary before deployment on shared network storage.


## Immutable cache generations

On a filesystem whose native exclusive directory rename is unsupported, setup
creates a unique `cache-generation-<random-id>` directory using exclusive mkdir,
builds the entire cache there, and verifies exact membership, captured bytes and
native identities. Only then does it publish `super-cache.active.json`. This
closed-schema selection binds the runtime identity, configuration identity,
generation name, manifest and every directory/file birth identity. First record
publication uses the exclusive complete-file protocol above; subsequent explicit
setup updates atomically replace only the exact captured prior selector.

Dispatch, composed worker payloads, plain base overlays and bootstrap receipts
resolve/pin the committed generation, never a guessed newest directory or a
symlink. Resume retains the already-installed overlay receipt's generation.
Older and incomplete/unselected generations remain as evidence; no automatic
cache garbage collection, inferred adoption, cleanup or rollback deletion is
performed. A failure after commit is resolved by validating the existing commit,
not by replaying publication. Unsupported migration of a legacy physical cache
fails clearly rather than moving/deleting it implicitly. Filesystems supporting
native exclusive directory rename retain their existing transaction protocol.

Use one control host for a live runtime. Storage may be on shared NFS, but the
native PID/creation identities and advisory service topology are host-local;
concurrent control from different hosts is not supported. NFS cross-client lock
grants and attribute refresh can be slow. Do not interpret a short timeout as
proof of owner absence, bypass locks, or launch providers automatically.
