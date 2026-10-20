"""Read-only, explicit Codex UserPromptSubmit selection for one managed ROOT.

This is a native hook, not a launcher or workflow enforcement engine. No prompt
or mode receipt is persisted; each submission independently selects ON or OFF.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, BinaryIO

from .config import load_config, path_identity
from .root_session import read_root_session, resolve_root_session
from .setup import read_runtime_state

MARKER = "[harness]"
MAX_INPUT_BYTES = 4_000_000

OFF_CONTEXT = (
    "HARNESS MODE OFF for this user submission: the exact first-line [harness] "
    "opt-in is absent. Do not start harness services or workers for this task; "
    "do not carry forward a previous submission's ON selection. Existing active "
    "worker ownership, safety, and native cleanup/Stop obligations still apply; "
    "this does not cancel, abandon, or shut down existing work."
)
ON_CONTEXT = (
    "HARNESS MODE ON for this user submission only. The exact first-line "
    "[harness] marker selected the task following it, and the existing Codex "
    "ROOT preparation passed read-only validation at submission time. Read "
    "the configured harness's AGENTS.md, QUICK_RULES.md, QUICK_START.md, and "
    "local-config/INSTALLATION.md before acting. Act as ROOT: use native harness "
    "lanes and isolated Git worktrees for implementation, explicit worker "
    "model/preferences, one writer per scope, required independent testing and "
    "review, native completion review/acceptance and lane retirement. Generic "
    "Codex subagents are not substitutes for native harness coding lanes. "
    "Preserve unrelated changes and configured storage constraints. Discover "
    "manager work only through native watch --until-actionable; do not read "
    "transcripts or introduce runners, supervisors, relays, retry controllers, "
    "or automatic setup/preparation. Preserve and diagnose failures. Settle all "
    "owned lanes and manager obligations, run native harness shutdown, and "
    "verify CLOSED before the final response. Report real lane IDs, worktrees, "
    "tests, acceptance/retirement results, and shutdown evidence. ON does not "
    "persist to the next submission; it never overrides live ownership or "
    "cleanup obligations. This hook selects the workflow and validates readiness; "
    "it does not prove complete workflow compliance or provider isolation."
)
PREPARATION_GUIDANCE = (
    "No harness work was authorized by this hook. Read the installed harness's "
    "local-config/INSTALLATION.md. Preparation must precede the managed client: "
    "stop this client, diagnose the preserved failure, and explicitly prepare "
    "in a terminal before restarting/resuming Codex at the configured manager "
    "workspace root. For an already prepared CLOSED runtime, use native harness "
    "setup once and scripts/prepare_root_launch.py with the SAME recorded run "
    "ID, then restart/resume. Never delete/fabricate receipts, silently fall "
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
    return context(ON_CONTEXT + "\nConfigured harness directory: "
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
        _native_identity(payload, session)
        resolve_root_session(config, provider_id="codex")
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
        return on_context(harness_dir, workspace)
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
