# Real-provider workflow acceptance test

## Status: blocked before coding (2026-10-21)

The workflow implementation was published at commit
`3a19cf56c150993ec252cd737bef9e79149b248f`. The real-provider test below
**does not confirm the complete coding/integration/audit workflow works**.
It found a reproducible native Linux manager-environment limitation, which
provider-free unit/fixture tests had not exercised.

## Task and method

In a fresh disposable Git repository, the original task was:

> Build a small standard-library Python todo-report CLI. Read a JSON file containing
> tasks with title:string and done:boolean, output total/completed/open counts,
> support human-readable default and --json output plus --help; malformed JSON or
> invalid task data must fail clearly with nonzero exit and no traceback. Include
> automated tests and a concise usage example.

The intended decomposition was two bounded implementation assignments:

- **A:** strictly validated `summarize_tasks` API plus focused tests.
- **B:** CLI, subprocess tests, documentation and example, depending on A's actual
  integrated implementation rather than a stub.

A separate coordinator was to integrate in its own worktree, recheck every
outcome, and commission an independent read-only native auditor on the exact
unified revision. The planner was to stop doing technical work after handoff.

The test used Codex CLI 0.163.0, real authenticated provider calls, two distinct
provider-native conversations, and a new private native home and harness/runtime.
Every role was configured for `gpt-6.1-sol`, reasoning effort `xhigh`, and explicit
ordinary routing `service_tier="default"`. No premium/fast routing was selected.
Native client transport handling remained unchanged; no harness provider-relaunch
loop, fabricated session identity, or mocked worker result was used.

## Actual observations

| Boundary | Result |
| --- | --- |
| Remote publication and fresh clone | PASS: published revision and portable skill/docs present |
| Distinct real native coordinator conversation | PASS: authenticated, tool-free READY seed with native session metadata and usage |
| Real `[harness]` planner submission | PASS: native UserPromptSubmit output selected ON and explicitly named the installed workflow skill |
| Planner decomposition | PASS: native validation of complete contract, two task cards, three outcomes and five whole-result integration criteria |
| Genuine native handoff offer | BLOCKED: monitor exact-process readiness failed inside the manager's workspace-write sandbox |
| Accepted transfer / former-planner rejection | NOT REACHED |
| Coding lanes / integrated product / independent product audit | NOT REACHED; no product implementation was performed |
| Failed-attempt cleanup | PASS: native shutdown returned CLOSED with monitor-owner cleanup; exact planner client was interrupted only afterward and its exit proved |

The prepared host monitor was actually alive with a healthy heartbeat and the
recorded boot/start identity. The manager tool saw it as absent. A separate
**provider-free native sandbox diagnostic** reproduced the visibility boundary:

```sh
# NATIVE_CODEX is the verified native binary; WORKSPACE is a disposable repository.
"$NATIVE_CODEX" sandbox --permission-profile :workspace --cd "$WORKSPACE" -- \
  python3 -B -c 'import os; print(os.getpid())'
```

On the tested Linux installation, that command's Python process had PID 2 in a
new PID namespace. The harness's exact identity lookup for the outside monitor
returned unknown, and its liveness lookup returned false. The handoff correctly
failed closed with:

```text
initialized monitor incarnation is not live; explicitly run health monitor-recover
```

**Do not run monitor recovery merely because of this message when the host
monitor is healthy.** A replacement monitor would not fix manager PID-namespace
visibility. Do not weaken identity validation, forge receipts, spoof native
identities, or treat an OPEN run as complete.

## Permission boundary and next step

A manager environment must be able to observe the exact host monitor/controller
identities and perform authorized native cleanup. The tested default Linux
workspace-write manager environment did not provide that capability. Filesystem
write access alone does not establish process visibility.

An explicitly authorized manager-only `danger-full-access` native session is a
possible broader environment change, **not a tested fix in this report**. Coding
and audit workers must retain their scoped isolated permissions. A narrower native 0.163.0 candidate was identified by source inspection: a
dedicated manager native home can select a stdio executor running
`codex exec-server --listen stdio --linux-sandbox-pid-namespace=inherit` through
`environments.toml`. This retains filesystem confinement but permits signaling
other same-UID processes and introduces an experimental native executor topology.
The manager must load that native-home configuration (not use
`--ignore-user-config`); worker invocations must still ignore it and must not
inherit executor-connection environment overrides. See the exact-release
[Linux sandbox documentation](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/linux-sandbox/README.md#L90-L118)
and [native configuration-loading path](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/exec/src/lib.rs#L708-L728).
This candidate **has not been runtime-tested** and also requires explicit approval.
Its nested-worker isolation, hook association and exact executor cleanup remain
unproven. Do not add a custom supervisor/relay or silently switch environments.

The failed private attempt was closed and preserved. A corrected run requires
explicit approval of the selected manager environment, preservation of this
CLOSED attempt, genuine preparation of a fresh run, and an explicit bounded
native retry/resume. Then the remaining boundaries in the table must actually
run before claiming end-to-end success. Existing production preparation, hooks,
configuration, native sessions and CLOSED runtime were not migrated or reopened.

See [workflow setup and safe run migration](WORKFLOW.md). Full native metadata,
transcripts and process evidence are private; they are intentionally not shipped
in this public repository. Earlier unit and provider-free fixture coverage is
useful regression evidence, not a substitute for the missing real coding/audit
execution or proof of OS isolation.
