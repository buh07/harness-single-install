# Versioned reviewed plan, audit and final-result records

## Contract: default v2, legacy v1

The default selected contract is `harness-outcome-workflow/v2`. Native handoff
snapshots its validated content and SHA256, preventing later edits from silently
changing the execution agreement. Preserve all original outcomes/criteria; a
meaningful scope change requires explicit new agreement, never silent weakening.
`harness-outcome-workflow/v1` remains readable for existing records; it does not
satisfy or demonstrate the added v2 initial-review stage.

[contract.example.json](contract.example.json) shows a complete **synthetic v2**
record; [contract.v1.example.json](contract.v1.example.json) preserves the legacy
example. Replace example preferences with actual authorized settings. The v2
review identities/hashes are placeholders, not native receipts or launchable
handoff authority. Never copy them into real native records.

Both versions preserve the original prompt, constraints, outcomes, assignments,
integration criteria, coordinator and auditor preferences. Assignment IDs link to
exactly one outcome; reverse links agree. Dependencies form an acyclic DAG and
outcome/criterion IDs are disjoint. All outcomes have meaningful acceptance
criteria; each global criterion has `id`, `description`, `outcome_ids`, `checks`.
A global outcome can have `assignment_ids: []` when covered by integration checks.
`constraints`, assignment `exclusions` and `dependencies` may be empty. Preferences
use native provider validation; they are declarations, not extra permissions.

V2 additionally requires:

- `repository_context`: nonempty text list with relevant task context.
- `interfaces`: text list, possibly empty, identifying relevant cross-lane contracts.
- `split_reviewer`: explicit provider/model/provider_options like other roles.
- `plan_review`: `{report, resolutions, native_review}` as below.

`plan_sha256(contract)` hashes the complete v2 plan **excluding `plan_review`**,
avoiding a circular hash. The review targets the final exact resolved plan; a
material revision requires fresh review of that new hash. Native handoff hashes
and freezes the **entire final contract**, including review/resolution linkage.
These two hashes serve different purposes; do not substitute the plan hash for
the accepted immutable contract hash in product audits.

## Initial split review and reasoned resolution

The report schema is `harness-split-review/v1` (a report version, not workflow v1):

- `schema`, `plan_sha256`, `prepared_run_id`, `root_session_id`.
- `reviewer_session_id`: genuine observed provider-native reviewer identity.
- `read_only: true`: an assignment declaration, not OS immutability.
- `dimensions`: exactly `coverage`, `semantic-independence`, `dependencies`,
  `shared-ownership`, `single-goal`, `granularity-cost`, `global-criteria`; each
  `{id, assessment, evidence}` with concrete nonempty assessment/evidence.
- `findings`: list of `{id, description}`; may be empty.

`resolutions` contains exactly one `{id, decision, rationale}` per finding;
`decision` is `accepted` or `declined`. Incorporate justified changes before the
final-plan review; explain declined advice. The exact final hash must match even
when a finding was accepted. There is no reviewer PASS field or veto gate.

The normal native worker's validated `RESULT.evidence` contains a structured
object `{ "plan_review": <report> }`. Keep the ordinary RESULT envelope and
lifecycle; do not replace it with the report. `native_review` records:

- `prepared_run_id`, `root_session_id`: current genuine preparation scope.
- `epoch_id`, `lane_id`, `run_id`: actual native epoch/lane/worker invocation.
- `result_sha256`: `core.sha256_hex` of the entire validated native RESULT object
  (canonical JSON object hash, **not** SHA256 of raw file bytes).

Planner discovers/settles this lane through ordinary native watch/events and
completion review, then retires it **before** offering handoff. The native offer
checks genuine review evidence, observed controller identity/protected invocation
history, current preparation
scope, retired cleanup, acceptance and event settlement. A synthetic valid JSON
shape alone is not enough. Distinctness is checked against actual planner and
recipient identities; a task label or auditor-selected identity is insufficient.
The reviewer's advice is advisory; accepting delivery of the assigned review is
not requiring approval of the plan. If review is missing/unavailable, clean up and
report incomplete rather than inventing evidence or blocking shutdown forever.

Read [planning-review.md](planning-review.md) for review content and responsibilities.
From the harness root, validate declarations offline without launching:

```python
from orchestrator_harness.workflow_contract import (
    plan_sha256, validate_contract, validate_plan_review,
)
contract = validate_contract(contract_data)
validate_plan_review(contract["plan_review"]["report"], contract,
    planner_session_id=actual_planner_native_id,
    reviewer_session_id=actual_observed_reviewer_native_id)
```

This checks typed declarations. It does not create native evidence or prove the
review happened. Native offer supplies the additional observed lifecycle linkage.

## Exact-revision final audit

Default `harness-outcome-audit/v2` retains `contract_sha256` (the **whole accepted
contract** hash), `candidate_revision` (full Git object ID),
`auditor_session_id`, `read_only: true`, `results`, `verdict`, `findings`.
`results` covers every original outcome **and** every integration criterion
exactly once. Each result is `{id, status, checks, evidence}`; `status` is `PASS`,
`FAIL` or `BLOCKED`; checks/evidence are nonempty. A check is
`{description, status, evidence}`. V2 `findings` contains typed `{id, description}`
records for unresolved actionable findings. Report PASS cannot contradict failed
checks/findings. A FAIL/BLOCKED report is valid evidence, not a veto.

```python
from orchestrator_harness.workflow_contract import validate_audit
report = validate_audit(report_data, contract,
    candidate_revision=actual_current_revision,
    implementer_session_ids=actual_author_native_ids,
    coordinator_session_id=actual_coordinator_native_id,
    auditor_session_id=actual_observed_auditor_native_id,
    prior_auditor_session_ids=earlier_round_auditor_native_ids)
```

V2 requires the caller-observed auditor identity, distinct from authors,
coordinator and earlier round auditors. Use fresh independent native auditors
for material new revisions; changing a role label does not establish independence.
Legacy audit/v1 remains readable for workflow/v1. All reports remain artifacts
within normal native RESULT/completion semantics, discovered through native watch.
The validator checks coverage, exact revision, identity comparisons and internal
consistency—not actual execution, filesystem read-only status or truth. Retain
actual commands/statuses and before/after candidate identity.

## Integrator repair loop and honest final result

The coordinator owns justified repairs **itself**, not planner ROOT or original
coders. Preserve the accepted immutable original contract. After material changes,
commit the new revision, rerun **every** outcome and overall criterion, and obtain
a fresh independent native audit of that exact revision. Retain earlier failed
reports as history. No old report becomes current merely because the failure was
fixed or an auditor previously approved a parent revision.

`harness-outcome-final/v2` contains:

- `schema`, `contract_sha256`, `candidate_revision`, `coordinator_session_id`.
- `checks`: full original outcome+criterion coverage, using the audit result shape.
- `audit_sha256`: `core.sha256_hex` of the validated current audit report.
- `resolutions`: `{id, decision, rationale, evidence}` for **every** audit finding
  (`finding:<id>`) and unsuccessful audit result (`result:<id>`); decisions are
  `addressed`, `declined`, `unresolved`, with concrete rationale/evidence.
- `status`: `COMPLETE` or `BLOCKED`; `limitations`: explicit text list.

```python
from orchestrator_harness.workflow_contract import validate_final_result
final = validate_final_result(final_data, contract, report,
    candidate_revision=actual_current_revision,
    expected_contract_sha256=accepted_immutable_contract_hash,
    implementer_session_ids=actual_author_native_ids,
    coordinator_session_id=actual_coordinator_native_id,
    auditor_session_id=actual_observed_auditor_native_id,
    prior_auditor_session_ids=earlier_round_auditor_native_ids)
```

COMPLETE requires every coordinator outcome/global check PASS and no unresolved
resolution; it does not require the advisory audit's verdict to say PASS. Decline
an incorrect finding only with reasoned evidence, never to relabel a justified
failure. A material code fix requires a **new exact-revision report**, not an
`addressed` disposition attached to a stale audit. Typed consistency cannot
establish semantic task completion: the owner remains accountable that **all
original outcomes work together and the overall request is actually satisfied**.

At resource/permission/capability/infrastructure bounds, report BLOCKED/INCOMPLETE
honestly, preserve failed checks/reviews and settle/retire all work. Always run
native shutdown and prove CLOSED; lifecycle closure is not product success.
Neither missing evidence nor reviewer advice may hold cleanup hostage. Do not
weaken/drop outcomes, count partial passes as success, introduce an automatic
retry controller, or loop indefinitely seeking a PASS label.
