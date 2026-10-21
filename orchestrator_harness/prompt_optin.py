"""Explicit newest-submission selection and native raw gateway registration.

Unmarked submissions are read-only OFF. Marked submissions register one exact
native raw request after readiness; never a mode toggle, manager or launcher.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, BinaryIO

from .config import load_config, path_identity
from .root_session import read_root_session, resolve_root_session
from .manager_ownership import read_ownership
from .setup import read_runtime_state

MARKER = "[harness]"
MAX_INPUT_BYTES = 4_000_000

OFF_CONTEXT = (
    "HARNESS MODE OFF for this user submission: the exact first-line [harness] "
    "opt-in is absent. Do not start harness services or workers for a new task "
    "requested by this submission; do not carry forward a previous submission's "
    "ON selection to new work. An unmarked recipient bootstrap may accept an "
    "existing valid native manager handoff or direct intake as its first tool operation. Only "
    "after genuine native acceptance, the coordinator continues the previously "
    "marked task's immutable contract, including initial assignment launches, "
    "integration, checks, repairs, independent audits, and shutdown, even if no "
    "workers were active at transfer. This is continuation of existing work, "
    "not authorization for a new unmarked task. This instruction grants no "
    "identity or ownership and does not replace native handoff, readiness, or "
    "permission checks. Never automatically set up, prepare, or reopen a runtime. "
    "Existing active worker ownership, safety, and native cleanup/Stop "
    "obligations still apply; OFF does not cancel, abandon, or shut down "
    "existing work."
)
WORKFLOW_SKILL = "skills/harness-outcome-workflow/SKILL.md"
ON_CONTEXT = (
    "HARNESS MODE ON for this user submission only. Explicitly load the "
    "configured harness-outcome-workflow v3 skill. You are the OUTER GATEWAY, "
    "completely outside planning, coding, integration, reviewing, repair routing, "
    "native manager events/watch and cleanup. Submit the ORIGINAL user prompt "
    "unchanged, INCLUDING [harness], exact whitespace and line endings, through "
    "manager intake-submit to the genuinely preseeded distinct coordinator. "
    "Do not resolve/bind yourself as prepared ROOT, interpret/decompose the task, "
    "or use the ROOT usage collector for yourself. The actual separate native "
    "coordinator must accept as its first tool operation, then owns separate "
    "planner and independent split-review lanes, all coding lanes, integration, "
    "self-repairs, fresh exact-revision whole-result audits and native shutdown. "
    "Relay its final response unchanged. After exact native acceptance you may "
    "yield without claiming task completion. Missing real native creation/resume "
    "capabilities or permissions mean BLOCKED, never a planner/manager fallback. "
    "[harness] selects instructions, not a provider launcher or semantic proof. "
    "Do not start clients/services, prepare/reopen a runtime or change global "
    "permissions automatically. Follow explicit operator bootstrap prerequisites. "
    "Uncertain or pending ownership cannot be treated as confirmed."
)

PREPARATION_GUIDANCE = (
    "No harness work was authorized by this hook. Read the installed harness's "
    "local-config/INSTALLATION.md. Preparation must precede the managed client: "
    "stop this client, diagnose the preserved failure, and explicitly prepare "
    "in a terminal before restarting/resuming Codex at the configured manager "
    "workspace root. Follow docs/WORKFLOW.md lifecycle guidance: after a manager "
    "handoff or changed prepared source, preserve/archive the proven CLOSED "
    "runtime and run records, then genuinely prepare a fresh run. Only unchanged "
    "legacy preparation with no handoff may use native harness setup once and "
    "scripts/prepare_root_launch.py with the SAME recorded run ID. Never "
    "delete/fabricate receipts, silently fall "
    "back to ordinary coding, or automatically retry setup."
)


class OptInError(ValueError):
    """A safe-to-display rejection, deliberately excluding prompt/config data."""


def blocked(code: str, reason: str) -> dict[str, Any]:
    return {"decision": "block", "reason": f"{code}: {reason}"}


def context(text: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": text,
    }}


def on_context(harness_dir: Path, workspace: Path) -> dict[str, Any]:
    # Supply the actual configured instruction location rather than relying
    # on a model guessing which repository's similarly named files to read.
    return context(ON_CONTEXT + "\nRequired workflow skill file: "
                   + json.dumps(str(harness_dir / WORKFLOW_SKILL)) + "."
                   + "\nConfigured harness directory: "
                   + json.dumps(str(harness_dir)) + ". Manager workspace: "
                   + json.dumps(str(workspace)) + ".")


def selected(prompt: str) -> bool:
    """Match the exact first physical line, allowing LF and CRLF only."""
    first, separator, _remainder = prompt.partition("\n")
    if separator and first.endswith("\r"):
        first = first[:-1]
    return first == MARKER


def _string(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip())
            and len(value) <= 1024 and not any(ord(c) < 32 for c in value))


def _native_identity(payload: dict[str, Any], session: dict[str, Any]) -> None:
    for field in ("session_id", "turn_id"):
        if not _string(payload.get(field)):
            raise OptInError("HARNESS_OPTIN_INVALID_INPUT: native session_id and turn_id are required.")
    native = payload["session_id"]
    prepared = session["native_session_id"]
    if prepared is not None and native != prepared:
        raise OptInError("HARNESS_OPTIN_IDENTITY_MISMATCH: native session differs from the prepared ROOT.")
    expected = {
        "CODEX_THREAD_ID": native,
        "HARNESS_ROOT_SESSION_ID": session["session_id"],
        "HARNESS_SESSION_ID": session["session_id"],
        "HARNESS_BINDING_ID": "codex",
    }
    for name, wanted in expected.items():
        if name in os.environ and os.environ[name] != wanted:
            raise OptInError("HARNESS_OPTIN_IDENTITY_MISMATCH: inherited native or logical ROOT identity differs.")


def evaluate(payload: object, *, harness_dir: Path, workspace: Path) -> dict[str, Any]:
    """Translate one native payload to allow+context or explicit native block.

    Unrelated/nested CWDs get no output or authority access. Scoped malformed
    input blocks. The existing native preparation validator is the sole source
    of authority; there is no second mode/session registry and no repair path.
    """
    try:
        if not harness_dir.is_absolute() or not workspace.is_absolute():
            raise OptInError("HARNESS_OPTIN_CONFIG_INVALID: explicit absolute harness and workspace paths are required.")
        if not isinstance(payload, dict):
            raise OptInError("HARNESS_OPTIN_INVALID_INPUT: expected a native hook JSON object.")
        cwd = payload.get("cwd")
        if not isinstance(cwd, str) or not cwd or not Path(cwd).is_absolute():
            raise OptInError("HARNESS_OPTIN_INVALID_INPUT: absolute native cwd is required.")
        if path_identity(cwd) != path_identity(workspace):
            return {}
        if (payload.get("hook_event_name") != "UserPromptSubmit"
                or not isinstance(payload.get("prompt"), str)):
            raise OptInError("HARNESS_OPTIN_INVALID_INPUT: expected UserPromptSubmit and a string prompt.")
        if not selected(payload["prompt"]):
            return context(OFF_CONTEXT)
        _first, _separator, task = payload["prompt"].partition("\n")
        if not task.strip():
            return blocked("HARNESS_OPTIN_TASK_REQUIRED", "Put [harness] alone on the first line and a nonempty task on the following lines.")
        config = load_config(harness_dir)
        if (config.profile != "managed"
                or path_identity(config.harness_root) != path_identity(harness_dir)
                or path_identity(config.manager_workspace) != path_identity(workspace)):
            raise OptInError("HARNESS_OPTIN_CONFIG_INVALID: the harness does not select this managed workspace.")
        session = read_root_session(config)
        if session["provider_id"] != "codex":
            raise OptInError("HARNESS_OPTIN_PROVIDER_MISMATCH: this workspace is not prepared for Codex ROOT.")
        if payload.get("agent_id") is not None or payload.get("agent_type") is not None:
            raise OptInError("HARNESS_OPTIN_IDENTITY_MISMATCH: nested native clients are not gateways.")
        from .manager_ownership import _not_worker
        from .workflow_intake import read_intake
        _not_worker()
        intake = read_intake(config, session)
        ownership = read_ownership(config, session)
        # Saved v1/v2 workflows keep their native manager semantics. Fresh
        # marked work selects an external gateway and never resolves ROOT.
        if ownership is not None:
            raise OptInError("HARNESS_OPTIN_LEGACY_RUN: continue the saved accepted v1/v2 contract unmarked with its manager duties intact; new v3 gateway work requires fresh preparation.")
        if intake is not None and intake["state"] == "ACTIVE":
            raise OptInError("HARNESS_OPTIN_EXISTING_RUN: coordinator already owns this immutable request; do not relaunch it. Use unmarked status/final relay, or fresh preparation for a new task.")
        expected = intake["gateway_session_id"] if intake is not None else None
        _native_identity(payload, {**session, "native_session_id": expected})
        if payload["session_id"] == session["native_session_id"] or (intake is not None and payload["session_id"] == intake["coordinator_session_id"]):
            raise OptInError("HARNESS_OPTIN_IDENTITY_MISMATCH: coordinator continues accepted intake unmarked; it is not the outer gateway.")
        # Do not enter the native validator's locks for an absent/CLOSED
        # runtime; it must never become a setup path for an unmarked task.
        state = read_runtime_state(config.runtime_root)
        if state is None or state.get("state") != "OPEN":
            return blocked("HARNESS_OPTIN_NOT_OPEN", PREPARATION_GUIDANCE)
        from scripts.prepare_root_launch import validate_prepared_root
        prepared = validate_prepared_root(harness_dir, workspace, session["run_id"], provider_id="codex")
        if (prepared["root_session_id"] != session["session_id"]
                or prepared["native_session_id"] != session["native_session_id"]):
            raise OptInError("HARNESS_OPTIN_IDENTITY_MISMATCH: ROOT binding changed during validation.")
        from .manager_ownership import _native_hook_identity
        from .workflow_intake import register_gateway
        with _native_hook_identity("codex", payload["session_id"]):
            registered = register_gateway(config, session, native=payload["session_id"], prompt=payload["prompt"])
        result = on_context(harness_dir, workspace)
        result["hookSpecificOutput"]["additionalContext"] += (
            "\nExact native raw request registered without manager authority; intake_id: "
            + registered["intake_id"])
        import hashlib
        result["hookSpecificOutput"]["additionalContext"] += (
            "\nOriginal submission UTF8 SHA256 (pass exactly to intake-submit --request-sha256): "
            + hashlib.sha256(payload["prompt"].encode("utf-8")).hexdigest())
        return result
    except OptInError as exc:
        return {"decision": "block", "reason": f"{exc} {PREPARATION_GUIDANCE}"}
    except Exception:
        # Never emit exception text: configuration/JSON errors can contain
        # secrets or the original prompt. A native block is exit-zero JSON.
        return blocked("HARNESS_OPTIN_NOT_READY", "Existing ROOT preparation or monitor validation failed. " + PREPARATION_GUIDANCE)


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON field")
        value[key] = item
    return value


def read_payload(stream: BinaryIO) -> object:
    """Bound one native stdin payload, rejecting ambiguous JSON without echo."""
    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("native input exceeds the configured bound")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                      parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
