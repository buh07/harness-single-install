"""Offline declared-evidence behavior, not native/model or semantic proof."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from orchestrator_harness.core import sha256_hex
from orchestrator_harness.workflow_contract import (CONTRACT_SCHEMA, AUDIT_SCHEMA, FINAL_SCHEMA,
    SPLIT_REVIEW_SCHEMA, SPLIT_DIMENSIONS, plan_sha256, validate_contract, validate_plan_review,
    validate_audit, validate_final_result)
from orchestrator_harness.tests.test_manager_ownership import contract as legacy_contract

REV = 'a' * 40


def reviewed_contract():
    c = legacy_contract()
    c.update(schema=CONTRACT_SCHEMA, repository_context=['Small Python standard-library project; no external services.'],
             interfaces=['normalize(words: list[str]) -> list[str]; preserve order, size and input.'],
             split_reviewer=deepcopy(c['auditor']), plan_review=None)
    c['original_prompt'] = 'Normalize surrounding whitespace in each word without dropping words or changing their order.'
    c['outcomes'][0].update(description='All words are stripped without losing elements.',
        acceptance_criteria=['Mixed and whitespace-only words preserve count and order.'])
    c['assignments'][0].update(task='Implement normalize(words) and focused regression.',
        goal='Every input word is stripped in order with the same number of output words.',
        scope=['normalize.py'], acceptance_criteria=['Mixed and whitespace-only inputs preserve count/order.'],
        checks=['Run normalize regression subprocess.'])
    c['integration_criteria'][0].update(description='Unified API handles empty input and does not mutate input.',
        checks=['Run mixed, empty and nonmutation cases at candidate HEAD.'])
    report = {'schema':SPLIT_REVIEW_SCHEMA, 'plan_sha256':plan_sha256(c),
        'reviewer_session_id':'fixture-split-reviewer', 'read_only':True,
        'prepared_run_id':'fixture-prepared-run', 'root_session_id':'fixture-root-session',
        'dimensions':[{'id':i,'assessment':'One cohesive assignment; check the complete API and integration contract.',
            'evidence':['Original prompt, all assignments, context and interfaces were supplied.']} for i in sorted(SPLIT_DIMENSIONS)],
        'findings':[]}
    c['plan_review'] = {'report':report,'resolutions':[], 'native_review':{
        'epoch_id':'fixture-planning-epoch','lane_id':'fixture-split-review','run_id':'fixture-review-invocation',
        'result_sha256':'0'*64,'prepared_run_id':report['prepared_run_id'],'root_session_id':report['root_session_id']}}
    return c


def results(c, revision=REV, status='PASS'):
    return [{'id':item['id'],'status':status,'checks':[{'description':'Run original acceptance check.',
        'status':status,'evidence':['Actual check receipt at '+revision]}], 'evidence':['checks.json']}
        for item in c['outcomes']+c['integration_criteria']]


def audit(c, revision=REV, identity='fixture-auditor-one', status='PASS'):
    return {'schema':AUDIT_SCHEMA,'contract_sha256':sha256_hex(c),'candidate_revision':revision,
        'auditor_session_id':identity,'read_only':True,'results':results(c,revision,status),
        'verdict':status,'findings':[]}


def final(c,a):
    return {'schema':FINAL_SCHEMA,'contract_sha256':sha256_hex(c),'candidate_revision':a['candidate_revision'],
        'coordinator_session_id':'fixture-integrator','checks':deepcopy(a['results']),
        'audit_sha256':sha256_hex(a),'resolutions':[],'status':'COMPLETE','limitations':[]}


def validate_final(f,c,a,**extra):
    arguments = dict(candidate_revision=a['candidate_revision'], expected_contract_sha256=sha256_hex(c),
        implementer_session_ids=['fixture-author'], coordinator_session_id='fixture-integrator',
        auditor_session_id=a['auditor_session_id'])
    arguments.update(extra)
    return validate_final_result(f,c,a,**arguments)


class ReviewedWorkflowTests(unittest.TestCase):
    def test_v2_default_and_legacy_saved_contract_readable(self):
        self.assertEqual('harness-outcome-workflow/v2',CONTRACT_SCHEMA)
        self.assertEqual(legacy_contract(),validate_contract(legacy_contract()))
        self.assertEqual(reviewed_contract(),validate_contract(reviewed_contract()))

    def test_unreviewed_different_and_stale_plan_rejected(self):
        for change in ('missing','original','assignment','context','interfaces'):
            c=reviewed_contract()
            if change=='missing': c['plan_review']=None
            elif change=='original': c['original_prompt']+=' New requirement.'
            elif change=='assignment': c['assignments'][0]['scope'].append('second.py')
            elif change=='context': c['repository_context'].append('Changed repository baseline.')
            else: c['interfaces'].append('Changed interface.')
            with self.subTest(change=change),self.assertRaises(ValueError):validate_contract(c)

    def test_reviewer_actual_identity_and_all_dimensions_required(self):
        c=reviewed_contract(); report=c['plan_review']['report']
        for planner,reviewer in [('fixture-split-reviewer','fixture-split-reviewer'),('planner','invented-reviewer')]:
            with self.subTest(planner=planner),self.assertRaisesRegex(ValueError,'independent'):
                validate_plan_review(report,c,planner_session_id=planner,reviewer_session_id=reviewer)
        report['dimensions'].pop()
        with self.assertRaisesRegex(ValueError,'every dimension'):validate_contract(c)

    def test_findings_require_reasoned_resolutions_not_reviewer_pass(self):
        c=reviewed_contract(); c['plan_review']['report']['findings']=[{'id':'cost','description':'Consider one lane rather than fragmenting this small API.'}]
        with self.assertRaisesRegex(ValueError,'resolution'):validate_contract(c)
        c['plan_review']['resolutions']=[{'id':'cost','decision':'accepted','rationale':'The frozen plan uses one cohesive coding lane.'}]
        self.assertEqual(c,validate_contract(c))
        c['plan_review']['resolutions'][0]['rationale']=' '
        with self.assertRaisesRegex(ValueError,'rationale'):validate_contract(c)

    def test_problematic_proposal_review_reasoned_revision_and_new_exact_review(self):
        c=reviewed_contract()
        second=deepcopy(c['assignments'][0]);second.update(id='second',dependencies=['assignment'],goal='Edit the same tiny function again.')
        c['assignments'].append(second);c['outcomes'][0]['assignment_ids'].append('second')
        proposal_hash=plan_sha256(c)
        report=deepcopy(c['plan_review']['report']);report['plan_sha256']=proposal_hash
        report['findings']=[{'id':i,'description':description} for i,description in [
            ('overlap','Both assignments write normalize.py; they are not semantically independent.'),
            ('missing','No assignment tests whitespace-only input; make the intended goal explicit.'),
            ('fragmentation','Two tiny sequential edits add avoidable coordination cost.'),
            ('dependency','The second task depends on the first; do not launch them as parallel work.')]]
        c['plan_review']['report']=report
        c['plan_review']['resolutions']=[{'id':i['id'],'decision':'accepted','rationale':'Consolidate to one complete checkable API assignment and preserve global checks.'} for i in report['findings']]
        validate_plan_review(report,c,planner_session_id='planner',reviewer_session_id='fixture-split-reviewer')
        c['assignments'].pop();c['outcomes'][0]['assignment_ids'].pop()
        with self.assertRaisesRegex(ValueError,'stale'):validate_contract(c)
        # A genuinely new final-plan review is declared; no old review hash is relabeled.
        fresh=reviewed_contract()['plan_review']['report'];fresh['reviewer_session_id']='fixture-fresh-split-reviewer'
        c['plan_review']['report']=fresh;c['plan_review']['resolutions']=[]
        self.assertNotEqual(proposal_hash,plan_sha256(c));validate_contract(c)

    def test_v2_audit_requires_observed_fresh_independent_identity(self):
        c=reviewed_contract();a=audit(c)
        args=dict(candidate_revision=REV,implementer_session_ids=['fixture-author'],coordinator_session_id='fixture-integrator')
        with self.assertRaisesRegex(ValueError,'caller-observed'):validate_audit(a,c,**args)
        for who in ('fixture-author','fixture-integrator','invented'):
            with self.subTest(identity=who),self.assertRaises(ValueError):validate_audit(a,c,**args,auditor_session_id=who)
        with self.assertRaisesRegex(ValueError,'independent'):
            validate_audit(a,c,**args,auditor_session_id=a['auditor_session_id'],prior_auditor_session_ids=[a['auditor_session_id']])

    def test_complete_rejects_partial_checks_old_revision_or_changed_contract(self):
        c=reviewed_contract();a=audit(c);f=final(c,a)
        for operation in ('outcome','global','failed','stale','weaken'):
            changed=deepcopy(f)
            with self.subTest(operation=operation),self.assertRaises(ValueError):
                if operation=='outcome':changed['checks'].pop(0)
                elif operation=='global':changed['checks'].pop()
                elif operation=='failed':changed['checks'][0]['checks'][0]['status']='FAIL'
                elif operation=='stale':
                    validate_final(changed,c,a,candidate_revision='b'*40);continue
                else:
                    weakened=deepcopy(c);weakened['outcomes'][0]['acceptance_criteria']=['Partial result allowed.']
                    weakened['plan_review']['report']['plan_sha256']=plan_sha256(weakened)
                    validate_final(changed,weakened,a,expected_contract_sha256=sha256_hex(c));continue
                validate_final(changed,c,a)

    def test_v2_audit_cannot_omit_original_outcome_or_global_criterion(self):
        c=reviewed_contract()
        for index in (0,-1):
            a=audit(c);a['results'].pop(index)
            with self.subTest(index=index),self.assertRaisesRegex(ValueError,'every outcome'):
                validate_audit(a,c,candidate_revision=REV,implementer_session_ids=['fixture-author'],
                    coordinator_session_id='fixture-integrator',auditor_session_id=a['auditor_session_id'])

    def test_advisory_fail_can_be_declined_with_evidence_not_pass_veto(self):
        c=reviewed_contract();a=audit(c,status='FAIL')
        a['findings']=[{'id':'false-oracle','description':'Auditor expected whitespace-only words to be removed.'}]
        f=final(c,a);f['checks']=results(c)
        with self.assertRaisesRegex(ValueError,'disposition'):validate_final(f,c,a)
        f['resolutions']=[{'id':'finding:false-oracle','decision':'declined','rationale':'Original contract explicitly preserves input size; the review used the wrong oracle.', 'evidence':['Original prompt and executable preservation case.']}]
        f['resolutions'] += [{'id':'result:'+item['id'],'decision':'declined','rationale':'Reran the original oracle at exact HEAD; review expectation contradicted unchanged original contract.', 'evidence':['Original complete checks, exit 0.']} for item in a['results']]
        self.assertEqual('COMPLETE',validate_final(f,c,a)['status'])
        f['resolutions'][0]['decision']='unresolved'
        with self.assertRaisesRegex(ValueError,'unresolved'):validate_final(f,c,a)
        f['status']='BLOCKED';self.assertEqual('BLOCKED',validate_final(f,c,a)['status'])

    def test_actual_offline_fail_integrator_repair_new_revision_full_pass(self):
        with tempfile.TemporaryDirectory(prefix='reviewed-workflow-product-') as name:
            receipt=run_offline_repair_fixture(Path(name))
            self.assertNotEqual(receipt['before_revision'],receipt['after_revision'])
            self.assertEqual('FAIL',receipt['before_audit']['verdict'])
            self.assertEqual('PASS',receipt['after_audit']['verdict'])
            self.assertEqual('COMPLETE',receipt['final']['status'])
            self.assertEqual(receipt['original_contract_sha256'],receipt['final']['contract_sha256'])
            self.assertEqual(['fixture-integrator'],receipt['repair_actors'])


def run_offline_repair_fixture(directory: Path):
    """Real local code/check/Git iteration; identities are fixture role labels only.

    This never launches a model, native worker, watch, manager or provider. The
    caller owns the directory and may retain it as private deterministic evidence.
    """
    directory.mkdir(parents=True,exist_ok=True)
    product=directory/'candidate';product.mkdir()
    evidence=directory/'evidence';evidence.mkdir()
    def git(*args):
        return subprocess.run(['git','-C',str(product),*args],check=True,text=True,capture_output=True).stdout.strip()
    git('init','-q');git('config','user.name','Offline workflow fixture');git('config','user.email','fixture@example.invalid')
    source=product/'normalize.py';source.write_text('def normalize(words):\n    return [word.strip() for word in words if word.strip()]\n')
    git('add','normalize.py');git('commit','-qm','Fixture coding contribution')
    c=reviewed_contract();accepted_hash=sha256_hex(c)
    def check(revision,identity):
        report=audit(c,revision,identity)
        checks=[('outcome',"from normalize import normalize; assert normalize([' a ',' ',' b ']) == ['a','','b']"),
                ('integrated',"from normalize import normalize; assert normalize([]) == []; x=[' a ',' ']; y=normalize(x); assert x==[' a ',' '] and y==['a','']")]
        for record,(label,script) in zip(report['results'],checks):
            completed=subprocess.run([sys.executable,'-B','-c',script],cwd=product,capture_output=True,text=True)
            log=evidence/(identity+'-'+label+'.log');log.write_text(completed.stdout+completed.stderr)
            status='PASS' if completed.returncode==0 else 'FAIL'
            record.update(status=status,evidence=[log.name]);record['checks']=[{'description':script,'status':status,'evidence':[log.name+': exit '+str(completed.returncode)+' at '+revision]}]
        report['verdict']='PASS' if all(item['status']=='PASS' for item in report['results']) else 'FAIL'
        return report
    before=git('rev-parse','HEAD');before_source=source.read_bytes()
    owner_before=check(before,'fixture-integrator-before')['results']
    a1=check(before,'fixture-auditor-one')
    assert before_source==source.read_bytes() and before==git('rev-parse','HEAD')
    f1=final(c,a1);f1['checks']=owner_before;f1['status']='BLOCKED';f1['resolutions']=[{'id':'result:'+item['id'],'decision':'unresolved','rationale':'Original preservation cases failed; integrator must repair the candidate.', 'evidence':item['evidence']} for item in a1['results'] if item['status']!='PASS']
    validate_final(f1,c,a1)
    # The integrator itself changes the unified candidate; no ROOT or original
    # coding-worker callback exists in this fixture.
    source.write_text('def normalize(words):\n    return [word.strip() for word in words]\n')
    git('add','normalize.py');git('commit','-qm','Fixture integrator repairs preservation')
    after=git('rev-parse','HEAD')
    try:validate_final(f1,c,a1,candidate_revision=after)
    except ValueError:pass
    else:raise AssertionError('Old audit survived changed unified HEAD')
    owner_after=check(after,'fixture-integrator-after')['results']
    a2=check(after,'fixture-auditor-two');f2=final(c,a2);f2['checks']=owner_after
    validate_final(f2,c,a2,prior_auditor_session_ids=['fixture-auditor-one'])
    assert accepted_hash==sha256_hex(c) and not git('status','--porcelain')
    receipt={'kind':'offline-real-code-not-native-provider-e2e','original_contract_sha256':accepted_hash,
        'contract':c,'before_revision':before,'after_revision':after,'before_audit':a1,
        'before_final':f1,'after_audit':a2,'owner_checks_before':owner_before,
        'owner_checks_after':owner_after,'final':f2,'repair_actors':['fixture-integrator']}
    for filename,value in [('contract.json',c),('audit-before.json',a1),('audit-after.json',a2),('final.json',f2),('receipt.json',receipt)]:
        (evidence/filename).write_text(json.dumps(value,indent=2)+'\n')
    return receipt


if __name__=='__main__':unittest.main()
