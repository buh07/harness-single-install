# Install and use this harness

This repository is a **full-source distribution** of harness-single, with NFS/POSIX
repairs and an explicit Codex `[harness]` prompt selector. Clone this repository
for each new installation; do not copy a prepared installation or its receipts.

**Quick mental model:** installation adds native hooks; preparation opens the
runtime for a genuinely separate native coordinator; the exact first line
`[harness]` makes the outer conversation only an unchanged-request submission /
final-response gateway. A separate planner, independent reviewer, coding lanes
and integration/audit loop run under the coordinator, not outer. This is not an
automatic provider launcher. Ordinary new messages are OFF.

Read [QUICK_RULES.md](QUICK_RULES.md) before live work. The detailed lane workflow
is in [QUICK_START.md](QUICK_START.md), and selector semantics are in
[docs/PROMPT_OPT_IN.md](docs/PROMPT_OPT_IN.md).

## 1. Clone the complete source

Prerequisites: Git, Python **3.11 or newer**, and an authenticated native provider
CLI. Codex prompt selection requires a client supporting `UserPromptSubmit`,
native home `hooks.json`, and hook review/trust. Native hook discovery, trust,
marked-prompt rejection, and ordinary-message delivery were checked with Codex
**0.163.0**; these checks do not certify every client version or a model-backed
coding lane. No Python third-party dependencies are needed for the source CLI.

On a POSIX shell, choose your own absolute paths. The examples below are
placeholders, not defaults:

```sh
git clone https://github.com/buh07/harness-single-install.git <installation-directory>
cd <installation-directory>
export HARNESS_DIR="$PWD"
export WORKSPACE='<absolute-path-to-your-Git-product-workspace>'
export CODEX_HOME='<absolute-path-to-the-Codex-home-you-use>'
export PYTHON='<absolute-path-to-Python-3.11-or-newer>'
export CODEX_BIN='<absolute-path-to-your-native-Codex-executable>'
```

This distribution is public; authenticated GitHub access is required only for
private copies or pushes.
Use a stable installation path and record the source commit (`git rev-parse
HEAD`). Keep the full checkout, including `adapters/`, `super-cache/`, `scripts/`,
and `tools/`; a module-only wheel is not a complete installation. The code does
not automatically update itself. Do not move or update a prepared installation
while its runtime is live.

Use a real Git product workspace with a deliberate, committed stable baseline
before splitting worker lanes. Do not blanket-add unrelated projects, logs,
credentials, or parent-directory contents to obtain a commit. A separate harness
checkout is not itself your product workspace.

Also inspect `command -v python`, `python --version`, and `command -v codex`.
Core installed hook commands invoke **`python` from PATH**, and the POSIX Codex
worker adapter invokes **`codex` from PATH**. Ensure those resolve to your chosen
supported installations (Python >=3.11), in the environment inherited by ROOT
and workers. `PYTHON` above selects the terminal/opt-in interpreter and
`CODEX_BIN` selects ROOT; those variables do not override the worker adapter's
PATH lookup. Do not accidentally start a tested ROOT binary but older workers.

On NFS, keep any temporary/evidence directories on your selected filesystem,
including test `TMPDIR`, and use **one manager/control host per runtime**.
This distribution does not relocate Codex sessions, logs, caches, or live SQLite
files; preserve existing provider state and never move a live database/WAL.

## 2. Configure a fresh installation

Edit **this checkout's** `harness-config.json` before preparation:

```json
{
  "root_workspace": "<absolute-path-to-your-Git-product-workspace>",
  "manager_workspace": "<absolute-path-where-you-start-ROOT>",
  "managed_coordination": "enabled"
}
```

The simplest choice is the **same path for both workspaces**. The optional
`manager_workspace` defaults to `root_workspace`; it is where ROOT hooks, skills,
and `.agent-workspace/` are installed. Set `WORKSPACE` in these commands to that
manager path if you deliberately separate them. `root_workspace` owns the
product's Git lanes and `.harness-runtime/`. Only these three keys are accepted;
do not add a literal `schema` key.

The shipped empty `root_workspace` deliberately refuses operation until chosen.
Keep `resource-manifest.json` as supplied for no exclusive resources, or declare
only the resources you actually need. Optional machine policy belongs under
ignored `local-config/`; do not commit credentials, runtime records, provider
homes, operator PASS receipts, or a selected machine workspace into this repo.
Do not change a prepared configuration simply to reuse an old receipt.

### Keep operator-specific installation notes locally

The selector's workflow/error guidance points ROOT at
`local-config/INSTALLATION.md`. Create that **ignored, operator-owned** file in
this checkout before preparation. If it already exists, preserve it and merge
only the missing installation notes; do not overwrite it. Record your chosen
absolute harness/product/manager paths, source commit, Python and provider CLI,
active Codex home, provider, and the run ID you will use in step 4. Link back to
this `INSTALL.md` and the fresh native startup/intake procedure in
`docs/WORKFLOW.md`; do not use legacy same-run reopening for v3. For example, fill in this local note (never commit the filled values):

```markdown
# Local installation
- Harness/source commit: <absolute harness path> / <git rev-parse HEAD>
- Product / manager workspace: <absolute product> / <absolute manager>
- Python / native Codex executable: <absolute interpreter> / <absolute CLI>
- Active CODEX_HOME: <absolute native home>
- ROOT provider / recorded run ID: codex / <your-run-id>
- Procedure: ../INSTALL.md (fresh preparation: step 4; reopening: step 7).
- Finish every managed run with native shutdown and verified CLOSED.
- Preserve all existing native configuration, hooks, sessions, and logs.
```

These are notes, not readiness authority. Never put copied receipts, credentials,
or old runtime records in them; preparation must produce genuine local evidence.

### Enable Codex native hooks without replacing shared configuration

For a Codex ROOT, ensure the manager workspace's `.codex/config.toml` contains:

```toml
[features]
hooks = true
```

If that file already exists, back it up and **edit/merge its existing**
`[features]` table. Do not append a second table or replace other settings. Setup
preserves an existing file byte-for-byte and refuses an existing configuration
without hooks explicitly enabled. Preserve native permissions, model settings,
trust, sessions, and logs. Hook installation is not authorization to weaken
sandbox or approval policy.

Windows Codex additionally requires the genuine read-only sandbox health gate
before preparation. Follow [docs/INTEGRATED_RUN_FIXES.md](docs/INTEGRATED_RUN_FIXES.md)
and [docs/PATH_PORTABILITY.md](docs/PATH_PORTABILITY.md); do not copy a PASS receipt
or bypass a failed gate. The POSIX shell snippet below is not a Windows quoting
recipe.

## 3. Add the optional Codex `[harness]` selector

This selector is **Codex-only**. Native setup installs the core PostToolUse/Stop
hooks in the manager workspace; it does **not** install this optional home hook.
Install it once in the **active** `$CODEX_HOME/hooks.json`, before starting the
client. Home and project hook sources are additive. Do not replace either file
or remove unrelated groups.

The following one-time POSIX-shell merge uses this checkout's existing
identity-checked mutation API. It starts no runtime, provider, service, or worker.
Close your Codex client and other configuration editors first. Confirm the
absolute environment values from step 1; do not blindly run against another
user's home. The selected Codex home must already exist.

```sh
"$PYTHON" -B - <<'PY'
import json
import os
from pathlib import Path
import shlex
import sys
import uuid


def absolute_directory(name):
    raw = os.environ[name]
    path = Path(raw)
    if not path.is_absolute() or not path.is_dir():
        raise SystemExit(f"{name} must select an existing absolute directory")
    return path


harness = absolute_directory("HARNESS_DIR")
workspace = absolute_directory("WORKSPACE")
home = absolute_directory("CODEX_HOME")
python = Path(os.environ["PYTHON"])
if not python.is_absolute() or not python.is_file() or not os.access(python, os.X_OK):
    raise SystemExit("PYTHON must select an executable absolute interpreter")
script = harness / "scripts/harness_prompt_optin.py"
if not script.is_file():
    raise SystemExit("The complete harness checkout is required")
sys.path.insert(0, str(harness))
from orchestrator_harness.config import load_config, same_path
from orchestrator_harness.mutation import TargetState, capture_target, replace

config = load_config(harness)
if config.profile != "managed" or not same_path(config.manager_workspace, workspace):
    raise SystemExit("Configure this checkout for this managed workspace first")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key; inspect the existing hooks file")
        result[key] = value
    return result


before = capture_target(home, "hooks.json")
if before.present and before.kind != "file":
    raise SystemExit("Existing hooks.json must be a plain file")
def reject_constant(value):
    raise ValueError("Non-finite JSON value; inspect the existing hooks file")


data = (json.loads(before.content.decode("utf-8-sig"), object_pairs_hook=unique_object,
                   parse_constant=reject_constant)
        if before.present else {})
if not isinstance(data, dict):
    raise SystemExit("Existing hooks.json must contain a JSON object")
hooks = data.setdefault("hooks", {})
if not isinstance(hooks, dict):
    raise SystemExit("Existing hooks member must be an object")
command = shlex.join([str(python), "-B", str(script), "--harness-dir",
                      str(harness), "--workspace", str(workspace)])
entry = {"type": "command", "command": command, "timeout": 30,
         "statusMessage": "Checking explicit harness opt-in"}
group = {"hooks": [entry]}
existing_optin = []
for event, groups in hooks.items():
    if not isinstance(groups, list):
        raise SystemExit("Inspect malformed existing hook groups before merging")
    for old_group in groups:
        if not isinstance(old_group, dict) or not isinstance(old_group.get("hooks"), list):
            raise SystemExit("Inspect malformed existing hook groups before merging")
        for old in old_group["hooks"]:
            if not isinstance(old, dict):
                raise SystemExit("Inspect malformed existing hooks before merging")
            old_command = old.get("command", "")
            if isinstance(old_command, str) and "harness_prompt_optin.py" in old_command:
                existing_optin.append((event, old_group))
if existing_optin:
    if existing_optin == [("UserPromptSubmit", group)]:
        print("The identical opt-in registration already exists; no files changed")
        raise SystemExit(0)
    raise SystemExit("A different/duplicate opt-in hook exists; inspect it before changing anything")
hooks.setdefault("UserPromptSubmit", []).append(group)
if before.present:
    backup = "hooks.json.before-harness-optin-" + uuid.uuid4().hex + ".bak"
    replace(home, backup, before.content, expected=TargetState.absent())
    print("Preserved original home hooks at", home / backup)
replace(home, "hooks.json", (json.dumps(data, indent=2) + "\n").encode(), expected=before)
print("Installed only the additive UserPromptSubmit hook; native trust is still required")
PY
```

Repeating the snippet with one identical registration is a no-op. It
refuses a different or duplicate opt-in hook rather than guessing whether an old
command, timeout, scope, or installation is correct. Inspect conflicts manually.
Backups remain local to the selected home; do not commit or publish them. Stop on an error and diagnose it; there is no retry loop. The
merge preserves unrelated JSON values and uses a captured target-state check;
it is not a lock against another configuration writer. Keep those writers shut
down until installation finishes.

For a manual merge or Windows setup, use the template in
[docs/PROMPT_OPT_IN.md](docs/PROMPT_OPT_IN.md#scope-installation-and-native-trust),
with absolute interpreter/script/workspace paths and appropriate native shell
quoting. Do not use POSIX `shlex` quoting for Windows.

## 4. Create the genuine coordinator before preparation

Follow the [executable native startup/intake procedure](docs/WORKFLOW.md#native-intake-and-startup)
for supported native CLI seeding, actual observed conversation ID, genuine
preparation, raw submission and exact-session resume. Keep all operator paths,
preferences and evidence in ignored local notes/private storage. A hook cannot
create a native coordinator, and this product adds no launcher or supervisor.

Finish a tool-free coordinator seed **before OPEN** and observe its genuine
native ID. Do not concurrently resume a running seed, use `--last`, invent IDs,
set identity variables to impersonate another thread, or run the prepared ROOT
collector for outer. The coordinator, not gateway/planner, is genuine logical ROOT.

Preparation performs native setup once internally, installs/merges core hooks,
starts native monitor and records genuine run readiness. It starts no provider
or coding lane. Select provider explicitly; Codex is default, `claude-code` and
`qwen-code` have native adapters but **not** the Codex `[harness]` selector. Native
hook trust, readiness, provider health/sandbox and permissions remain required.
Never switch prepared provider bindings to bypass a failed gate.

If prior runtime/attempt/receipts exist, stop and diagnose ownership/state; do not
run a fresh recipe over them. Preserve records and follow the guarded archive
procedure only after the actual owner proves CLOSED. Changed source/hook hashes
need diagnosed fresh preparation, not copied receipts or repeated same-run setup.

## 5. Start the external gateway; review native trust

Use the configured native home/executable and exact manager workspace. Native
`/hooks` must show loaded/enabled/trusted UserPromptSubmit and core hooks. Restart/
resume after installation; files on disk do not prove client discovery/trust.
Do not weaken permissions, manufacture trust hashes or change shared config to
make a test pass. Preserve existing sessions/logs and unrelated hook groups.

The separate gateway is **not** prepared ROOT. It must not use a ROOT usage
collector or claim logical ROOT identity. The [startup procedure](docs/WORKFLOW.md#native-intake-and-startup)
explains direct native coordinator dispatch and first-tool acceptance. These are
real prerequisites, not hidden automatic calls performed by `[harness]`.

## 6. Submit the exact marked request

```text
[harness]
Implement my feature and run its focused tests.
```

The marker must be the exact first physical line with a nonempty request below,
no leading whitespace/blank line/quote/fence/trailing spaces. LF/CRLF both work.
Only the **newest submitted message** selects ON/OFF; it is not a sticky mode.

- **Marked + ready OPEN scope:** register exact original request/gateway in
  REGISTERED intake and explicitly select portable v3 workflow. Outer
  submits entire original text unchanged through `manager intake-submit`; actual
  separate coordinator accepts through `manager intake-accept` as first tool.
- **Unmarked at manager root:** OFF for new tasks, no automatic setup/launch.
  Authentic unmarked coordinator bootstrap continues the immutable accepted
  request, not a new unrelated task and not a cleanup-only restriction.
- **Marked unprepared/CLOSED/stale/mismatched:** block, not ordinary coding.
- **Other/nested CWD:** selector is inert; use exact configured manager root.

Provide authorized role preferences for **planner**, independent split reviewer,
coding lanes, coordinator and final auditor. Codex lane options require model,
`reasoning_effort` and `service_tier`; Claude needs model/`effort`; Qwen needs model.
Declarations grant no premium tiers, extra permission or publish authority.

The gateway does no decomposition/checking/integration/repair routing, consumes no
manager events and never owns shutdown. Once exact scoped native acceptance is
confirmed it may yield, truthfully saying accepted—not completed. A PENDING
submission is not ownership. REGISTERED/PENDING/missing/unknown/stale ownership is
not a Stop bypass;
actual manager OPEN Stop still needs CLOSED, including an empty queue.

## 7. Finish, then prepare the next task

Coordinator commissions separate native planner and independent reviewer, freezes
actual resolved planning provenance, launches useful one-task/one-goal native coding
lanes, checks/integrates all contributions and checks every original/global criterion
together. It repairs **itself**, not through outer, planner or original coders.
After material change it reruns all original checks and commissions a fresh
independent exact-revision whole-result auditor. Advice is advisory, never a PASS
veto. Keep reasoned dispositions and failed evidence; never weaken outcomes,
claim partial success or reuse a stale audit.

Only the actual coordinator handles native events/acceptance/retirement and runs:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m orchestrator_harness.operator_launch harness shutdown
```

It verifies CLOSED even for incomplete work and produces the final response;
outer only relays. Resume that exact native coordinator on interruption. Never
copy/forge `CODEX_THREAD_ID` or other identity variables to bypass ownership. A
terminal `scan --no-write` or empty queue is neither CLOSED proof nor task success.
Pending dispatch failures require the [documented coordinator/operator recovery](docs/WORKFLOW.md#failure-final-relay-and-recovery),
not outer lifecycle fallback or silent abandonment of a monitor.

For the next independent task, coordinator first proves CLOSED. Stop native
clients and preserve linked worktrees/settled runtime/old run records using the
[guarded fresh-run procedure](docs/WORKFLOW.md#fresh-run-after-a-handed-off-task).
Seed the next genuine coordinator before fresh preparation with new run ID. Old
accepted intake/legacy handoff is never authority for a future run. Legacy unchanged
same-run `harness setup` reopening is **not** a v3 next-task or hash-mismatch fix.

## Limits, troubleshooting, removal and upgrades

- Selection/readiness is deterministic per submission, not mechanical enforcement
  of every model action or a security sandbox. Disabled/untrusted hooks, interpreter
  failure and unsupported native clients defeat delivery; verify native trust.
- V3 requires separate native session capability and direct authorized dispatch.
  No automatic launcher, provider retry, fallback model or outer execution exists.
- OFF does not cancel existing owned work or weaken actual manager Stop/cleanup.
- Remove only the selector's UserPromptSubmit registration to remove prompt opt-in;
  restart Codex and preserve unrelated groups/core hooks. Never remove core
  integration while work exists. Claude is unaffected by this Codex selector.
- Freeze source/configuration during live work. Follow [safe upgrade](docs/WORKFLOW.md#upgrade-an-existing-installed-harness-safely),
  preserving prior notes/config/session/logs/receipts and using diagnosed fresh
  preparation after CLOSED. No external skill install is required.
- [Historical native results](docs/REAL_WORKFLOW_TEST.md) remain unchanged v1
  Codex/Linux evidence. V2 reviewed-plan/repair fixtures and v3 offline role-flow
  fixtures are **not** new provider-backed/model E2E or Claude validation.

Focused non-provider tests:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m unittest orchestrator_harness.tests.test_prompt_optin -v
```

Read [prompt semantics/trust](docs/PROMPT_OPT_IN.md),
[native hook contract](https://learn.chatgpt.com/docs/hooks), and
[provenance/redistribution caveat](PROVENANCE.md).
