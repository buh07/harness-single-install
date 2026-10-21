"""Shared binding, receipt, and provider-output support for ROOT hooks."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .core import iso_utc
from .config import compute_config_identity, load_config, load_resource_manifest, path_identity
from .mutation import ensure_directory_path, open_append_file, read_bytes, safe_relative_path
from .manager_queue import append_delivery_history
from .root_hook_dispatch import dispatch, unresolved_event_ids
from .root_session import resolve_root_session

BINDING_SCHEMA = "harness-hook-binding/v1"
DECISIONS = frozenset({"ALLOW", "NOTICE", "REJECT"})


class RootHookBindingError(ValueError):
    """An installed ROOT hook is absent, unbound, or cross-bound."""


def _read_binding(path: Path, provider_id: str) -> dict[str, Any]:
    if not path.is_file():
        raise RootHookBindingError(
            f"installed {provider_id} hook has no harness binding"
        )
    try:
        target = path.absolute()
        value = json.loads(read_bytes(target.parent, target.name).decode("utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RootHookBindingError(
            f"installed {provider_id} hook has invalid harness binding: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise RootHookBindingError(
            f"installed {provider_id} hook has invalid harness binding object"
        )
    expected = {
        "schema": BINDING_SCHEMA,
        "role": "root",
        "provider_id": provider_id,
    }
    for field, wanted in expected.items():
        if value.get(field) != wanted:
            raise RootHookBindingError(
                f"installed {provider_id} hook has invalid binding {field}"
            )
    for field in ("harness_root", "runtime_root", "manager_workspace", "root_workspace"):
        raw = value.get(field)
        if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
            raise RootHookBindingError(
                f"installed {provider_id} hook has no bound {field}"
            )
    config = load_config(Path(value["harness_root"]))
    expected_identity = compute_config_identity(config, load_resource_manifest(config.harness_root))
    expected_paths = {"runtime_root": config.runtime_root,
                      "manager_workspace": config.manager_workspace,
                      "root_workspace": config.root_workspace}
    if (value.get("config_identity") != expected_identity
            or any(path_identity(value[field]) != path_identity(wanted)
                   for field, wanted in expected_paths.items())
            or path_identity(path.absolute().parent.parent) != path_identity(config.manager_workspace)):
        raise RootHookBindingError("ROOT_BINDING_STALE: explicitly prepare hooks for the current manager/product configuration")
    return value


def _workspace_path(binding_path: Path, relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise RootHookBindingError(f"ROOT hook binding has invalid {field}")
    workspace = binding_path.absolute().parent.parent
    return workspace / safe_relative_path(relative)


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path = path.absolute()
    ensure_directory_path(path.parent)
    with open_append_file(path.parent, path.name) as handle:
        handle.write((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def _notice_text(notice: object) -> str:
    if not isinstance(notice, dict):
        return "Harness ROOT hook reported an actionable notice."
    return "Harness ROOT notice: " + json.dumps(
        notice, sort_keys=True, separators=(",", ":")
    )


def translate(boundary: str, decision: dict[str, Any]) -> dict[str, Any]:
    kind = decision.get("decision")
    if kind == "ALLOW":
        return {}
    if boundary == "post-tool-use" and kind == "NOTICE":
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": _notice_text(decision.get("notice")),
            }
        }
    reason = decision.get("reason") or "rejected by harness ROOT hook"
    if boundary == "stop":
        return {"decision": "block", "reason": str(reason)}
    return {"continue": False, "stopReason": str(reason)}


def _run_owned(provider_id: str, boundary: str, binding_path: Path) -> dict[str, Any]:
    """Run one ROOT hook and return its native JSON output object."""
    try:
        binding = _read_binding(binding_path, provider_id)
        config = load_config(Path(binding["harness_root"]))
        managed = config.profile == "managed"
        scope = {}
        if managed:
            session_id, binding_id = resolve_root_session(config, provider_id=provider_id)
            scope = {"session_id": session_id, "binding_id": binding_id}
        liveness = _workspace_path(
            binding_path, binding.get("liveness_path"), "liveness_path"
        )
        _append_jsonl(
            liveness,
            {
                "schema": "hook-liveness/v1",
                "role": "root",
                "provider_id": provider_id,
                "boundary": boundary,
                "at": iso_utc(),
                **scope,
            },
        )
        decision = dispatch(Path(binding["harness_root"]), boundary, provider_id)
        if not isinstance(decision, dict) or decision.get("decision") not in DECISIONS:
            decision = {
                "decision": "REJECT",
                "reason": "ROOT hook dispatcher returned an invalid decision",
            }
        # Plain mode must remain queue-free, including when a provider leaves
        # an old event-id environment variable behind.
        event_id = os.environ.get("HARNESS_EVENT_ID") if managed else None
        event_ids = (
            [event_id]
            if event_id
            else (unresolved_event_ids(Path(binding["runtime_root"])) if managed else [])
        )
        if boundary == "post-tool-use" and event_ids:
            receipt_path = _workspace_path(
                binding_path,
                binding.get("delivery_receipt_path"),
                "delivery_receipt_path",
            )
            for selected_event_id in event_ids:
                receipt: dict[str, Any] = {
                    "outcome": "DELIVERED",
                    "source": "hook",
                    "event_id": selected_event_id,
                    "provider_id": provider_id,
                    "at": iso_utc(),
                    **scope,
                }
                try:
                    append_delivery_history(
                        Path(binding["runtime_root"]), selected_event_id, **scope
                    )
                except Exception as exc:
                    receipt.update({"outcome": "DELIVERY_FAILED", "error": str(exc)})
                    if decision.get("decision") == "ALLOW":
                        decision = {
                            "decision": "NOTICE",
                            "notice": {
                                "provider_id": provider_id,
                                "binding_id": provider_id,
                                "unresolved_count": len(event_ids),
                                "event_classes": [],
                                "highest_class": None,
                                "highest_severity": "error",
                                "at": iso_utc(),
                                "message": f"manager delivery receipt failed: {exc}",
                            },
                        }
                _append_jsonl(receipt_path, receipt)
    except Exception as exc:
        decision = {"decision": "REJECT", "reason": str(exc)}
    return translate(boundary, decision)


def _codex_hook_identity(provider_id: str, boundary: str, hook_input: str) -> str:
    """Map Codex's native hook stdin; do not infer other providers' schemas.

    Codex v0.163 hooks/schema.rs defines session_id and hook_event_name for
    PostToolUseCommandInput and StopCommandInput. This cooperative identity is
    provided by the native client, not a prepared receipt or a prompt field.
    """
    if provider_id != "codex":
        raise RootHookBindingError("MANAGER_HOOK_INPUT_UNSUPPORTED: native hook identity mapping requires Codex")
    try:
        value = json.loads(hook_input)
    except (ValueError, TypeError) as exc:
        raise RootHookBindingError("MANAGER_HOOK_INPUT_INVALID: expected native hook JSON object") from exc
    expected = {"post-tool-use": "PostToolUse", "stop": "Stop"}.get(boundary)
    if not isinstance(value, dict) or expected is None or value.get("hook_event_name") != expected:
        raise RootHookBindingError("MANAGER_HOOK_INPUT_INVALID: native hook event differs from installed boundary")
    # Codex subagent hooks can carry the parent's session_id. They are not a
    # distinct execution manager and must not inherit that parent's authority.
    if value.get("agent_id") is not None or value.get("agent_type") is not None:
        raise RootHookBindingError("MANAGER_HANDOFF_WORKER: subagent hooks cannot operate the manager")
    native = value.get("session_id")
    if (not isinstance(native, str) or not native.strip() or native != native.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in native)):
        raise RootHookBindingError("MANAGER_IDENTITY_REQUIRED: native hook session_id is missing or invalid")
    return native


def run(provider_id: str, boundary: str, binding_path: Path, *,
        hook_input: str | None = None) -> dict[str, Any]:
    """Never deliver manager events to a retired planner; CLOSED still permits exit."""
    try:
        binding = _read_binding(binding_path, provider_id)
        config = load_config(Path(binding["harness_root"]))
        if config.profile == "managed":
            from .setup import read_runtime_state
            from .manager_ownership import manager_operation, _native_hook_identity, read_ownership
            from .shutdown import prove_runtime_closed
            if (read_runtime_state(config.runtime_root) or {}).get("state") == "CLOSED":
                # Cleanup proof is required even for the retired planner. Do not
                # append delivery receipts or revive its old ownership here.
                prove_runtime_closed(config.runtime_root, config.root_workspace, config.harness_root)
                return {}
            if hook_input is not None:
                native = _codex_hook_identity(provider_id, boundary, hook_input)
                with _native_hook_identity(provider_id, native):
                    # Legacy prepared roots can have a pinned native identity
                    # even before a handoff record exists. Keep that check too.
                    from .root_session import read_root_session
                    session = read_root_session(config)
                    from .workflow_intake import gateway_boundary
                    if gateway_boundary(config, session, native, boundary):
                        return {}
                    if (read_ownership(config, session) is None
                            and session["native_session_id"] not in (None, native)):
                        raise RootHookBindingError("ROOT_SESSION_MISMATCH: native hook session differs from prepared binding")
                    with manager_operation(config):
                        return _run_owned(provider_id, boundary, binding_path)
            with manager_operation(config):
                return _run_owned(provider_id, boundary, binding_path)
        return _run_owned(provider_id, boundary, binding_path)
    except Exception as exc:
        return translate(boundary, {"decision": "REJECT", "reason": str(exc)})
