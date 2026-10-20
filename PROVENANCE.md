# Source provenance and local additions

This distribution is published at
[github.com/buh07/harness-single-install](https://github.com/buh07/harness-single-install).
It is a separate, modified full-source repository, not a claim of upstream
ownership or an unmodified upstream release.

## Upstream baseline

- Original repository: [JasonPeng2019/harness-single](https://github.com/JasonPeng2019/harness-single).
- Original branch: `base/working-v1`.
- Pinned source commit: `2fa584fcab4b0802f66867bb931122594eb87eac`.
- The upstream operating rules, implementations, tests, examples, and technical
  documentation remain part of this source distribution.

The new repository has its own publication history. This provenance identifies
the baseline even if upstream later moves the branch. It does not import an old
operator runtime as authority.

## Retained modifications

The implementation copied from the working installation retains these repair
categories in addition to the upstream baseline:

- NFS-compatible identity-checked mutation and process/monitor lifecycle handling,
  including POSIX monitor detachment and safe cleanup/closure ordering.
- The additive Codex `UserPromptSubmit` selector in
  `orchestrator_harness/prompt_optin.py` and
  `scripts/harness_prompt_optin.py`, with focused tests in
  `orchestrator_harness/tests/test_prompt_optin.py`.
- Exact first-line `[harness]` selection, unmarked per-submission OFF context,
  existing prepared ROOT validation, and explicit rejection of marked requests
  that are not ready. It does not automatically set up or reopen a runtime,
  launch a worker, fabricate native trust, or add a new runner/supervisor.
- Portable prompt-selector documentation in `docs/PROMPT_OPT_IN.md`.

For publication, `harness-config.json` was reset to its deliberately unconfigured
shape (`root_workspace` empty, managed coordination enabled). `INSTALL.md`, this
provenance record, and README/portable-contents links describe fresh installation
without copying machine-specific state. No behavioral rewrite or new runtime
installer was added for publication.

## Excluded operator material

The source repository excludes provider homes, sessions, logs, caches,
credentials, live runtime/service records, machine-specific `local-config/`,
prelaunch/health PASS receipts, and archived retired-workspace implementation.
An installation generates its own configuration and genuine evidence. Never
copy a working installation's authority records to claim a new target is ready.

The source does not claim a complete model-backed native lane was validated by
publication alone. Focused tests and native hook checks prove only their stated
boundaries. See `INSTALL.md` and the prompt-selector guide for limitations.

## License / redistribution caveat

No `LICENSE` file was present in the pinned upstream source used for this
snapshot. This repository does **not** invent a license, relicense upstream code,
or imply that visibility grants unrestricted redistribution rights. Preserve
upstream attribution and obtain the upstream author's permission or other
applicable rights before public redistribution. Repository visibility and
access control are not a substitute for license permission.
