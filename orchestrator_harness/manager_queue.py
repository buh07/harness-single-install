"""The manager queue (managed) and the worker inbox.

Three components write the manager queue, each under the same short queue
lock: the monitor (sole producer of events), ROOT (advances event state via
the manager commands), and the managed PostToolUse hook (appends a
delivery-history receipt only).  The controller and worker never write it.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import hashlib
from pathlib import Path
from typing import Any

from .activity_log import append_detail
from .core import canonical_json, iso_utc, new_id, read_json, require_schema
from .epochs import (
    MANAGER_QUEUE_SCHEMA,
    current_epoch_path,
    lane_record_dir,
    manager_queue_path,
    read_current_epoch,
)
from .records import RecordLock, atomic_write_json, read_record, runtime_admission_lock
from .mutation import capture_target, read_bytes as anchored_read
from .stable_io import PreparedOutputTransaction

LANE_INBOX_SCHEMA = "lane-inbox/v1"

EVENT_TYPES = frozenset(
    {
        "COMPLETION_REVIEW_REQUIRED",
        "LANE_RESULT_INVALID",
        "LANE_RESUME_REQUIRED",
        "LANE_STATUS_CHANGED",
    }
)
EVENT_STATES = frozenset({"PENDING", "ACKNOWLEDGED", "COMPLETE", "BLOCKED"})
ASSIGNMENT_STATES = frozenset({"PENDING", "ACKNOWLEDGED", "COMPLETE", "BLOCKED"})

MANAGER_ACK_EVENT_NOT_FOUND = "MANAGER_ACK_EVENT_NOT_FOUND"
MANAGER_ACK_ALREADY_ACKNOWLEDGED = "MANAGER_ACK_ALREADY_ACKNOWLEDGED"
MANAGER_ACK_NOT_ROOT_EVENT = "MANAGER_ACK_NOT_ROOT_EVENT"
MANAGER_CLOSE_NOT_ACKNOWLEDGED = "MANAGER_CLOSE_NOT_ACKNOWLEDGED"
MANAGER_CLOSE_ALREADY_CLOSED = "MANAGER_CLOSE_ALREADY_CLOSED"
MANAGER_CLOSE_NOT_ROOT_EVENT = "MANAGER_CLOSE_NOT_ROOT_EVENT"
MANAGER_CLOSE_INVALID_OUTCOME = "MANAGER_CLOSE_INVALID_OUTCOME"
MANAGER_CLOSE_SUMMARY_REQUIRED = "MANAGER_CLOSE_SUMMARY_REQUIRED"
SEND_LANE_NOT_FOUND = "SEND_LANE_NOT_FOUND"
SEND_LANE_NOT_MANAGED = "SEND_LANE_NOT_MANAGED"
SEND_LANE_NOT_RUNNING = "SEND_LANE_NOT_RUNNING"
SEND_LANE_WRITE_FAILED = "SEND_LANE_WRITE_FAILED"

SEVERITIES = frozenset({"info", "warning", "error", "blocking"})


class ManagerQueueError(RuntimeError):
    """A manager-queue or worker-inbox operation failed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _queue_header(rt: Path) -> dict[str, Any]:
    marker = read_current_epoch(rt)
    if marker is None:
        raise ManagerQueueError("MANAGER_QUEUE_NO_EPOCH", "no active epoch")
    return {
        "epoch_id": str(marker["epoch_id"]),
        "queue_id": str(marker.get("queue_id") or ""),
    }


def read_manager_queue(rt: Path) -> dict[str, Any]:
    """Read the manager queue, confirming its header matches the epoch marker."""
    path = manager_queue_path(rt)
    if not path.is_file():
        raise ManagerQueueError("MANAGER_QUEUE_MISSING", f"manager queue missing: {path}")
    try:
        record = read_record(path, MANAGER_QUEUE_SCHEMA)
    except (OSError, ValueError) as exc:
        raise ManagerQueueError("MANAGER_QUEUE_INVALID", str(exc)) from exc
    header = _queue_header(rt)
    if record.get("epoch_id") != header["epoch_id"] or record.get("queue_id") != header["queue_id"]:
        raise ManagerQueueError("QUEUE_REPLACED", "manager queue header does not match the active epoch")
    validate_queue_record(record)
    return record


def validate_queue_record(record: dict[str, Any]) -> None:
    """Unknown or malformed event state is not a resolved ROOT obligation."""
    events = record.get("events")
    if not isinstance(events, list):
        raise ManagerQueueError("MANAGER_QUEUE_INVALID", "manager events must be a list")
    if (type(record.get("archived_event_count", 0)) is not int or record.get("archived_event_count", 0) < 0
            or not isinstance(record.get("archived_event_xor", "0" * 64), str)
            or len(record.get("archived_event_xor", "0" * 64)) != 64
            or any(c not in "0123456789abcdef" for c in record.get("archived_event_xor", "0" * 64))):
        raise ManagerQueueError("MANAGER_QUEUE_INVALID", "invalid bounded archive inventory")
    identities = set()
    for event in events:
        if (not isinstance(event, dict) or not isinstance(event.get("event_id"), str)
                or not event["event_id"] or event["event_id"] in identities
                or event.get("type") not in EVENT_TYPES or event.get("state") not in EVENT_STATES
                or not isinstance(event.get("lane_id"), str) or not isinstance(event.get("run_id"), str)):
            raise ManagerQueueError("MANAGER_QUEUE_INVALID", "manager event identity, type or state is invalid")
        identities.add(event["event_id"])
        references = event.get("preserved_delivery_history", [])
        if (not isinstance(references, list) or any(not isinstance(value, str) or len(value) != 64
                or any(c not in "0123456789abcdef" for c in value) for value in references)):
            raise ManagerQueueError("MANAGER_QUEUE_INVALID", "invalid preserved delivery reference")
        history = event.get("history")
        delivery = event.get("delivery_history")
        if (not isinstance(history, list) or not history or not isinstance(delivery, list)
                or any(not isinstance(item, dict) or item.get("state") not in EVENT_STATES for item in history)
                or history[-1]["state"] != event["state"]
                or any(not isinstance(item, dict) for item in delivery)):
            raise ManagerQueueError("MANAGER_QUEUE_INVALID", "manager event history is invalid")


ARCHIVE_SCHEMA = "manager-event-archive/v1"


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _archive_root(rt: Path, record: dict[str, Any]) -> Path:
    # Hash every supplied identity, never interpolate event/dedup strings in paths.
    from .epochs import epoch_dir
    return epoch_dir(rt, record["epoch_id"]) / "manager-history" / _digest(record["queue_id"])


def _archive_path(rt: Path, record: dict[str, Any], event_id: str) -> Path:
    return _archive_root(rt, record) / "events" / (_digest(event_id) + ".json")


def _immutable_json(path: Path, value: dict[str, Any]) -> None:
    # Queue lock serializes publishers. Atomic no-follow publication is NFS-safe;
    # an already published different record is evidence corruption, not replaceable.
    try:
        previous = read_record(path, value["schema"])
    except FileNotFoundError:
        atomic_write_json(path, value)
    else:
        if previous != value:
            raise ManagerQueueError("MANAGER_ARCHIVE_CONFLICT", f"conflicting manager evidence: {path}")


def _read_archived_event(rt: Path, record: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    path = _archive_path(rt, record, event_id)
    try:
        envelope = read_record(path, ARCHIVE_SCHEMA)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", str(exc)) from exc
    event = envelope.get("event")
    if (envelope.get("epoch_id") != record["epoch_id"] or envelope.get("queue_id") != record["queue_id"]
            or not isinstance(event, dict) or event.get("event_id") != event_id
            or envelope.get("event_sha256") != _digest(event)):
        raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", f"invalid archived event: {path}")
    validate_queue_record({"events": [event]})
    if event["state"] not in {"COMPLETE", "BLOCKED"}:
        raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", "archive cannot contain actionable work")
    return event


def find_event(rt: Path, record: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    """Explicit historical lookup; ordinary queue reads remain hot-only."""
    return _find_event(record, event_id) or _read_archived_event(rt, record, event_id)


def find_dedup_event(rt: Path, record: dict[str, Any], dedup_key: str) -> dict[str, Any] | None:
    for event in record["events"]:
        if event.get("dedup_key") == dedup_key:
            return event
    path = _archive_root(rt, record) / "dedup" / (_digest(dedup_key) + ".json")
    try:
        pointer = read_record(path, "manager-event-dedup/v1")
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", str(exc)) from exc
    if (pointer.get("epoch_id") != record["epoch_id"] or pointer.get("queue_id") != record["queue_id"]
            or pointer.get("dedup_key") != dedup_key or not isinstance(pointer.get("event_id"), str)):
        raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", "invalid archived dedup identity")
    event = _read_archived_event(rt, record, pointer["event_id"])
    if event is None or event.get("dedup_key") != dedup_key:
        raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", "archived dedup target is missing or foreign")
    return event


def historical_events(rt: Path, record: dict[str, Any]) -> list[dict[str, Any]]:
    """Full evidence enumeration only for explicit provenance/close, never hooks."""
    validate_queue_record(record)
    events = {event["event_id"]: event for event in record["events"]}
    root = _archive_root(rt, record) / "events"
    if root.exists():
        for path in sorted(root.iterdir()):
            if path.name.startswith(".") and path.name.endswith(".lock"):
                continue
            envelope = read_record(path, ARCHIVE_SCHEMA)
            archived = envelope.get("event")
            event_id = archived.get("event_id") if isinstance(archived, dict) else None
            if not isinstance(event_id, str) or path != _archive_path(rt, record, event_id):
                raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", "archive filename differs from event identity")
            event = _read_archived_event(rt, record, event_id)
            if event_id in events and events[event_id] != event:
                raise ManagerQueueError("MANAGER_ARCHIVE_CONFLICT", "live/archive event bytes differ")
            events[event_id] = event
            if event.get("dedup_key") and find_dedup_event(rt, {**record, "events": []}, event["dedup_key"]) != event:
                raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", "archive dedup evidence is missing")
    archived = [event for event_id, event in events.items() if _find_event(record, event_id) is None]
    checksum = 0
    for event in archived:
        checksum ^= int(_digest(event), 16)
    if (len(archived) != record.get("archived_event_count", 0)
            or format(checksum, "064x") != record.get("archived_event_xor", "0" * 64)):
        raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", "archive inventory is missing or differs from durable hot manifest")
    for event in events.values():
        for digest in event.get("preserved_delivery_history", []):
            path = _archive_root(rt, record) / "legacy-delivery" / (digest + ".json")
            snapshot = read_record(path, "manager-delivery-history/v1")
            if (_digest(snapshot) != digest or snapshot.get("epoch_id") != record["epoch_id"]
                    or snapshot.get("queue_id") != record["queue_id"] or snapshot.get("event_id") != event["event_id"]):
                raise ManagerQueueError("MANAGER_ARCHIVE_INVALID", "legacy delivery evidence differs")
    return sorted(events.values(), key=lambda event: event["event_id"])


def _compact_terminal(rt: Path, record: dict[str, Any]) -> bool:
    terminal = [event for event in record["events"] if event["state"] in {"COMPLETE", "BLOCKED"}]
    for event in terminal:
        _immutable_json(_archive_path(rt, record, event["event_id"]), {
            "schema": ARCHIVE_SCHEMA, "epoch_id": record["epoch_id"], "queue_id": record["queue_id"],
            "event_sha256": _digest(event), "event": event})
        if event.get("dedup_key"):
            _immutable_json(_archive_root(rt, record) / "dedup" / (_digest(event["dedup_key"]) + ".json"), {
                "schema": "manager-event-dedup/v1", "epoch_id": record["epoch_id"], "queue_id": record["queue_id"],
                "dedup_key": event["dedup_key"], "event_id": event["event_id"]})
    if terminal:
        checksum = int(record.get("archived_event_xor", "0" * 64), 16)
        for event in terminal:
            checksum ^= int(_digest(event), 16)
        record["archived_event_count"] = record.get("archived_event_count", 0) + len(terminal)
        record["archived_event_xor"] = format(checksum, "064x")
        record["events"] = [event for event in record["events"] if event["state"] not in {"COMPLETE", "BLOCKED"}]
    return bool(terminal)


def _normalize_deliveries(rt: Path, record: dict[str, Any]) -> None:
    for event in record["events"]:
        history = event["delivery_history"]
        unique, seen = [], set()
        for receipt in history:
            key = _digest({field: receipt.get(field) for field in
                           ("outcome", "source", "queue_id", "event_id", "session_id", "binding_id", "provider_id")})
            if key not in seen:
                seen.add(key)
                unique.append(receipt)
        if len(unique) != len(history):
            snapshot = {"schema": "manager-delivery-history/v1", "epoch_id": record["epoch_id"],
                        "queue_id": record["queue_id"], "event_id": event["event_id"], "delivery_history": history}
            digest = _digest(snapshot)
            _immutable_json(_archive_root(rt, record) / "legacy-delivery" / (digest + ".json"), snapshot)
            event.setdefault("preserved_delivery_history", []).append(digest)
            event["delivery_history"] = unique


def _write_manager_queue(rt: Path, record: dict[str, Any]) -> None:
    """Replace the queue while the caller owns its queue lock."""
    path = manager_queue_path(rt)
    atomic_write_json(path, record)


def _update_manager_queue(
    rt: Path,
    mutate: Callable[[dict[str, Any]], tuple[Any, bool]],
    *, compact: bool = False,
) -> Any:
    """Validate, mutate, and replace the manager queue in one transaction."""
    path = manager_queue_path(rt)
    with runtime_admission_lock(rt), RecordLock(path):
        record = read_manager_queue(rt)
        if compact and _compact_terminal(rt, record):
            _write_manager_queue(rt, record)
        result, changed = mutate(record)
        if changed:
            _normalize_deliveries(rt, record)
            # Persist terminal state before immutable archive publication, so a
            # crash never regenerates a different terminal timestamp on retry.
            _write_manager_queue(rt, record)
            if compact and _compact_terminal(rt, record):
                _write_manager_queue(rt, record)
        return result


def promote_event(
    rt: Path,
    *,
    event_type: str,
    lane_id: str,
    run_id: str,
    summary: str,
    actionable_status: str | None = None,
    event_class: str | None = None,
    severity: str | None = None,
    data: dict[str, Any] | None = None,
    dedup_key: str | None = None,
) -> dict[str, Any]:
    """The monitor's sole-producer admission of one PENDING event."""
    if event_type not in EVENT_TYPES:
        raise ManagerQueueError("MANAGER_QUEUE_INVALID_EVENT_TYPE", event_type)
    admitted = False

    def mutate(record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        nonlocal admitted
        if dedup_key:
            existing = find_dedup_event(rt, record, dedup_key)
            if existing is not None:
                return existing, False
        event = {
            "event_id": new_id(),
            "type": event_type,
            "lane_id": lane_id,
            "run_id": run_id,
            "summary": summary,
            "state": "PENDING",
            "history": [{"state": "PENDING", "at": iso_utc()}],
            "delivery_history": [],
        }
        if actionable_status is not None:
            event["actionable_status"] = actionable_status
        if event_class:
            event["event_class"] = event_class
        if severity:
            if severity not in SEVERITIES:
                raise ManagerQueueError(
                    "MANAGER_QUEUE_INVALID_SEVERITY", severity
                )
            event["severity"] = severity
        if data:
            event["data"] = dict(data)
        if dedup_key:
            event["dedup_key"] = dedup_key
        record["events"].append(event)
        admitted = True
        return event, True

    event = _update_manager_queue(rt, mutate, compact=True)
    if admitted:
        append_detail(
            rt,
            "queue.manager.added",
            component="queue",
            added_event=event,
            queue_snapshot=read_manager_queue(rt),
        )
    return event


def acknowledge_event(rt: Path, event_id: str, *, root_session_id: str | None = None,
                      binding_id: str | None = None) -> dict[str, Any]:
    """ACK an unresolved event, retaining each prepared ROOT's exact scope."""
    scoped = root_session_id is not None or binding_id is not None
    if scoped and any(not isinstance(value, str) or not value.strip()
                      for value in (root_session_id, binding_id)):
        raise ManagerQueueError("MANAGER_ACK_SCOPE_INVALID", "ACK requires both ROOT session and binding")

    def mutate(record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        event = find_event(rt, record, event_id)
        if event is None:
            raise ManagerQueueError(
                MANAGER_ACK_EVENT_NOT_FOUND, f"event not found: {event_id}"
            )
        scope = {"queue_id": record["queue_id"], "event_id": event_id,
                 "session_id": root_session_id, "binding_id": binding_id,
                 "lane_id": event["lane_id"], "run_id": event["run_id"]}
        already_scoped = any(item.get("state") == "ACKNOWLEDGED"
                             and all(item.get(key) == value for key, value in scope.items())
                             for item in event["history"])
        if event["state"] != "PENDING" and (
                event["state"] != "ACKNOWLEDGED" or not scoped or already_scoped):
            raise ManagerQueueError(
                MANAGER_ACK_ALREADY_ACKNOWLEDGED,
                f"event {event_id} is already {event['state']}",
            )
        event["state"] = "ACKNOWLEDGED"
        receipt = {"state": "ACKNOWLEDGED", "at": iso_utc()}
        if scoped:
            receipt.update(scope)
        event["history"].append(receipt)
        return event, True

    return _update_manager_queue(rt, mutate, compact=True)


def close_event(
    rt: Path, event_id: str, outcome: str, summary: str | None = None
) -> dict[str, Any]:
    """ROOT closes an acknowledged event with COMPLETE or BLOCKED."""
    if outcome not in ("COMPLETE", "BLOCKED"):
        raise ManagerQueueError(MANAGER_CLOSE_INVALID_OUTCOME, f"invalid outcome: {outcome}")
    normalized_summary = summary.strip() if isinstance(summary, str) else ""
    if not normalized_summary:
        raise ManagerQueueError(
            MANAGER_CLOSE_SUMMARY_REQUIRED, "close summary must be nonblank"
        )
    def mutate(record: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        event = find_event(rt, record, event_id)
        if event is None:
            raise ManagerQueueError(
                MANAGER_ACK_EVENT_NOT_FOUND, f"event not found: {event_id}"
            )
        if event["state"] == "PENDING":
            raise ManagerQueueError(
                MANAGER_CLOSE_NOT_ACKNOWLEDGED,
                f"event {event_id} is not acknowledged",
            )
        if event["state"] in ("COMPLETE", "BLOCKED"):
            raise ManagerQueueError(
                MANAGER_CLOSE_ALREADY_CLOSED,
                f"event {event_id} is already {event['state']}",
            )
        event["state"] = outcome
        event["history"].append(
            {"state": outcome, "at": iso_utc(), "summary": normalized_summary}
        )
        event["summary"] = normalized_summary
        return event, True

    return _update_manager_queue(rt, mutate, compact=True)


def append_delivery_history(
    rt: Path, event_id: str, *, source: str = "hook", queue_id: str | None = None,
    session_id: str | None = None, binding_id: str | None = None,
    provider_id: str | None = None,
) -> bool:
    """Publish at most one unresolved receipt for the exact observed scope.

    False means no new receipt: absent/terminal, foreign queue, incomplete scope,
    or repeated delivery. It must not cause a local DELIVERED log entry.
    """
    if any(not isinstance(value, str) or not value.strip() for value in
           (session_id, binding_id)):
        return False
    def mutate(record: dict[str, Any]) -> tuple[bool, bool]:
        event = _find_event(record, event_id)
        if (event is None or event["state"] not in {"PENDING", "ACKNOWLEDGED"}
                or (queue_id is not None and queue_id != record["queue_id"])):
            return False, False
        receipt = {"outcome": "DELIVERED", "source": source, "event_id": event_id,
                   "queue_id": record["queue_id"], "session_id": session_id,
                   "binding_id": binding_id, "provider_id": provider_id or binding_id}
        # Old receipts lacked provider_id: binding already identified provider.
        for previous in event["delivery_history"]:
            if all((previous.get(key, previous.get("binding_id")) if key == "provider_id" else previous.get(key)) == value
                   for key, value in receipt.items()):
                return False, False
        event["delivery_history"].append({**receipt, "at": iso_utc()})
        return True, True
    return bool(_update_manager_queue(rt, mutate))


def append_watch_delivery(
    rt: Path,
    event_id: str,
    *,
    root_session_id: str,
    binding_id: str,
) -> bool:
    """Record one idle-watch delivery unless this ROOT session already saw it."""

    def mutate(record: dict[str, Any]) -> tuple[bool, bool]:
        event = _find_event(record, event_id)
        if event is None or event.get("state") not in {"PENDING", "ACKNOWLEDGED"}:
            return False, False
        queue_id = record.get("queue_id")
        history = event.setdefault("delivery_history", [])
        for receipt in history:
            if (
                receipt.get("source") == "watch"
                and receipt.get("queue_id") == queue_id
                and receipt.get("event_id") == event_id
                and receipt.get("session_id") == root_session_id
                and receipt.get("binding_id") == binding_id
            ):
                return False, False
        history.append(
            {
                "outcome": "DELIVERED",
                "source": "watch",
                "event_id": event_id,
                "queue_id": queue_id,
                "session_id": root_session_id,
                "binding_id": binding_id,
                "at": iso_utc(),
            }
        )
        return True, True

    return bool(_update_manager_queue(rt, mutate))


def _find_event(record: dict[str, Any], event_id: str) -> dict[str, Any] | None:
    for event in record.get("events", []):
        if event.get("event_id") == event_id:
            return event
    return None


def read_lane_inbox(worktree: Path) -> dict[str, Any]:
    path = worktree / ".agent-workspace" / "QUEUE.json"
    try:
        record = json.loads(anchored_read(worktree, path.relative_to(worktree)))
        if not isinstance(record, dict):
            raise ValueError("lane inbox is not an object")
        require_schema(record, LANE_INBOX_SCHEMA, path)
        if (not isinstance(record.get("lane_id"), str) or not record["lane_id"]
                or not isinstance(record.get("run_id"), str) or not record["run_id"]
                or not isinstance(record.get("assignments"), list)
                or any(not isinstance(item, dict) or item.get("lane_id") != record["lane_id"]
                       or item.get("run_id") != record["run_id"]
                       or item.get("state") not in ASSIGNMENT_STATES
                       for item in record["assignments"])):
            raise ValueError("lane inbox identity or assignments are invalid")
        return record
    except FileNotFoundError as exc:
        raise ManagerQueueError("LANE_INBOX_MISSING", f"lane inbox missing: {path}") from exc
    except (OSError, ValueError) as exc:
        raise ManagerQueueError("LANE_INBOX_INVALID", str(exc)) from exc


def write_lane_inbox(worktree: Path, record: dict[str, Any]) -> None:
    path = worktree / ".agent-workspace" / "QUEUE.json"
    output = PreparedOutputTransaction(worktree)
    output.prepare()
    output.admit(path)
    output.ensure_parent(path)
    with RecordLock(path, root=worktree):
        output.atomic_json(path, record)


def append_assignment(
    rt: Path, lane: dict[str, Any], prompt: str
) -> dict[str, Any]:
    """ROOT appends one PENDING assignment to a running managed lane's inbox."""
    from .lanes import lane_operation_lock, read_lane, require_same_run
    from .setup import read_runtime_state
    from .processes import identity_matches
    try:
        with runtime_admission_lock(rt):
            state = read_runtime_state(rt)
            marker = read_current_epoch(rt)
            if not state or state["state"] != "OPEN" or not marker:
                raise ValueError("lane assignments require the current OPEN runtime")
            epoch_id = marker["epoch_id"]
            with lane_operation_lock(rt, epoch_id, lane["lane_id"]):
                current = read_lane(rt, epoch_id, lane["lane_id"])
                require_same_run(current, lane)
                process = current.get("process") or {}
                if (current.get("lifecycle") != "running" or not current.get("incoming_queue_path")
                        or not identity_matches(process.get("pid"), process.get("creation_time"))):
                    raise ValueError("managed lane owner is no longer running")
                worktree = Path(current["worktree_path"]).absolute()
                path = worktree / ".agent-workspace" / "QUEUE.json"
                if Path(current["incoming_queue_path"]).absolute() != path:
                    raise ValueError("lane inbox path differs from its assigned worktree")
                output = PreparedOutputTransaction(worktree)
                output.prepare()
                if tuple(current.get("worktree_identity", ())) != output.root_identity:
                    raise ValueError("lane worktree identity changed or is missing")
                output.admit(path)
                with RecordLock(path, root=worktree):
                    expected = capture_target(worktree, path.relative_to(worktree))
                    inbox = read_lane_inbox(worktree)
                    if not expected.present or json.loads(expected.content) != inbox:
                        raise ValueError("lane inbox changed during the assignment read")
                    if (inbox["lane_id"], inbox["run_id"]) != (lane["lane_id"], lane["run_id"]):
                        raise ValueError("lane inbox identity is stale or foreign")
                    assignment = {
                        "event_id": new_id(), "lane_id": lane["lane_id"], "run_id": lane["run_id"],
                        "prompt": prompt, "created_at": iso_utc(), "state": "PENDING",
                        "history": [{"state": "PENDING", "at": iso_utc()}],
                    }
                    inbox["assignments"].append(assignment)
                    require_same_run(read_lane(rt, epoch_id, lane["lane_id"]), lane)
                    output.atomic_json(path, inbox, expected=expected)
    except ManagerQueueError:
        raise
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        raise ManagerQueueError(SEND_LANE_WRITE_FAILED, str(exc)) from exc
    append_detail(
        rt,
        "queue.worker.added",
        component="queue",
        lane_id=lane["lane_id"],
        run_id=lane["run_id"],
        prompt=prompt,
        added_assignment=assignment,
        queue_snapshot=inbox,
    )
    return assignment
