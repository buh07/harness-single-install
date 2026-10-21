# Install and use this harness

This repository is a **full-source distribution** of harness-single, with NFS/POSIX
repairs and an explicit Codex `[harness]` prompt selector. Clone this repository
for each new installation; do not copy a prepared installation or its receipts.

**Quick mental model:** installation adds native hooks; preparation opens the
runtime; the exact first line `[harness]` opts one new Codex message into the
harness workflow. It is not automatic startup. Ordinary messages are OFF.

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
this `INSTALL.md` and include the same-run-ID CLOSED reopening instructions from
step 7. For example, fill in this local note (never commit the filled values):

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

## 4. Prepare before starting ROOT

For a **fresh** managed Codex workspace, do not run `harness setup` separately:
preparation performs native setup once internally.

```sh
cd "$HARNESS_DIR"
export HARNESS_RUN_ID='<your-new-recorded-run-id>'
"$PYTHON" -B scripts/prepare_root_launch.py \
  --harness-dir "$HARNESS_DIR" --workspace "$WORKSPACE" \
  --run-id "$HARNESS_RUN_ID" --provider codex
```

Require successful preparation. It validates configuration, installs/merges
native ROOT payloads and core hooks, starts the monitor, and records the genuine
run/session receipt under the manager workspace's `.agent-workspace/`. It starts
**no coding lane or model call**. Keep the run ID, paths, and receipt unchanged.

If this workspace already contains a harness runtime, preparation attempt, or
receipt, **stop and diagnose its ownership/state first**; it is not a fresh
installation. Never delete, copy, fabricate, or reset authority records to make
setup pass. An interrupted preparation or a prepared CLOSED runtime has a
separate documented recovery/reopen path. Do not overwrite existing shared hook
or provider configuration. The core setup structurally merges its registrations
and preserves unrelated native files.

Provider selection is explicit: `--provider claude-code` or `--provider qwen-code`
prepares that provider instead. Use its native CLI and provider instructions from
[QUICK_START.md](QUICK_START.md). Do not install/use the Codex selector for those
ROOTs or change an existing receipt's provider. Their core harness integration
remains available, but this `[harness]` feature does **not** add Claude/Qwen prompt
selection. The Windows Codex health gate is never bypassed by a provider change.

## 5. Start or resume native Codex, then review trust

Start at the **exact configured manager workspace root**, using the same active
Codex home and a deliberately chosen native executable:

```sh
cd "$WORKSPACE"
"$CODEX_BIN" --no-daemon
# Or, resume a deliberately selected existing native session:
# "$CODEX_BIN" resume --no-daemon <your-session-id>
```

These startup commands describe the tested Codex 0.163.0 CLI; if your installed
client does not support them or the hook contract, stop and check its native
help/documentation. Do not silently select a different executable from PATH or
resume `--last` when diagnostic sessions might have changed which one is last.
Existing native sessions/logs are preserved; this distribution does not import
archived sessions as new prepared authority.

Use native **`/hooks`** to inspect/enable/trust the new UserPromptSubmit command
and the core PostToolUse/Stop hooks. Check the exact interpreter, installed
script, scope arguments, and source. Normal native review/trust is required;
never manufacture trusted hashes, disable trust checks, or treat a file on disk
as proof an existing client loaded it. Restart/resume after hook installation or
configuration changes. Editing the home registration does not make an already
running client reload it.

Preparation opens a managed runtime. Do not ask an unrelated preliminary
question and expect it to remain open: **any final response requires CLOSED**
under the existing Stop hook. Once loaded/trusted, submit the actual marked task
directly. If preparation or trust/loading fails, preserve the diagnostic and use
native `harness shutdown` as appropriate; do not leave an idle OPEN runtime.

## 6. Submit a harness task

The actual message must start with this exact, case-sensitive first line, not a
quote, code fence, leading blank line, or an inline prefix:

```text
[harness]
Implement my feature and run its focused tests using native harness lanes.
```

Put a nonempty task below the marker. The hook checks **only the newest submitted
message**, not conversation history. Repeat the marker for each new message
requesting harness work; it is not sticky. During the model's internal steps you
do not need to send the marker again.

- **Exact marker + ready OPEN runtime:** validate prepared identities/receipts and
  explicitly select the portable `skills/harness-outcome-workflow/SKILL.md`.
- **Unmarked message at the manager root:** explicit OFF for this submission;
  no automatic setup or launch. Existing work/cleanup obligations still apply.
- **Marked but unprepared, CLOSED, stale, or mismatched:** block instead of
  silently performing ordinary coding. The marker never reopens anything.
- **Different or nested CWD:** the selector is inert, even inside a nested Git
  project. Start at the exact manager root to use it.

Tell ROOT your actual task, desired provider/model/preferences, and acceptance
criteria. Worker launch preferences have no defaults: Codex needs model,
`reasoning_effort`, and `service_tier`; Claude Code needs model and `effort`; Qwen
Code needs model. Require actual lane IDs/worktrees, tests/review/acceptance,
retirement, and CLOSED evidence in the result. Generic subagent activity is not
proof a native harness lane ran.

## 7. Finish, then prepare the next task

Under the default workflow, planner ROOT decomposes once and uses the
[explicit native manager handoff](docs/WORKFLOW.md). The distinct execution
coordinator handles native events, checks/integrates all assignments, repairs the
candidate and cycles with an independent read-only auditor. **That coordinator's
actual native conversation** settles/retires lanes and runs:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m orchestrator_harness.operator_launch harness shutdown
```

Planner ROOT remains idle until CLOSED. After an offer/accept handoff, an ordinary
terminal lacking the owner's native identity cannot run manager mutations. Do not
copy/forge `CODEX_THREAD_ID` or other native identity variables to bypass this.
Resume the actual owner conversation if interrupted. A read-only terminal
`scan --no-write` remains diagnostic; a successful scan or empty queue is not a
CLOSED proof or task success.

**After a handed-off run:** the next independent task requires a genuinely fresh
run/epoch. First have the coordinator prove CLOSED, stop both native clients,
then preserve/archive the settled runtime and old run records using the
[concrete fresh-run procedure](docs/WORKFLOW.md#fresh-run-after-a-handed-off-task).
Run genuine preparation with a new run ID, restart the planner client, and submit
the next marked task. The old ACTIVE handoff is not authority for a future epoch.

**Only if no handoff was offered, source/configuration are unchanged, and the
existing prepared ROOT is CLOSED:** the legacy same-run reopening remains:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m orchestrator_harness.operator_launch harness setup &&
"$PYTHON" -B scripts/prepare_root_launch.py \
  --harness-dir "$HARNESS_DIR" --workspace "$WORKSPACE" \
  --run-id "$HARNESS_RUN_ID" --provider codex
```

Stop on failure and diagnose; neither command automatically retries. This legacy
sequence is **not** the next-task procedure after a manager handoff, nor a repair
for source/hash changes. Never fabricate receipts, change run IDs over existing
records, use `--overwrite` speculatively, or repeatedly run setup.

## Limits, troubleshooting, and removal

- This is deterministic per-submission **selection and readiness checking**, not
  mechanical enforcement of every model action or proof of task completion.
  Native delivery must be loaded, enabled, and trusted. A missing interpreter,
  killed hook, disabled hooks, or native client failure is not an unconditional
  fail-closed security boundary.
- Validation is point-in-time. A `null` prepared native session binding does not
  prove exclusive native-thread ownership or bind it; do not run concurrent
  ROOT managers over one runtime. Keep source/configuration frozen during work.
- `HARNESS_OPTIN_NOT_OPEN`: reopen/prelaunch explicitly, then restart/resume.
  Other hook errors require checking scope, native/logical identities, genuine
  preparation, and the exact configured command; do not bypass validation.
- Ordinary unmarked prompts do **not** cancel active workers or bypass the
  always-installed Stop hook. Finish normal cleanup even if the latest prompt
  was OFF.
- To remove only prompt selection, remove its one UserPromptSubmit registration
  from the active home file and restart Codex. Preserve unrelated groups and
  core PostToolUse/Stop hooks. Do not remove core integration while work exists.
- Updating this source, changing paths/config, or replacing prepared hook bytes
  may invalidate preparation/trust. Stop and use a separately diagnosed native
  migration, not a copied receipt or an in-place live update.

Focused, non-provider tests from this checkout:

```sh
cd "$HARNESS_DIR"
"$PYTHON" -B -m unittest orchestrator_harness.tests.test_prompt_optin -v
```

Those tests do not run a full model-backed coding lane or certify native sandbox
isolation. Native discovery/trust/loading and a real project lane must be checked
in the actual target environment before claiming end-to-end provider proof.

Official native contract: [OpenAI hooks documentation](https://learn.chatgpt.com/docs/hooks).
Provenance and redistribution caveat: [PROVENANCE.md](PROVENANCE.md).

## Upgrading source with existing receipts

Use [the safe upgrade procedure](docs/WORKFLOW.md#upgrade-an-existing-installed-harness-safely).
Prove CLOSED before changing code. Preserve/archive prior run records; changed
hashed inputs require diagnosed fresh preparation, not overwritten PASS receipts
or blind same-run reopening. No external skill installation is needed because
the selector explicitly gives the configured portable skill path.
