# Portable harness operating rules

Before any live use, read `QUICK_RULES.md` and follow `QUICK_START.md`. Consult `README.md`,
`orchestrator_harness/SPEC.md`, and `docs/HARNESS_WATCHER_GUIDE.md` for the full contracts.
Implementation workers follow the current scoped task card supplied by ROOT;
archived plans and historical ownership records do not grant additional work.

- Use the native harness directly. Do not add a runner, wrapper, scheduler, retry controller,
  collaboration relay, or AI watcher subagent.
- Keep the deterministic watcher diagnostic-only with `evaluator_enabled: false` unless the user
  explicitly authorizes a different topology.
- The harness and watcher never decide, schedule, repair, operate hardware, or replace the root
  orchestrator.
- The orchestrator must discover requests only through the native blocking wait.
- Keep source directories free of runtime output. Put local configuration under `local-config/`
  and all portable runtime output under `runtime/`.
- Keep the entire product portable: do not hardcode absolute machine, user,
  installation, workspace, or project paths in code, scripts, tests, or shipped
  configuration. Relative path constants are allowed only for files internal to
  the harness. Obtain external paths from explicit configuration, arguments,
  environment, operating-system discovery, or owned temporary fixtures. Never
  ship a configuration that silently selects a developer's external workspace.
- Prioritize the everyday user workflows and preserve working features. Before
  fixing a possible problem, weigh its likelihood in normal use and consequence.
  Fix common workflow failures and credible rare risks of lost work, security
  failures, silent corruption, or damage that is hard to undo.
- Prefer the smallest change that gets the real workflow working. Review affected
  callers and meaningful safety boundaries; private code needs to support its
  actual callers. Do not add impossible-input checks, hypothetical abstractions,
  or broad rewrites just to satisfy improbable tests.
- A clear error is usually enough for an uncommon unsupported use. Record
  lower-priority concerns briefly for the user rather than fixing them unasked.
  Finish when the everyday workflows work end to end and serious risks are
  covered; exhaustive internal-path audits and repeated whole-product review
  cohorts are not required.
- Assign product implementation to fresh, scoped implementation workers. In the
  outcome workflow v2, planning ROOT drafts the complete original outcome ledger,
  obtains a fresh independent native initial split review, records reasoned
  resolutions, settles/retires that planning-only lane, then makes the supported
  explicit native manager handoff with the frozen complete plan. Review useful
  semantic independence, coverage, interfaces, ownership/DAG and coordination
  cost—not maximum lane count; one small coding lane is valid. The
  execution/integration coordinator then exclusively owns the logical ROOT lifecycle, integration,
  checks, bounded integration repairs, acceptance, retirement, and shutdown. It
  receives the complete original prompt, every assigned outcome, all task cards,
  relevant context/interfaces and global criteria. It performs justified repairs
  itself (not via planner ROOT or original coders), reruns every original outcome
  and global check after material changes, and obtains a fresh independent native
  audit of the exact new revision. Success requires all original outcomes working
  together and the whole request satisfied; resource/permission limits mean an
  honest incomplete report plus cleanup, not weakened outcomes or stale approval.
  Transfer shared paths with one implementation writer at a time; planning ROOT does not
  code, check, integrate, or delegate repairs after handoff. This is an explicit
  ownership transfer, not an autonomous harness replacement for a manager.
- Testing, validation, and review subagents are advisory only. They can NEVER
  block progress, veto acceptance, require fixes, or prevent shutdown. ROOT alone
  judges their criticisms; under the outcome workflow that owner is the
  execution/integration coordinator, which performs justified bounded repairs.
  Reviewer PASS verdicts are never authority gates; owners record reasoned
  resolutions. V2 successful reviewed-plan handoff requires actual initial review
  evidence and settled retirement, not a reviewer PASS recommendation. Missing
  reviews cannot delay shutdown but cannot be claimed as completed. Actual checks
  are reported honestly. Advisory agents have read-only product source and private
  evidence,
  with no product writing/resource lease. When an auditor is an actual native
  lane, its normal identity, RESULT, settlement, retirement and Stop obligations
  still apply; advisory status never bypasses cleanup. A missing audit cannot
  hold shutdown hostage, but means the result is not independently verified and
  must be reported incomplete rather than successful.
- Deploy fresh independent testers for each completed implementation step and
  fresh semantic reviewers after the first full coding workflow, after retry/
  cancellation/service work, and with final testing before delivery. Use fixed
  completed source and private test copies so coding can continue. Scheduled
  advisory reports and verdicts never gate progress, acceptance or shutdown.
- Use a fresh epoch and fresh runtime directories for every live run.
- Preserve exact event identities: `data.signal_id` identifies the worker request; the envelope's
  top-level `event_id` is used for native acknowledgement.
- Validate response identities before atomic publication. Acknowledge only after successful
  handling.
- Stop cooperatively and verify exact PID plus creation identity. Never kill by broad name or
  command matching.
- Treat harness or watcher difficulty as a defect/configuration signal; do not hide it with support
  machinery.
