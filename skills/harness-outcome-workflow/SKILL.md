---
name: harness-outcome-workflow
description: Run explicitly selected harness coding work through independently reviewed bounded assignments, a separate integration coordinator, and exact-revision whole-result auditing. Use when the harness prompt selector or operator selects this workflow.
---

# Harness outcome workflow — v2

For `[harness]` coding requests, follow **plan → independent split review →
reasoned plan resolution → frozen handoff → coding → integrator ↔ independent
final auditor**. This skill guides agents using the native harness; selection is
not scheduling, permission, or proof of compliance. Explanation/research-only
requests need no artificial coding lanes or handoff; existing cleanup still applies.

## Planner ROOT: review the split, then hand off

1. Preserve the **entire original prompt**, constraints, authorization and relevant
   project context. Build a complete ledger of concrete original outcomes and
   whole-result integration criteria. Give each coding assignment exactly **one
   concrete task and one checkable outcome**, with scope, exclusions, dependencies,
   interfaces, deliverables and actual checks. Do not weaken requirements to pass.
2. Use as many **useful semantically independent** coding lanes as the work
   warrants, not the maximum count. One small lane is valid; multiple files or
   tests serving one outcome need not be split. Sequence genuinely coupled work;
   keep a single writer for shared paths and a valid dependency DAG. Read
   [the planning review guide](references/planning-review.md).
3. Obtain a **fresh independent initial split review before implementation**.
   Give a native read-only-product reviewer the original prompt/constraints,
   complete proposed ledger, **all** task cards, relevant context/interfaces and
   proposed role preferences. It checks coverage, meaningful independence,
   ownership/DAG, one goal per card, granularity versus coordination cost, and
   global criteria—not product completion. Use normal native RESULT, blocking
   `watch --until-actionable`, acknowledgement, settlement and retirement. Planner
   ROOT handles this planning-only lane **before** handoff, avoiding an authority
   deadlock; no worker or audit relay is introduced.
4. Reason about every actionable planning finding: revise the split or record a
   specific evidence-backed rejection. Reviewer PASS is **not** an authority gate.
   Freeze the resolved plan and review linkage using
   [the contract reference](references/contract.md). Record explicit authorized
   provider/model/options for reviewer, coding lanes, coordinator and final
   auditor. Do not invent premium tiers, auth scope, permissions or preferences.
5. Settle/retire the planning reviewer, then transfer the complete frozen contract
   to a **distinct real native manager conversation**, using
   [the native handoff](../../docs/WORKFLOW.md#explicit-native-manager-handoff).
   No supported authorized recipient capability means BLOCKED, not fake IDs or
   planner execution. Until acceptance, planner owns cleanup. After acceptance it
   performs **no** product checking, integration, repairs, repair delegation or
   lifecycle management; remain idle until coordinator proves CLOSED. On an
   interruption resume the exact coordinator, never spoof or reclaim its identity.

## Integration/execution coordinator: own the whole result

Read the immutable original contract and **every** assignment, including accepted
planning resolutions. Own a separate candidate branch/worktree and native coding
lanes with complete task cards and authorized preferences. Generic collaboration
subagents are not substitutes for native lanes.

Own native blocking watch, event handling, contribution checking, integration,
acceptance/retirement and shutdown. Check **all original outcomes and all overall
criteria together on the integrated candidate**, including interactions and
preserved behavior—not just each worker's isolated tests. Keep unrelated work and
original constraints intact. Git lane commits grant no push/promotion permission.

## Fresh final audit and integrator-owned repair loop

Launch a fresh independent read-only-product native auditor, neither author nor
integrator. Give it the entire original prompt/constraints, frozen ledger, **all**
assignments, relevant context/interfaces, exact candidate revision, actual checks
and known limitations. It independently inspects/tests whether **every original
outcome still works in the final merge and the overall request is satisfied**.
Findings return through genuine native RESULT/events, discovered by native watch.

Evaluate advisory findings with reasoned resolutions. **Repair justified failures
yourself**; do not send repairs to planner ROOT or original coding agents. Any
material candidate change invalidates the old audit: commit the new exact
revision, rerun **all** original outcome and global checks, then commission a
**fresh independent native auditor** for that revision. Repeat while justified
work remains and authorized resources permit. Never drop/relabel outcomes, weaken
criteria, reuse stale approval, count partial passes as whole-task success, or
chase reviewer PASS through endless retries. See the contract reference for
coverage, exact-revision audit and final-result records.

Reviews remain advisory, not vetoes. Typed validation checks declared linkage,
coverage, identities and revision; it cannot prove evidence truth, read-only
behavior, or semantic completion. Retain real commands/statuses and explain
rejected findings. A success claim requires all original outcomes and overall
criteria working together with current independent evidence and no justified
unresolved failure—not merely a reviewer verdict or CLOSED runtime.

Do not add a scheduler, wrapper, supervisor, retry controller, relay, transcript
watcher or automatic provider retries. If permissions, capabilities, ambiguity,
resource bounds or infrastructure prevent completion, report BLOCKED/INCOMPLETE
honestly. Settle owned lanes/events, run native `harness shutdown` and prove CLOSED
**even when incomplete**; a missing review cannot hold cleanup hostage. Report
exact revision, coverage/checks, review resolutions, actual lane identities and
lifecycle evidence. Preserve logs and failed audit evidence.
