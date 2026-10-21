"""Read-only hook contract tests; mocks are NOT live provider proof."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from orchestrator_harness import prompt_optin as optin

SOURCE = Path(__file__).resolve().parents[2]


class PromptOptInTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="prompt-optin-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.harness, self.workspace = self.base / "harness", self.base / "manager"
        self.harness.mkdir()
        self.workspace.mkdir()
        self.config = SimpleNamespace(profile="managed", harness_root=self.harness,
            manager_workspace=self.workspace, runtime_root=self.workspace / ".harness-runtime")
        self.session = {"provider_id": "codex", "run_id": "prepared-run",
            "session_id": "logical-root", "native_session_id": "native-root"}
        self.prepared = {"root_session_id": "logical-root", "native_session_id": "native-root"}
        self.payload = {"hook_event_name": "UserPromptSubmit", "cwd": str(self.workspace),
            "session_id": "native-root", "turn_id": "native-turn",
            "prompt": "[harness]\nImplement the bounded fixture task."}
        environment = patch.dict(os.environ, {}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def call(self, payload=None):
        return optin.evaluate(self.payload if payload is None else payload,
                              harness_dir=self.harness, workspace=self.workspace)

    def mocks(self):
        """Enter read-only native API doubles, not fabricated runtime records."""
        import contextlib
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        load = stack.enter_context(patch.object(optin, "load_config", return_value=self.config))
        session = stack.enter_context(patch.object(optin, "read_root_session", return_value=self.session))
        resolve = stack.enter_context(patch.object(optin, "resolve_root_session", return_value=("logical-root", "codex")))
        state = stack.enter_context(patch.object(optin, "read_runtime_state", return_value={"state": "OPEN"}))
        validation = stack.enter_context(patch("scripts.prepare_root_launch.validate_prepared_root", return_value=self.prepared))
        return SimpleNamespace(load=load, session=session, resolve=resolve, state=state, validation=validation)

    def assert_blocked(self, result, code=None):
        self.assertEqual("block", result["decision"])
        self.assertNotIn("hookSpecificOutput", result)
        if code:
            self.assertIn(code, result["reason"])

    def test_on_explicitly_selects_configured_portable_skill(self) -> None:
        self.mocks()
        result = self.call()["hookSpecificOutput"]["additionalContext"]
        self.assertIn(str(self.harness / "skills/harness-outcome-workflow/SKILL.md"), result)
        self.assertIn("harness-outcome-workflow v2", result)
        self.assertIn("independent product-read-only native split", result)
        self.assertIn("Integrator repairs ITSELF", result)
        self.assertIn("For noncoding requests", result)
        self.assertIn("Instruction selection/readiness does not", result)

    def test_active_coordinator_payload_replaces_prepared_native_identity(self) -> None:
        self.mocks()
        with patch.object(optin, "read_ownership", return_value={
                "state": "ACTIVE", "to_native_session_id": "native-coordinator"}):
            self.assertEqual(optin.on_context(self.harness, self.workspace), self.call({
                **self.payload, "session_id": "native-coordinator"}))
            self.assert_blocked(self.call(), "IDENTITY_MISMATCH")

    def test_offered_handoff_does_not_change_prompt_authority(self) -> None:
        self.mocks()
        with patch.object(optin, "read_ownership", return_value={
                "state": "OFFERED", "to_native_session_id": "native-coordinator"}):
            self.assertEqual(optin.on_context(self.harness, self.workspace), self.call())
            self.assert_blocked(self.call({**self.payload, "session_id": "native-coordinator"}),
                                "IDENTITY_MISMATCH")

    def test_exact_marker_truth_table(self) -> None:
        cases = {
            "[harness]": True, "[harness]\nTask": True,
            "[harness]\r\nTask": True, "[harness]\n\nTask": True,
            "[harness]\nTask\n[harness]": True,
            "": False, "harness": False, "[Harness]\nTask": False,
            "[HARNESS]\nTask": False, " [harness]\nTask": False,
            "\t[harness]\nTask": False, "[harness] \nTask": False,
            "[harness]\t\nTask": False, "\n[harness]\nTask": False,
            "\r\n[harness]\r\nTask": False, "Task\n[harness]": False,
            "> [harness]\nTask": False, "`[harness]`\nTask": False,
            "```\n[harness]\nTask\n```": False,
            "Please use [harness]": False, "[harness] Task": False,
            "[harness]\rTask": False, "[harness]\r": False,
            "\ufeff[harness]\nTask": False, "[harness]\u2028Task": False,
            "[harness]\r\r\nTask": False,
        }
        for prompt, selected in cases.items():
            with self.subTest(prompt=repr(prompt)):
                self.assertIs(selected, optin.selected(prompt))

    def test_marker_requires_task_without_validating_or_starting_runtime(self) -> None:
        with patch.object(optin, "load_config") as load:
            for prompt in ("[harness]", "[harness]\n", "[harness]\r\n \t\r\n"):
                with self.subTest(prompt=repr(prompt)):
                    self.assert_blocked(self.call({**self.payload, "prompt": prompt}), "TASK_REQUIRED")
            load.assert_not_called()

    def test_unmarked_off_is_explicit_and_does_not_touch_authority(self) -> None:
        with (patch.object(optin, "load_config") as load,
              patch.object(optin, "read_root_session") as session,
              patch.object(optin, "read_ownership") as ownership,
              patch.object(optin, "resolve_root_session") as resolve,
              patch.object(optin, "read_runtime_state") as state,
              patch("scripts.prepare_root_launch.validate_prepared_root") as validation,
              patch("orchestrator_harness.setup.run_setup") as setup,
              patch("scripts.prepare_root_launch.prepare") as prepare,
              patch("subprocess.Popen") as spawn):
            result = self.call({**self.payload, "prompt": "Explain this file."})
        self.assertEqual(optin.context(optin.OFF_CONTEXT), result)
        self.assertIn("OFF for this user submission", result["hookSpecificOutput"]["additionalContext"])
        self.assertIn("Existing active worker ownership", result["hookSpecificOutput"]["additionalContext"])
        load.assert_not_called()
        session.assert_not_called()
        ownership.assert_not_called()
        resolve.assert_not_called()
        state.assert_not_called()
        validation.assert_not_called()
        setup.assert_not_called()
        prepare.assert_not_called()
        spawn.assert_not_called()

    def test_unmarked_bootstrap_preserves_full_accepted_contract_not_new_work(self) -> None:
        # Instruction regression, not proof of native acceptance or model behavior.
        # No runtime exists: OFF must not inspect authority to issue this context.
        with patch.object(optin, "load_config") as load:
            result = self.call({**self.payload, "session_id": "recipient-native",
                "prompt": "Accept the existing native manager handoff as your first tool operation."})
        self.assertEqual(optin.context(optin.OFF_CONTEXT), result)
        text = result["hookSpecificOutput"]["additionalContext"]
        self.assertIn("as its first tool operation", text)
        self.assertIn("Only after genuine native acceptance", text)
        self.assertIn("previously marked task's immutable contract", text)
        self.assertIn("initial assignment launches", text)
        self.assertIn("integration, checks, repairs, independent audits, and shutdown", text)
        self.assertIn("even if no workers were active at transfer", text)
        self.assertIn("not authorization for a new unmarked task", text)
        self.assertIn("grants no identity or ownership", text)
        self.assertIn("does not replace native handoff, readiness, or permission checks", text)
        load.assert_not_called()

    def test_on_then_off_has_no_sticky_registry(self) -> None:
        self.mocks()
        self.assertEqual(optin.on_context(self.harness, self.workspace), self.call())
        self.assertEqual(optin.context(optin.OFF_CONTEXT), self.call({**self.payload, "prompt": "Ordinary next task."}))
        self.assertEqual([], list(self.workspace.iterdir()))

    def test_other_and_nested_workspace_have_no_effect(self) -> None:
        with patch.object(optin, "load_config") as load:
            for cwd in (self.workspace / "nested", self.base / "other", self.harness):
                with self.subTest(cwd=cwd):
                    self.assertEqual({}, self.call({**self.payload, "cwd": str(cwd)}))
            load.assert_not_called()

    def test_malformed_scoped_payload_blocks(self) -> None:
        for payload in ([], "secret task", {"cwd": "relative"}, {},
                        {**self.payload, "hook_event_name": "Stop"},
                        {**self.payload, "prompt": ["[harness]"]}):
            with self.subTest(payload=repr(payload)):
                self.assert_blocked(self.call(payload), "INVALID_INPUT")

    def test_relative_explicit_configuration_blocks(self) -> None:
        self.assert_blocked(optin.evaluate(self.payload, harness_dir=Path("harness"), workspace=self.workspace), "CONFIG_INVALID")
        self.assert_blocked(optin.evaluate(self.payload, harness_dir=self.harness, workspace=Path("manager")), "CONFIG_INVALID")

    def test_valid_marked_uses_full_native_validator_and_existing_run(self) -> None:
        mocks = self.mocks()
        with (patch("orchestrator_harness.setup.run_setup") as setup,
              patch("scripts.prepare_root_launch.prepare") as prepare,
              patch("subprocess.Popen") as spawn):
            self.assertEqual(optin.on_context(self.harness, self.workspace), self.call())
        mocks.validation.assert_called_once_with(self.harness, self.workspace, "prepared-run", provider_id="codex")
        mocks.resolve.assert_called_once_with(self.config, provider_id="codex")
        setup.assert_not_called()
        prepare.assert_not_called()
        spawn.assert_not_called()

    def test_crlf_marker_accepts_valid_read_only_preparation(self) -> None:
        self.mocks()
        self.assertEqual(optin.on_context(self.harness, self.workspace), self.call({**self.payload, "prompt": "[harness]\r\nTask"}))

    def test_missing_closed_or_shutting_down_runtime_rejects(self) -> None:
        mocks = self.mocks()
        for state in (None, {"state": "CLOSED"}, {"state": "SHUTTING_DOWN"}):
            with self.subTest(state=state):
                mocks.state.return_value = state
                self.assert_blocked(self.call(), "NOT_OPEN")
        mocks.validation.assert_not_called()

    def test_missing_stale_or_unhealthy_preparation_rejects_without_echoing_error(self) -> None:
        mocks = self.mocks()
        for failure in (FileNotFoundError("secret missing receipt"),
                        ValueError("secret stale hash"), RuntimeError("secret unhealthy monitor")):
            with self.subTest(kind=type(failure).__name__):
                mocks.validation.side_effect = failure
                result = self.call()
                self.assert_blocked(result, "NOT_READY")
                self.assertNotIn("secret", json.dumps(result))

    def test_missing_logical_root_rejects(self) -> None:
        mocks = self.mocks()
        mocks.session.side_effect = ValueError("root-session missing")
        self.assert_blocked(self.call(), "NOT_READY")
        mocks.validation.assert_not_called()

    def test_wrong_provider_rejects_before_native_validator(self) -> None:
        mocks = self.mocks()
        self.session["provider_id"] = "claude-code"
        self.assert_blocked(self.call(), "PROVIDER_MISMATCH")
        mocks.validation.assert_not_called()

    def test_wrong_manager_configuration_rejects(self) -> None:
        mocks = self.mocks()
        self.config.manager_workspace = self.base / "other"
        self.assert_blocked(self.call(), "CONFIG_INVALID")
        mocks.validation.assert_not_called()

    def test_plain_configuration_rejects(self) -> None:
        mocks = self.mocks()
        self.config.profile = "plain"
        self.assert_blocked(self.call(), "CONFIG_INVALID")
        mocks.validation.assert_not_called()

    def test_native_session_and_turn_required_and_well_formed(self) -> None:
        mocks = self.mocks()
        for field in ("session_id", "turn_id"):
            for value in (None, "", "   ", 1, "unexpected\ncontrol", "x" * 1025):
                with self.subTest(field=field, value=repr(value)):
                    self.assert_blocked(self.call({**self.payload, field: value}), "INVALID_INPUT")
        mocks.validation.assert_not_called()

    def test_wrong_prepared_native_session_rejects(self) -> None:
        mocks = self.mocks()
        self.assert_blocked(self.call({**self.payload, "session_id": "other-native"}), "IDENTITY_MISMATCH")
        mocks.validation.assert_not_called()

    def test_all_inherited_logical_and_native_identities_checked(self) -> None:
        mocks = self.mocks()
        for name in ("CODEX_THREAD_ID", "HARNESS_ROOT_SESSION_ID", "HARNESS_SESSION_ID", "HARNESS_BINDING_ID"):
            for wrong in ("other", ""):
                with self.subTest(name=name, wrong=wrong), patch.dict(os.environ, {name: wrong}):
                    self.assert_blocked(self.call(), "IDENTITY_MISMATCH")
        mocks.validation.assert_not_called()

    def test_both_logical_environment_aliases_are_checked_not_just_precedence(self) -> None:
        self.mocks()
        with patch.dict(os.environ, {"HARNESS_ROOT_SESSION_ID": "logical-root", "HARNESS_SESSION_ID": "other"}):
            self.assert_blocked(self.call(), "IDENTITY_MISMATCH")

    def test_matching_inherited_identity_accepts(self) -> None:
        self.mocks()
        with patch.dict(os.environ, {"CODEX_THREAD_ID": "native-root", "HARNESS_ROOT_SESSION_ID": "logical-root",
                                    "HARNESS_SESSION_ID": "logical-root", "HARNESS_BINDING_ID": "codex"}):
            self.assertEqual(optin.on_context(self.harness, self.workspace), self.call())

    def test_unbound_native_session_is_not_mutated_or_claimed_as_ownership(self) -> None:
        self.mocks()
        self.session["native_session_id"] = None
        self.prepared["native_session_id"] = None
        self.assertEqual(optin.on_context(self.harness, self.workspace), self.call())
        self.assertIsNone(self.session["native_session_id"])

    def test_resolver_failure_and_changed_binding_reject(self) -> None:
        mocks = self.mocks()
        mocks.resolve.side_effect = ValueError("mismatch")
        self.assert_blocked(self.call(), "NOT_READY")
        mocks.resolve.side_effect = None
        self.prepared["root_session_id"] = "other"
        self.assert_blocked(self.call(), "IDENTITY_MISMATCH")

    def test_bounded_strict_json_reader(self) -> None:
        self.assertEqual({"prompt": "fixture"}, optin.read_payload(io.BytesIO(b'{"prompt":"fixture"}')))
        for raw in (b"", b"{", b"\xff", b'{"cwd":1,"cwd":2}', b'{"value":NaN}'):
            with self.subTest(raw=repr(raw)), self.assertRaises((ValueError, UnicodeError)):
                optin.read_payload(io.BytesIO(raw))
        with patch.object(optin, "MAX_INPUT_BYTES", 4), self.assertRaises(ValueError):
            optin.read_payload(io.BytesIO(b"12345"))


class NativeEntryPointTests(unittest.TestCase):
    def invoke(self, raw: bytes, *arguments: str):
        return subprocess.run([sys.executable, "-B", str(SOURCE / "scripts/harness_prompt_optin.py"), *arguments],
                              input=raw, capture_output=True, cwd=SOURCE, timeout=20)

    def test_invalid_input_is_exit_zero_native_block_without_secret_echo(self) -> None:
        for raw in (b"secret-not-json", b"[]", b'{"cwd":1,"cwd":2}'):
            with self.subTest(raw=repr(raw)):
                result = self.invoke(raw, "--harness-dir", str(SOURCE), "--workspace", str(SOURCE))
                self.assertEqual(0, result.returncode, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual("block", payload["decision"])
                self.assertNotIn("secret-not-json", payload["reason"])
                self.assertEqual(b"", result.stderr)

    def test_missing_arguments_are_exit_zero_native_block(self) -> None:
        result = self.invoke(b"{}")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("block", json.loads(result.stdout)["decision"])
        self.assertEqual(b"", result.stderr)

    def test_other_workspace_is_empty_output_object_even_for_marker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="optin-other-") as raw:
            payload = {"hook_event_name": "UserPromptSubmit", "cwd": raw,
                       "session_id": "native", "turn_id": "turn", "prompt": "[harness]\nTask"}
            result = self.invoke(json.dumps(payload).encode(), "--harness-dir", str(SOURCE), "--workspace", str(SOURCE))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({}, json.loads(result.stdout))

    def test_unprepared_unmarked_bootstrap_is_read_only_off_not_automatic_setup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="optin-bootstrap-") as raw:
            workspace = Path(raw)
            payload = {"hook_event_name": "UserPromptSubmit", "cwd": raw,
                       "prompt": "Accept the existing manager handoff, then continue its contract."}
            result = self.invoke(json.dumps(payload).encode(), "--harness-dir", str(SOURCE),
                                 "--workspace", raw)
            self.assertEqual([], list(workspace.iterdir()))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(b"", result.stderr)
        self.assertEqual(optin.context(optin.OFF_CONTEXT), json.loads(result.stdout))
        self.assertIn("Never automatically set up, prepare, or reopen a runtime", result.stdout.decode())


if __name__ == "__main__":
    unittest.main()
