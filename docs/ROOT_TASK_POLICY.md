# Coding task policy: outcome workflow v1

The default for accepted `[harness]` coding submissions is the versioned
[`harness-outcome-workflow` skill](../skills/harness-outcome-workflow/SKILL.md),
not optional unselected guidance. [WORKFLOW.md](WORKFLOW.md) documents role
ownership, the supported native manager handoff and safe upgrade procedure.

Planner ROOT decomposes once. A distinct integration/execution coordinator then
owns checking, native coding assignments, integration, all repairs, manager
bookkeeping and shutdown. Every assignment has one concrete checkable outcome;
the coordinator receives **all** assignments and the complete original request
and outcome ledger. A fresh independent read-only auditor validates the unified
exact revision against all individual and cross-cutting outcomes. Coordinator
and auditor cycle directly; repairs never return to planner ROOT.

This policy grants no new permissions, model defaults or commit/publish authority.
Missing authorized preferences/capabilities mean clarification or BLOCKED, not
invented identities or fallback planner execution. Audits are advisory and may
not veto acceptance/shutdown. Preserve failures and report incomplete work
truthfully. Native Stop enforces cleanup/CLOSED, not successful implementation;
skill selection and schema validation do not mechanically enforce every action.

Manual non-selector use may explicitly select the same skill. Explanation-only
requests need no fake coding topology. Do not add wrappers, schedulers, relays,
retry supervisors or AI watchers to implement the policy.
