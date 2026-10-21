# Portable contents

Upstream snapshot date: 2026-08-02. Distribution additions: 2026-10-20.

## Included

- Versioned `skills/harness-outcome-workflow/` with bounded outcome assignments,
  coordinator-owned integration/repair and independent whole-result auditing;
  strict workflow/audit contract validators and explicit selector loading.
  [Workflow documentation](docs/WORKFLOW.md) covers external gateway/native intake, legacy handoff history and upgrades.

- Reusable full-source installation guide (`INSTALL.md`) and pinned upstream
  provenance (`PROVENANCE.md`).
- Additive Codex `[harness]` first-line prompt selector, its focused tests, and
  portable native home-hook installation/trust instructions. Ordinary new
  messages are OFF; no automatic setup or runtime reopening is added.
- Retained NFS/POSIX mutation, monitor detachment, and cleanup-order repairs.

- Complete production Python code from `orchestrator_harness/`.
- Complete shared `harness_common/` process-identity code.
- Protected retry history, Windows health/prelaunch validation, and optional direct
  build/test service and staged worker client, including scripts and operator documentation.
- Canonical RESULT/source validation and protected linked-Git assignments;
  bootstrap/resume stage the required validator modules, assignment mirror and
  complete template into each worker's `.agent-workspace/`.
- General configuration templates with no selected external workspace. OS/tool paths
  are discovered or explicitly configured; no operator PASS receipt is shipped.
- Complete production Python code and schema from `harness_watcher_implementation/`.
- Harness and watcher unit/integration tests that are self-contained in this portable tree.
- Example configuration, setup instructions, specifications, attention-logging documentation, and
  testing guides.
- A disposable coding integration fixture with two worktree lanes, one contended named resource,
  stale/valid result paths, a merge lane, native event acknowledgement, and cleanup.
- One static harness configuration fixture required by a copied unit test.

## Deliberately excluded

- Machine-specific provider homes, sessions, logs, credentials, `local-config/`,
  runtime/service state, and prelaunch/health PASS receipts.

- `multi-agent-logs/`, `harness_watcher/<epoch>/`, and `fresh-experiments/`.
- Canary state directories, generated JSONL, snapshots, pending notifications, caches, and
  `test_results/`.
- Historical sprint plans, reviews, checkpoints, handoffs, verdicts, and repair prompts.
- The AI watcher-subagent relay model and all collaboration-notification machinery.
- Obsolete owner/watcher wrappers and their repository-history-only test.
- External provider service code and experiment artifacts; they are observed targets, not harness
  or watcher dependencies.

The portable runtime generates new state only under paths selected in local configuration. No
historical runtime evidence was copied into this folder.

The wheel includes runtime modules and the new scripts/client/docs as data files.
It is a module distribution: a runnable harness root also needs the single-source
`adapters/` and `super-cache/` trees from this portable checkout and explicit local
configuration. It does not include runtime output, credentials or local policy.
