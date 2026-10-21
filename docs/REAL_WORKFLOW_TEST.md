# Real-provider workflow acceptance test

## Status: passed for the tested Codex/Linux path (2026-10-21)

The real coding/integration/audit workflow completed using harness implementation
`569da07`. The unified todo-report product is commit
`8690780166218cc1ba9d2adf1d7523fda0620ff1` in the disposable test repository.
A distinct native coordinator integrated both coding contributions, checked the
complete original outcome ledger, obtained an independent native exact-revision
audit, accepted and retired the lanes, and ran native shutdown to CLOSED with the
monitor stopped. No product repair was needed after integration.

This confirms the tested successful path, **not every provider, permission mode,
marked resubmission or repair cycle**. The manager-only broad permission approval
and known continuation limitation below are part of the result.

## Task and method

The original task in a fresh disposable Git repository was:

> Build a small standard-library Python todo-report CLI. Read a JSON file containing
> tasks with title:string and done:boolean, output total/completed/open counts,
> support human-readable default and --json output plus --help; malformed JSON or
> invalid task data must fail clearly with nonzero exit and no traceback. Include
> automated tests and a concise usage example.

The planner recorded the original task, constraints, both assignments, three
outcomes and five whole-result criteria in the immutable handoff contract:

- **A:** a strictly validated `summarize_tasks` API and focused tests, with one
  checkable outcome and bounded file scope.
- **B:** the CLI, subprocess tests, usage documentation and example, with one
  checkable outcome. B must start from A's actual integrated implementation, not
  an invented stub or parallel substitute.
- **Unified result:** both outcomes remain correct together, the complete test
  suite and real CLI commands pass, errors are clear, and usage matches behavior.

A distinct integration/execution coordinator owns its own candidate worktree,
contribution checking, integration, repairs, acceptance, retirement and shutdown.
The planner performs no technical work after accepted handoff. A fresh native
product auditor must receive the original task, full outcome ledger and exact
unified revision, perform independent whole-result checks, and deliver its report
through native RESULT/events discovered with `watch --until-actionable`.

The test uses Codex CLI 0.163.0, genuine authenticated model calls, distinct native
manager conversations, private native homes and fresh disposable run state. Roles
use `gpt-6.1-sol`, reasoning effort `xhigh`, and explicit ordinary routing
`service_tier="default"`. No premium/fast routing was selected. Native client
transport handling remains unchanged; no scheduler, relay, provider-relaunch
loop, fabricated native identity or substitute hand-written worker RESULT is used.

## Acceptance evidence

| Boundary | Result |
| --- | --- |
| Real `[harness]` instruction selection | PASS: native prompt hook selects the installed versioned workflow skill |
| Complete bounded decomposition | PASS: original task, both assignments, three outcomes and five global criteria recorded |
| Genuine offer and acceptance | PASS: distinct authenticated native coordinator accepts the snapshotted contract as its first tool operation |
| First coding lane and integration | PASS: native completion delivered; coordinator passed 12 focused tests and 16 direct cases, then integrated actual A commit `7f802e1` |
| Dependent second coding lane | PASS: native completion at `8690780`, based on actual A `7f802e1`; coordinator checked scope/API and fast-forward integrated B |
| Unified integration and real product checks | PASS: exact `8690780`; suite ran 24 tests: 23 passed, one environment-dependent unreadable-file case skipped; all five whole-result criteria satisfied |
| Independent native exact-revision product audit | PASS: distinct native auditor checked exact `8690780`, reported all three outcomes and five global criteria satisfied, no findings; coordinator validated and accepted the report |
| Event settlement, retirement and CLOSED proof | PASS: audit completion accepted, all lanes retired; native shutdown returned CLOSED and stopped the monitor |

This table deliberately distinguishes native execution from schema/unit-test
coverage. CLOSED alone is cleanup evidence, not proof the requested task passed.

An additional independent advisory reviewer checked a fresh clone of exact
product revision `8690780`: the same 24-test suite ran with 23 passes and one
capability skip, and 35 extra CLI subprocess checks passed. Those covered seeded
valid inputs, invalid task data, malformed JSON, invalid UTF-8, missing files and
directories. It also checked standard-library-only imports, real summary-API use
and unchanged product source/revision, with no task findings. This is additional
verification, **not a replacement for the separate native product auditor**.

The genuine native auditor completed at the same exact revision with no findings:
23 suite tests passed, one unsupported-permission test was skipped, and 107
independent API checks passed across 143 recorded commands. It verified unchanged product source and HEAD,
then returned its own report through native completion. A transient
`PROVIDER_EXITED_NO_RESULT` diagnostic preceded the final valid completion; the
coordinator handled the diagnostic and continued native waiting, without a
provider relaunch. The coordinator then validated the exact-revision audit,
acknowledged and accepted its completion, retired the lane and shut down.

## Earlier attempts and diagnosed fixes

Failures were preserved, diagnosed and closed rather than hidden by a retry loop.

1. **Manager process visibility:** the default Linux workspace-write manager
   sandbox placed tools in a new PID namespace. A healthy host monitor was
   invisible to the manager's exact-process lookup, so handoff correctly failed
   closed. A separate provider-free native sandbox probe reproduced this; it was
   not evidence of successful coding. Monitor replacement would not fix that
   visibility boundary.
2. **Accepted continuation and hook identity:** after explicit user approval of
   manager-only `danger-full-access`, genuine handoff succeeded. The coordinator
   correctly refused new workers because the unmarked bootstrap's OFF wording
   contradicted continuation of an already marked contract. Host-side native
   hooks also needed to consume the genuine native JSON session identity rather
   than assume the shell's identity environment was inherited. Commit `84ae3f9`
   fixes these boundaries without granting new unmarked tasks authority or
   spoofing identities; independent focused coverage passed 103 tests.
3. **Unrelated process exit during cleanup:** a real isolated A worker completed
   its implementation, tests and own RESULT, but cleanup encountered an unrelated
   process disappearing during a global process snapshot. Commit `569da07`
   handles exited unrelated entries without weakening exact owned-process
   validation. Focused independent coverage passed 43 tests with three skips;
   the actual native owner then force-stopped the affected lane and proved CLOSED.

The completed run used fresh preparation and the one diagnosed manual retry of
the affected coding assignment, not an automatic continuation loop. Prior source revisions, results, sessions and failed
run records remain preserved privately. Earlier completed partial work is not
substituted for the completed run's own coding, integration and native audit evidence.

## Reproducing the workflow

Use [installation and preparation](../QUICK_START.md) and the
[handoff contract and migration instructions](WORKFLOW.md). Configure explicit
paths to a disposable product repository, harness installation, private native
home and persistent runtime storage. Use a genuinely fresh run and frozen source;
do not reuse receipts or reopen an offered/active epoch as a new task.

The tested Linux manager environment requires host process visibility. The user
explicitly approved **manager-only** `--sandbox danger-full-access`; this broadens
filesystem/process access and is not an automatic safe default. Do not silently
enable it for another installation. Both coding workers and the auditor retain
native `permission_mode=worker-isolated`; they must not inherit manager bypasses.
The narrower experimental executor topology considered during diagnosis was not
used and is not validated here.

The tested startup order matters:

1. Create the disposable product repository and private native home; configure
   the prompt selector and explicit local paths.
2. **Before fresh preparation opens the managed runtime**, create the real
   tool-free recipient seed conversation and record its genuine native session
   ID. Seeding after OPEN can invoke ROOT Stop obligations and prevent a clean
   seed exit; do not concurrently resume a still-running client.
3. Perform genuine fresh-run preparation to install the managed ROOT hooks and
   produce readiness evidence for the frozen harness/configuration.
4. Start the marked planner task and offer the full contract to that recipient.
5. Resume the exact recipient with the unmarked first-tool acceptance bootstrap.

The native client shape is:

```sh
# NATIVE_CODEX, PRIVATE_CODEX_HOME and MANAGER_WORKSPACE are explicit local paths.
# This broad manager mode requires the operator's separate approval.
CODEX_HOME="$PRIVATE_CODEX_HOME" "$NATIVE_CODEX" exec \
  --cd "$MANAGER_WORKSPACE" --sandbox danger-full-access \
  -m gpt-6.1-sol -c 'model_reasoning_effort="xhigh"' \
  -c 'service_tier="default"' --json '<manager prompt>'
```

That fragment shows the manager permission/model choices, not a standalone
installation script. Hooks must already be installed, enabled, loaded and trusted
through the native client's supported mechanism. Using the recipient ID obtained
before preparation, the planner receives the marked task and uses the normal
native offer command:

```sh
python -B -m orchestrator_harness.operator_launch --json manager handoff-offer \
  --to-native-session-id <actual-recipient-session> --contract <contract.json>
```

Resume that exact recipient with an **unmarked** bootstrap whose first tool is:

```sh
python -B -m orchestrator_harness.operator_launch --json manager handoff-accept \
  --offer-id <actual-offer> --contract-sha256 <returned-contract-hash>
```

After genuine acceptance, the recipient continues the existing marked immutable
contract, including initial coding launches. It does not gain authority for new
unmarked tasks. It uses native lane bootstrap/launch, `watch --until-actionable`,
event acknowledgement and settlement, completion review, retirement and
`harness shutdown`; it must prove CLOSED rather than merely observe an empty queue.
Planner ROOT stays idle until that cleanup proof.

## Scope and limits

- `[harness]` selects the installed skill and checks readiness. It does not
  automatically prepare a run, create native manager conversations, schedule
  work, or mechanically prove model compliance with the selected instructions.
- The auditor's product-read-only assignment is not a claim of OS-enforced
  filesystem immutability. Its scoped native worker may write its own protocol
  report; exact product revision and unchanged product source must be checked.
- Successful-path evidence does not prove an unexercised repair cycle. Unit and
  fixture coverage must remain labeled separately from actual model behavior.
- Known continuation limitation: a later **marked** submission to the active
  coordinator can return NOT_READY when the host prompt hook has only the native
  payload session ID, not the shell identity environment. Resume the **exact**
  authenticated coordinator with an **unmarked continuation of its already
  accepted immutable contract**. This grants no authority for a new unmarked
  task. Do not spoof identity variables or reprepare an active epoch. The tested
  fresh marked planner → unmarked first-tool acceptance path is distinct from
  this unvalidated marked-resubmission path.
- This is a Codex/Linux test, not a Claude end-to-end validation or a guarantee
  for every platform, provider or native CLI version.
- Private logs, native IDs, transcripts, credentials and machine paths are not
  part of the public report. Existing production sessions/configuration/runtime
  are preserved separately, not silently migrated or reopened by this test.
