"""Behavioral validation of bounded contracts and exact-candidate audit evidence."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from orchestrator_harness.workflow_contract import validate_contract, validate_audit
from orchestrator_harness.core import sha256_hex

EXAMPLE = Path(__file__).resolve().parents[2] / 'skills/harness-outcome-workflow/references/contract.example.json'
REVISION = 'a' * 40


class WorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(EXAMPLE.read_text(encoding='utf-8'))

    def audit(self):
        ids = [x['id'] for x in self.contract['outcomes'] + self.contract['integration_criteria']]
        return {'schema':'harness-outcome-audit/v1', 'contract_sha256':sha256_hex(self.contract),
            'candidate_revision':REVISION,
            'auditor_session_id':'independent-native', 'read_only':True,
            'results':[{'id':i, 'status':'PASS', 'checks':[{'description':'Actual regression check',
                'status':'PASS', 'evidence':['check.log: exit 0 at '+REVISION]}],
                'evidence':['check.log']} for i in ids], 'verdict':'PASS', 'findings':[]}

    def check_audit(self, report):
        return validate_audit(report, self.contract, candidate_revision=REVISION,
            implementer_session_ids=['author-native'], coordinator_session_id='coordinator-native')

    def test_example_valid_and_detached(self):
        validated = validate_contract(self.contract)
        validated['constraints'].append('detached')
        self.assertNotIn('detached', self.contract['constraints'])

    def test_each_assignment_exactly_one_outcome(self):
        self.contract['assignments'][0]['outcome_ids'].append('valid-token')
        with self.assertRaisesRegex(ValueError,'exactly one'):
            validate_contract(self.contract)

    def test_missing_global_outcome_coverage_rejected(self):
        self.contract['integration_criteria'][0]['outcome_ids'] = ['expired-token']
        with self.assertRaisesRegex(ValueError,'coverage'):
            validate_contract(self.contract)

    def test_assignment_reciprocal_links_required(self):
        self.contract['outcomes'][0]['assignment_ids'] = []
        with self.assertRaisesRegex(ValueError,'disagree'):
            validate_contract(self.contract)

    def test_unknown_references_and_self_dependencies_rejected(self):
        for field, value in [('outcome_ids',['unknown']), ('dependencies',['token-rejection'])]:
            with self.subTest(field=field):
                contract = deepcopy(self.contract)
                contract['assignments'][0][field] = value
                with self.assertRaises(ValueError):
                    validate_contract(contract)

    def test_cyclic_dependencies_rejected(self):
        a = self.contract['assignments'][0]
        b = deepcopy(a); b['id'] = 'second'; b['dependencies'] = [a['id']]
        a['dependencies'] = ['second']
        self.contract['assignments'].append(b)
        self.contract['outcomes'][0]['assignment_ids'].append('second')
        with self.assertRaisesRegex(ValueError,'cyclic'):
            validate_contract(self.contract)

    def test_no_preferences_defaults_for_any_role(self):
        for role in ('coordinator','auditor','assignment'):
            with self.subTest(role=role):
                contract = deepcopy(self.contract)
                (contract['assignments'][0] if role=='assignment' else contract[role])['provider_options'] = {}
                with self.assertRaisesRegex(ValueError,'preferences'):
                    validate_contract(contract)

    def test_native_provider_validators_reused(self):
        for provider, options in [('claude-code',{'effort':'high'}), ('qwen-code',{})]:
            with self.subTest(provider=provider):
                contract = deepcopy(self.contract)
                contract['auditor'].update(provider=provider, provider_options=options)
                self.assertEqual(provider, validate_contract(contract)['auditor']['provider'])

    def test_unknown_fields_empty_checks_duplicate_ids_rejected(self):
        variants = []
        c = deepcopy(self.contract); c['extra'] = True; variants.append(c)
        c = deepcopy(self.contract); c['assignments'][0]['checks'] = []; variants.append(c)
        c = deepcopy(self.contract); c['outcomes'].append(deepcopy(c['outcomes'][0])); variants.append(c)
        for contract in variants:
            with self.subTest(contract=contract):
                with self.assertRaises(ValueError):
                    validate_contract(contract)

    def test_complete_independent_audit_valid(self):
        report = self.audit()
        self.assertEqual(report, self.check_audit(report))

    def test_missing_global_criterion_rejected(self):
        report = self.audit(); report['results'].pop()
        with self.assertRaisesRegex(ValueError,'every outcome'):
            self.check_audit(report)

    def test_missing_worker_outcome_rejected(self):
        report = self.audit(); report['results'].pop(0)
        with self.assertRaisesRegex(ValueError,'every outcome'):
            self.check_audit(report)

    def test_contract_change_invalidates_same_revision_audit(self):
        report = self.audit()
        self.contract["outcomes"][0]["acceptance_criteria"].append("Additional authorized requirement")
        with self.assertRaisesRegex(ValueError,"contract hash mismatch"):
            self.check_audit(report)

    def test_stale_revision_rejected(self):
        report = self.audit(); report['candidate_revision'] = 'b'*40
        with self.assertRaisesRegex(ValueError,'stale'):
            self.check_audit(report)

    def test_author_integrator_or_writable_auditor_rejected(self):
        for identity in ('author-native','coordinator-native'):
            report = self.audit(); report['auditor_session_id'] = identity
            with self.subTest(identity=identity), self.assertRaisesRegex(ValueError,'independent'):
                self.check_audit(report)
        report = self.audit(); report['read_only'] = False
        with self.assertRaisesRegex(ValueError,'read-only'):
            self.check_audit(report)

    def test_pass_cannot_hide_failed_check_or_finding(self):
        report = self.audit(); report['results'][0]['checks'][0]['status'] = 'FAIL'
        with self.assertRaisesRegex(ValueError,'unsuccessful'):
            self.check_audit(report)
        report = self.audit(); report['findings'] = ['Unresolved original requirement']
        with self.assertRaisesRegex(ValueError,'unresolved'):
            self.check_audit(report)

    def test_failed_or_blocked_audit_is_valid_evidence_not_veto(self):
        for status in ('FAIL','BLOCKED'):
            report = self.audit(); report['results'][0]['status'] = status
            report['results'][0]['checks'][0]['status'] = status
            report['verdict'] = status; report['findings'] = ['Explain the failure.']
            with self.subTest(status=status):
                self.assertEqual(status, self.check_audit(report)['verdict'])

    def test_actual_checks_required_not_only_worker_summary(self):
        report = self.audit(); report['results'][0]['checks'] = []
        with self.assertRaisesRegex(ValueError,'actual audit checks'):
            self.check_audit(report)

    def test_real_full_revision_and_actual_identities_required(self):
        with self.assertRaisesRegex(ValueError,'full candidate'):
            validate_audit(self.audit(), self.contract, candidate_revision='short',
                implementer_session_ids=['author'], coordinator_session_id='coordinator')
        with self.assertRaisesRegex(ValueError,'actual implementer'):
            validate_audit(self.audit(), self.contract, candidate_revision=REVISION,
                implementer_session_ids=[], coordinator_session_id='coordinator')

if __name__ == '__main__':
    unittest.main()
