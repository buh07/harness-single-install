# Manager queue and hook-log validation

This report covers the queue-retention and overlapping hook-log fixes tested on
Linux with Python 3.14 and shared NFS. It is finite regression evidence, not a
promise that no bugs remain. See [retention, concurrency and safe upgrades](MANAGER_QUEUE_RETENTION.md)
for the operational contract.

## Comprehensive run: not all green

The entire Linux discovery run collected **1,349 tests across 104 files**:
**1,232 passed, 53 skipped, 81 failure rows (64 ordinary failures plus 17
failed subtests), and 2 teardown errors**; 904 subtests passed. It ran for
4,587.82 seconds. This is **not a passing whole-product suite**.

That run used an earlier 365-file snapshot: before the actual-data-inode
coherence repair, the default POSIX lock-acquisition repair, and a Linux-specific
test-expectation correction. The final repaired source receives focused
regression and independent concurrency testing below, not a claimed second
complete-suite pass. Git provenance is required by two lifecycle tests; their
initial plain-copy failures do not establish product behavior.

Committed-baseline comparisons reproduced concrete representatives of the
remaining failure classes: Linux tests globally mocking Windows paths; NFS
without atomic no-replace rename; old literal cache-path expectations where the
NFS implementation uses generation directories; obsolete documentation and
native-boundary fixtures; public-check timing mocks; retained-resume fixtures
missing overlay receipts; malformed/deep JSON observation expectations; a
service fixture missing the pinned workflow skill; and a V2 cache configuration
identity mismatch after an explicit resource-manifest change. Not every failed
member of these classes was individually rerun at baseline. These failures are
reported, not silently deselected or presented as fixed by this patch.

Two NFS fixture-cleanup `ENOTEMPTY` errors remain **untriaged**. Their trees were
retained, recorded owned processes were exit-proven, and no unknown files were
deleted. They are not being asserted to be baseline failures. The comprehensive
run also exposed a relevant same-host first-lock-creation stall in default
blocking POSIX acquisition; that defect was repaired, with new finite
same-host contention and identity tests. One platform-specific test assertion
was corrected to expect Windows job handles only on Windows.

## Final repaired-source checks

Independent final-source storage testing repeated the actual three-client
append checks below, including 2,448 exact unique writer rows, 144 exclusion
critical sections and 72 unsafe-target negative checks. Ten rounds of six
same-host default-lock first-creation processes completed and were reaped.
The original queue-growth, terminal no-op, history and outbox reproduction also
passed against this final repair. The independent final focused cohort passed
**62 tests and 62 subtests**, with **2 native-Windows skips**. Separately, two
real-Git lifecycle fixtures passed with saved-session feedback/resume and active
cancellation, CLOSED runtimes and recorded process-exit proofs; those lifecycle
checks used the preceding coherence candidate, before the generic default-lock
repair. These are offline storage/protocol checks,
not native model sessions or a full-suite rerun.

## What was exercised

- Real private queue I/O through the owned-hook entry point: 101 repeated calls
  preserve queue and auxiliary delivery bytes after the first receipt. Normal
  and stale explicit selections of both terminal states do not mutate them.
  Terminal events are archived while all unresolved events remain actionable;
  full history, closed snapshots and interrupted outbox replay retain identity.
- Independent processes and threads append fresh and existing liveness/delivery
  logs. Substituted targets, symlinks, hardlinks and changed ancestors fail closed;
  lock errors/timeouts release handles without replaying an append.
- **Actual three-client NFS storage tests:** twelve independent writers produced
  1,200 unique complete JSON rows in a fresh log and 1,200 more in an existing
  log, retaining its seed. All clients observed identical bytes, without NULs or
  rejected writes. Two forced first-lock-creation windows each retained all 24
  expected rows from twelve writers.

The stronger cross-client test caught corruption in the earlier sibling-lock-only
candidate. The repaired POSIX path also locks the existing data inode, through
held no-follow ancestors, before strict append authorization. The numbers above
refer to that repaired implementation, not a diagnostic monkeypatch.

## Scope boundaries

Cross-client **storage protocol** tests do not establish multi-host control of one
live runtime. An earlier-candidate whole-hook/manager-queue cross-host cohort exceeded its
finite bound in the ordinary runtime-state lock; it is **not a passing workflow
test**. Run each live manager/runtime on one host. The hook-log acquisition bounds
do not make unrelated record locks or unresponsive filesystem I/O time-bounded.

Owned-hook fixtures use explicit native identity/readiness doubles, but real
private queue/log files. No paid model, actual native client hook overlap, native
Windows/macOS execution, production runtime activation or new provider-backed
workflow is claimed. The earlier [workflow test](REAL_WORKFLOW_TEST.md) has its
own separate scope and is not evidence for these changes.

## Repeating the portable checks

Use a private disposable **Git checkout** of the revision under test and an owned
temporary directory on the target filesystem. Lifecycle tests that inspect Git
provenance need real repository metadata, not just a copied source tree.
Prefer a disposable checkout over executing tests in a configured installation:
legacy fixture logging can resolve the installation's live diagnostic destination.
The provider-binding fixture now explicitly captures its implicit prompt/lifecycle
logging under its private runtime; this test-only isolation fix does not change
live logging behavior. During installed validation before that fixture correction,
two diagnostic rows were appended to each of two existing monitor logs. Their
historical byte prefixes were verified unchanged and all rows preserved; runtime
state and configuration were not changed. This deviation is not described as
byte-for-byte preservation of every production log. Keep native clients off `PATH` when running offline fixtures; use a
private `HOME` and `CODEX_HOME`. Do not point fixtures at live runtime records.

```sh
: "${PRIVATE_TEST_ROOT:?set an owned absolute private test directory first}"
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="${PRIVATE_TEST_ROOT}/tmp"
export HOME="${PRIVATE_TEST_ROOT}/home"
export CODEX_HOME="$HOME/.codex"
mkdir -p "$TMPDIR" "$CODEX_HOME"
python -B -m pytest -q -p no:cacheprovider \
  orchestrator_harness/tests/test_root_hook_append_lock.py \
  orchestrator_harness/tests/test_manager_queue_retention.py \
  orchestrator_harness/tests/test_manager_queue_atomicity.py \
  orchestrator_harness/tests/test_manager_queue_close.py \
  scripts/tests/test_workflow_hash_inputs.py

# Entire offline discovery; some tests require platform/filesystem capabilities.
python -B -m pytest -q -p no:cacheprovider
```

Python 3.14 emits a large number of existing `PurePath.is_reserved` deprecation
warnings. The comprehensive run retained them; an optional pytest
`-W ignore::DeprecationWarning` reduces warning capture, not test selection or
failure reporting.

Cross-client qualification additionally needs independently authenticated hosts
sharing the private fixture directory, strict host-key verification, actual
shipped append calls, exact row/content accounting on every client, and cleanup
of owned processes by host, boot identity, PID and creation identity. Do not
substitute a one-host process test or weaken no-follow checks to obtain a pass.

Installing this source changes pinned preparation inputs. First settle and prove
the old runtime `CLOSED`, preserve its records, then follow the documented fresh
preparation procedure. Existing preparation hashes must not be rewritten.
