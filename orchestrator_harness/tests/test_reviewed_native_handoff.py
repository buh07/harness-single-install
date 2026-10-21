"""Real native epoch/queue/monitor transfer with explicit provider-evidence doubles.

No provider is launched: RESULT, protected history, cleanup and acceptance
observations are scoped doubles. These tests are not real model execution proof.
"""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch

from orchestrator_harness import manager_ownership as ownership, root_session, launch
from orchestrator_harness.config import ConfigError
from orchestrator_harness.core import iso_utc, sha256_hex
from orchestrator_harness.epochs import close_epoch, epoch_dir, read_current_epoch
from orchestrator_harness.lanes import write_lane
from orchestrator_harness.manager_queue import promote_event, acknowledge_event, close_event
from orchestrator_harness.records import atomic_write_json
from orchestrator_harness.tests.support import PreparedRootFixture, write_json
from orchestrator_harness.tests.test_reviewed_workflow import reviewed_contract, REV


class ReviewedNativeHandoffTests(unittest.TestCase):
    def setUp(self):
        self.fixture=PreparedRootFixture(self);self.config=self.fixture.config
        env=patch.dict(os.environ,{**self.fixture.environment,'CODEX_THREAD_ID':'planner'},clear=True);env.start();self.addCleanup(env.stop)
        preparation=patch('scripts.prepare_root_launch.validate_prepared_root',return_value={});preparation.start();self.addCleanup(preparation.stop)
        self.c=reviewed_contract();self.report=self.c['plan_review']['report'];self.ref=self.c['plan_review']['native_review']
        scope={'prepared_run_id':self.fixture.session['run_id'],'root_session_id':self.fixture.session['session_id']}
        self.report.update(scope);self.ref.update(scope,epoch_id=self.fixture.epoch['epoch_id'])
        self.epoch=self.ref['epoch_id'];self.lane_id=self.ref['lane_id']
        self.status_path=self.fixture.home/'controller.status.json'
        self.status={'schema':'controller-status/v1','lane_id':self.lane_id,'run_id':self.ref['run_id'],
            'provider_state':{'provider_session_id':'fixture-split-reviewer'}}
        atomic_write_json(self.status_path,self.status)
        expected=self.c['split_reviewer']
        self.lane={'run_id':self.ref['run_id'],'lifecycle':'retired','exclusive_resources':[],
            'provider':{'id':expected['provider'],'model':expected['model'],'launch_config':expected['provider_options']},
            'controller_status_path':str(self.status_path),'git_source':{'base_commit':REV}}
        self.save_lane()
        self.result={'commit':REV,'completed_at':iso_utc(),'evidence':[{'plan_review':deepcopy(self.report)}]}
        self.ref['result_sha256']=sha256_hex(self.result)
        self.contract_path=self.fixture.home/'contract.json';self.save_contract()
        folder=epoch_dir(self.fixture.rt,self.epoch)/'lanes'/self.lane_id
        atomic_write_json(folder/'ORCHESTRATOR_ACCEPTANCE.json',{'schema':'orchestrator-acceptance/v1'})
        self.event=promote_event(self.fixture.rt,event_type='COMPLETION_REVIEW_REQUIRED',event_class='COMPLETION_REVIEW_REQUIRED',
            lane_id=self.lane_id,run_id=self.ref['run_id'],summary='Fixture review completed.')
        acknowledge_event(self.fixture.rt,self.event['event_id'])
        close_event(self.fixture.rt,self.event['event_id'],'COMPLETE','Planner received and resolved advisory review.')
        for target,value in [
            ('orchestrator_harness.lane_cleanup.cleanup_is_proven',True),
            ('orchestrator_harness.lane_authority.read_invocation',{}),
            ('orchestrator_harness.result_validation.read_result',self.result),
            ('orchestrator_harness.launch._validate_current_acceptance',None),
            ('orchestrator_harness.retry_policy.current_invocation_facts',[{'kind':'COMPLETED','session_id':'fixture-split-reviewer'}])]:
            p=patch(target,return_value=value);p.start();self.addCleanup(p.stop)

    def save_lane(self):
        write_lane(self.fixture.rt,self.epoch,self.lane_id,self.lane)

    def save_contract(self):write_json(self.contract_path,self.c)

    def offer(self):return ownership.offer_handoff(self.config,to_native_session_id='coordinator',contract_path=self.contract_path)

    def test_retired_closed_planning_epoch_transfers_into_new_epoch_without_deadlock(self):
        before=root_session.root_session_path(self.config).read_bytes()
        close_epoch(self.fixture.rt,self.epoch)
        archive=epoch_dir(self.fixture.rt,self.epoch)/'CLOSED_MANAGER_QUEUE.json';archived=archive.read_bytes()
        offered=self.offer();new=read_current_epoch(self.fixture.rt)['epoch_id']
        self.assertNotEqual(self.epoch,new);self.assertEqual(archived,archive.read_bytes())
        with patch.dict(os.environ,{'CODEX_THREAD_ID':'coordinator'}):
            self.assertEqual('MANAGER_HANDOFF_ACTIVE',ownership.accept_handoff(self.config,offer_id=offered['offer_id'],contract_sha256=offered['contract_sha256'])['code'])
        self.assertEqual(before,root_session.root_session_path(self.config).read_bytes())

    def test_unretired_lane_pending_event_or_wrong_prepared_scope_refuses(self):
        for change in ('running','pending','scope'):
            with self.subTest(change=change):
                if change=='running':
                    self.lane['lifecycle']='running';self.save_lane()
                elif change=='pending':
                    pending=promote_event(self.fixture.rt,event_type='COMPLETION_REVIEW_REQUIRED',event_class='COMPLETION_REVIEW_REQUIRED',lane_id='other',run_id='other-run',summary='Still pending.')
                else:
                    self.ref['prepared_run_id']=self.report['prepared_run_id']='other-run';self.save_contract()
                with self.assertRaises(ConfigError):self.offer()
                self.assertFalse(ownership.ownership_path(self.config).exists())
                self.lane['lifecycle']='retired';self.save_lane()
                if change=='pending':
                    acknowledge_event(self.fixture.rt,pending['event_id']);close_event(self.fixture.rt,pending['event_id'],'BLOCKED','No work outstanding.')

    def test_native_identity_not_self_selected_or_same_planner(self):
        for native in ('different-observed-reviewer','planner','coordinator'):
            self.status['provider_state']['provider_session_id']=native;atomic_write_json(self.status_path,self.status)
            with patch('orchestrator_harness.retry_policy.current_invocation_facts',return_value=[{'kind':'COMPLETED','session_id':native}]):
                with self.subTest(native=native),self.assertRaises(ValueError):self.offer()
        self.assertFalse(ownership.ownership_path(self.config).exists())

    def test_report_result_hash_and_readonly_commit_are_linked(self):
        original=deepcopy(self.result)
        for change in ('hash','embedded-report','commit'):
            self.result.clear();self.result.update(deepcopy(original))
            if change=='hash':self.ref['result_sha256']='1'*64
            elif change=='embedded-report':self.result['evidence']=[];self.ref['result_sha256']=sha256_hex(self.result)
            else:self.result['commit']='b'*40;self.ref['result_sha256']=sha256_hex(self.result)
            self.save_contract()
            with self.subTest(change=change),self.assertRaisesRegex(ConfigError,'REVIEW_RESULT'):self.offer()

    def test_closed_queue_archive_missing_or_changed_is_not_reconstructed(self):
        close_epoch(self.fixture.rt,self.epoch)
        archive=epoch_dir(self.fixture.rt,self.epoch)/'CLOSED_MANAGER_QUEUE.json'
        original=archive.read_bytes();archive.unlink()
        with self.assertRaises(FileNotFoundError):self.offer()
        archive.write_bytes(original)
        queue=__import__('json').loads(original);queue['queue_id']='altered';atomic_write_json(archive,queue)
        with self.assertRaises(Exception):close_epoch(self.fixture.rt,self.epoch)
        self.assertEqual('altered',__import__('json').loads(archive.read_bytes())['queue_id'])


if __name__=='__main__':unittest.main()
