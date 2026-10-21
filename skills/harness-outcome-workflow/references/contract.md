# Versioned contract and audit records

The contract is `harness-outcome-workflow/v1`. The native handoff snapshots its
validated content and SHA256, preventing later file edits from silently changing
the execution agreement. A meaningful scope change requires an explicit new
agreement; never relabel an unmet outcome as success.

See [contract.example.json](contract.example.json) for a complete fictitious
assignment. Replace every example preference with actual authorized settings.
`constraints` can be empty when none were given. `exclusions` and `dependencies`
can be empty. All other lists are nonempty, except a global outcome can have
`assignment_ids: []` when an integration criterion references it.

- Outcome/criterion IDs are disjoint. Assignments reference exactly one outcome;
  outcome assignment links must agree. Dependencies must form an acyclic graph.
- Each integration criterion has `id`, `description`, `outcome_ids`, and `checks`.
  This traces global requirements to unified checks, not only worker tasks.
- Assignment preferences and coordinator/auditor preferences use the native
  bootstrap provider validator. They are explicit declarations, not permissions.
- Extra/missing fields, ambiguous references and missing coverage are rejected.

Validate without launching anything, from the harness source root:

```python
import json
from orchestrator_harness.workflow_contract import validate_contract
contract = validate_contract(json.loads(contract_path.read_text(encoding="utf-8")))
```

## Exact-revision audit

A `harness-outcome-audit/v1` report contains `contract_sha256` (the native
handoff contract hash), `candidate_revision` (full Git object
ID), `auditor_session_id`, `read_only: true`, `results`, `verdict` and `findings`.
`results` must contain every outcome **and** every integration criterion exactly
once. Each result contains `id`, `status` (`PASS`, `FAIL`, `BLOCKED`), nonempty
`checks` and nonempty `evidence` paths/details. Each check contains `description`,
`status` and nonempty `evidence`. `findings` lists unresolved actionable findings;
it may be empty. PASS contradicting unsuccessful checks/findings is rejected.

```python
from orchestrator_harness.workflow_contract import validate_audit
report = validate_audit(report, contract, candidate_revision=actual_revision,
    implementer_session_ids=actual_author_native_session_ids,
    coordinator_session_id=actual_coordinator_native_session_id)
```

Use actual observed provider-native identities, not task labels or identities
selected by the auditor. Validation checks declared independence/coverage; it
cannot prove the auditor really stayed read-only or executed its claimed tests.
The coordinator must retain actual commands, statuses and exact-revision evidence.
A failed/blocked audit is a valid report, not an automatic veto. Native RESULT
schema/lane completion rules still apply; attach this report as an artifact rather
than replacing the native RESULT envelope with it.
