# External-gateway v3 acceptance evidence

## Scope

This version's validation is **offline**, not a new native/model-backed provider
E2E. The historical [real-provider report](REAL_WORKFLOW_TEST.md) remains unchanged:
it proves the v1 Codex/Linux successful path, not the new separate planner,
marker registration or external-gateway topology. V2 fixtures likewise are not
v3 provider proof. No new provider permission profile is authorized by this report.

## Behavioral coverage

The isolated `test_workflow_intake` fixtures exercise the public native helpers
with explicit provider-identity/provenance doubles and real private monitor/Git
processes. Doubled native metadata/RESULT records are **not** evidence that a model
followed the skill or that a provider launcher ran.

- Exact original UTF-8 text, Unicode, CRLF and trailing whitespace survive native
  marker registration, raw submission, frozen plan and final evidence.
- The outer is nonmanager before even its first skill-read tool. REGISTERED and
  PENDING grant no generic manager powers; only actual designated acceptance
  binds the coordinator. Unknown, nested-worker, stale or conflicting identities
  cannot claim the gateway Stop allowance. The actual owner stays Stop-blocked
  while OPEN, including empty-queue/retirement gaps.
- Gateway hooks append no manager delivery/liveness receipts or queue notices.
  The coordinator's epoch survives planner/reviewer/coding/audit gaps.
- Independent actual-native-evidence linkage is checked when freezing the full
  original plan: wrong planner/reviewer identity, result, base, hash, scope and
  stale review are rejected. Saved v1/v2 records remain distinct legacy semantics.
- Interrupted native binding/acceptance, acceptance races and terminal-only
  unclaimed prelaunch recovery retain one owner and normal cleanup requirements.
- A small actual offline coding fixture follows raw intake → separate planner/
  review provenance → bounded code → failing whole-result audit → integrator
  repair/new Git revision → every original outcome/global check rerun → fresh
  exact-revision audit → COMPLETE evidence → normal shutdown/CLOSED proof.
  It rejects old audit reuse; outer performs no coding, checking or cleanup.

Reproduce the focused behavior and saved-record regressions from a clean source
checkout with owned persistent temporary storage selected by `TMPDIR`:

```sh
python -B -m unittest orchestrator_harness.tests.test_workflow_intake -v
python -B -m unittest \
  orchestrator_harness.tests.test_workflow_contract \
  orchestrator_harness.tests.test_reviewed_workflow \
  orchestrator_harness.tests.test_prompt_optin \
  orchestrator_harness.tests.test_manager_ownership -v
```

## What this does not prove

Typed validation establishes declared linkage, coverage, identity and revision
consistency—not evidence truth, semantic independence, actual agent compliance,
provider filesystem isolation or automatic client creation. Native direct
seed/observe/resume instructions are documented in [WORKFLOW.md](WORKFLOW.md#native-intake-and-startup),
with real hook trust, readiness and operator-authorized permissions as
prerequisites. A new real native v3/model run is still needed before claiming
provider-backed acceptance of this topology. Claude/Qwen v3 E2E is not established.
