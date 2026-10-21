# Explicit Codex harness opt-in: v3 external gateway

Put `[harness]` **alone on the first line of the newest submitted message**, then
a nonempty task. Exact case, no leading blank/indentation/quote/fence or trailing
spaces; LF/CRLF work. Mentioning the marker later or in an example does not select
it. Every new task needs its own marker; prior prompts do not create sticky mode.

```text
[harness]
Implement the feature and run the focused regression tests.
```

## What happens—and what does not

At the **exact configured manager CWD**, native UserPromptSubmit validates genuine
OPEN preparation/readiness and selects installed
[`harness-outcome-workflow` v3](../skills/harness-outcome-workflow/SKILL.md), supplying
its absolute path. After successful readiness, the authentic native marker hook
registers that exact original request and observed gateway identity as REGISTERED
intake before the first tool. This closes pre-submission manager/Stop ambiguity;
it is not manager authority, a sticky mode or a second actionable task queue. No
external skill install or automatic discovery is needed.

The outer conversation only submits the **complete original raw text unchanged**
and relays the final response. It is not planner, prepared logical ROOT, manager,
technical checker, repair router, watcher or cleanup owner. A separate genuine
native coordinator owns management from intake, commissions separate native
planner and independent split-reviewer lanes, then coding/integration/fresh-audit
repair work. See [actual native startup/intake](WORKFLOW.md#native-intake-and-startup).

**The hook does not create/resume a native conversation or launch a provider.**
Only one immutable intake belongs to a prepared run. A different later marked
request cannot overwrite it; use a fresh prepared run after owned cleanup. An
unmarked prompt creates no new registration.

A supported authorized native seed/observe/resume method and correct genuine
preparation are prerequisites. `[harness]` never sets up/reopens a runtime or grants
permissions. Absent capability is BLOCKED, not outer performing the selected task.
Noncoding selected requests also go to coordinator without artificial coding lanes.

Unmarked prompts receive OFF for **new** tasks and start nothing. They do not
cancel existing work. An authentic coordinator's unmarked first-tool acceptance
bootstrap continues the submitted immutable request, including initial lane
launches—not only cleanup—and grants no unrelated new unmarked task authority.

## Ownership, Stop and failure

Outer gateway submits exact UTF-8 request bytes—including marker, line endings,
Unicode and trailing whitespace—using `manager intake-submit`, advancing REGISTERED to PENDING with its designated
real coordinator. Do not paraphrase,
strip marker or normalize newlines. Use `--request-sha256` from native prompt
hook context so an altered copy is rejected. Submission is PENDING, not accepted/completed.
The actual designated coordinator accepts as first tool through `intake-accept`.
Gateway never resolves/binds prepared ROOT or obtains generic manager commands.

After **exact scoped confirmed native ownership**, the registered nonworker
gateway may finish/yield and receives no manager notices or manager delivery/
liveness receipts. It may report accepted, not task-complete. Actual coordinator
OPEN Stop still requires CLOSED even with empty queue. Unknown, stale, corrupt,
pending or identity-inconsistent ownership never gets a blanket Stop bypass just
because some manager exists. OFF cannot cancel owner obligations.

If dispatch fails, use [explicit recovery](WORKFLOW.md#failure-final-relay-and-recovery):
resume the designated actual coordinator to accept/shut down, or have an actual
independent operator terminal use narrow REGISTERED/PENDING never-accepted/no-work
`intake-abandon`.
Outer cannot
impersonate an owner, run shutdown, erase intake or claim CLOSED; prelaunch resources
may remain outstanding until supported cleanup. No provider retries or relay appear.

## Deterministic boundary and limits

The selector matches only newest exact first-line marker, exact configured root
CWD, Codex provider binding, native payload identity and consistent inherited
identities. It requires nonempty task/native turn identity and genuine OPEN
`validate_prepared_root` readiness: receipt/config/workspace/hook hashes, prepared
scope, actual native monitor owner and applicable health/service checks. Then it
atomically registers exact native prompt bytes/hash and gateway identity; an
altered copied request cannot replace that original. Missing,
stale, CLOSED, mismatched or unhealthy preparation blocks rather than silently
coding normally. The registered intake is provenance/lifecycle data, not an
actionable prompt queue. It does not bind gateway as ROOT, alter preparation
receipts or launch workers/services/models.

Marked requests at other/nested CWDs are inert; malformed input without trustworthy
scope fails explicitly. Readiness is point-in-time, not a future permission lease.
Do not run concurrent managers or multiple control hosts over one runtime.

**Instruction selection/typed records are not semantic proof or a security sandbox.**
Request real native role/lane identities, unified exact revision, complete original
outcome/global checks, current independent audit/resolutions and coordinator CLOSED
proof. Generic subagents or hook presence prove none of these. Initial review and
final audit are advisory, never PASS vetoes; missing evidence means incomplete,
not permission to hold cleanup hostage. Historical [v1 provider test](REAL_WORKFLOW_TEST.md)
and v2/v3 offline fixtures must not be relabeled as a native v3/model E2E.

## If a marked prompt is blocked

Follow [INSTALL.md](../INSTALL.md) and operator-owned ignored
`local-config/INSTALLATION.md`. Stop on scope/identity/readiness/hash diagnostics;
do not bypass gates, fabricate receipts or blindly repeat setup. A CLOSED runtime
must be genuinely prepared afresh after guarded archival. For v3 intake or legacy
handoff use [fresh-run procedure](WORKFLOW.md#fresh-run-after-a-handed-off-task), not
same-run legacy reopening. Changed source/hooks require [safe upgrade](WORKFLOW.md#upgrade-an-existing-installed-harness-safely).
Restart/resume correctly scoped native clients with hooks loaded/trusted before
new selection. Every managed task ends CLOSED; marker never opens it automatically.

## Scope, installation, and native trust

The native script is `scripts/harness_prompt_optin.py` with explicit absolute
`--harness-dir` and `--workspace` arguments. Its harness argument must identify
the source containing that script; its configured manager must match the
workspace. There are no machine-specific defaults.

Install one command hook under `UserPromptSubmit` in the selected native
`$CODEX_HOME/hooks.json` (merge rather than replace any existing groups). Use
absolute paths and suitable shell quoting; for example, with operator-selected
paths:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "<python> -B <harness>/scripts/harness_prompt_optin.py --harness-dir <harness> --workspace <manager-workspace>"
          }
        ]
      }
    ]
  }
}
```

This is a template, not a runnable shipped configuration. Existing project
`.codex/hooks.json`, `.codex/config.toml`, binding, prelaunch receipts and hashed
native harness inputs stay unchanged. The native home file is an installation
extension, not a new prepared-authority record. Review the new command in the
native trust UI; never forge trusted hashes or disable native trust checks.
Client support, hooks enablement, and trust are prerequisites: an untrusted,
disabled, or undiscovered hook provides **no opt-in guarantee**. Run the native
hook review again if its command/contents change.

The hook returns `{}` for a valid payload whose normalized CWD is any other
workspace or a nested directory, including an independent nested Git project.
It does not search parents or launch anything there, even for `[harness]`.
Start from the manager root to opt in. Invalid JSON without a trustworthy CWD
cannot be safely scoped and yields an explicit block. Input is bounded to
4,000,000 UTF-8 bytes, duplicate/nonfinite JSON is rejected, and failures use
native exit-zero `decision: block` JSON without echoing prompt/configuration
contents. As with any native command hook, a killed interpreter, unavailable
executable, disabled hooks, or native-client failure lies outside its ability to
return a decision; do not treat hook presence as an unconditional security gate.

To remove this opt-in feature, remove only its UserPromptSubmit command/group
from the native home hook file and restart Codex. Do not remove the original
PostToolUse/Stop hooks while managed work exists. Claude is unaffected either way.

## Validation and evidence limits

```sh
python -B -m unittest orchestrator_harness.tests.test_prompt_optin -v
```

Offline fixtures explicitly use test identities/preparation doubles; they do not
prove live provider/model behavior, native isolation or client trust/loading. V1
[real-provider report](REAL_WORKFLOW_TEST.md) stays unchanged historical evidence.
Check target-native discovery/trust explicitly after installing.

Source updates may invalidate pinned receipts; [preserve and genuinely prepare
afresh](WORKFLOW.md#upgrade-an-existing-installed-harness-safely), never overwrite
receipts or silently reopen. Native hook contract:
[OpenAI hook documentation](https://learn.chatgpt.com/docs/hooks).
