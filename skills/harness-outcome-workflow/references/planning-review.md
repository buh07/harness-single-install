# Independent initial split review

This review evaluates a **plan before coding**, not the final product. Planner
ROOT still owns the runtime and may launch/settle this planning-only native lane.
It must finish reasoned resolution and settle/retire the lane before manager
handoff. The separate coordinator then owns implementation and all later repairs.

## Reviewer input and one bounded goal

Provide the unabridged original request and constraints; all proposed outcomes,
whole-result criteria and task cards; relevant repository context/interfaces;
shared-path ownership and dependencies; proposed checks; and explicit authorized
role preferences, including this reviewer. Its one goal is to identify whether
this split faithfully and efficiently enables the whole request. Product source
is read-only by assignment (not a claim of operating-system immutability); use
private evidence and no product-writing/resource lease.

Review these dimensions with specific references to outcomes/cards or source:

- **Coverage:** every requested behavior, constraint and preservation obligation
  has an owner/check; no worker receives only an integration summary.
- **Semantic independence:** lanes represent useful bounded outcomes rather than
  arbitrary file fragments or duplicate versions of the same change. Each card
  has exactly one concrete checkable goal; several files/tests may serve it.
- **Dependencies/interfaces:** the DAG is acyclic and explicit. Coupled consumers
  start from the verified predecessor result, not invented stubs or assumptions.
- **Ownership:** one writer per shared path at a time; candidate integration is
  separate from worker worktrees. Dependencies and scope transfers are clear.
- **Proportional granularity:** add lanes only when independent value exceeds
  coordination/context/integration cost. One lane is acceptable for a small
  change; unrelated outcomes should not be artificially bundled to avoid review.
- **Whole-result criteria:** all original outcomes must survive together after
  integration, with explicit interaction/regression checks and a fresh exact-
  revision final audit. Worker-local PASS alone is insufficient.
- **Execution feasibility:** authorized model/options, capabilities and bounds are
  explicit. No permission, premium tier or retry entitlement is invented.

## Resolution, freeze and native lifecycle

Return findings as an artifact attached to the ordinary native RESULT, with the
observed reviewer identity and reviewed plan linkage required by the contract
reference. Planner discovers the real completion through native blocking watch,
not transcript polling or an AI relay. Schema validity is not proof that review
or tests occurred.

Planner considers each actionable finding. Revise the plan when justified; when
rejecting advice, record a concrete reason/evidence. Preserve the reviewed proposal
and link the frozen final plan and resolutions so an old review cannot silently
be presented as reviewing an unrelated split. The final report must target the exact final plan hash: changing any hashed
plan content requires fresh review of that final plan, not attaching old approval
to the revision. Keep review effort proportionate, and stop honestly at authorized
bounds rather than running endless rounds merely to secure a PASS label.

The reviewer is advisory. It cannot veto the owner's resolution or shutdown.
Native completion acceptance records that its assigned review was delivered,
**not** that the reviewer approved the plan or product. Do not require a PASS
recommendation to transfer authority; do require the declared review and reasoned
resolution for a successful v2 reviewed-plan handoff. If review cannot be obtained
within authorized resources, record BLOCKED/INCOMPLETE and clean up rather than
claiming this stage happened or holding an OPEN runtime indefinitely.

Keep the ordinary lane RESULT, acknowledged event, completion-review/settlement
and retirement evidence. Only after the planning lane is fully settled and retired
may planner offer the immutable resolved contract. After accepted handoff it is
idle; the coordinator—not planner or initial coders—owns final-result repairs.
