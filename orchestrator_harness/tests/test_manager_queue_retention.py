"""Real queue/filesystem retention tests; no model/provider processes."""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from orchestrator_harness import manager_queue as q
from orchestrator_harness.epochs import current_epoch_path, manager_queue_path
from orchestrator_harness.records import atomic_write_json, read_record


class QueueRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="manager-retention-")
        self.addCleanup(self.temp.cleanup)
        self.rt = Path(self.temp.name)
        atomic_write_json(current_epoch_path(self.rt), {
            "schema": "current-epoch/v1", "epoch_id": "epoch", "queue_id": "queue"})
        atomic_write_json(manager_queue_path(self.rt), {
            "schema": "manager-queue/v1", "epoch_id": "epoch", "queue_id": "queue", "events": []})

    def event(self, dedup=None):
        return q.promote_event(self.rt, event_type="LANE_STATUS_CHANGED", lane_id="lane", run_id="run",
                               summary="notice", dedup_key=dedup, data={"notice_sha256": "original"})

    def finish(self, event, outcome="COMPLETE"):
        q.acknowledge_event(self.rt, event["event_id"], root_session_id="session", binding_id="codex")
        return q.close_event(self.rt, event["event_id"], outcome, "handled")

    def test_hundred_receipts_are_idempotent_and_exact_scope(self):
        event = self.event()
        scope = {"session_id": "session", "binding_id": "codex", "provider_id": "codex", "queue_id": "queue"}
        self.assertTrue(q.append_delivery_history(self.rt, event["event_id"], **scope))
        initial = manager_queue_path(self.rt).read_bytes()
        for _ in range(100):
            self.assertFalse(q.append_delivery_history(self.rt, event["event_id"], **scope))
        self.assertEqual(initial, manager_queue_path(self.rt).read_bytes())
        self.assertFalse(q.append_delivery_history(self.rt, event["event_id"], **{**scope, "queue_id": "other"}))
        self.assertFalse(q.append_delivery_history(self.rt, "missing", **scope))
        self.assertFalse(q.append_delivery_history(self.rt, event["event_id"]))
        self.assertEqual(initial, manager_queue_path(self.rt).read_bytes())
        self.assertTrue(q.append_delivery_history(self.rt, event["event_id"], **{**scope, "session_id": "fresh"}))
        self.assertTrue(q.append_delivery_history(self.rt, event["event_id"], **{**scope, "provider_id": "claude-code"}))
        self.assertTrue(q.append_watch_delivery(self.rt, event["event_id"], root_session_id="session", binding_id="codex"))
        self.assertFalse(q.append_watch_delivery(self.rt, event["event_id"], root_session_id="session", binding_id="codex"))
        self.finish(event)
        initial = manager_queue_path(self.rt).read_bytes()
        for _ in range(10):
            self.assertFalse(q.append_delivery_history(self.rt, event["event_id"], **scope))
        self.assertEqual(initial, manager_queue_path(self.rt).read_bytes())

    def test_many_terminal_events_bound_hot_queue_without_losing_history(self):
        pending = [self.event() for _ in range(12)]
        finished = []
        for number in range(40):
            event = self.event(f"notice-{number}")
            finished.append(self.finish(event, "BLOCKED" if number % 2 else "COMPLETE"))
            self.assertEqual(12, len(q.read_manager_queue(self.rt)["events"]))
        hot = q.read_manager_queue(self.rt)
        self.assertEqual(40, hot["archived_event_count"])
        self.assertEqual(52, len(q.historical_events(self.rt, hot)))
        for event in finished:
            self.assertEqual(event, q.find_event(self.rt, hot, event["event_id"]))
            self.assertEqual(event, self.event(event["dedup_key"]))
        self.assertEqual(12, len(q.read_manager_queue(self.rt)["events"]))
        with self.assertRaises(q.ManagerQueueError) as raised:
            q.close_event(self.rt, finished[0]["event_id"], "COMPLETE", "retry")
        self.assertEqual(q.MANAGER_CLOSE_ALREADY_CLOSED, raised.exception.code)
        with self.assertRaises(q.ManagerQueueError) as raised:
            q.acknowledge_event(self.rt, finished[0]["event_id"])
        self.assertEqual(q.MANAGER_ACK_ALREADY_ACKNOWLEDGED, raised.exception.code)
        self.assertEqual({event["event_id"] for event in pending}, {event["event_id"] for event in hot["events"]})

    def test_legacy_delivery_duplicates_preserved_before_normalization(self):
        event = self.event()
        hot = q.read_manager_queue(self.rt)
        receipt = {"source": "hook", "outcome": "DELIVERED", "event_id": event["event_id"],
                   "queue_id": "queue", "session_id": "session", "binding_id": "codex", "at": "old"}
        original = [{**receipt, "at": str(number)} for number in range(101)]
        hot["events"][0]["delivery_history"] = original
        atomic_write_json(manager_queue_path(self.rt), hot)
        q.acknowledge_event(self.rt, event["event_id"])
        hot = q.read_manager_queue(self.rt)
        normalized = hot["events"][0]
        self.assertEqual(1, len(normalized["delivery_history"]))
        digest, = normalized["preserved_delivery_history"]
        snapshot = read_record(q._archive_root(self.rt, hot) / "legacy-delivery" / (digest + ".json"),
                               "manager-delivery-history/v1")
        self.assertEqual(original, snapshot["delivery_history"])
        self.assertEqual(1, len(q.historical_events(self.rt, hot)))
        q.close_event(self.rt, event["event_id"], "COMPLETE", "done")
        self.assertEqual(1, len(q.historical_events(self.rt, q.read_manager_queue(self.rt))))

    def test_archive_failure_preserves_durable_terminal_then_recovers(self):
        event = self.event("dedup")
        q.acknowledge_event(self.rt, event["event_id"])
        with patch.object(q, "_immutable_json", side_effect=OSError("publication interrupted")):
            with self.assertRaises(OSError):
                q.close_event(self.rt, event["event_id"], "COMPLETE", "done")
        durable = q.read_manager_queue(self.rt)["events"][0]
        self.assertEqual("COMPLETE", durable["state"])
        self.assertEqual(durable, self.event("dedup"))
        hot = q.read_manager_queue(self.rt)
        self.assertEqual([], hot["events"])
        self.assertEqual(durable, q.find_event(self.rt, hot, event["event_id"]))

    def test_prune_failure_replays_identical_evidence_without_new_timestamp(self):
        event = self.event("dedup")
        q.acknowledge_event(self.rt, event["event_id"])
        write = q._write_manager_queue
        def fail_prune(rt, record):
            if not record["events"]:
                raise OSError("prune interrupted")
            write(rt, record)
        with patch.object(q, "_write_manager_queue", side_effect=fail_prune):
            with self.assertRaises(OSError):
                q.close_event(self.rt, event["event_id"], "COMPLETE", "done")
        durable = q.read_manager_queue(self.rt)["events"][0]
        self.assertEqual(durable, self.event("dedup"))
        self.assertEqual([], q.read_manager_queue(self.rt)["events"])
        self.assertEqual(1, len(q.historical_events(self.rt, q.read_manager_queue(self.rt))))

    def test_dedup_publication_failure_recovers_before_pruning(self):
        event = self.event("dedup")
        q.acknowledge_event(self.rt, event["event_id"])
        publish = q._immutable_json
        def fail_pointer(path, value):
            if value["schema"] == "manager-event-dedup/v1":
                raise OSError("pointer interrupted")
            publish(path, value)
        with patch.object(q, "_immutable_json", side_effect=fail_pointer):
            with self.assertRaises(OSError):
                q.close_event(self.rt, event["event_id"], "COMPLETE", "done")
        self.assertEqual("COMPLETE", q.read_manager_queue(self.rt)["events"][0]["state"])
        self.assertEqual(event["event_id"], self.event("dedup")["event_id"])
        self.assertEqual([], q.read_manager_queue(self.rt)["events"])

    def test_conflicting_archive_never_prunes_live_evidence(self):
        event = self.event()
        q.acknowledge_event(self.rt, event["event_id"])
        hot = q.read_manager_queue(self.rt)
        path = q._archive_path(self.rt, hot, event["event_id"])
        atomic_write_json(path, {"schema": q.ARCHIVE_SCHEMA, "event": {"wrong": "evidence"}})
        with self.assertRaises(q.ManagerQueueError):
            q.close_event(self.rt, event["event_id"], "COMPLETE", "done")
        self.assertEqual("COMPLETE", q.read_manager_queue(self.rt)["events"][0]["state"])
        self.assertEqual({"wrong": "evidence"}, read_record(path, q.ARCHIVE_SCHEMA)["event"])

    def test_missing_malformed_foreign_archive_cannot_prove_closed(self):
        from orchestrator_harness.shutdown import _unresolved_manager_obligations, ShutdownError
        event = self.finish(self.event("dedup"))
        hot = q.read_manager_queue(self.rt)
        path = q._archive_path(self.rt, hot, event["event_id"])
        original = path.read_bytes()
        path.unlink()
        with self.assertRaises(ShutdownError):
            _unresolved_manager_obligations(self.rt)
        path.write_bytes(original)
        envelope = read_record(path, q.ARCHIVE_SCHEMA)
        envelope["queue_id"] = "foreign"
        atomic_write_json(path, envelope)
        with self.assertRaises(ShutdownError):
            _unresolved_manager_obligations(self.rt)
        path.write_text("not json")
        with self.assertRaises(ShutdownError):
            _unresolved_manager_obligations(self.rt)

    def test_missing_dedup_pointer_cannot_prove_complete_history(self):
        event = self.finish(self.event("dedup"))
        hot = q.read_manager_queue(self.rt)
        pointer = q._archive_root(self.rt, hot) / "dedup" / (q._digest("dedup") + ".json")
        pointer.unlink()
        original = manager_queue_path(self.rt).read_bytes()
        with self.assertRaises(q.ManagerQueueError):
            q.historical_events(self.rt, hot)
        self.assertEqual(original, manager_queue_path(self.rt).read_bytes())
        self.assertEqual(event, q.find_event(self.rt, hot, event["event_id"]))

    def test_new_producer_dedup_after_history_does_not_enumerate_archive(self):
        self.finish(self.event("prior"))
        with patch.object(q, "historical_events", side_effect=AssertionError("unexpected producer full scan")):
            event = self.event("new")
            self.assertEqual("PENDING", event["state"])
            self.assertEqual(event, self.event("new"))
            prior = self.event("prior")
            self.assertEqual("COMPLETE", prior["state"])

    def close_fixture(self, *, lifecycle="active"):
        from orchestrator_harness.epochs import epoch_dir
        directory = epoch_dir(self.rt, "epoch")
        atomic_write_json(directory / "epoch-state.json", {"schema": "epoch-state/v1", "epoch_id": "epoch",
                          "lifecycle": lifecycle, "lane_mode": "managed", "queue_id": "queue", "closing_queue_id": "queue"})
        atomic_write_json(directory / "active-lanes.json", {"schema": "active-lanes/v1", "epoch_id": "epoch", "lanes": []})
        return directory

    def test_interrupted_new_close_retains_full_archive_and_retries_exact_bytes(self):
        from orchestrator_harness import epochs
        directory = self.close_fixture()
        first = self.finish(self.event("first"))
        second = self.finish(self.event("second"))
        actual_write = epochs.atomic_write_json
        def interrupt_final(path, record):
            if record.get("schema") == "epoch-state/v1" and record.get("lifecycle") == "closed":
                raise OSError("interrupted final write")
            actual_write(path, record)
        with patch.object(epochs, "atomic_write_json", side_effect=interrupt_final):
            with self.assertRaises(OSError):
                epochs.close_epoch(self.rt, "epoch")
        snapshot_path = directory / "CLOSED_MANAGER_QUEUE.json"
        snapshot_bytes = snapshot_path.read_bytes()
        snapshot = read_record(snapshot_path, "manager-queue/v1")
        self.assertEqual({first["event_id"], second["event_id"]}, {event["event_id"] for event in snapshot["events"]})
        epochs.close_epoch(self.rt, "epoch")
        self.assertEqual(snapshot_bytes, snapshot_path.read_bytes())
        self.assertEqual("closed", epochs.read_epoch_state(self.rt, "epoch")["lifecycle"])

    def test_interrupted_legacy_close_preserves_unsorted_snapshot_without_new_fields(self):
        from orchestrator_harness import epochs
        directory = self.close_fixture(lifecycle="closing")
        events = [self.finish(self.event()), self.finish(self.event())]
        # Reconstruct a legitimate saved pre-retention closure: full terminal hot
        # history, no archive inventory fields, arbitrary original event order.
        for path in (q._archive_root(self.rt, q.read_manager_queue(self.rt)) / "events").iterdir():
            path.unlink()
        legacy = {"schema": "manager-queue/v1", "epoch_id": "epoch", "queue_id": "queue",
                  "events": sorted(events, key=lambda event: event["event_id"], reverse=True)}
        atomic_write_json(manager_queue_path(self.rt), legacy)
        snapshot_path = directory / "CLOSED_MANAGER_QUEUE.json"
        atomic_write_json(snapshot_path, legacy)
        original = snapshot_path.read_bytes()
        current_epoch_path(self.rt).unlink()
        epochs.close_epoch(self.rt, "epoch")
        self.assertEqual(original, snapshot_path.read_bytes())
        self.assertEqual("closed", epochs.read_epoch_state(self.rt, "epoch")["lifecycle"])

    def test_closed_snapshot_conflicting_event_stops_retry_without_rewrite(self):
        from orchestrator_harness import epochs
        directory = self.close_fixture(lifecycle="closing")
        self.finish(self.event())
        snapshot = q.read_manager_queue(self.rt)
        snapshot["events"] = q.historical_events(self.rt, snapshot)
        snapshot["archived_event_count"] = 0
        snapshot["archived_event_xor"] = "0" * 64
        snapshot["events"][0]["summary"] = "foreign closed decision"
        path = directory / "CLOSED_MANAGER_QUEUE.json"
        atomic_write_json(path, snapshot)
        original = path.read_bytes()
        with self.assertRaises((epochs.EpochError, q.ManagerQueueError)):
            epochs.close_epoch(self.rt, "epoch")
        self.assertEqual(original, path.read_bytes())

    def test_no_full_history_enumeration_on_hook_or_watch(self):
        event = self.event()
        with patch.object(q, "historical_events", side_effect=AssertionError("unexpected full scan")):
            self.assertTrue(q.append_delivery_history(self.rt, event["event_id"], session_id="session", binding_id="codex"))
            self.assertTrue(q.append_watch_delivery(self.rt, event["event_id"], root_session_id="session", binding_id="codex"))


if __name__ == "__main__":
    unittest.main()
