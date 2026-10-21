"""Real private monitor/epoch fixtures; mocked preparation validator only.

Native strings here exercise cooperative authority, not provider invocation.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from orchestrator_harness import manager_ownership as ownership, operator_launch, root_hook_wrapper, root_session, shutdown
from orchestrator_harness.config import ConfigError
from orchestrator_harness.core import content_hash
from orchestrator_harness.epochs import close_epoch
from orchestrator_harness.records import atomic_write_json
from orchestrator_harness.setup import _materialized_binding, set_runtime_state
from orchestrator_harness.tests.support import PreparedRootFixture, write_json


def contract():
    preferences = {"provider": "codex", "model": "fixture-model", "provider_options": {"reasoning_effort": "high", "service_tier": "normal"}}
    return {"schema": "harness-outcome-workflow/v1", "original_prompt": "Implement one bounded outcome and preserve it after integration.",
            "constraints": [], "outcomes": [{"id": "outcome", "description": "The feature works.", "acceptance_criteria": ["Feature regression passes."], "assignment_ids": ["assignment"]}],
            "assignments": [{"id": "assignment", "task": "Implement the feature.", "goal": "Feature regression passes.", "outcome_ids": ["outcome"], "scope": ["Feature implementation and regression."], "exclusions": [], "dependencies": [], "acceptance_criteria": ["Feature regression passes."], "deliverables": ["Code and tests."], "checks": ["Run feature regression."], **deepcopy(preferences)}],
            "integration_criteria": [{"id": "integrated", "description": "Regression passes on unified target.", "outcome_ids": ["outcome"], "checks": ["Run unified regression."]}],
            "coordinator": deepcopy(preferences), "auditor": deepcopy(preferences)}


class ManagerOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.fixture = PreparedRootFixture(self)
        self.config = self.fixture.config
        self.session_path = root_session.root_session_path(self.config)
        self.original_session = self.session_path.read_bytes()
        self.contract_path = self.fixture.home / "contract.json"
        write_json(self.contract_path, contract())
        environment = patch.dict(os.environ, {**self.fixture.environment, "CODEX_THREAD_ID": "planner"}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        # The actual monitor and runtime readiness are never mocked. The fixture
        # intentionally has no fabricated pre-launch receipt.
        self.validator_patch = patch("scripts.prepare_root_launch.validate_prepared_root", return_value={})
        self.validator = self.validator_patch.start()
        self.addCleanup(self.validator_patch.stop)

    def offer(self):
        return ownership.offer_handoff(self.config, to_native_session_id="coordinator", contract_path=self.contract_path)

    def accept(self, offer):
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "coordinator"}):
            return ownership.accept_handoff(self.config, offer_id=offer["offer_id"], contract_sha256=offer["contract_sha256"])

    def binding(self):
        path = self.fixture.manager / ".codex/orchestrator-harness-binding.json"
        write_json(path, _materialized_binding({"schema": "harness-hook-binding/v1", "role": "root", "provider_id": "codex", "harness_root": None, "runtime_root": None, "liveness_path": ".agent-workspace/root-hook-liveness.jsonl", "delivery_receipt_path": ".agent-workspace/root-hook-delivery.jsonl"}, self.fixture.harness, self.fixture.rt))
        return path

    def test_transfer_preserves_prepared_session_and_exclusively_admits_target(self):
        # Exercise the stronger case: prepared ROOT already bound to planner.
        root_session.bind_native_root_session(self.config, run_id=self.fixture.session["run_id"], session_id=self.fixture.session["session_id"], native_session_id="planner")
        before = self.session_path.read_bytes()
        offered = self.offer()
        self.assertEqual("MANAGER_HANDOFF_OFFERED", offered["code"])
        self.assertEqual((self.fixture.session["session_id"], "codex"), root_session.resolve_root_session(self.config))
        accepted = self.accept(offered)
        self.assertEqual(2, accepted["generation"])
        self.assertEqual(before, self.session_path.read_bytes())
        for native in ("planner", "worker", ""):
            with self.subTest(native=native), patch.dict(os.environ, {"CODEX_THREAD_ID": native}), self.assertRaises(ConfigError):
                root_session.resolve_root_session(self.config)
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "coordinator"}):
            self.assertEqual((self.fixture.session["session_id"], "codex"), root_session.resolve_root_session(self.config))
        self.assertEqual(2, self.validator.call_count)

    def test_offer_initializes_native_epoch_before_any_coding_lane(self):
        from orchestrator_harness.epochs import read_active_lanes, read_current_epoch
        close_epoch(self.fixture.rt, self.fixture.epoch["epoch_id"])
        self.assertIsNone(read_current_epoch(self.fixture.rt))
        before = self.session_path.read_bytes()
        offered = self.offer()
        epoch = read_current_epoch(self.fixture.rt)
        self.assertIsNotNone(epoch)
        self.assertNotEqual(self.fixture.epoch["epoch_id"], epoch["epoch_id"])
        self.assertEqual([], read_active_lanes(self.fixture.rt, epoch["epoch_id"]))
        self.assertEqual(before, self.session_path.read_bytes())
        self.assertEqual("MANAGER_HANDOFF_ACTIVE", self.accept(offered)["code"])

    def test_empty_transferred_epoch_remains_available_for_independent_audit(self):
        from orchestrator_harness import launch
        from orchestrator_harness.epochs import read_current_epoch
        self.accept(self.offer())
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "coordinator"}):
            launch._maybe_close_epoch(self.fixture.rt, self.fixture.epoch["epoch_id"], config=self.config)
            self.assertEqual(self.fixture.epoch["epoch_id"], read_current_epoch(self.fixture.rt)["epoch_id"])
            self.assertEqual((self.fixture.session["session_id"], "codex"), root_session.resolve_root_session(self.config))
            with ownership.manager_operation(self.config), patch.object(shutdown, "find_harness_root", return_value=self.fixture.harness):
                self.assertTrue(shutdown.run_shutdown()["ok"])
        shutdown.prove_runtime_closed(self.fixture.rt, self.fixture.product, self.fixture.harness)

    def test_no_identity_same_target_and_worker_refuse_without_authority_publication(self):
        for environment, target in (({"CODEX_THREAD_ID": ""}, "coordinator"), ({}, "planner"), ({"HARNESS_LANE_ID": "coding"}, "coordinator")):
            with self.subTest(environment=environment), patch.dict(os.environ, environment), self.assertRaises(ConfigError):
                ownership.offer_handoff(self.config, to_native_session_id=target, contract_path=self.contract_path)
        self.assertFalse(ownership.ownership_path(self.config).exists())
        self.assertEqual(self.original_session, self.session_path.read_bytes())

    def test_accept_requires_target_exact_offer_and_contract_then_refuses_duplicate(self):
        offered = self.offer()
        for native, offer_id, digest in (("planner", offered["offer_id"], offered["contract_sha256"]), ("coordinator", "stale", offered["contract_sha256"]), ("coordinator", offered["offer_id"], "wrong")):
            with self.subTest(native=native, offer_id=offer_id), patch.dict(os.environ, {"CODEX_THREAD_ID": native}), self.assertRaises(ConfigError):
                ownership.accept_handoff(self.config, offer_id=offer_id, contract_sha256=digest)
        self.accept(offered)
        with self.assertRaisesRegex(ConfigError, "MANAGER_HANDOFF_STALE"):
            self.accept(offered)

    def test_contract_is_snapshotted_not_reread_from_mutable_input(self):
        offered = self.offer()
        write_json(self.contract_path, {"changed": True})
        self.accept(offered)
        record = ownership.read_ownership(self.config, self.fixture.session)
        self.assertEqual(contract(), record["contract"])
        self.assertEqual(contract(), json.loads(Path(offered["contract_path"]).read_text()))

    def test_damaged_or_stale_owner_records_fail_closed(self):
        self.accept(self.offer())
        path = ownership.ownership_path(self.config)
        original = json.loads(path.read_text())
        for field, value in (("config_identity", "stale"), ("epoch_id", "different"), ("generation", 99), ("contract_sha256", "bad"), ("content_hash", "bad")):
            changed = {**original, field: value}
            if field != "content_hash":
                changed["content_hash"] = content_hash(changed)
            atomic_write_json(path, changed)
            with self.subTest(field=field), patch.dict(os.environ, {"CODEX_THREAD_ID": "coordinator"}), self.assertRaises(ConfigError):
                root_session.resolve_root_session(self.config)
        atomic_write_json(path, original)

    def test_genuine_preparation_failure_blocks_offer_and_accept(self):
        self.validator.side_effect = ValueError("genuine receipt missing")
        with self.assertRaisesRegex(ValueError, "genuine receipt"):
            self.offer()
        self.assertFalse(ownership.ownership_path(self.config).exists())
        self.validator.side_effect = None
        offered = self.offer()
        self.validator.side_effect = ValueError("genuine receipt stale")
        with self.assertRaisesRegex(ValueError, "genuine receipt"):
            self.accept(offered)
        self.assertEqual("OFFERED", ownership.read_ownership(self.config, self.fixture.session)["state"])

    def test_cross_provider_and_worker_accept_are_not_supported(self):
        data = contract()
        data["coordinator"] = {"provider": "claude-code", "model": "fixture-model", "provider_options": {"effort": "high"}}
        write_json(self.contract_path, data)
        with self.assertRaisesRegex(ConfigError, "MANAGER_HANDOFF_PROVIDER"):
            self.offer()
        write_json(self.contract_path, contract())
        offered = self.offer()
        with patch.dict(os.environ, {"HARNESS_LANE_ID": "coding"}), self.assertRaisesRegex(ConfigError, "MANAGER_HANDOFF_WORKER"):
            self.accept(offered)

    def test_registered_coding_native_session_cannot_receive_authority_without_worker_env(self):
        from orchestrator_harness.lanes import write_lane
        write_lane(self.fixture.rt, self.fixture.epoch["epoch_id"], "coding", {
            "lifecycle": "retired", "run_id": "coding-run", "provider": {"id": "codex"},
            "session": {"session_id": "coordinator"}})
        with self.assertRaisesRegex(ConfigError, "MANAGER_HANDOFF_WORKER"):
            self.offer()
        self.assertFalse(ownership.ownership_path(self.config).exists())
        # A target which only becomes a known lane after the offer still cannot
        # accept. No invented worker environment variables are involved.
        path = self.fixture.rt / "epochs" / self.fixture.epoch["epoch_id"] / "lanes" / "coding" / "lane.json"
        value = json.loads(path.read_text())
        value["session"]["session_id"] = "different-worker"
        atomic_write_json(path, value)
        offered = self.offer()
        value["session"]["session_id"] = "coordinator"
        atomic_write_json(path, value)
        with self.assertRaisesRegex(ConfigError, "MANAGER_HANDOFF_WORKER"):
            self.accept(offered)

    def test_public_mutations_watch_and_shutdown_reject_retired_planner(self):
        self.accept(self.offer())
        parser = operator_launch._build_parser()
        for argv in (("harness", "shutdown"), ("health", "monitor-recover"), ("watch", "--until-actionable", "--timeout", "0"), ("manager", "acknowledge", "--event-id", "event"), ("lane", "launch", "--lane-id", "coding")):
            with self.subTest(argv=argv), patch.object(operator_launch, "find_harness_root", return_value=self.fixture.harness), patch.object(operator_launch, "_dispatch_owned") as dispatch:
                with self.assertRaisesRegex(ConfigError, "MANAGER_NOT_OWNER"):
                    operator_launch._dispatch(parser.parse_args(argv))
                dispatch.assert_not_called()
        with patch.object(operator_launch, "find_harness_root", return_value=self.fixture.harness), patch.object(operator_launch, "_dispatch_owned", return_value={"ok": True}) as dispatch:
            operator_launch._dispatch(parser.parse_args(["scan", "--no-write"]))
            dispatch.assert_called_once()

    def test_retired_planner_hooks_block_open_without_delivery_but_allow_proven_closed(self):
        binding = self.binding()
        self.accept(self.offer())
        with patch.object(root_hook_wrapper, "dispatch") as dispatch, patch.object(root_hook_wrapper, "append_delivery_history") as delivered:
            self.assertEqual("block", root_hook_wrapper.run("codex", "stop", binding)["decision"])
            self.assertFalse(root_hook_wrapper.run("codex", "post-tool-use", binding)["continue"])
            dispatch.assert_not_called()
            delivered.assert_not_called()
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "coordinator"}), patch.object(shutdown, "find_harness_root", return_value=self.fixture.harness):
            with ownership.manager_operation(self.config):
                self.assertTrue(shutdown.run_shutdown()["ok"])
            with ownership.manager_operation(self.config):
                self.assertTrue(shutdown.run_shutdown()["ok"])
        shutdown.prove_runtime_closed(self.fixture.rt, self.fixture.product, self.fixture.harness)
        self.assertEqual({}, root_hook_wrapper.run("codex", "stop", binding))
        self.assertEqual({}, root_hook_wrapper.run("codex", "post-tool-use", binding))
        with patch.object(shutdown, "prove_runtime_closed", side_effect=RuntimeError("cleanup unproven")):
            self.assertEqual("block", root_hook_wrapper.run("codex", "stop", binding)["decision"])

    def test_owner_can_recover_after_epoch_marker_removed_during_shutdown(self):
        self.accept(self.offer())
        set_runtime_state(self.fixture.rt, "SHUTTING_DOWN")
        close_epoch(self.fixture.rt, self.fixture.epoch["epoch_id"])
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "coordinator"}):
            self.assertEqual((self.fixture.session["session_id"], "codex"), root_session.resolve_root_session(self.config))
        with self.assertRaisesRegex(ConfigError, "MANAGER_NOT_OWNER"):
            root_session.resolve_root_session(self.config)

    def test_accept_waits_for_inflight_manager_operation_then_revokes_old_owner(self):
        offered = self.offer()
        entered = threading.Event()
        released = threading.Event()
        results = []
        def accept():
            entered.set()
            results.append(ownership.accept_handoff(self.config, offer_id=offered["offer_id"], contract_sha256=offered["contract_sha256"]))
            released.set()
        # Both threads share process env; operation was admitted as planner
        # before target identity is observed in the accepting thread.
        operation = ownership.manager_operation(self.config)
        operation.__enter__()
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "coordinator"}):
            try:
                worker = threading.Thread(target=accept)
                worker.start()
                self.assertTrue(entered.wait(2))
                self.assertFalse(released.wait(.15), "accept must not race an admitted manager operation")
                self.assertEqual("OFFERED", ownership.read_ownership(self.config, self.fixture.session)["state"])
            finally:
                operation.__exit__(None, None, None)
            worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertEqual("MANAGER_HANDOFF_ACTIVE", results[0]["code"])
        with self.assertRaisesRegex(ConfigError, "MANAGER_NOT_OWNER"):
            with ownership.manager_operation(self.config):
                self.fail("retired planner entered a new manager operation")


if __name__ == "__main__":
    unittest.main()
