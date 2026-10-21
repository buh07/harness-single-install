---
name: harness-outcome-workflow
description: Run explicitly selected harness coding work through bounded implementation outcomes, a separate integration coordinator, and independent whole-result auditing. Use when the harness prompt selector or operator selects this workflow.
---

# Harness outcome workflow — v1

Use this workflow for coding requests selected by `[harness]`. It is a policy for
AI agents using the native harness, not an automatic scheduler or proof of task
completion. For explanation/research-only requests, answer without inventing
coding lanes or a manager handoff; retain existing lifecycle obligations.

## Planner ROOT: split once, then hand off

1. Preserve the **original prompt**, user constraints and authorization. Define a
   complete outcome ledger: individual concrete outcomes and cross-cutting checks
   proving the unified target fulfills the original request. Do not narrow the
   request to make it easier to pass.
2. Give each coding assignment **one concrete task and exactly one checkable
   outcome**. Several files/tests can serve that outcome. Record scope,
   exclusions, dependencies, acceptance criteria, deliverables and checks.
   Partition overlapping scopes to keep one writer at a time. Record explicitly
   authorized provider/model/options for every coding agent, coordinator and
   auditor; missing preferences/permissions require clarification, not invention.
3. Write and validate the contract using the schema/example in
   [references/contract.md](references/contract.md). Give the coordinator the
   **entire** original prompt, constraints, ledger and **all** assignments, not
   just an integration summary.
4. Transfer manager authority through the native two-phase handoff described in
   [../../docs/WORKFLOW.md](../../docs/WORKFLOW.md). The recipient must be an
   actual distinct provider-native manager conversation, not a coding lane with
   a new role label. If no authorized client/session-creation capability exists,
   report BLOCKED; never fake a session ID or silently make ROOT do execution.
   Until acceptance, ROOT retains ownership and must not abandon an OPEN runtime.
   After acceptance, planner ROOT performs **no** technical checking, integration,
   repair delegation, manager-event handling, acceptance, retirement or shutdown.
   It remains idle until the coordinator closes the runtime; there is no Stop
   bypass. If interrupted after transfer, resume the exact coordinator native
   conversation; never spoof its ID or silently reclaim authority. Do not add a runner, supervisor, queue, relay or retry controller.

## Integration/execution coordinator: own the unified target

Read the immutable handed-off contract. Own a dedicated candidate branch/worktree,
separate from implementation lanes. Launch the bounded native coding assignments
with their authorized preferences and complete native project task cards. Include
all acceptance criteria/deliverables and their reason; generic platform subagents
are not substitutes for native coding lanes.

You—not planner ROOT—own native blocking `watch --until-actionable`, event
handling/acknowledgement, contribution checking, completion review/acceptance,
integration, lane retirement and final shutdown. Integrate useful verified
contributions without mistaking partial progress for overall completion. Check
**every** assigned outcome again on the unified candidate plus every cross-cutting
criterion. Keep original constraints and unrelated work intact. Commits needed by
native Git lanes do not grant permission to publish, push or promote.

## Independent auditor and repair cycle

Launch a fresh, read-only native auditor that did not implement or integrate the
candidate. Supply the original prompt, constraints, complete ledger, **all**
assignments, exact integrated Git revision, checks/evidence and known limitations.
Its one goal is to independently inspect/test whether that exact unified result
fulfills the original request. Require meaningful actual checks, not approval of
worker summaries. Return findings through native lane RESULT/completion events;
the coordinator discovers them through native watch, not a custom relay.

The coordinator evaluates advisory findings and **repairs the candidate itself**;
it does not send repairs back to planner ROOT or silently launch repair workers.
Then commission fresh independent auditing of the new exact candidate. Material
changes invalidate prior audit approval; retain evidence but do not present old
checks as current. The audit schema in the reference checks full ledger coverage,
revision and declared independence, not whether evidence is true. An auditor is
advisory and has no veto over acceptance, progress or shutdown.

Continue the integration–audit cycle while justified work remains and authorized
resources permit. Do not retry infrastructure/provider failures automatically or
chase PASS indefinitely. Diagnose failures; stop and report BLOCKED/INCOMPLETE
when permissions, missing capabilities, resource limits or an unresolved ambiguity
prevent progress. Settle all owned lanes/events, use native `harness shutdown`,
and prove CLOSED before final response even for incomplete work. Report unified
revision, outcome coverage, actual checks, auditor findings, any reasoned rejected
findings, native lane identities and lifecycle evidence. CLOSED is not task success.
