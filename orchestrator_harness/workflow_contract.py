"""Portable outcome contract and exact-candidate advisory audit validation.

These checks validate declared evidence, not its truth or model compliance. They
never launch clients, schedule work, confer permission, or decide acceptance.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import re
from typing import Any

LEGACY_CONTRACT_SCHEMA = "harness-outcome-workflow/v1"
CONTRACT_SCHEMA = "harness-outcome-workflow/v2"
LEGACY_AUDIT_SCHEMA = "harness-outcome-audit/v1"
AUDIT_SCHEMA = "harness-outcome-audit/v2"
SPLIT_REVIEW_SCHEMA = "harness-split-review/v1"
FINAL_SCHEMA = "harness-outcome-final/v2"
SPLIT_DIMENSIONS = frozenset({"coverage", "semantic-independence", "dependencies",
    "shared-ownership", "single-goal", "granularity-cost", "global-criteria"})
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


def _validate_plan(value: Any) -> dict[str, Any]:
    """Return a detached structurally validated plan, or raise ValueError.

    Every implementation assignment owns exactly one bounded outcome. Global
    outcomes may instead map to integration criteria. All references must resolve;
    every outcome must be covered and assignment/outcome links must agree.
    """
    if not isinstance(value, dict) or value.get("schema") not in {LEGACY_CONTRACT_SCHEMA, CONTRACT_SCHEMA}:
        raise ValueError("unsupported workflow contract schema")
    fields = {"schema", "original_prompt", "constraints", "outcomes",
        "assignments", "integration_criteria", "coordinator", "auditor"}
    if value["schema"] == CONTRACT_SCHEMA:
        fields |= {"repository_context", "interfaces", "split_reviewer", "plan_review"}
    contract = _object(value, fields, "contract")
    if contract["schema"] == CONTRACT_SCHEMA:
        _strings(contract["repository_context"], "repository_context")
        _strings(contract["interfaces"], "interfaces", empty=True)
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
    for role in (("coordinator", "auditor", "split_reviewer") if contract["schema"] == CONTRACT_SCHEMA
                 else ("coordinator", "auditor")):
        _object(contract[role], {"provider", "model", "provider_options"}, role)
        _preferences(contract[role], role)
    return deepcopy(contract)


def plan_sha256(value: Any) -> str:
    """Hash the complete final v2 plan, excluding only its review envelope.

    Drafts use ``plan_review: None``. The hash includes all original outcomes,
    assignments, context, interfaces and preferences; changing any invalidates
    prior review. It is declaration linkage, not a semantic quality guarantee.
    """
    plan = _validate_plan(value)
    if plan["schema"] != CONTRACT_SCHEMA:
        raise ValueError("split review requires v2 plan")
    from .core import sha256_hex
    return sha256_hex({key: item for key, item in plan.items() if key != "plan_review"})


def _findings(value: Any, name: str) -> list[dict[str, Any]]:
    findings = _records(value, name, empty=True)
    for finding in findings:
        _object(finding, {"id", "description"}, name)
        _text(finding["description"], name + ".description")
    return findings


def validate_plan_review(value: Any, contract: Any, *, planner_session_id: str,
                         reviewer_session_id: str) -> dict[str, Any]:
    """Validate a complete exact-plan advisory review against observed identities.

    The caller obtains identities from native metadata, not the report. No PASS
    verdict is demanded: the planner remains responsible for reasoned resolution.
    """
    report = _review_shape(value, contract)
    planner = _text(planner_session_id, "observed planner session")
    reviewer = _text(reviewer_session_id, "observed reviewer session")
    if report["reviewer_session_id"] != reviewer or planner == reviewer:
        raise ValueError("split reviewer must be caller-observed, read-only and independent")
    return report


def _review_shape(value: Any, contract: Any) -> dict[str, Any]:
    report = _object(value, {"schema", "plan_sha256", "reviewer_session_id", "read_only",
        "prepared_run_id", "root_session_id", "dimensions", "findings"}, "split review")
    if report["schema"] != SPLIT_REVIEW_SCHEMA or report["plan_sha256"] != plan_sha256(contract):
        raise ValueError("split review is stale or targets a different final plan")
    _text(report["reviewer_session_id"], "reviewer_session_id")
    if report["read_only"] is not True:
        raise ValueError("split reviewer must be read-only")
    for key in ("prepared_run_id", "root_session_id"):
        _text(report[key], "split review." + key)
    dimensions = _records(report["dimensions"], "split review dimensions")
    if {item["id"] for item in dimensions} != SPLIT_DIMENSIONS:
        raise ValueError("split review must assess every dimension exactly once")
    for item in dimensions:
        _object(item, {"id", "assessment", "evidence"}, "split review dimension")
        _text(item["assessment"], "split review assessment")
        _strings(item["evidence"], "split review evidence")
    _findings(report["findings"], "split review findings")
    return deepcopy(report)


def validate_contract(value: Any) -> dict[str, Any]:
    """Validate v2 reviewed declarations, retaining saved v1 read compatibility.

    Offline validation checks linkage and reasoned dispositions. Native offer
    additionally checks actual retired lane metadata and current prepared scope.
    """
    contract = _validate_plan(value)
    if contract["schema"] == LEGACY_CONTRACT_SCHEMA:
        return contract
    envelope = _object(contract["plan_review"], {"report", "resolutions", "native_review"}, "plan_review")
    report = envelope["report"]
    # Actual identities are intentionally supplied again at the native boundary.
    # Here only report shape/linkage is checked, not claimed independence.
    if not isinstance(report, dict):
        raise ValueError("plan_review: reviewed report required")
    _review_shape(report, contract)
    resolutions = _records(envelope["resolutions"], "plan resolutions", empty=True)
    if {item["id"] for item in resolutions} != {item["id"] for item in report["findings"]}:
        raise ValueError("every split-review finding requires a reasoned planner resolution")
    for item in resolutions:
        _object(item, {"id", "decision", "rationale"}, "plan resolution")
        if item["decision"] not in {"accepted", "declined"}:
            raise ValueError("plan resolution must be accepted or declined")
        _text(item["rationale"], "plan resolution rationale")
    native = _object(envelope["native_review"], {"epoch_id", "lane_id", "run_id", "result_sha256",
        "prepared_run_id", "root_session_id"}, "native_review")
    from .portable_paths import component
    for key in ("epoch_id", "lane_id"):
        component(native[key])
    for key in ("run_id", "prepared_run_id", "root_session_id"):
        _text(native[key], "native_review." + key)
    if any(native[key] != report[key] for key in ("prepared_run_id", "root_session_id")):
        raise ValueError("split review prepared scope differs from native linkage")
    if not isinstance(native["result_sha256"], str) or not re.fullmatch("[a-f0-9]{64}", native["result_sha256"]):
        raise ValueError("native review RESULT SHA256 required")
    return contract


def validate_audit(value: Any, contract: Any, *, candidate_revision: str,
                   implementer_session_ids: tuple[str, ...] | list[str],
                   coordinator_session_id: str, auditor_session_id: str | None = None,
                   prior_auditor_session_ids: tuple[str, ...] | list[str] = ()) -> dict[str, Any]:
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
    expected_schema = AUDIT_SCHEMA if contract["schema"] == CONTRACT_SCHEMA else LEGACY_AUDIT_SCHEMA
    if report["schema"] != expected_schema or report["candidate_revision"] != candidate_revision:
        raise ValueError("unsupported or stale audit")
    from .core import sha256_hex
    if report["contract_sha256"] != sha256_hex(contract):
        raise ValueError("audit workflow contract hash mismatch")
    auditor = _text(report["auditor_session_id"], "auditor_session_id")
    if contract["schema"] == CONTRACT_SCHEMA and auditor_session_id is None:
        raise ValueError("caller-observed auditor native session required for v2")
    if auditor_session_id is not None and auditor != _text(auditor_session_id, "observed auditor"):
        raise ValueError("audit identity differs from caller-observed native session")
    if report["read_only"] is not True or auditor in {*implementer_session_ids, coordinator_session_id, *prior_auditor_session_ids}:
        raise ValueError("auditor must be read-only and independent of implementation/integration")
    statuses = _validate_results(report["results"], contract)
    if contract["schema"] == CONTRACT_SCHEMA:
        _findings(report["findings"], "audit findings")
    else:
        _strings(report["findings"], "audit findings", empty=True)
    if report["verdict"] not in {"PASS", "FAIL", "BLOCKED"}:
        raise ValueError("invalid audit verdict")
    if report["verdict"] == "PASS" and (any(s != "PASS" for s in statuses) or report["findings"]):
        raise ValueError("passing audit contradicts unsuccessful checks or unresolved findings")
    return deepcopy(report)



def _validate_results(value: Any, contract: dict[str, Any]) -> list[str]:
    results = _records(value, "audit results")
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
    return statuses

def validate_final_result(value: Any, contract: Any, audit: Any, *, candidate_revision: str,
                          expected_contract_sha256: str,
                          implementer_session_ids: tuple[str, ...] | list[str],
                          coordinator_session_id: str, auditor_session_id: str,
                          prior_auditor_session_ids: tuple[str, ...] | list[str] = ()) -> dict[str, Any]:
    """Validate explicit current-candidate completion, never decide it for owner.

    A contrary advisory audit can be declined with reasoned evidence; it has no
    veto. COMPLETE still requires all original owner checks PASS, complete audit
    coverage and disposition of every adverse finding/result. A changed HEAD or
    accepted-contract hash invalidates old evidence. No semantic truth is inferred.
    """
    from .core import sha256_hex
    contract = validate_contract(contract)
    if contract["schema"] != CONTRACT_SCHEMA or sha256_hex(contract) != expected_contract_sha256:
        raise ValueError("final result must preserve the complete accepted v2 contract")
    audit = validate_audit(audit, contract, candidate_revision=candidate_revision,
        implementer_session_ids=implementer_session_ids, coordinator_session_id=coordinator_session_id,
        auditor_session_id=auditor_session_id, prior_auditor_session_ids=prior_auditor_session_ids)
    result = _object(value, {"schema", "contract_sha256", "candidate_revision", "coordinator_session_id",
        "checks", "audit_sha256", "resolutions", "status", "limitations"}, "final result")
    if (result["schema"] != FINAL_SCHEMA or result["contract_sha256"] != expected_contract_sha256
            or result["candidate_revision"] != candidate_revision
            or result["coordinator_session_id"] != coordinator_session_id
            or result["audit_sha256"] != sha256_hex(audit)):
        raise ValueError("final result has stale candidate, audit, contract or coordinator linkage")
    _validate_results(result["checks"], contract)
    resolutions = result["resolutions"]
    if (not isinstance(resolutions, list) or any(not isinstance(item, dict)
            or not isinstance(item.get("id"), str) for item in resolutions)
            or len({item["id"] for item in resolutions}) != len(resolutions)):
        raise ValueError("audit resolutions require unique keyed objects")
    required = {"finding:" + item["id"] for item in audit["findings"]}
    required |= {"result:" + item["id"] for item in audit["results"] if item["status"] != "PASS"}
    if {item["id"] for item in resolutions} != required:
        raise ValueError("all adverse audit findings/results require reasoned dispositions")
    for item in resolutions:
        _object(item, {"id", "decision", "rationale", "evidence"}, "audit resolution")
        if item["decision"] not in {"addressed", "declined", "unresolved"}:
            raise ValueError("invalid audit resolution decision")
        _text(item["rationale"], "audit resolution rationale")
        _strings(item["evidence"], "audit resolution evidence")
    _strings(result["limitations"], "final limitations", empty=True)
    if result["status"] not in {"COMPLETE", "BLOCKED"}:
        raise ValueError("final status must be COMPLETE or BLOCKED")
    if result["status"] == "COMPLETE" and (any(item["status"] != "PASS" for item in result["checks"])
            or any(item["decision"] == "unresolved" for item in resolutions)):
        raise ValueError("COMPLETE cannot hide unsuccessful original checks or unresolved failures")
    return deepcopy(result)
