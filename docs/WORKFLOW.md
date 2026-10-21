# Default outcome workflow and manager handoff

Accepted Codex `[harness]` submissions explicitly select
[`skills/harness-outcome-workflow/SKILL.md`](../skills/harness-outcome-workflow/SKILL.md),
version 2. No external skill installation or automatic model discovery is needed:
the hook gives the configured skill's absolute path. The hook selects instructions
and validates readiness; it does **not** execute this workflow or prove compliance.

The [historical real-provider report](REAL_WORKFLOW_TEST.md) records the completed
**v1** Codex/Linux coding → integration → independent native audit → CLOSED test.
It does **not** demonstrate the new v2 initial split review or a real repair
iteration; v2 adds offline behavioral/repair fixtures and independent source
review, not another provider-backed E2E. Other providers are not implied.

## Roles and completion

1. **Planner ROOT** preserves the original prompt, constraints, context/interfaces
   and full ledger. Each useful coding assignment has one concrete checkable goal,
   explicit ownership/dependencies, deliverables and checks. Include overall
   interaction/regression criteria and authorized provider/model/options for
   **every** role, including the initial reviewer. Choose as many useful independent
   lanes as warranted, not maximum count. One small lane is valid; genuinely
   coupled outcomes may require sequencing rather than artificial parallelism.
2. **Independent initial split reviewer** is a fresh read-only-product native lane
   before implementation. It receives the whole original request, all proposed
   cards, relevant context/interfaces and criteria. It evaluates coverage,
   semantic independence, dependency DAG, shared-path ownership, one goal per
   assignment, granularity/coordination cost and overall criteria. It reviews the
   **plan**, not the finished product. See the skill's
   [planning-review guide](../skills/harness-outcome-workflow/references/planning-review.md).
3. **Planner resolves the review**, revising justified problems or explaining
   declined advice with reasons. Record current-plan linkage and authentic normal
   RESULT/evidence. Material changes require a review of the final exact plan;
   do not attach an unrelated old review. Reviewer PASS is not a gate: owner
   judgment resolves advice. Settle/retire the planning lane through native watch,
   events and completion review **before handoff**; planner still has authority
   for these planning-only actions. This avoids a transfer deadlock with active
   reviewer work. A retired initial-review epoch may be followed by the normal
   handoff epoch; do not fabricate freshness/preparation receipts.
4. **Integration/execution coordinator** becomes the distinct native manager
   through the explicit handoff below. It receives the immutable resolved plan,
   original prompt, **all** cards/outcomes and whole-result criteria. It launches
   bounded coding assignments, checks/integrates contributions into its dedicated
   candidate worktree, and reruns every original outcome/global check together.
   After accepted transfer planner is idle: no product checking, integration,
   repairs, repair delegation, event management, acceptance or shutdown.
5. **Independent final auditor** is a fresh read-only-product native worker,
   neither author nor integrator, with no product-writing/resource lease. It
   receives the full original contract, all cards, context/interfaces, exact
   candidate revision, actual checks and known limitations. It independently
   tests whether **all original outcomes work together and the overall task was
   completed as desired**, not merely whether worker summaries sound plausible.
   Return structured audit evidence through genuine native RESULT/events;
   coordinator discovers it using native `watch --until-actionable`, not a relay.
6. **Integrator ↔ fresh auditor:** the coordinator judges advisory findings and
   makes justified repairs **itself**, never through ROOT or original coders. Any
   material candidate change invalidates the previous audit. Commit the new exact
   revision, rerun **all** original outcomes and overall criteria, then commission
   a fresh independent native auditor. Preserve old findings/evidence as history,
   not current approval. Continue until the unified result meets the entire
   original request or authorized resources/capabilities prevent further progress.

Auditors are advisory, never autonomous vetoes. The owner records reasoned
resolutions rather than chasing reviewer PASS. Typed validation checks declared
review linkage, observed identity comparisons, coverage and revision consistency;
it cannot prove truth, read-only behavior or semantic success. Native lane
acceptance records the assigned review was delivered, not that advice is binding.
See the [contract/reference](../skills/harness-outcome-workflow/references/contract.md)
for initial review, exact-revision audit and final-result records.

Claim success only when **every original outcome and all overall criteria work
together on the exact current target**, with independent evidence and no justified
unresolved failure. Never drop/weaken/relabel requirements, accept a partial PASS,
reuse stale audit evidence or call CLOSED task success. If permissions, ambiguity,
missing capabilities, resource bounds or infrastructure block progress, report
BLOCKED/INCOMPLETE honestly; no automatic provider retries or endless PASS chase.
Always settle owned lanes/events, shut down and prove CLOSED even when incomplete.
A missing review cannot hold cleanup hostage but must not be claimed completed.
A noncoding marked question needs no artificial coding lanes or handoff.

## Explicit native manager handoff

This is authority transfer between **distinct real provider-native manager
conversations**, not relabeling an ordinary coding lane. Initial support requires
the coordinator to use the same provider as prepared ROOT. It does not create a
client or call a provider API. Starting another client may cost money and requires
available authorized tooling; do not infer broader external permissions.

After completing/resolving independent initial review and settling/retiring its
normal native lane, the planner writes the valid final v2 contract (see the skill's
[contract reference](../skills/harness-outcome-workflow/references/contract.md))
and creates/identifies the actual distinct coordinator native conversation,
observing its provider-native conversation/session ID through the provider
client's supported metadata. Keep that conversation idle until the offer is
ready, or resume that exact ID later; do not create a different second client
conversation. Provider-native metadata discovery is not a product tool operation.
A made-up ID, ordinary collaboration subagent ID or lane session is not sufficient.
If no supported way exists to create/observe that conversation, stop honestly as
BLOCKED rather than making planner ROOT execute the task.

For the tested Codex `exec` seed/resume method, finish the tool-free recipient
seed and record its genuine native ID **before fresh preparation opens the
managed runtime**. Then prepare and start the marked planner. Otherwise ROOT Stop
obligations can hold the seed client open; never concurrently resume that running
client. Native app-server idle-thread creation is a different method and was not
end-to-end tested here. See the [tested startup order](REAL_WORKFLOW_TEST.md#reproducing-the-workflow).

From the harness source root, in the planner's native session:

```sh
python -B -m orchestrator_harness.operator_launch --json manager handoff-offer \
  --to-native-session-id <actual-distinct-native-session> --contract <contract.json>
```

Keep the returned `offer_id`, `contract_sha256` and evidence. The offer snapshots
the validated contract. Planner still owns the run until acceptance; an offer
alone never permits abandonment or concurrent managers.

Use that exact recipient conversation at the **same configured manager workspace**, with native
hooks loaded/trusted and the same prepared harness context. For Codex, send an
**unmarked** bootstrap instruction containing the exact acceptance command,
offer/hash and harness path. Do not prefix this bootstrap with `[harness]`: it is
not yet the owner. Its **first tool operation must accept**; reading files with a
tool before acceptance can correctly fail the native ownership check.

In the coordinator's actual native environment, with its observed identity:

```sh
python -B -m orchestrator_harness.operator_launch --json manager handoff-accept \
  --offer-id <returned-offer-id> --contract-sha256 <returned-contract-sha256>
```

Do not forge identity environment variables. After successful acceptance, load
this workflow skill and immutable contract evidence. Acceptance transfers native
manager authority; it does not rewrite original preparation receipts or create a
second runtime. The bootstrap's OFF selection applies to new unmarked tasks,
not continuation of the previously marked immutable contract. After genuine
acceptance, the coordinator executes that entire contract, including **initial
assignment launches even when no workers existed at transfer**, integration,
checks, repairs, independent audits and shutdown. It is not limited to existing
workers or cleanup. An offer or a prompt claiming acceptance grants no authority;
all native ownership, readiness and permission checks still apply. The unmarked
hook path remains read-only and never automatically sets up, prepares or reopens
a runtime. The planner remains idle until coordinator proves CLOSED;
there is no early Stop exemption. Only the coordinator consumes native manager
work or performs lifecycle actions after transfer. Never add a custom supervisor,
retry controller, watcher agent, transcript reader or event relay.

## Interrupted handoff and recovery

Before acceptance, planner still owns cleanup: if no authorized recipient can
accept, preserve the offer/contract and shut down rather than abandon OPEN.
After ACTIVE transfer, resume the **exact coordinator native conversation** if
its client exits. Planner must not spoof its identity or take ownership back.
If that conversation cannot be resumed, preserve native records and report the
blocker for explicit operator recovery; do not invent a supervisor or bypass
native ownership. Original preparation receipts remain historical authority.

## Fresh run after a handed-off task

An OFFERED/ACTIVE ownership record belongs to exactly one prepared workflow epoch.
Handoff initializes that native epoch before coding bootstrap. Retirement of the
last contribution keeps it open for auditing/repairs; native shutdown closes it. Do not
use the legacy terminal `harness setup` reopening recipe for the next independent
workflow after a handoff. The actual execution coordinator must first complete
native shutdown and prove CLOSED. Stop **both** planner and coordinator clients
and ensure no other operator/client uses this runtime during archival.

Before moving runtime records, inspect `git -C "$PRODUCT_WORKSPACE" worktree list
--porcelain`. Retired/abandoned lane worktrees can remain under the runtime even
after CLOSED. Preserve each such **registered** worktree outside the runtime using
Git, with explicit unused destination paths:

```sh
git -C "$PRODUCT_WORKSPACE" worktree move -- "$OLD_LANE" "$PRESERVED_LANE"
```

Do not blindly rename a runtime containing linked worktrees, prune away their
registration, delete branches, or force-remove dirty/unmerged work. Keep their
commits, files and branches. Stop on locked/submodule/other move failures for
explicit operator reconciliation; the archival example below refuses any
registered worktree still under the runtime. Historical lane records retain their
original paths; do not rewrite them to manufacture fresh authority.

Choose an unused absolute `ARCHIVE_DIR` on your configured persistent storage,
outside the runtime being archived. Keep it private and retain it; this is
preservation, not deleting receipts or manufacturing new readiness. From the
harness source root, export `HARNESS_DIR`, `ARCHIVE_DIR`, `WORKSPACE`, `PYTHON`,
and a genuinely new `HARNESS_RUN_ID`, then run this **one explicit migration**:

```sh
"$PYTHON" -B - <<'PY_ARCHIVE'
import os
import subprocess
from pathlib import Path
from orchestrator_harness.git_source import environment
from orchestrator_harness.config import load_config
from orchestrator_harness.setup import read_runtime_state
from orchestrator_harness.shutdown import prove_runtime_closed

harness = Path(os.environ["HARNESS_DIR"]).absolute()
config = load_config(harness)
archive = Path(os.environ["ARCHIVE_DIR"])
if not archive.is_absolute() or archive.exists():
    raise SystemExit("Select an unused absolute archive directory")
if archive.resolve().is_relative_to(config.runtime_root.resolve()):
    raise SystemExit("Archive must be outside the runtime being preserved")
if (read_runtime_state(config.runtime_root) or {}).get("state") != "CLOSED":
    raise SystemExit("Actual owner must finish shutdown first")
prove_runtime_closed(config.runtime_root, config.root_workspace, harness)
listing = subprocess.run(["git", "-C", str(config.root_workspace), "worktree", "list",
    "--porcelain", "-z"], env=environment(), check=True, stdout=subprocess.PIPE)
for field in listing.stdout.split(b"\0"):
    if field.startswith(b"worktree "):
        worktree = Path(os.fsdecode(field[len(b"worktree "):]))
        if worktree.resolve().is_relative_to(config.runtime_root.resolve()):
            raise SystemExit("Preserve retained linked worktrees with git worktree move first")
records = config.manager_workspace / ".agent-workspace"
paths = [(config.runtime_root, "runtime")]
paths += [(records / name, name) for name in (
    "ROOT_SESSION.json", "ROOT_PRELAUNCH_SETUP.json", "ROOT_PRELAUNCH_ATTEMPT.json"
) if (records / name).exists()]
archive.mkdir(mode=0o700)
for source, name in paths:
    source.rename(archive / name)
print("Preserved prior runtime and run records at", archive)
PY_ARCHIVE
```

The rename requires the archive and each source to be on the same filesystem.
If it fails partway, stop and reconcile the preserved paths; do not automatically
retry or prepare over a partial migration. Do not archive provider homes/native
session databases or unrelated research records.

Only after all moves succeed, perform genuine fresh preparation:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B scripts/prepare_root_launch.py \
  --harness-dir "$HARNESS_DIR" --workspace "$WORKSPACE" \
  --run-id "$HARNESS_RUN_ID" --provider codex
```

Use the configured provider rather than `codex` for an explicitly selected other
provider. Stop and diagnose any failure. Restart the appropriate native planner
client, then submit the next `[harness]` task. New preparation creates genuine new
records; the archive stays intact and the previous handoff never carries forward.

## Upgrade an existing installed harness safely

V2 adds independently reviewed planning and integrator-owned full-check/fresh-audit
repair cycles. Saved v1 records remain readable as **legacy** evidence; do not
rewrite them into v2 review receipts or claim the historical native v1 test covers
v2. Installing v2 source does not activate a runtime or run a new provider test.

Freeze source/configuration during a live run. Before replacing installed code,
settle all lanes and prove CLOSED. Changes to hashed source/hooks may invalidate
existing prelaunch receipts; a previously valid receipt is not proof the new
source is prepared. Do not overwrite, fabricate or silently delete receipts, and
do not repeat same-run reopening after a hash-mismatch diagnostic.

Diagnose the mismatch, preserve/archive the prior run's records on the operator's
configured storage, and follow native **fresh preparation** with a new run and
fresh runtime records only after confirming the old run is closed. Keep archives
and native sessions/logs intact. This upgrade does not automatically set up,
repair or reopen production. Revisit native hook trust if changed contents require
it. A source install/test pass alone does not prove a real model-backed handoff,
coding lane or completed repair/audit cycle.
