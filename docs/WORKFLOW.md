# External gateway and default outcome workflow v3

The outer conversation sits **completely outside** managed execution. It submits
exact original request bytes and relays the final report. The distinct native
execution/integration coordinator is prepared logical ROOT and manager **from
intake**. Separate native planner, independent split reviewer, coding lanes and
fresh whole-result auditors work under that coordinator, not under outer.

Accepted Codex `[harness]` messages explicitly select
[`harness-outcome-workflow`](../skills/harness-outcome-workflow/SKILL.md).
The hook supplies the installed skill path; no external skill install is needed.
After genuine readiness the native marker hook registers the exact original
request and observed gateway as REGISTERED intake before any tool. This is narrow
request provenance/nonmanager identity—not a provider launcher, new queue or
sticky mode. Selection/registration does not execute the skill.

## Roles and completion

1. **Outer gateway:** submit the whole original request unchanged (including the
   marker, Unicode, line endings and trailing whitespace), initiate only the
   authorized thin native dispatch, and relay the final response. No decomposition,
   technical checks, events/watch, repairs, acceptance, retirement or shutdown.
2. **Native coordinator:** accept the immutable intake before managing work. It
   commissions a separate read-only-product native **planner**, giving the whole
   request, constraints, context and authorized preferences. Planner's single
   bounded deliverable is the original-outcome ledger, all concrete coding cards
   and global criteria. Manager is not a planner disguised by a role label.
3. **Independent split reviewer:** a distinct fresh read-only-product native lane
   receives the entire proposed ledger, **all** cards, original request, context/
   interfaces and preferences. Review coverage, semantic independence, DAG/shared
   ownership, one concrete checkable goal per card, coordination cost and global
   criteria. One small coding lane is valid. See [planning review](../skills/harness-outcome-workflow/references/planning-review.md).
4. **Planner resolves/revises** justified findings or explains declined advice;
   coordinator owns native communications and lifecycle. Material changes require
   review of the exact final plan. Freeze actual current planner/reviewer
   provenance and all original outcomes—never synthetic receipts or stale review.
   Both lanes use ordinary RESULT/events, native blocking watch, settlement and
   retirement. Reviewer advice is not a PASS veto.
5. **Coordinator launches coding lanes**, each with one concrete task and one
   checkable outcome, complete bounded card and explicit authorized preferences.
   Keep one writer per shared path; sequence dependencies. It checks/integrates
   contributions in its separate candidate and checks **all original outcomes and
   global criteria together**, including interactions and preserved behavior.
6. **Fresh independent whole-result auditor:** receives the original request,
   frozen entire ledger, every card, context/interfaces, exact candidate revision,
   actual checks and limitations. It independently inspects/tests the unified
   target, not only isolated worker summaries. Use genuine native RESULT/watch.
7. **Coordinator ↔ fresh auditor:** coordinator judges advisory findings and makes
   justified repairs **itself**, never through outer, planner or original coders.
   Every material change needs a new exact commit, rerun of **all** original
   outcome/global checks and a fresh independent auditor. Keep failed evidence.
   Continue within authorized resources until the whole request works, or report
   honest BLOCKED/INCOMPLETE, not weakened outcomes or a partial PASS.

Coordinator alone handles native events, acceptance, retirement and shutdown.
Auditors are advisory, never vetoes; reasoned rejection of incorrect findings is
allowed. Missing required review means incomplete but cannot hold cleanup hostage.
Typed validation checks linkage/identity/coverage/revision consistency, not truth
or semantic completion. CLOSED proves cleanup, not success. Noncoding selected
requests still go to coordinator without artificial coding contracts/lanes or
outer fallback; it fulfills them and owns shutdown. The detailed planning/coding/
audit stages above describe coding work.

## Native intake and startup

Prerequisites: a full configured installation and native trusted/loaded hooks
([INSTALL.md](../INSTALL.md)), a fresh run, authorized provider access/preferences,
and a supported way to **create, observe and resume a distinct genuine native
coordinator conversation**. This product deliberately adds no provider launcher,
scheduler, relay or supervisor. A hook cannot create that conversation. If native
capability or permission is absent, report BLOCKED; do not promise automatic use.

### 1. Seed a genuine coordinator before OPEN

The Codex CLI shape below is an executable operator procedure for clients with
`exec --json` and `exec resume`; inspect your installed native `--help` first.
Choose existing absolute `HARNESS_DIR`, `WORKSPACE`, `CODEX_HOME`, `PYTHON`,
`CODEX_BIN` and an unused private persistent `EVIDENCE_DIR`. Export `CODEX_HOME`
for both native calls (as in INSTALL); use no copied authentication. Set explicit authorized
`CODEX_MODEL`, `CODEX_REASONING` and `CODEX_SERVICE_TIER`. Shell snippets are POSIX,
not Windows quoting recipes. Do not silently enable danger-full-access or bypass
hooks, sandbox, approval, trust or health gates. Native/model calls may cost money.

Before preparation opens the runtime, with any previous run proved CLOSED:

```sh
mkdir -m 700 "$EVIDENCE_DIR"
cd "$WORKSPACE"
"$CODEX_BIN" exec --cd "$WORKSPACE" --json -m "$CODEX_MODEL" \
  -c "model_reasoning_effort=\"$CODEX_REASONING\"" \
  -c "service_tier=\"$CODEX_SERVICE_TIER\"" \
  'Do not use tools. This is an idle coordinator seed; reply READY only.' \
  > "$EVIDENCE_DIR/coordinator-seed.jsonl"
```

Wait for a successful **client exit**, then read the actual native `thread.started`
`thread_id` in that JSONL and record it as `COORDINATOR_NATIVE_ID`. Never invent an
ID, use a collaboration-agent ID, resume `--last`, or concurrently resume the still
running seed. Preserve native sessions/logs; no auth copy or new native home is
required by this procedure. Idle-thread creation via another native API is valid
only if actually supported/authorized; it is not automatically supplied here.

### 2. Prepare that coordinator, not outer

From the harness installation, create genuine fresh preparation. Its initial
native binding may remain unset; the immutable intake designates the genuine
seeded coordinator. Actual native first-tool acceptance performs the supported
one-time bind to that observed session—not the gateway.

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B scripts/prepare_root_launch.py \
  --harness-dir "$HARNESS_DIR" --workspace "$WORKSPACE" \
  --run-id "$HARNESS_RUN_ID" --provider codex
```

Require successful readiness. Never set `CODEX_THREAD_ID`/other identity variables
to impersonate this target, run the ROOT usage collector on the gateway, replace
preparation receipts, or change a provider binding. The gateway is not the prepared
ROOT. Keep one control host/runtime and frozen source/configuration.

### 3. Submit unchanged raw text from actual gateway

Start/resume the separate outer Codex at the exact configured manager root with
native hooks loaded/trusted. Submit `[harness]` on the exact first line and a
nonempty request. After readiness the authentic native prompt hook records exact
original bytes/hash and gateway identity in REGISTERED intake, before even a
skill-read tool can be mistaken for manager activity. The selected gateway writes
the **entire native submitted text**
to a private UTF-8 file without trimming or newline conversion. Preserve marker
and trailing whitespace; if a reliable exact copy is unavailable, stop rather
than silently paraphrase. From the actual observed gateway environment:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m orchestrator_harness.operator_launch --json manager intake-submit \
  --to-native-session-id "$COORDINATOR_NATIVE_ID" --request-file "$REQUEST_FILE" \
  --request-sha256 "$REQUEST_SHA256"
```

Use `REQUEST_SHA256` supplied by the native prompt hook for that original message,
not a replacement hash computed from a possibly altered copy. Submission rejects
a copied file whose exact bytes differ from that native-message hash. Keep returned
intake ID, request SHA256 and evidence paths. Submission advances REGISTERED to
PENDING with the designated coordinator—**not accepted ownership or task completion**. It neither grants gateway manager
access nor rewrites ROOT/preparation records. The immutable request hash covers
the exact decoded UTF-8 bytes, not a normalized task summary. The intake stores
request data/provenance, not a second actionable manager queue. A different new
marked request cannot overwrite this intake; independent tasks require fresh
preparation after owned CLOSED cleanup. Unmarked prompts create no new intake.

### 4. Resume the exact coordinator; accept as first tool

Use the native client directly, only when authorized. In the same configured
workspace/native home, resume the actual seed ID with an **unmarked** bootstrap:

```sh
cd "$WORKSPACE"
"$CODEX_BIN" exec resume "$COORDINATOR_NATIVE_ID" --json -m "$CODEX_MODEL" \
  -c "model_reasoning_effort=\"$CODEX_REASONING\"" \
  -c "service_tier=\"$CODEX_SERVICE_TIER\"" \
  --output-last-message "$EVIDENCE_DIR/coordinator-final.txt" \
  "Your first tool operation must run: cd '$HARNESS_DIR' && '$PYTHON' -B -m orchestrator_harness.operator_launch --json manager intake-accept --intake-id '$INTAKE_ID' --request-sha256 '$REQUEST_SHA256'. After successful acceptance load '$HARNESS_DIR/skills/harness-outcome-workflow/SKILL.md' and execute the entire immutable original request. You own planner/review/coding/audit and shutdown, even if the task is blocked. Do not read files or run another tool before acceptance." \
  > "$EVIDENCE_DIR/coordinator-execution.jsonl"
```

The fragment assumes ordinary paths without single quotes; use a native argument
API or correct shell quoting otherwise. Do not wrap this in a custom launcher or
retry controller. Native permissions and provider options remain the operator's
explicit choices; the seed grants no additional inherited authorization.
An unmarked bootstrap continues the submitted immutable request after actual
acceptance; it authorizes no unrelated new unmarked task.

Actual acceptance validates native identity, designated target, prepared scope,
request hash and readiness. If native ROOT is unbound it uses the existing supported
one-time bind API with the **actual observed** coordinator identity, then publishes
accepted ownership. A crash after binding leaves PENDING (no manager authority);
only the exact designated coordinator may retry acceptance. Existing receipts are
not rewritten or fabricated. Only confirmed ACTIVE ownership permits manager work.
The exact registered gateway can finish/yield without consuming manager events,
writing manager delivery/liveness receipts or running shutdown. This says
**accepted, not completed**. Pending, unknown, stale, corrupt or inconsistent
ownership is not a Stop bypass. Actual manager OPEN Stop still requires CLOSED.

### 5. Freeze the separate native plan

Coordinator commissions and settles/retires actual planner and split-review lanes,
then validates/freezes their resolved complete v3 contract:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m orchestrator_harness.operator_launch --json manager plan-freeze \
  --intake-id "$INTAKE_ID" --contract "$CONTRACT_FILE"
```

See [record reference](../skills/harness-outcome-workflow/references/contract.md)
for original-byte linkage, plan/review hashes and real native evidence. Generic
subagents or synthetic JSON examples cannot substitute for native provenance.
After freeze coordinator executes all cards and owns the full repair/audit loop.

## Failure, final relay and recovery

Before dispatch, absent capability means BLOCKED, not outer execution. After
PENDING submission, dispatch failure is **not** successful ownership. Resume the
**exact designated authentic coordinator** to accept and perform owned shutdown,
reporting the task BLOCKED if necessary. Gateway never gets generic manager
commands or lifecycle fallback.

If that native conversation cannot resume, an **independent actual operator
terminal** may abandon a REGISTERED or PENDING never-accepted, never-started
intake and clean up:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m orchestrator_harness.operator_launch --json manager intake-abandon \
  --intake-id "$INTAKE_ID" --request-sha256 "$REQUEST_SHA256"
```

This is not an outer/gateway tool operation. Use a genuine terminal with no
provider-native, logical ROOT or worker identity environment; do not strip identity
inside an agent shell to impersonate an operator. The command requires exact
REGISTERED/PENDING intake/hash/scope, no accepted owner, no current epoch or admitted lanes/
events/work, serializes against acceptance and invokes normal shutdown. ABANDONED
is terminal evidence, prevents late acceptance and is **not** successful execution.
Verify its CLOSED result; unknown work/ownership fails closed. If refused, preserve
records and diagnose explicit operator recovery—never erase intake/receipts or
invent identity. This is a narrow prelaunch failure cleanup, not authority takeover
of active/coordinator-owned work. Prepared services/monitor can remain outstanding
when recovery is unavailable; report that honestly rather than claiming cleanup.

After acceptance, only actual coordinator owns work and cleanup. Resume that
same conversation if interrupted. It settles/retire all lanes/events, runs native
`harness shutdown`, verifies CLOSED and emits final response with immutable
contract/intake linkage, exact revision, every original outcome/global check,
current independent audit/resolutions, limitations and cleanup evidence. Outer
relays that final response unchanged, not a second technical audit. Native final
text is in `coordinator-final.txt` from the native `--output-last-message` flag
(or genuine native client/session output when that flag is unavailable). Outer
reads/relays only that final response, not internal transcripts or worker events.
For read-only intake ownership status, actual gateway may run:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m orchestrator_harness.operator_launch --json manager intake-status \
  --intake-id "$INTAKE_ID"
```

Status/empty queue/client exit alone proves neither task success nor CLOSED. No
transcript watcher, polling relay, background AI or second queue is introduced.

## Legacy history and evidence limits

Saved v1/v2 workflow/ownership records remain readable where supported. Their
planner-as-ROOT explicit `manager handoff-offer`/`handoff-accept` lifecycle is
**legacy**, not the default v3 external-gateway route. Do not reinterpret those
records as coordinator-from-intake proof. The [real-provider report](REAL_WORKFLOW_TEST.md)
is unchanged **v1 Codex/Linux** history, not a test of v2 split review or v3
external gateway. V2 offline reviewed-plan/repair fixtures and [v3 offline role-flow
fixtures](OUTER_GATEWAY_TEST.md) are labeled test doubles, not real model-backed provider E2E. Claude/Qwen
have native harness adapters but no Codex `[harness]` selector; their new topology
must not be claimed provider-tested without actual evidence.

## Fresh run after a handed-off task

The heading retains its historical link; it applies to v3 intake-owned runs too.
A v3 intake/accepted owner belongs to exactly one prepared run. The same owner
retains its epoch across planner/reviewer/coding/audit retirement gaps; explicit
native shutdown closes it. Do not use legacy same-run reopening for a new task.
The actual coordinator must first complete shutdown and prove CLOSED. Stop gateway,
planner/reviewer and coordinator clients
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

Seed/observe the next genuine coordinator before preparation as described above.
Use the configured provider for explicitly selected other providers. Stop and
diagnose failures. Start the external gateway and submit the next marked task.
The archive stays intact; previous intake/handoff never grants a new run authority.

## Upgrade an existing installed harness safely

V3 moves outer wholly outside execution and introduces direct native intake with
separate planner/reviewer provenance. Preserve saved v1/v2 records and historical
reports unchanged; do not upgrade old evidence by relabeling. Installing source
never activates a runtime or performs a provider test.

Freeze source/configuration during live work. Before replacing installed code,
actual owner settles all lanes/events and proves CLOSED. Preserve local config,
patches, installation notes, native sessions/logs and prior receipts. Changed
hashed source/hooks can invalidate old prelaunch evidence. Diagnose, archive the
settled prior run and perform genuine **fresh** preparation with new run and
observed new coordinator identity. Never overwrite/delete/fabricate receipts or
blindly repeat same-run reopening after a hash mismatch. Revisit native hook trust
if required. Source install/unit tests do not prove a real v3 model-backed run.
