"""Native Codex UserPromptSubmit entry point; never launches the harness."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Also contain import/argument failures: nonzero hook exits are not a portable
# substitute for UserPromptSubmit's explicit native decision:block contract.
sys.dont_write_bytecode = True


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise ValueError("invalid hook command arguments")


def main() -> int:
    try:
        source = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(source))
        from orchestrator_harness.prompt_optin import evaluate, read_payload
        from orchestrator_harness.config import path_identity
        parser = _Parser(description=__doc__, add_help=False)
        parser.add_argument("--harness-dir", required=True, type=Path)
        parser.add_argument("--workspace", required=True, type=Path)
        args = parser.parse_args()
        if path_identity(args.harness_dir) != path_identity(source):
            raise ValueError("hook source and explicit harness directory differ")
        result = evaluate(read_payload(sys.stdin.buffer),
                          harness_dir=args.harness_dir, workspace=args.workspace)
    except Exception:
        result = {"decision": "block", "reason": (
            "HARNESS_OPTIN_HOOK_ERROR: The native opt-in hook could not safely "
            "read its input or configuration. No marked request is authorized. "
            "Check the hook command, installed files, and "
            "local-config/INSTALLATION.md; preserve the failure and do not "
            "automatically retry setup or bypass the hook."
        )}
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
