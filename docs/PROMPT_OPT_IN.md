# Explicit Codex harness opt-in

Use an exact marker instead of asking the model to infer when you want the
harness. This additive native `UserPromptSubmit` hook is **Codex-only**. It does
not change Claude settings, launch a worker, reopen the runtime, or replace the
existing PostToolUse and Stop hooks.

**Fresh installation:** follow [INSTALL.md](../INSTALL.md) for full-source clone,
configuration, the safe additive native home-hook merge, trust, and startup.
Create the ignored, operator-owned `local-config/INSTALLATION.md` notes required
by that guide before preparation; they are not shipped with this repository.

## Everyday usage

1. Prepare the managed Codex ROOT **before starting the client**, following
   [INSTALL.md](../INSTALL.md), `QUICK_START.md`, and your required operator-owned
   `local-config/INSTALLATION.md`.
2. Start/resume Codex with the configured Codex home, at the **exact configured
   manager workspace root**. Review/enable the opt-in hook through native
   `/hooks` trust controls. Restart/resume after installing a hook; a file on
   disk is not proof an existing client has loaded or trusted it.
3. To use the harness, put this exact, case-sensitive text on the first line:

   ```text
   [harness]
   Implement the requested feature and run its focused tests.
   ```

   Put a nonempty task after the marker. LF and CRLF line endings both work.
   There must be **no leading blank line, indentation, spaces after the marker,
   quote prefix, or Markdown fence** in the actual submitted prompt. Merely
   mentioning `harness`, including `[harness]` later, or showing it in a quoted
   example does not activate the hook.
4. Without that first line, submit an ordinary prompt normally. The hook adds
   an explicit **OFF for this submission** instruction and starts nothing. A
   prior ON prompt is not a persistent toggle. Use the marker again for every
   new task/submission that should use the harness; continuation of an already
   accepted native handoff is not a new task (see below).

An unmarked message **does not cancel existing work** or remove worker ownership,
manager, safety, or cleanup obligations. Finish/retire existing lanes normally.
The always-installed native Stop hook still requires `CLOSED` before a final
response, even when the queue is empty. OFF is not a way to bypass it.

The coordinator's required **unmarked recipient bootstrap** may accept an existing
valid native manager handoff as its first tool operation. After genuine native
acceptance, it continues the **entire previously marked immutable contract**:
initial assignment launches (even when no workers existed at transfer), checks,
integration, repairs, independent audits and shutdown. OFF applies to new work
requested by the unmarked submission, not this existing contract. It does not
restrict the accepted coordinator to cleanup or to workers already running.

This is an instruction clarification, not automatic activation or an authority
grant. An offered handoff or a prompt claiming acceptance is insufficient; native
ownership, readiness and permission checks still apply. The unmarked hook path
does not inspect authority or preparation, start anything, or automatically set
up, prepare or reopen a runtime. An ordinary unmarked prompt without an accepted
handoff remains OFF and authorizes no new harness task.

### If a marked prompt is blocked

The hook explicitly blocks the prompt, rather than silently doing ordinary
coding. It never runs setup/preparation or retries anything for you. The
rejection identifies input, scope/configuration, identity, or readiness failure;
the detailed native diagnostic is obtained through the installed operator
instructions, not by echoing potentially sensitive input/configuration.

If the installed runtime is **CLOSED**, a marked prompt is expected to block.
Follow the [installation lifecycle instructions](../INSTALL.md#7-finish-then-prepare-the-next-task):

- **After any manager handoff:** use the
  [fresh-run archive/preparation procedure](WORKFLOW.md#fresh-run-after-a-handed-off-task)
  after the actual coordinator proves CLOSED and both clients are stopped.
  An ordinary terminal or the old planner cannot impersonate the coordinator.
- **No handoff and unchanged prepared source/configuration:** legacy native
  `harness setup` once, followed by preparation with the same recorded run ID,
  can reopen that existing ROOT. This does not apply to a source/hash mismatch.
- **New installation or changed authority inputs:** follow genuine fresh
  preparation after preserving the settled prior run. Do not fabricate/delete
  receipts, change a prepared provider binding, or blindly repeat failed setup.

Restart the correctly scoped client before submitting the marked task. Every
finished harness task ends CLOSED; no marked prompt starts a fresh run or reopens
anything automatically.

## What is deterministic

For a submission at the exact configured manager CWD, the hook:

- Matches only the exact first physical line `[harness]`.
- Requires a task, native `session_id` and `turn_id`, the Codex provider binding,
  and consistent inherited native/logical ROOT identities where supplied.
- Reads the genuine prepared ROOT run/session; it does not invent a second mode
  registry, bind an unbound native session, or persist prompts/mode receipts.
- Requires OPEN, then calls the existing full
  `scripts.prepare_root_launch.validate_prepared_root` validator. This checks
  receipt/configuration/workspace/hook hashes, prepared session, monitor owner
  and native live readiness, plus applicable health/service checks. Missing,
  stale, CLOSED, mismatched, and unhealthy preparation is rejected.
- Injects concise ROOT workflow instructions on acceptance, or explicit OFF
  instructions for an unmarked submission. Neither path starts services,
  setup, preparation, a worker, a model call, a retry, or a supervisor.

Validation is point-in-time, not a lease over all future model actions. Existing
native validation takes its ordinary record/admission locks; this hook does not
alter receipts, authority records, configuration, or runtime state. If the
prepared native session is `null`, validation does **not** prove exclusive native
thread ownership or bind it. Keep one manager/control host and do not run
concurrent ROOT sessions over the same runtime.

**Instruction delivery is not full workflow enforcement or a security sandbox.**
ON explicitly selects the configured
[`harness-outcome-workflow` skill](../skills/harness-outcome-workflow/SKILL.md).
For coding, planner ROOT decomposes once and transfers native manager authority
to a distinct integration/execution coordinator. That agent checks/integrates all
contributions and repairs the unified result itself, cycling with fresh independent
read-only auditing against the original prompt and complete outcome ledger.
Planner ROOT does not inspect/integrate code, delegate repairs or handle lifecycle
work after accepted transfer. See [WORKFLOW.md](WORKFLOW.md) for the exact handoff,
recipient bootstrap and missing-capability BLOCKED behavior. Noncoding requests
do not need artificial coding lanes/handoff.

Ask for real lane IDs/worktrees, unified revision, complete outcome/audit evidence
and CLOSED proof. Generic Codex subagents or hook presence prove none of these.
Schema checks reject missing coverage, stale revisions and declared nonindependence,
but do not prove evidence truth or full compliance. The native Stop gate still
requires CLOSED, not task success. Planner waits idle after transfer until CLOSED;
there is no Stop bypass. No external `$CODEX_HOME/skills` installation is required:
the hook supplies the configured portable skill's path explicitly.

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

## Validation

Focused contract tests:

```sh
python -B -m unittest orchestrator_harness.tests.test_prompt_optin -v
```

These tests label mocked preparation explicitly; they do not prove a live model
invocation or provider isolation. A disposable real setup/preparation/native
monitor check validates the lifecycle boundary separately. User-facing native
trust/loading must also be checked in the actual client after installation.

Native hook contract: [OpenAI hook documentation](https://learn.chatgpt.com/docs/hooks).

## Source upgrades

Changing pinned code/hooks may invalidate old receipts. Prove CLOSED first and
follow [the upgrade procedure](WORKFLOW.md#upgrade-an-existing-installed-harness-safely);
preserve/archive records and use diagnosed fresh preparation, never overwrite
receipts or blindly repeat same-run reopening after a hash mismatch.
