"""Authority/instruction code is part of genuine preparation fingerprint."""
from pathlib import Path
import tempfile
import unittest
from scripts.prepare_root_launch import HARNESS_INPUTS, configuration_hashes


class WorkflowHashInputsTests(unittest.TestCase):
    def test_intake_authority_and_planning_instructions_are_hash_pinned(self):
        authority='orchestrator_harness/workflow_intake.py'
        instructions='skills/harness-outcome-workflow/references/planning-review.md'
        self.assertIn(authority,HARNESS_INPUTS)
        self.assertIn(instructions,HARNESS_INPUTS)
        with tempfile.TemporaryDirectory(prefix='workflow-input-hash-') as directory:
            base=Path(directory);harness=base/'harness';workspace=base/'manager'
            for name in (*HARNESS_INPUTS,'orchestrator_harness/provider_adapters/codex/launcher_binding.py'):
                if name=='local-config/public-check-policy.json':continue
                path=harness/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'original fixture bytes\n')
            config=workspace/'.codex/config.toml';config.parent.mkdir(parents=True);config.write_bytes(b'')
            before=configuration_hashes(harness,workspace)
            for name in (authority,instructions):
                path=harness/name;path.write_bytes(b'changed fixture bytes\n')
                after=configuration_hashes(harness,workspace)
                self.assertNotEqual(before[name],after[name])
                self.assertEqual({name},{key for key in before if before[key]!=after[key]})
                path.write_bytes(b'original fixture bytes\n')


if __name__=='__main__':unittest.main()
