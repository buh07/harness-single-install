"""Offline v3 roles/ownership: real monitor, records, queue, Git/code/checks.

Native IDs and provider RESULT/history/acceptance observations are explicit
fixtures, NOT provider invocations or model-compliance proof.
"""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from orchestrator_harness import workflow_intake as intake, manager_ownership as ownership
from orchestrator_harness import root_session, root_hook_wrapper, shutdown, launch, prompt_optin
from orchestrator_harness.config import ConfigError
from orchestrator_harness.core import content_hash, iso_utc, sha256_hex
from orchestrator_harness.epochs import close_epoch, read_current_epoch, epoch_dir
from orchestrator_harness.records import atomic_write_json
from orchestrator_harness.lanes import write_lane
from orchestrator_harness.manager_queue import promote_event, acknowledge_event, close_event, read_manager_queue
from orchestrator_harness.setup import _materialized_binding
from orchestrator_harness.tests.support import PreparedRootFixture, write_json
from orchestrator_harness.tests.test_reviewed_workflow import reviewed_contract, run_offline_repair_fixture
from orchestrator_harness.workflow_contract import DIRECT_CONTRACT_SCHEMA, plan_sha256, validate_contract

RAW = '[harness]\r\nNormalize surrounding whitespace in each word without dropping words or changing their order. café\r\n\r\n'


def v3_contract(value, session):
    c = reviewed_contract()
    c.update(schema=DIRECT_CONTRACT_SCHEMA, original_prompt=value['original_prompt'],
             planner=deepcopy(c['coordinator']), intake=intake.linkage(value), native_plan=None, plan_review=None)
    draft = deepcopy(c)
    report = reviewed_contract()['plan_review']['report']
    report.update(plan_sha256=plan_sha256(c), prepared_run_id=session['run_id'], root_session_id=session['session_id'])
    scope = {'epoch_id':value['epoch_id'], 'prepared_run_id':session['run_id'], 'root_session_id':session['session_id']}
    c['native_plan'] = {**scope, 'lane_id':'fixture-planner', 'run_id':'fixture-planner-run',
                        'result_sha256':'0'*64, 'planner_session_id':'fixture-planner-native'}
    c['plan_review'] = {'report':report,'resolutions':[], 'native_review':{
        **scope,'lane_id':'fixture-review','run_id':'fixture-review-run','result_sha256':'0'*64}}
    return c,draft


class WorkflowIntakeTests(unittest.TestCase):
    def setUp(self):
        self.f = PreparedRootFixture(self)
        close_epoch(self.f.rt, self.f.epoch['epoch_id'])
        self.config = self.f.config
        env = patch.dict(os.environ,{**self.f.environment,'CODEX_THREAD_ID':'fixture-gateway'},clear=True)
        env.start();self.addCleanup(env.stop)
        ready=patch('scripts.prepare_root_launch.validate_prepared_root',return_value={})
        ready.start();self.addCleanup(ready.stop)
        self.request=self.f.home/'raw-request.txt';self.request.write_bytes(RAW.encode('utf-8'))
        self.digest=hashlib.sha256(self.request.read_bytes()).hexdigest()
        self.before=root_session.root_session_path(self.config).read_bytes()

    def submit(self):
        return intake.submit(self.config,to_native_session_id='fixture-integrator',request_file=self.request,request_sha256=self.digest)

    def accept(self, sent):
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}):
            return intake.accept(self.config,intake_id=sent['intake_id'],request_sha256=sent['request_sha256'])

    def binding(self):
        path=self.f.manager/'.codex/orchestrator-harness-binding.json'
        write_json(path,_materialized_binding({'schema':'harness-hook-binding/v1','role':'root','provider_id':'codex',
            'harness_root':None,'runtime_root':None,'liveness_path':'.agent-workspace/root-hook-liveness.jsonl',
            'delivery_receipt_path':'.agent-workspace/root-hook-delivery.jsonl'},self.f.harness,self.f.rt))
        return path

    def test_native_marker_registers_before_first_skill_read_without_manager_effects(self):
        binding=self.binding()
        payload={'hook_event_name':'UserPromptSubmit','cwd':str(self.f.manager),
                 'session_id':'fixture-gateway','turn_id':'fixture-turn','prompt':RAW}
        prepared={'root_session_id':self.f.session['session_id'],'native_session_id':None}
        with patch('scripts.prepare_root_launch.validate_prepared_root',return_value=prepared),patch.object(root_session,'resolve_root_session',side_effect=AssertionError('gateway resolved ROOT')):
            result=prompt_optin.evaluate(payload,harness_dir=self.f.harness,workspace=self.f.manager)
        self.assertIn(self.digest,result['hookSpecificOutput']['additionalContext'])
        registered=intake.read_intake(self.config)
        self.assertEqual('REGISTERED',registered['state'])
        self.assertEqual(RAW,registered['original_prompt'])
        self.assertIsNone(registered['coordinator_session_id'])
        self.assertEqual(self.before,root_session.root_session_path(self.config).read_bytes())
        self.assertEqual({},root_hook_wrapper.run('codex','post-tool-use',binding,hook_input=json.dumps({'session_id':'fixture-gateway','hook_event_name':'PostToolUse'})))
        self.assertFalse((self.f.manager/'.agent-workspace/root-hook-liveness.jsonl').exists())
        self.assertIsNone(read_current_epoch(self.f.rt))
        self.assertEqual(registered['intake_id'],self.submit()['intake_id'])
        changed=prompt_optin.evaluate({**payload,'prompt':RAW+'new task'},harness_dir=self.f.harness,workspace=self.f.manager)
        self.assertEqual('block',changed['decision'])
        self.assertEqual(RAW,intake.read_intake(self.config)['original_prompt'])

    def test_exact_raw_intake_gateway_never_binds_manager_pending_denies_everyone(self):
        sent=self.submit()
        self.assertEqual(self.before,root_session.root_session_path(self.config).read_bytes())
        self.assertEqual(RAW,intake.read_intake(self.config)['original_prompt'])
        self.assertEqual(self.digest,sent['request_sha256'])
        self.assertIsNone(read_current_epoch(self.f.rt))
        for native in ('fixture-gateway','fixture-integrator','fixture-planner-native','unknown'):
            with self.subTest(native=native),patch.dict(os.environ,{'CODEX_THREAD_ID':native}),self.assertRaisesRegex(ConfigError,'MANAGER_NOT_OWNER'):
                root_session.resolve_root_session(self.config)
        self.assertEqual(sent,self.submit())
        with self.assertRaisesRegex(ConfigError,'WORKFLOW_REQUEST_HASH'):
            intake.submit(self.config,to_native_session_id='fixture-integrator',request_file=self.request,request_sha256='0'*64)

    def test_genuine_accept_binds_only_observed_target_and_exclusive_owner(self):
        sent=self.submit()
        for native in ('fixture-gateway','unknown'):
            with patch.dict(os.environ,{'CODEX_THREAD_ID':native}),self.assertRaises(ConfigError):
                intake.accept(self.config,intake_id=sent['intake_id'],request_sha256=self.digest)
        with self.assertRaises(ConfigError):
            root_session.bind_native_root_session(self.config,run_id=self.f.session['run_id'],session_id=self.f.session['session_id'],native_session_id='wrong')
        accepted=self.accept(sent)
        self.assertEqual('ACTIVE',accepted['state'])
        self.assertEqual('fixture-integrator',root_session.read_root_session(self.config)['native_session_id'])
        self.assertEqual(accepted,self.accept(sent))
        for native in ('fixture-gateway','fixture-planner-native','fixture-split-reviewer','coder','unknown'):
            with patch.dict(os.environ,{'CODEX_THREAD_ID':native}),self.assertRaises(ConfigError):
                ownership.require_manager_owner(self.config)
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}):
            self.assertEqual('ACTIVE',ownership.require_manager_owner(self.config)['state'])
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator','HARNESS_LANE_ID':'ordinary'}),self.assertRaises(ConfigError):
            ownership.require_manager_owner(self.config)

    def test_accept_interrupt_after_bind_and_after_epoch_recovers_pending_without_authority(self):
        sent=self.submit()
        real=intake._publish
        with patch.object(intake,'_publish',side_effect=RuntimeError('fixture interruption')):
            with self.assertRaisesRegex(RuntimeError,'interruption'):self.accept(sent)
        self.assertEqual('PENDING',intake.read_intake(self.config)['state'])
        self.assertEqual('fixture-integrator',root_session.read_root_session(self.config)['native_session_id'])
        epoch=read_current_epoch(self.f.rt)['epoch_id']
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}),self.assertRaises(ConfigError):
            ownership.require_manager_owner(self.config)
        self.assertEqual(epoch,self.accept(sent)['epoch_id'])

    def test_gateway_hooks_no_manager_events_receipts_liveness_owner_stop_stays_blocked(self):
        sent=self.submit();binding=self.binding()
        self.assertEqual({},root_hook_wrapper.run('codex','post-tool-use',binding,hook_input=json.dumps({'session_id':'fixture-gateway','hook_event_name':'PostToolUse'})))
        self.assertEqual('block',root_hook_wrapper.run('codex','stop',binding,hook_input=json.dumps({'session_id':'fixture-gateway','hook_event_name':'Stop'}))['decision'])
        accepted=self.accept(sent)
        event=promote_event(self.f.rt,event_type='COMPLETION_REVIEW_REQUIRED',event_class='COMPLETION_REVIEW_REQUIRED',lane_id='fixture-notice',run_id='notice-run',summary='Owner only.')
        before=(self.f.rt/'manager/QUEUE.json').read_bytes()
        with patch.object(root_hook_wrapper,'dispatch') as dispatched,patch.object(root_hook_wrapper,'append_delivery_history') as delivered:
            self.assertEqual({},root_hook_wrapper.run('codex','stop',binding,hook_input=json.dumps({'session_id':'fixture-gateway','hook_event_name':'Stop'})))
            dispatched.assert_not_called();delivered.assert_not_called()
        self.assertEqual(before,(self.f.rt/'manager/QUEUE.json').read_bytes())
        self.assertFalse((self.f.manager/'.agent-workspace/root-hook-liveness.jsonl').exists())
        self.assertFalse((self.f.manager/'.agent-workspace/root-hook-delivery.jsonl').exists())
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}):
            result=root_hook_wrapper.run('codex','stop',binding,hook_input=json.dumps({'session_id':'fixture-integrator','hook_event_name':'Stop'}))
            self.assertEqual('block',result['decision']);self.assertIn('unresolved manager',result['reason'])
        for payload in ({'session_id':'unknown','hook_event_name':'Stop'},
                        {'session_id':'fixture-gateway','hook_event_name':'Stop','agent_id':'child'}):
            clean={k:v for k,v in os.environ.items() if k!='CODEX_THREAD_ID'}
            with patch.dict(os.environ,clean,clear=True):
                self.assertEqual('block',root_hook_wrapper.run('codex','stop',binding,hook_input=json.dumps(payload))['decision'])
        # Settle event as authentic owner and close normally, not via gateway.
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}),patch.object(shutdown,'find_harness_root',return_value=self.f.harness):
            acknowledge_event(self.f.rt,event['event_id']);close_event(self.f.rt,event['event_id'],'BLOCKED','Fixture no work.')
            stopped=root_hook_wrapper.run('codex','stop',binding,hook_input=json.dumps({'session_id':'fixture-integrator','hook_event_name':'Stop'}))
            self.assertEqual('block',stopped['decision']);self.assertIn('OPEN',stopped['reason'])
            with ownership.manager_operation(self.config):self.assertTrue(shutdown.run_shutdown()['ok'])
        shutdown.prove_runtime_closed(self.f.rt,self.f.product,self.f.harness)
        self.assertEqual({},root_hook_wrapper.run('codex','stop',binding,hook_input='invalid'))

    def test_accepted_epoch_survives_all_role_gaps_and_owner_can_close(self):
        sent=self.submit();accepted=self.accept(sent)
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}),patch.object(shutdown,'find_harness_root',return_value=self.f.harness):
            for phase in ('planner','split-reviewer','coding','auditor','repair','fresh-auditor'):
                launch._maybe_close_epoch(self.f.rt,accepted['epoch_id'],config=self.config)
                self.assertEqual(accepted['epoch_id'],read_current_epoch(self.f.rt)['epoch_id'],phase)
            with ownership.manager_operation(self.config):self.assertTrue(shutdown.run_shutdown()['ok'])
        shutdown.prove_runtime_closed(self.f.rt,self.f.product,self.f.harness)

    def test_operator_prelaunch_abandon_is_terminal_and_not_gateway_authority(self):
        sent=self.submit()
        with self.assertRaisesRegex(ConfigError,'WORKFLOW_OPERATOR_ONLY'):
            intake.abandon(self.config,intake_id=sent['intake_id'],request_sha256=self.digest)
        clean={k:v for k,v in os.environ.items() if k not in ('CODEX_THREAD_ID','HARNESS_ROOT_SESSION_ID','HARNESS_SESSION_ID','HARNESS_BINDING_ID')}
        with patch.dict(os.environ,clean,clear=True),patch.object(shutdown,'find_harness_root',return_value=self.f.harness):
            result=intake.abandon(self.config,intake_id=sent['intake_id'],request_sha256=self.digest)
            self.assertTrue(result['ok'])
            self.assertTrue(intake.abandon(self.config,intake_id=sent['intake_id'],request_sha256=self.digest)['ok'])
        self.assertEqual('ABANDONED',intake.read_intake(self.config)['state'])
        with self.assertRaises(ConfigError):self.accept(sent)
        shutdown.prove_runtime_closed(self.f.rt,self.f.product,self.f.harness)

    def test_concurrent_duplicate_accepts_are_idempotent_one_owner(self):
        sent=self.submit()
        clean={k:v for k,v in os.environ.items() if k!='CODEX_THREAD_ID'}
        answers=[];errors=[]
        def accept_thread():
            try:
                with ownership._native_hook_identity('codex','fixture-integrator'):
                    answers.append(intake.accept(self.config,intake_id=sent['intake_id'],request_sha256=self.digest))
            except Exception as exc:errors.append(exc)
        with patch.dict(os.environ,clean,clear=True):
            workers=[threading.Thread(target=accept_thread) for _ in range(2)]
            for worker in workers:worker.start()
            for worker in workers:worker.join(15)
        self.assertFalse(errors,errors)
        self.assertEqual(2,len(answers));self.assertEqual(answers[0],answers[1])
        self.assertEqual(answers[0]['epoch_id'],read_current_epoch(self.f.rt)['epoch_id'])

    def test_registered_operator_recovery_and_no_late_submission(self):
        with ownership._native_hook_identity('codex','fixture-gateway'):
            registered=intake.register_gateway(self.config,self.f.session,native='fixture-gateway',prompt=RAW)
        self.assertEqual('REGISTERED',registered['state'])
        clean={k:v for k,v in os.environ.items() if k!='CODEX_THREAD_ID'}
        with patch.dict(os.environ,clean,clear=True),patch.object(shutdown,'find_harness_root',return_value=self.f.harness):
            self.assertTrue(intake.abandon(self.config,intake_id=registered['intake_id'],request_sha256=self.digest)['ok'])
        with self.assertRaises(ConfigError):self.submit()
        shutdown.prove_runtime_closed(self.f.rt,self.f.product,self.f.harness)

    def test_operator_retry_finishes_abandoned_shutdown_without_late_accept(self):
        sent=self.submit()
        clean={k:v for k,v in os.environ.items() if k!='CODEX_THREAD_ID'}
        with patch.dict(os.environ,clean,clear=True),patch.object(shutdown,'run_shutdown',return_value={'ok':False,'code':'FIXTURE_INTERRUPTED_SHUTDOWN'}):
            self.assertFalse(intake.abandon(self.config,intake_id=sent['intake_id'],request_sha256=self.digest)['ok'])
        self.assertEqual('ABANDONED',intake.read_intake(self.config)['state'])
        with self.assertRaisesRegex(ConfigError,'WORKFLOW_ABANDONED'):self.accept(sent)
        with patch.dict(os.environ,clean,clear=True),patch.object(shutdown,'find_harness_root',return_value=self.f.harness):
            self.assertTrue(intake.abandon(self.config,intake_id=sent['intake_id'],request_sha256=self.digest)['ok'])
        shutdown.prove_runtime_closed(self.f.rt,self.f.product,self.f.harness)

    def test_stale_actual_owner_epoch_cannot_exempt_gateway_stop(self):
        sent=self.submit();accepted=self.accept(sent);binding=self.binding()
        state_path=epoch_dir(self.f.rt,accepted['epoch_id'])/'epoch-state.json'
        state=json.loads(state_path.read_text());state['lifecycle']='closed';atomic_write_json(state_path,state)
        result=root_hook_wrapper.run('codex','stop',binding,hook_input=json.dumps({'session_id':'fixture-gateway','hook_event_name':'Stop'}))
        self.assertEqual('block',result['decision']);self.assertIn('STALE',result['reason'])

    def test_recovery_refuses_accepted_stale_or_unknown_work(self):
        sent=self.submit();self.accept(sent)
        clean={k:v for k,v in os.environ.items() if k!='CODEX_THREAD_ID'}
        with patch.dict(os.environ,clean,clear=True),self.assertRaises(ConfigError):
            intake.abandon(self.config,intake_id=sent['intake_id'],request_sha256=self.digest)
        value=intake.read_intake(self.config);value['run_id']='other';value['content_hash']=content_hash(value)
        atomic_write_json(intake.intake_path(self.config),value)
        with self.assertRaisesRegex(ConfigError,'STALE'):intake.read_intake(self.config)

    def native_plan_fixture(self, value):
        c,draft=v3_contract(value,root_session.read_root_session(self.config))
        results={};statuses={};lanes={}
        for role,ref,prefs,native,payload in (
            ('planner',c['native_plan'],c['planner'],'fixture-planner-native',{'workflow_plan':draft}),
            ('reviewer',c['plan_review']['native_review'],c['split_reviewer'],'fixture-split-reviewer',{'plan_review':c['plan_review']['report']})):
            status_path=self.f.home/(role+'-status.json')
            status={'schema':'controller-status/v1','lane_id':ref['lane_id'],'run_id':ref['run_id'],'provider_state':{'provider_session_id':native}}
            atomic_write_json(status_path,status)
            lane={'run_id':ref['run_id'],'lifecycle':'retired','exclusive_resources':[],
                'provider':{'id':prefs['provider'],'model':prefs['model'],'launch_config':prefs['provider_options']},
                'controller_status_path':str(status_path),'git_source':{'base_commit':'a'*40}}
            lane=write_lane(self.f.rt,value['epoch_id'],ref['lane_id'],lane);lanes[role]=lane;statuses[ref['lane_id']]=native
            result={'commit':'a'*40,'completed_at':iso_utc(),'evidence':[deepcopy(payload)]};results[ref['lane_id']]=result
            ref['result_sha256']=sha256_hex(result)
            atomic_write_json(epoch_dir(self.f.rt,value['epoch_id'])/'lanes'/ref['lane_id']/'ORCHESTRATOR_ACCEPTANCE.json',{'schema':'orchestrator-acceptance/v1'})
            event=promote_event(self.f.rt,event_type='COMPLETION_REVIEW_REQUIRED',event_class='COMPLETION_REVIEW_REQUIRED',lane_id=ref['lane_id'],run_id=ref['run_id'],summary=role+' fixture complete.')
            acknowledge_event(self.f.rt,event['event_id']);close_event(self.f.rt,event['event_id'],'COMPLETE','Coordinator receives independent bounded planning output.')
        stack=ExitStack();self.addCleanup(stack.close)
        for target,kwargs in [
            ('orchestrator_harness.lane_cleanup.cleanup_is_proven',{'return_value':True}),
            ('orchestrator_harness.shutdown.cleanup_is_proven',{'return_value':True}),
            ('orchestrator_harness.lane_authority.read_invocation',{'return_value':{}}),
            ('orchestrator_harness.result_validation.read_result',{'side_effect':lambda lane,**kw:results[lane['lane_id']]}),
            ('orchestrator_harness.launch._validate_current_acceptance',{'return_value':None}),
            ('orchestrator_harness.retry_policy.current_invocation_facts',{'side_effect':lambda lane:[{'kind':'COMPLETED','session_id':statuses[lane['lane_id']]}]})]:
            stack.enter_context(patch(target,**kwargs))
        return c,draft,results,lanes,statuses

    def test_actual_native_provenance_freeze_hashes_and_immutable_original(self):
        sent=self.submit();self.accept(sent);value=intake.read_intake(self.config)
        c,draft,results,lanes,statuses=self.native_plan_fixture(value)
        self.assertEqual(c,validate_contract(c))
        path=self.f.home/'v3-contract.json';write_json(path,c)
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}):
            frozen=intake.freeze(self.config,intake_id=sent['intake_id'],contract_path=path)
            self.assertEqual(sha256_hex(c),frozen['contract_sha256'])
            self.assertEqual(frozen,intake.freeze(self.config,intake_id=sent['intake_id'],contract_path=path))
        c['original_prompt']=c['original_prompt'].replace('\r\n','\n')
        with self.assertRaises(ValueError):validate_contract(c)

    def test_native_planner_wrong_result_base_identity_or_stale_review_refuses(self):
        sent=self.submit();self.accept(sent);value=intake.read_intake(self.config)
        c,draft,results,lanes,statuses=self.native_plan_fixture(value)
        path=self.f.home/'v3-contract.json'
        baseline=deepcopy(c);baseline_results=deepcopy(results)
        for change in ('wrong-result','wrong-base','wrong-native','stale-review','wrong-resource','wrong-preferences'):
            c=deepcopy(baseline);results.clear();results.update(deepcopy(baseline_results))
            planner=results[c['native_plan']['lane_id']]
            lane=deepcopy(lanes['planner'])
            if change=='wrong-result':planner['evidence']=[];c['native_plan']['result_sha256']=sha256_hex(planner)
            elif change=='wrong-base':planner['commit']='b'*40;c['native_plan']['result_sha256']=sha256_hex(planner)
            elif change=='wrong-native':statuses[lane['lane_id']]='unrelated-native'
            elif change=='stale-review':c['assignments'][0]['scope'].append('new-file.py')
            elif change=='wrong-resource':lane['exclusive_resources']=['not-read-only']
            else:lane['provider']['model']='different-model'
            write_lane(self.f.rt,value['epoch_id'],lane['lane_id'],lane);write_json(path,c)
            with self.subTest(change=change),patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}),self.assertRaises((ConfigError,ValueError)):
                intake.freeze(self.config,intake_id=sent['intake_id'],contract_path=path)
            statuses[lane['lane_id']]='fixture-planner-native';write_lane(self.f.rt,value['epoch_id'],lanes['planner']['lane_id'],lanes['planner'])
        self.assertIsNone(intake.read_intake(self.config)['contract'])

    def test_offline_full_role_flow_raw_to_frozen_plan_code_repair_fresh_audit_closed(self):
        sent=self.submit();self.accept(sent);value=intake.read_intake(self.config)
        c,draft,results,lanes,statuses=self.native_plan_fixture(value)
        path=self.f.home/'full-v3-contract.json';write_json(path,c)
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'fixture-integrator'}):
            intake.freeze(self.config,intake_id=sent['intake_id'],contract_path=path)
            # Real local source, Git commits and original complete subprocess
            # checks; only role/provider observations above are test doubles.
            receipt=run_offline_repair_fixture(self.f.home/'coding-audit-repair',contract=c)
            self.assertNotEqual(receipt['before_revision'],receipt['after_revision'])
            self.assertEqual('FAIL',receipt['before_audit']['verdict'])
            self.assertEqual('PASS',receipt['after_audit']['verdict'])
            self.assertEqual('COMPLETE',receipt['final']['status'])
            self.assertEqual(RAW,receipt['contract']['original_prompt'])
            with patch.object(shutdown,'find_harness_root',return_value=self.f.harness),ownership.manager_operation(self.config):
                closed=shutdown.run_shutdown();self.assertTrue(closed['ok'],closed)
        shutdown.prove_runtime_closed(self.f.rt,self.f.product,self.f.harness)
        self.assertEqual('ACTIVE',intake.status(self.config,intake_id=sent['intake_id'])['state'])


if __name__=='__main__':unittest.main()
