"""Portable outcome contract and exact-candidate advisory audit validation.

These checks validate declared evidence, not its truth or model compliance. They
never launch clients, schedule work, confer permission, or decide acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

CONTRACT_SCHEMA = "harness-outcome-workflow/v1"
AUDIT_SCHEMA = "harness-outcome-audit/v1"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
_REVISION = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def _object(value: Any, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{name}: expected exactly {', '.join(sorted(fields))}")
    return value


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty text required")
    return value


def _strings(value: Any, name: str, *, empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not empty):
        raise ValueError(f"{name}: list required")
    for item in value:
        _text(item, name)
    if len(set(value)) != len(value):
        raise ValueError(f"{name}: duplicate entries")
    return value


def _records(value: Any, name: str, *, empty: bool = False) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not value and not empty):
        raise ValueError(f"{name}: records required")
    if any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{name}: objects required")
    ids = [item.get("id") for item in value]
    if any(not isinstance(item, str) or not _ID.fullmatch(item) for item in ids):
        raise ValueError(f"{name}: invalid ID")
    if len(set(ids)) != len(ids):
        raise ValueError(f"{name}: duplicate ID")
    return value


def _preferences(value: dict[str, Any], name: str) -> None:
    provider = _text(value["provider"], name + ".provider")
    if provider not in {"codex", "claude-code", "qwen-code"}:
        raise ValueError(f"{name}: unsupported provider")
    _text(value["model"], name + ".model")
    if not isinstance(value["provider_options"], dict):
        raise ValueError(f"{name}: provider_options must be an object")
    # Reuse the native bootstrap's authoritative provider preference validator.
    from .bootstrap import _validate_provider_launch_config
    try:
        _validate_provider_launch_config(Path(__file__).resolve().parent.parent,
            provider_id=provider, model=value["model"], launch_config=value["provider_options"])
    except Exception as exc:
        raise ValueError(f"{name}: invalid explicit provider preferences") from exc


def validate_contract(value: Any) -> dict[str, Any]:
    """Return a detached validated v1 contract, or raise ValueError.

    Every implementation assignment owns exactly one bounded outcome. Global
    outcomes may instead map to integration criteria. All references must resolve;
    every outcome must be covered and assignment/outcome links must agree.
    """
    contract = _object(value, {"schema", "original_prompt", "constraints", "outcomes",
        "assignments", "integration_criteria", "coordinator", "auditor"}, "contract")
    if contract["schema"] != CONTRACT_SCHEMA:
        raise ValueError("unsupported workflow contract schema")
    _text(contract["original_prompt"], "original_prompt")
    _strings(contract["constraints"], "constraints", empty=True)
    outcomes = _records(contract["outcomes"], "outcomes")
    assignments = _records(contract["assignments"], "assignments")
    criteria = _records(contract["integration_criteria"], "integration_criteria")
    outcome_ids = {item["id"] for item in outcomes}
    assignment_ids = {item["id"] for item in assignments}
    criterion_ids = {item["id"] for item in criteria}
    if outcome_ids & criterion_ids:
        raise ValueError("outcome and integration criterion IDs must be disjoint")
    links: dict[str, set[str]] = {item: set() for item in outcome_ids}
    for item in assignments:
        _object(item, {"id", "task", "goal", "outcome_ids", "scope", "exclusions",
            "dependencies", "acceptance_criteria", "deliverables", "checks", "provider",
            "model", "provider_options"}, "assignment")
        for key in ("task", "goal"):
            _text(item[key], key)
        for key in ("scope", "acceptance_criteria", "deliverables", "checks", "outcome_ids"):
            _strings(item[key], key)
        for key in ("exclusions", "dependencies"):
            _strings(item[key], key, empty=True)
        if len(item["outcome_ids"]) != 1 or not set(item["outcome_ids"]) <= outcome_ids:
            raise ValueError("each assignment must reference exactly one known outcome")
        if not set(item["dependencies"]) <= assignment_ids or item["id"] in item["dependencies"]:
            raise ValueError("unknown or self assignment dependency")
        links[item["outcome_ids"][0]].add(item["id"])
        _preferences(item, "assignment")
    # A cyclic task graph cannot be executed as bounded dependency assignments.
    pending = {item["id"]: set(item["dependencies"]) for item in assignments}
    while pending:
        ready = {key for key, deps in pending.items() if not deps}
        if not ready:
            raise ValueError("cyclic assignment dependencies")
        pending = {key: deps - ready for key, deps in pending.items() if key not in ready}
    integration_outcomes: set[str] = set()
    for item in criteria:
        _object(item, {"id", "description", "outcome_ids", "checks"}, "integration criterion")
        _text(item["description"], "integration criterion.description")
        _strings(item["checks"], "integration criterion.checks")
        _strings(item["outcome_ids"], "integration criterion.outcome_ids")
        if not set(item["outcome_ids"]) <= outcome_ids:
            raise ValueError("unknown integration outcome")
        integration_outcomes.update(item["outcome_ids"])
    for item in outcomes:
        _object(item, {"id", "description", "acceptance_criteria", "assignment_ids"}, "outcome")
        _text(item["description"], "outcome.description")
        _strings(item["acceptance_criteria"], "outcome.acceptance_criteria")
        _strings(item["assignment_ids"], "outcome.assignment_ids", empty=True)
        if set(item["assignment_ids"]) != links[item["id"]]:
            raise ValueError("assignment/outcome links disagree")
        if not links[item["id"]] and item["id"] not in integration_outcomes:
            raise ValueError("outcome has no implementation or integration coverage")
    for role in ("coordinator", "auditor"):
        _object(contract[role], {"provider", "model", "provider_options"}, role)
        _preferences(contract[role], role)
    return deepcopy(contract)


def validate_audit(value: Any, contract: Any, *, candidate_revision: str,
                   implementer_session_ids: tuple[str, ...] | list[str],
                   coordinator_session_id: str) -> dict[str, Any]:
    """Validate independent, complete declared checks for one exact Git revision.

    A valid report may say FAIL/BLOCKED; validation does not turn it into PASS.
    The caller supplies actual native author/coordinator identities, not values
    selected by the auditor. Any changed revision requires a new audit.
    """
    contract = validate_contract(contract)
    if not isinstance(candidate_revision, str) or not _REVISION.fullmatch(candidate_revision):
        raise ValueError("full candidate Git revision required")
    _text(coordinator_session_id, "coordinator native session")
    if not implementer_session_ids or any(not isinstance(s, str) or not s.strip() for s in implementer_session_ids):
        raise ValueError("actual implementer native sessions required")
    report = _object(value, {"schema", "contract_sha256", "candidate_revision", "auditor_session_id", "read_only",
        "results", "verdict", "findings"}, "audit")
    if report["schema"] != AUDIT_SCHEMA or report["candidate_revision"] != candidate_revision:
        raise ValueError("unsupported or stale audit")
    from .core import sha256_hex
    if report["contract_sha256"] != sha256_hex(contract):
        raise ValueError("audit workflow contract hash mismatch")
    auditor = _text(report["auditor_session_id"], "auditor_session_id")
    if report["read_only"] is not True or auditor in {*implementer_session_ids, coordinator_session_id}:
        raise ValueError("auditor must be read-only and independent of implementation/integration")
    results = _records(report["results"], "audit results")
    required = {item["id"] for item in contract["outcomes"] + contract["integration_criteria"]}
    if {item["id"] for item in results} != required:
        raise ValueError("audit must cover every outcome and integration criterion exactly once")
    statuses = []
    for item in results:
        _object(item, {"id", "status", "checks", "evidence"}, "audit result")
        if item["status"] not in {"PASS", "FAIL", "BLOCKED"}:
            raise ValueError("invalid audit result status")
        _strings(item["evidence"], "audit evidence")
        if not isinstance(item["checks"], list) or not item["checks"]:
            raise ValueError("actual audit checks required")
        for check in item["checks"]:
            _object(check, {"description", "status", "evidence"}, "audit check")
            _text(check["description"], "audit check description")
            _strings(check["evidence"], "audit check evidence")
            if check["status"] not in {"PASS", "FAIL", "BLOCKED"}:
                raise ValueError("invalid audit check status")
        if item["status"] == "PASS" and any(c["status"] != "PASS" for c in item["checks"]):
            raise ValueError("passing result contains unsuccessful check")
        statuses.append(item["status"])
    _strings(report["findings"], "audit findings", empty=True)
    if report["verdict"] not in {"PASS", "FAIL", "BLOCKED"}:
        raise ValueError("invalid audit verdict")
    if report["verdict"] == "PASS" and (any(s != "PASS" for s in statuses) or report["findings"]):
        raise ValueError("passing audit contradicts unsuccessful checks or unresolved findings")
    return deepcopy(report)
