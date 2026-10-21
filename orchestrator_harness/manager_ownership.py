"""Explicit native-conversation transfer of a prepared manager's authority.

This is cooperative same-user ownership, not a security sandbox: provider-owned
native identity must be present (tool environment or validated native hook input),
and fabricating either is unsupported. No provider is started and no prepared receipt/session is modified here.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import os
from pathlib import Path
from typing import Any

from .config import ConfigError, HarnessConfig, load_resource_manifest
from .core import content_hash, iso_utc, new_id, read_json, sha256_hex
from .epochs import open_epoch, read_current_epoch, read_epoch_state
from .records import RecordLock, atomic_write_json, read_record, runtime_admission_lock

SCHEMA = "manager-ownership/v1"
_NATIVE = {"codex": "CODEX_THREAD_ID", "claude-code": "CLAUDE_SESSION_ID", "qwen-code": "QWEN_SESSION_ID"}
_HOOK_NATIVE: ContextVar[tuple[str, str] | None] = ContextVar("manager_hook_native", default=None)
_FIELDS = {"schema", "run_id", "session_id", "provider_id", "config_identity", "epoch_id",
           "generation", "state", "offer_id", "original_native_session_id", "to_native_session_id",
           "contract", "contract_sha256", "contract_path", "offered_at", "accepted_at", "content_hash"}


def ownership_path(config: HarnessConfig) -> Path:
    return config.runtime_root / "MANAGER_OWNERSHIP.json"


@contextmanager
def _native_hook_identity(provider: str, native: str):
    """Scope a validated provider-owned hook input without changing process env.

    This is only used by the installed hook adapter, never an operator option.
    Context-local state also keeps nested prepared-scope checks consistent.
    """
    token = _HOOK_NATIVE.set((provider, native))
    try:
        observed_native(provider)  # An inherited contradictory identity is fatal.
        yield
    finally:
        _HOOK_NATIVE.reset(token)


def observed_native(provider: str) -> str:
    value = os.environ.get(_NATIVE[provider])
    hook = _HOOK_NATIVE.get()
    if hook is not None:
        if hook[0] != provider or (value is not None and value != hook[1]):
            raise ConfigError("MANAGER_IDENTITY_CONFLICT: native hook and environment identities differ")
        value = hook[1]
    if (not isinstance(value, str) or not value.strip() or value != value.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ConfigError("MANAGER_IDENTITY_REQUIRED: observed provider-native conversation identity is required")
    return value


def _not_worker() -> None:
    if any(os.environ.get(key) for key in ("HARNESS_LANE_ID", "HARNESS_WORKER_INVOCATION_ID", "HARNESS_WORKER_RUN_ID")):
        raise ConfigError("MANAGER_HANDOFF_WORKER: an ordinary coding lane cannot receive manager authority")


def read_ownership(config: HarnessConfig, session: dict[str, Any]) -> dict[str, Any] | None:
    path = ownership_path(config)
    try:
        value = read_record(path, SCHEMA)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ConfigError("MANAGER_OWNERSHIP_INVALID: preserve and reconcile ownership record") from exc
    epoch = read_current_epoch(config.runtime_root)
    epoch_matches = epoch is not None and value.get("epoch_id") == epoch.get("epoch_id")
    if epoch is None and isinstance(value.get("epoch_id"), str):
        from .setup import read_runtime_state
        runtime = read_runtime_state(config.runtime_root) or {}
        prior = read_epoch_state(config.runtime_root, value["epoch_id"])
        epoch_matches = (runtime.get("state") in {"SHUTTING_DOWN", "CLOSED"}
                         and prior.get("lifecycle") in {"closing", "closed"}
                         and prior.get("config_identity") == session["config_identity"])
    if (set(value) != _FIELDS or value.get("content_hash") != content_hash(value)
            or any(value.get(key) != session[key] for key in ("run_id", "session_id", "provider_id", "config_identity"))
            or not epoch_matches
            or value.get("state") not in ("OFFERED", "ACTIVE")
            or type(value.get("generation")) is not int
            or value["generation"] != (1 if value["state"] == "OFFERED" else 2)
            or any(not isinstance(value.get(key), str) or not value[key].strip()
                   for key in ("offer_id", "original_native_session_id", "to_native_session_id", "offered_at", "contract_path"))
            or value["original_native_session_id"] == value["to_native_session_id"]
            or (session["native_session_id"] is not None and session["native_session_id"] != value["original_native_session_id"])
            or (value["accepted_at"] is not None if value["state"] == "OFFERED"
                else not isinstance(value["accepted_at"], str))
            or not isinstance(value.get("contract"), dict)
            or value.get("contract_sha256") != sha256_hex(value["contract"])
            or value["contract_path"] != str(config.runtime_root / ("manager-contract-" + value["offer_id"] + ".json"))):
        raise ConfigError("MANAGER_OWNERSHIP_STALE: ownership scope, generation, or contract is invalid")
    from .workflow_contract import validate_contract
    validate_contract(value["contract"])
    if value["contract"]["coordinator"]["provider"] != session["provider_id"]:
        raise ConfigError("MANAGER_HANDOFF_PROVIDER: cross-provider ownership is unsupported")
    return value


def require_manager_owner(config: HarnessConfig, session: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if config.profile != "managed":
        return None
    if session is None:
        from .root_session import read_root_session
        # Preserve legacy unprepared setup behavior, but never ignore an existing
        # ownership record when preparation is missing or invalid.
        try:
            ownership_path(config).lstat()
        except FileNotFoundError:
            return None
        session = read_root_session(config)
    value = read_ownership(config, session)
    if value is not None:
        expected = value["to_native_session_id"] if value["state"] == "ACTIVE" else value["original_native_session_id"]
        if observed_native(session["provider_id"]) != expected:
            raise ConfigError("MANAGER_NOT_OWNER: only the current native manager conversation may operate this runtime")
        _not_worker()
    return value


@contextmanager
def manager_operation(config: HarnessConfig):
    """Exclude handoff acceptance while an admitted manager command is running.

    Separate from runtime admission: launch/wait/shutdown must allow controllers
    to make progress. A handoff waits for any previous command to return.
    """
    if config.root_workspace is None:
        yield
        return
    with RecordLock(config.runtime_root / "MANAGER_OPERATION.json"):
        require_manager_owner(config)
        yield


def _not_registered_lane(config: HarnessConfig, native: str) -> None:
    from .lanes import retained_lanes
    epoch = read_current_epoch(config.runtime_root)
    if epoch is None:
        return
    from .root_session import read_root_session
    provider = read_root_session(config)["provider_id"]
    for lane in retained_lanes(config.runtime_root, epoch["epoch_id"]).values():
        if (lane.get("provider") or {}).get("id", provider) != provider:
            continue
        if native in {lane.get("provider_session_id"), lane.get("session_id"),
                      (lane.get("session") or {}).get("session_id")}:
            raise ConfigError("MANAGER_HANDOFF_WORKER: a registered coding lane cannot become execution manager")
    # Native clients launched directly in an ordinary worker worktree are also
    # refused before their provider session appears in lane completion records.
    for parent in (Path.cwd(), *Path.cwd().parents):
        path = parent / ".agent-workspace" / "harness-hook-binding.json"
        try:
            binding = read_json(path)
        except FileNotFoundError:
            continue
        if binding.get("role") == "worker":
            raise ConfigError("MANAGER_HANDOFF_WORKER: worker worktree cannot receive manager ownership")
        break


def _ready(config: HarnessConfig, session: dict[str, Any]) -> None:
    from .setup import read_runtime_state, require_monitor_ready
    if (read_runtime_state(config.runtime_root) or {}).get("state") != "OPEN":
        raise ConfigError("MANAGER_HANDOFF_NOT_OPEN: transfer requires the existing OPEN runtime")
    require_monitor_ready(config.runtime_root, session["config_identity"])
    from scripts.prepare_root_launch import validate_prepared_root
    validate_prepared_root(config.harness_root, config.manager_workspace, session["run_id"], provider_id=session["provider_id"])


def offer_handoff(config: HarnessConfig, *, to_native_session_id: str, contract_path: Path) -> dict[str, Any]:
    from .root_session import read_root_session, resolve_root_session
    from .workflow_contract import validate_contract
    contract = validate_contract(read_json(contract_path))
    if not isinstance(to_native_session_id, str) or not to_native_session_id.strip() or any(ord(c) < 32 for c in to_native_session_id):
        raise ConfigError("MANAGER_HANDOFF_TARGET: a distinct native conversation identity is required")
    with RecordLock(config.runtime_root / "MANAGER_OPERATION.json"), runtime_admission_lock(config.runtime_root):
        session = read_root_session(config)
        resolve_root_session(config)
        _not_worker()
        original = observed_native(session["provider_id"])
        if original == to_native_session_id:
            raise ConfigError("MANAGER_HANDOFF_TARGET: planner and execution coordinator must be different native conversations")
        if contract["coordinator"]["provider"] != session["provider_id"]:
            raise ConfigError("MANAGER_HANDOFF_PROVIDER: cross-provider ownership is unsupported")
        _ready(config, session)
        _not_registered_lane(config, to_native_session_id)
        with RecordLock(ownership_path(config)):
            if read_ownership(config, session) is not None:
                raise ConfigError("MANAGER_HANDOFF_EXISTS: this prepared epoch already has a handoff; preserve it")
            # Genuine prelaunch preparation readies the runtime but need not
            # create an epoch. Handoff precedes coding-lane bootstrap, so it
            # initializes the ordinary native epoch itself, without a lane,
            # provider launch, setup, or replacement preparation receipt.
            epoch = open_epoch(config.runtime_root, config, load_resource_manifest(config.harness_root))
            offer_id = new_id()
            snapshot = config.runtime_root / ("manager-contract-" + offer_id + ".json")
            atomic_write_json(snapshot, contract)
            value = {"schema": SCHEMA, **{key: session[key] for key in ("run_id", "session_id", "provider_id", "config_identity")},
                     "epoch_id": epoch["epoch_id"], "generation": 1, "state": "OFFERED", "offer_id": offer_id,
                     "original_native_session_id": original, "to_native_session_id": to_native_session_id,
                     "contract": contract, "contract_sha256": sha256_hex(contract), "contract_path": str(snapshot),
                     "offered_at": iso_utc(), "accepted_at": None}
            value["content_hash"] = content_hash(value)
            atomic_write_json(ownership_path(config), value)
            return _result(value, "Manager handoff offered; planner retains ownership until target accepts")


def accept_handoff(config: HarnessConfig, *, offer_id: str, contract_sha256: str) -> dict[str, Any]:
    from .root_session import read_root_session
    with RecordLock(config.runtime_root / "MANAGER_OPERATION.json"), runtime_admission_lock(config.runtime_root):
        session = read_root_session(config)
        _not_worker()
        _ready(config, session)
        with RecordLock(ownership_path(config)):
            value = read_ownership(config, session)
            if value is None or value["state"] != "OFFERED" or value["offer_id"] != offer_id:
                raise ConfigError("MANAGER_HANDOFF_STALE: no matching unaccepted offer")
            if value["contract_sha256"] != contract_sha256:
                raise ConfigError("MANAGER_HANDOFF_CONTRACT: supplied contract digest differs from immutable offer")
            if observed_native(session["provider_id"]) != value["to_native_session_id"]:
                raise ConfigError("MANAGER_NOT_OWNER: only the offered distinct native conversation may accept")
            _not_registered_lane(config, value["to_native_session_id"])
            # Logical identity cannot be silently inherited from a coding lane.
            for key, expected in (("HARNESS_ROOT_SESSION_ID", session["session_id"]),
                                  ("HARNESS_SESSION_ID", session["session_id"]),
                                  ("HARNESS_BINDING_ID", session["provider_id"])):
                if key in os.environ and os.environ[key] != expected:
                    raise ConfigError("ROOT_SESSION_MISMATCH: accepting native conversation has conflicting logical scope")
            value.update(state="ACTIVE", generation=2, accepted_at=iso_utc())
            value["content_hash"] = content_hash(value)
            atomic_write_json(ownership_path(config), value)
            return _result(value, "Execution coordinator exclusively owns the prepared manager scope")


def _result(value: dict[str, Any], summary: str) -> dict[str, Any]:
    return {"ok": True, "code": "MANAGER_HANDOFF_" + value["state"], "summary": summary,
            "offer_id": value["offer_id"], "contract_sha256": value["contract_sha256"],
            "contract_path": value["contract_path"], "generation": value["generation"],
            "evidence_paths": [value["contract_path"]],
            "next_action": "target accepts the exact offered contract" if value["state"] == "OFFERED" else "follow the outcome workflow as execution coordinator"}
