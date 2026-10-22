# Manager queue retention and delivery receipts

This behavior applies to **managed** coordination. It changes neither manager
authority nor the event-handling workflow: use native `watch --until-actionable`,
handle the top-level `event_id`, acknowledge it, and close it with a truthful
`COMPLETE` or `BLOCKED` outcome. Delivery is not acknowledgement or completion.

## What stops repeated growth

An unresolved event gets at most one hook delivery receipt for the exact
`(queue_id, event_id, source, provider_id, session_id, binding_id)` scope.
Repeating the same hook call does not append another receipt, rewrite the queue,
or append another local `DELIVERED` row. Watch delivery is a separate source;
genuinely different native session/binding scopes retain their own receipts.

Unknown, already-terminal or stale event selections do not create a successful
delivery receipt. A stale `HARNESS_EVENT_ID` environment variable therefore does
not keep growing the delivery history of an already-closed event. Invalid or
foreign scopes cannot be used to claim delivery.

**An acknowledged event is still unresolved until closed.** Hook notices can
continue reminding the manager about it even though the one-time receipt is
already recorded. This fix does not auto-acknowledge, auto-close, suppress real
obligations, or change the distinction between hook notices and idle watch.

## Hot queue versus retained history

`manager/QUEUE.json` is the active, epoch/queue-scoped work view. All `PENDING`
and `ACKNOWLEDGED` events remain there. Normal event admission, acknowledgement
and closure move durable `COMPLETE`/`BLOCKED` records to inert archives before
removing them from the hot queue. There is no arbitrary cap on unresolved work.
Successful compacting mutations leave no terminal tail in the hot queue.
Terminal closure is persisted first: archive publication must never invent a
terminal transition that did not durably happen.

The archive is under the matching epoch's
`manager-history/<queue-identity-hash>/` directory:

- `events/`: immutable full terminal records (`manager-event-archive/v1`),
  including event payload, state history, delivery history and content hash;
- `dedup/`: immutable `manager-event-dedup/v1` references for exact producer
  deduplication;
- `legacy-delivery/`: immutable `manager-delivery-history/v1` snapshots taken
  **before** normalizing repeated legacy delivery receipts.

Identity strings are hashed for filenames, not used as unchecked path fragments.
Archive records are bound to the exact epoch and queue. They are evidence, not a
second actionable queue, and cannot resurrect work or satisfy another epoch's
obligations. Archive write/validation failures are errors, not permission to
discard history. An interrupted prune may leave identical hot/archive copies;
conflicting evidence must not be silently overwritten.

The queue retains a bounded archive inventory (count and XOR256 digest), not an
ever-growing list of archive references. Explicit full-history reads validate
that inventory and any preserved legacy-delivery snapshots, so missing or
conflicting evidence is not silently treated as an empty history.

Ordinary queue reads, hook selection and watch do **not** reload all history.
Explicit historical lookup preserves terminal event-ID responses, producer
deduplication, worker notice byte-conflict checks, review recovery and native
planner/reviewer provenance. Epoch close materializes the full settled history
once in `CLOSED_MANAGER_QUEUE.json`; retry preserves the existing snapshot bytes.
Reading closed history does not reopen the epoch or rewrite that snapshot.

## Existing installations and safe upgrades

Legacy archive-less queues remain readable. Migration is lazy on ordinary safe
mutations: there is no background migration command and read-only inspection
does not rewrite the queue. Before legacy duplicate deliveries are normalized,
their exact prior history is preserved in a separate immutable snapshot.
Already-terminal entries may remain hot until a normal compacting mutation.

Installing changed source invalidates source-pinned preparation receipts. Do not
edit a live queue, rewrite hashes, delete session records, or re-sign an old
receipt to make the upgrade appear prepared. Have the actual native manager
finish cleanup and prove `CLOSED`, preserve existing evidence/worktrees, then
follow the [fresh-run archival and preparation procedure](WORKFLOW.md#fresh-run-after-a-handed-off-task).
This document does not authorize activation or a new provider invocation.

## Limits and diagnosis

This bounds **repeat receipt amplification and hot terminal history**, not total
storage. Full historical evidence, ordinary activity/liveness logs, genuine
unresolved events, distinct authentic delivery scopes and large event payloads
can still grow. Archives are not automatically deleted; any later retention
policy must preserve required evidence explicitly. Full historical inspection
can cost more than a hot queue read. Targeted new-producer deduplication does
not scan all historical evidence: external deletion of an archived dedup pointer
can permit a transient duplicate before full-history, provenance or closure
validation detects the corrupted evidence. Ordinary interrupted publication is
recovered before pruning; do not manually edit or delete these archives.

The auxiliary hook JSONL is not authoritative queue state. A crash between the
durable queue receipt and its JSONL append may leave that auxiliary row absent;
repeating the hook does not manufacture a new queue delivery to repair the log.

### Overlapping hook invocations

Liveness and auxiliary delivery JSONL appends each hold a short per-destination
thread/process advisory lock, covering strict target authorization, open, write,
flush, fsync and close. This prevents a legitimate overlapping append from
looking like an unauthorized target change. The log lock is released before
dispatch or manager-queue work; it does not serialize the entire hook or replace
queue authority checks. A failed log append is not retried or silently ignored.
Hook logs use native nonblocking acquisition with a bounded 30-second local/
kernel-lock contention wait, rather than an indefinitely blocking kernel wait.
This avoids a reproduced NFS blocking-lock stall under sustained contention.
Only acquisition is polled; the append itself is never replayed. Timeout or an
unrelated lock I/O error fails closed. This is not a wall-clock guarantee for
unresponsive filesystem I/O, and does not break or remove a genuine holder's
lock. Other record-lock callers retain their unbounded contention-wait semantics.
Their POSIX kernel acquisition now also polls native nonblocking lock attempts:
a forced same-host first-creation test reproduced the blocking-kernel stall
outside the hook-specific path. This changes how acquisition waits, not the
protected operation, and introduces no default timeout or stale-lock breaking.
Windows default acquisition remains unchanged.

On POSIX, an existing log also receives a native lock on its **actual data
inode**, acquired before strict append authorization and retained until the
append descriptor has closed. A sibling lock alone did not provide sufficient
cross-client NFS data-cache coherence in a real multi-host stress test: despite
successful sibling-lock exclusion, it produced lost/corrupt JSONL bytes. The
data descriptor is opened through held no-follow ancestors, without creating
or modifying the file. Plain/single-link, pathname/inode and ancestor identity
are checked before and after acquisition. An absent log still uses the original
strict exclusive first creation; there is no preflight creation, weakened size
proof, or append replay. Data-lock contention has its own bounded 30-second
acquisition wait and fails closed on timeout or unrelated kernel errors.
Windows retains the existing record-lock/append path; this POSIX change does
not establish native Windows or arbitrary filesystem coherence guarantees.

The persistent sibling `.<log-name>.lock` is nondestructive coordination state,
not evidence or a stale-lock marker. First-use processes may safely open the
same newly created plain single-linked lock file; existing locks and actual log
targets retain strict identity/no-follow/ancestor checks. The kernel releases
ownership when the handle closes or the process exits. Lock-name/inode and
ancestor identity are checked again after acquisition. Do not delete or replace
lock files while writers may be active, or use an independent writer that
bypasses this advisory lock. This does not claim protection from arbitrary
hostile changes after the last identity proof.

Offline concurrency tests exercise real threads, independent Python processes,
first-use and existing logs, actual owned-hook queue/delivery I/O and substituted
path rejection. Native identity/readiness are explicit fixture doubles; this is
not evidence that a particular native client overlaps hooks or a provider-backed
end-to-end run.

For a growing queue, distinguish event count/state from the number of repeated
delivery receipts. Preserve the epoch, queue and relevant hook evidence before
diagnosing it; do not clear unresolved events just to make the file smaller.
Reproducing and fixing these defects is not proof that they caused an incident
in an unavailable external project, nor is offline testing provider-backed
end-to-end evidence.
