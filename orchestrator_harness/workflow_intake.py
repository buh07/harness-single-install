"""Direct native ownership from immutable raw intake; no client launcher.

Cooperative native identities are observed, never granted by a task file. The
prepared manager is the genuinely created coordinator, never the gateway.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from .config import ConfigError, load_resource_manifest
from .core import content_hash, iso_utc, new_id, read_json, sha256_hex
from .epochs import open_epoch, read_current_epoch, read_epoch_state
from .records import RecordLock, atomic_write_json, read_record, runtime_admission_lock

SCHEMA = 'harness-workflow-intake/v1'
_SCOPE = ('run_id', 'session_id', 'provider_id', 'config_identity')
_FIELDS = {'schema', *_SCOPE, 'intake_id', 'gateway_session_id', 'coordinator_session_id',
           'original_prompt', 'request_sha256', 'state', 'submitted_at', 'accepted_at',
           'epoch_id', 'contract', 'contract_sha256', 'content_hash'}

def intake_path(config):
    return config.runtime_root / 'WORKFLOW_INTAKE.json'

def linkage(value):
    return {key: value[key] for key in ('intake_id', 'request_sha256', 'gateway_session_id', 'coordinator_session_id')}

def read_intake(config, session=None):
    from .root_session import read_root_session
    try:
        value = read_record(intake_path(config), SCHEMA)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ConfigError('WORKFLOW_INTAKE_INVALID: preserve intake evidence') from exc
    session = session or read_root_session(config)
    from .manager_ownership import ownership_path
    if ownership_path(config).exists():
        raise ConfigError('WORKFLOW_INTAKE_INVALID: conflicting legacy ownership remains')
    if (set(value) != _FIELDS or value.get('content_hash') != content_hash(value)
            or any(value.get(k) != session[k] for k in _SCOPE)
            or value.get('state') not in {'REGISTERED', 'PENDING', 'ACTIVE', 'ABANDONED'}
            or (value.get('coordinator_session_id') is not None and session['native_session_id'] not in (None, value.get('coordinator_session_id')))
            or (value.get('state') in {'PENDING', 'ACTIVE'} and (not isinstance(value.get('coordinator_session_id'), str) or not value['coordinator_session_id'].strip()))
            or (value.get('state') == 'REGISTERED' and value.get('coordinator_session_id') is not None)
            or not isinstance(value.get('gateway_session_id'), str) or not value['gateway_session_id'].strip()
            or value['gateway_session_id'] == value['coordinator_session_id']
            or not isinstance(value.get('original_prompt'), str)
            or value.get('request_sha256') != hashlib.sha256(value['original_prompt'].encode('utf-8')).hexdigest()
            or not isinstance(value.get('intake_id'), str) or not value['intake_id']
            or not isinstance(value.get('submitted_at'), str)
            or (value.get('accepted_at') is not None if value['state'] in {'REGISTERED', 'PENDING', 'ABANDONED'}
                else not isinstance(value.get('accepted_at'), str))):
        raise ConfigError('WORKFLOW_INTAKE_STALE: intake identity, bytes, or scope differs')
    if value['state'] in {'REGISTERED', 'PENDING', 'ABANDONED'} and value['epoch_id'] is not None:
        raise ConfigError('WORKFLOW_INTAKE_INVALID: pending intake cannot own an epoch')
    if value['state'] == 'ACTIVE':
        if session['native_session_id'] != value['coordinator_session_id']:
            raise ConfigError('WORKFLOW_INTAKE_STALE: accepted coordinator not genuinely bound')
        marker = read_current_epoch(config.runtime_root)
        epoch = read_epoch_state(config.runtime_root, marker['epoch_id']) if marker is not None else None
        if epoch is None:
            from .setup import read_runtime_state
            state = read_runtime_state(config.runtime_root) or {}
            if state.get('state') not in {'SHUTTING_DOWN', 'CLOSED'}:
                raise ConfigError('WORKFLOW_INTAKE_STALE: active owner epoch missing')
            epoch = read_epoch_state(config.runtime_root, value['epoch_id'])
        if epoch.get('epoch_id') != value['epoch_id'] or epoch.get('config_identity') != session['config_identity']:
            raise ConfigError('WORKFLOW_INTAKE_STALE: owner epoch differs')
        from .setup import read_runtime_state
        runtime = (read_runtime_state(config.runtime_root) or {}).get('state')
        if (runtime not in {'OPEN', 'SHUTTING_DOWN', 'CLOSED'}
                or (runtime == 'OPEN' and (marker is None or epoch.get('lifecycle') != 'active'))
                or (runtime == 'CLOSED' and (marker is not None or epoch.get('lifecycle') != 'closed'))):
            raise ConfigError('WORKFLOW_INTAKE_STALE: runtime and actual owner lifecycle differ')
    if value['contract'] is None:
        if value['contract_sha256'] is not None:
            raise ConfigError('WORKFLOW_INTAKE_INVALID: contract hash without contract')
    else:
        from .workflow_contract import validate_contract
        contract = validate_contract(value['contract'])
        if (value['state'] != 'ACTIVE' or value['contract_sha256'] != sha256_hex(contract)
                or contract['original_prompt'] != value['original_prompt'] or contract['intake'] != linkage(value)):
            raise ConfigError('WORKFLOW_INTAKE_INVALID: frozen contract linkage differs')
    return value

def _publish(config, value):
    value['content_hash'] = content_hash(value)
    atomic_write_json(intake_path(config), value)
    return _result(config, value)

def _result(config, value):
    return {'ok': True, 'code': 'WORKFLOW_INTAKE_' + value['state'],
            **{k: value[k] for k in ('intake_id', 'request_sha256', 'state', 'gateway_session_id',
                'coordinator_session_id', 'epoch_id', 'contract_sha256')},
            'intake_path': str(intake_path(config)),
            'next_action': 'gateway submits exact registered request to genuine preseeded coordinator' if value['state'] == 'REGISTERED' else 'operator must finish explicit prelaunch shutdown; intake is terminal' if value['state'] == 'ABANDONED' else 'designated native coordinator accepts, then owns planning and cleanup' if value['state'] in {'REGISTERED', 'PENDING', 'ABANDONED'}
                           else 'coordinator owns all work and shutdown; gateway may yield'}


def register_gateway(config, session, *, native: str, prompt: str):
    """Native UserPromptSubmit intake registration, not a mode toggle/launcher.

    Exact original bytes and gateway identity come from validated native hook
    JSON. Registration grants no manager authority or provider execution.
    """
    from .manager_ownership import _not_worker, _not_registered_lane, _ready, observed_native, ownership_path
    with RecordLock(config.runtime_root / 'MANAGER_OPERATION.json'), runtime_admission_lock(config.runtime_root):
        _not_worker()
        if observed_native(session['provider_id']) != native or session['native_session_id'] == native:
            raise ConfigError('WORKFLOW_GATEWAY_IDENTITY: native gateway must be distinct from prepared manager')
        _not_registered_lane(config, native)
        _ready(config, session)
        if ownership_path(config).exists():
            raise ConfigError('WORKFLOW_LEGACY_OWNERSHIP: preserve saved manager workflow; fresh preparation required')
        value = read_intake(config, session)
        if value is not None:
            if value['gateway_session_id'] == native and value['original_prompt'] == prompt and value['state'] in {'REGISTERED', 'PENDING'}:
                return _result(config, value)
            raise ConfigError('WORKFLOW_INTAKE_EXISTS: preserve current immutable request; new task needs fresh preparation')
        if read_current_epoch(config.runtime_root) is not None:
            raise ConfigError('WORKFLOW_INTAKE_NOT_FRESH: gateway registration must precede work admission')
        value = {'schema': SCHEMA, **{key: session[key] for key in _SCOPE}, 'intake_id': new_id(),
            'gateway_session_id': native, 'coordinator_session_id': None,
            'original_prompt': prompt, 'request_sha256': hashlib.sha256(prompt.encode('utf-8')).hexdigest(),
            'state': 'REGISTERED', 'submitted_at': iso_utc(), 'accepted_at': None,
            'epoch_id': None, 'contract': None, 'contract_sha256': None}
        return _publish(config, value)

def submit(config, *, to_native_session_id: str, request_file: Path, request_sha256: str):
    from .manager_ownership import _not_worker, _not_registered_lane, _ready, observed_native, ownership_path
    from .root_session import read_root_session
    from .mutation import read_bytes
    path = request_file.absolute()
    raw = read_bytes(path.parent, path.name, max_bytes=4_000_000)
    if hashlib.sha256(raw).hexdigest() != request_sha256:
        raise ConfigError('WORKFLOW_REQUEST_HASH: file must match original native prompt SHA256 exactly')
    prompt = raw.decode('utf-8')  # Deliberately no newline normalization or stripping.
    if not prompt.strip():
        raise ConfigError('WORKFLOW_REQUEST_REQUIRED: exact nonempty UTF8 request required')
    with RecordLock(config.runtime_root / 'MANAGER_OPERATION.json'), runtime_admission_lock(config.runtime_root):
        session = read_root_session(config)
        _not_worker()
        native = observed_native(session['provider_id'])
        if (not isinstance(to_native_session_id, str) or not to_native_session_id.strip()
                or any(ord(c) < 32 for c in to_native_session_id)
                or session['native_session_id'] not in (None, to_native_session_id) or native == to_native_session_id):
            raise ConfigError('WORKFLOW_COORDINATOR_REQUIRED: distinct genuinely preseeded native coordinator required')
        _not_registered_lane(config, native)
        _ready(config, session)
        if ownership_path(config).exists():
            raise ConfigError('WORKFLOW_LEGACY_OWNERSHIP: preserve legacy run; prepare a fresh run')
        existing = read_intake(config, session)
        if existing is not None:
            if existing['state'] == 'REGISTERED' and existing['gateway_session_id'] == native and existing['original_prompt'] == prompt:
                existing.update(state='PENDING', coordinator_session_id=to_native_session_id)
                return _publish(config, existing)
            if existing['gateway_session_id'] == native and existing['original_prompt'] == prompt and existing['coordinator_session_id'] == to_native_session_id:
                return _result(config, existing)
            raise ConfigError('WORKFLOW_INTAKE_EXISTS: preserve immutable intake; new task needs fresh preparation')
        if read_current_epoch(config.runtime_root) is not None:
            raise ConfigError('WORKFLOW_INTAKE_NOT_FRESH: submit before any native epoch/work admission')
        value = {'schema': SCHEMA, **{key: session[key] for key in _SCOPE}, 'intake_id': new_id(),
            'gateway_session_id': native, 'coordinator_session_id': to_native_session_id,
            'original_prompt': prompt, 'request_sha256': hashlib.sha256(raw).hexdigest(),
            'state': 'PENDING', 'submitted_at': iso_utc(), 'accepted_at': None,
            'epoch_id': None, 'contract': None, 'contract_sha256': None}
        return _publish(config, value)

def accept(config, *, intake_id: str, request_sha256: str):
    from .manager_ownership import _not_worker, _not_registered_lane, _ready, observed_native
    from .root_session import read_root_session, bind_native_root_session
    with RecordLock(config.runtime_root / 'MANAGER_OPERATION.json'):
        session = read_root_session(config)
        _not_worker()
        _ready(config, session)
        value = read_intake(config, session)
        native = observed_native(session['provider_id'])
        if (value is None or value['intake_id'] != intake_id or value['request_sha256'] != request_sha256
                or native != value['coordinator_session_id']):
            raise ConfigError('WORKFLOW_ACCEPT_MISMATCH: exact observed native coordinator and intake required')
        _not_registered_lane(config, native)
        if value['state'] == 'ACTIVE':
            return _result(config, value)
        if value['state'] != 'PENDING':
            raise ConfigError('WORKFLOW_ABANDONED: terminal intake cannot be accepted')
        # Genuine first-tool native identity, not the gateway's supplied target,
        # is bound through the existing one-time ROOT session API. It takes its
        # own admission lock. A crash leaves exact-target PENDING, never generic
        # authority; the same native coordinator can retry safely.
        bind_native_root_session(config, run_id=session['run_id'], session_id=session['session_id'],
                                 native_session_id=native)
        with runtime_admission_lock(config.runtime_root):
            session = read_root_session(config)
            _ready(config, session)
            value = read_intake(config, session)
            if value['state'] != 'PENDING':
                raise ConfigError('WORKFLOW_ACCEPT_MISMATCH: pending intake changed')
            # Interrupted publication after epoch creation is recoverable:
            # pending denies every generic operation; retry reuses empty epoch.
            epoch = open_epoch(config.runtime_root, config, load_resource_manifest(config.harness_root))
            value.update(state='ACTIVE', accepted_at=iso_utc(), epoch_id=epoch['epoch_id'])
            return _publish(config, value)


def status(config, *, intake_id: str):
    from .manager_ownership import _not_worker, observed_native
    _not_worker()
    value = read_intake(config)
    if (value is None or value['intake_id'] != intake_id
            or observed_native(value['provider_id']) not in {value['gateway_session_id'], value['coordinator_session_id']}):
        raise ConfigError('WORKFLOW_INTAKE_UNKNOWN: exact registered identity/intake required')
    return _result(config, value)

def gateway_boundary(config, session, native: str, boundary: str):
    """Exact non-owner gateway only; never consumes manager delivery evidence."""
    from .manager_ownership import _not_worker, _not_registered_lane
    value = read_intake(config, session)
    if value is None or native != value['gateway_session_id']:
        return False
    _not_worker()
    _not_registered_lane(config, native)
    if boundary == 'stop' and value['state'] != 'ACTIVE':
        raise ConfigError('WORKFLOW_ACCEPTANCE_PENDING: resume designated coordinator to accept and own cleanup')
    return True

def freeze(config, *, intake_id: str, contract_path: Path):
    from .manager_ownership import manager_operation, _require_native_plan_review
    from .workflow_contract import DIRECT_CONTRACT_SCHEMA, validate_contract
    from .root_session import read_root_session
    contract = validate_contract(read_json(contract_path))
    with manager_operation(config), runtime_admission_lock(config.runtime_root):
        session = read_root_session(config)
        value = read_intake(config, session)
        if value is None or value['state'] != 'ACTIVE' or value['intake_id'] != intake_id:
            raise ConfigError('WORKFLOW_FREEZE_MISMATCH: active exact intake required')
        if (contract['schema'] != DIRECT_CONTRACT_SCHEMA or contract['original_prompt'] != value['original_prompt']
                or contract['intake'] != linkage(value) or contract['coordinator']['provider'] != session['provider_id']):
            raise ConfigError('WORKFLOW_FREEZE_MISMATCH: preserve exact original bytes and native intake scope')
        if value['contract'] is not None:
            if value['contract'] == contract:
                return _result(config, value)
            raise ConfigError('WORKFLOW_CONTRACT_FROZEN: original ledger cannot be replaced')
        planner = _require_native_planner(config, session, contract, value)
        _require_native_plan_review(config, session, contract, planner, value['coordinator_session_id'])
        value.update(contract=contract, contract_sha256=sha256_hex(contract))
        return _publish(config, value)

def _require_native_planner(config, session, contract, intake):
    """Actual retired clean native planning RESULT, not a claimed role string."""
    from .epochs import epoch_dir
    from .lanes import read_lane
    from .lane_cleanup import cleanup_is_proven, observe_controller_status
    from .lane_authority import read_invocation
    from .result_validation import read_result
    from .retry_policy import current_invocation_facts
    from .bootstrap import _validate_provider_launch_config
    from .workflow_contract import plan_sha256
    from datetime import datetime
    ref = contract['native_plan']
    if (ref['epoch_id'] != intake['epoch_id'] or ref['prepared_run_id'] != session['run_id']
            or ref['root_session_id'] != session['session_id']):
        raise ConfigError('WORKFLOW_PLANNER_SCOPE: planner differs from current native intake')
    lane = read_lane(config.runtime_root, ref['epoch_id'], ref['lane_id'])
    expected = contract['planner']
    preferences = _validate_provider_launch_config(Path(__file__).resolve().parent.parent, provider_id=expected['provider'],
        model=expected['model'], launch_config=expected['provider_options'])
    if (lane.get('run_id') != ref['run_id'] or lane.get('lifecycle') != 'retired'
            or lane.get('exclusive_resources') or not cleanup_is_proven(lane)
            or lane.get('provider') != {'id': expected['provider'], 'model': expected['model'], 'launch_config': preferences}):
        raise ConfigError('WORKFLOW_PLANNER_LANE: exact retired resource-free planner/preferences required')
    read_invocation(lane)
    result = read_result(lane, clean=True)
    native = ((observe_controller_status(lane).status or {}).get('provider_state') or {}).get('provider_session_id')
    completed = [fact for fact in current_invocation_facts(lane) if fact['kind'] == 'COMPLETED']
    plans = [item['workflow_plan'] for item in result['evidence'] if isinstance(item, dict) and 'workflow_plan' in item]
    if (not native or native != ref['planner_session_id'] or native in {intake['gateway_session_id'], intake['coordinator_session_id']}
            or not completed or any(fact.get('session_id') != native for fact in completed)
            or sha256_hex(result) != ref['result_sha256'] or result['commit'] != lane['git_source']['base_commit']
            or len(plans) != 1 or plan_sha256(plans[0]) != plan_sha256(contract)
            or datetime.fromisoformat(result['completed_at'].replace('Z', '+00:00'))
                < datetime.fromisoformat(session['prepared_at'].replace('Z', '+00:00'))):
        raise ConfigError('WORKFLOW_PLANNER_RESULT: exact independent native planner identity/RESULT/plan required')
    from .launch import _validate_current_acceptance
    from .review import ACCEPTANCE_SCHEMA
    acceptance = read_record(epoch_dir(config.runtime_root, ref['epoch_id']) / 'lanes' / ref['lane_id']
                             / 'ORCHESTRATOR_ACCEPTANCE.json', ACCEPTANCE_SCHEMA)
    _validate_current_acceptance(config.runtime_root, ref['epoch_id'], lane, acceptance)
    from .manager_queue import read_manager_queue, historical_events
    queue = read_manager_queue(config.runtime_root)
    if not any(event.get('lane_id') == ref['lane_id'] and event.get('run_id') == ref['run_id']
               and event.get('type') == 'COMPLETION_REVIEW_REQUIRED' and event['state'] == 'COMPLETE'
               for event in historical_events(config.runtime_root, queue)):
        raise ConfigError('WORKFLOW_PLANNER_UNSETTLED: actual completed native planning event required')
    if contract['plan_review']['report']['reviewer_session_id'] in {intake['gateway_session_id'], intake['coordinator_session_id']}:
        raise ConfigError('WORKFLOW_REVIEW_IDENTITY: outer and coordinator cannot review')
    return native


def abandon(config, *, intake_id: str, request_sha256: str):
    """Explicit human-terminal recovery, never authority for the gateway.

    Only a wholly unclaimed prelaunch runtime can use this path. Preserve the
    terminal intake and normal shutdown cleanup proof; a new task needs fresh
    preparation. Cooperative same-user boundary, not a hostile-process sandbox.
    """
    import os
    from .manager_ownership import _NATIVE, _not_worker, _HOOK_NATIVE
    from . import shutdown
    _not_worker()
    if _HOOK_NATIVE.get() is not None or any(os.environ.get(key) for key in (*_NATIVE.values(), 'HARNESS_ROOT_SESSION_ID',
            'HARNESS_SESSION_ID', 'HARNESS_BINDING_ID')):
        raise ConfigError('WORKFLOW_OPERATOR_ONLY: recovery requires the independent prelaunch operator terminal, not any native client')
    with RecordLock(config.runtime_root / 'MANAGER_OPERATION.json'):
        with runtime_admission_lock(config.runtime_root):
            value = read_intake(config)
            if (value is None or value['intake_id'] != intake_id or value['request_sha256'] != request_sha256
                    or value['state'] not in {'REGISTERED', 'PENDING', 'ABANDONED'}
                    or read_current_epoch(config.runtime_root) is not None):
                raise ConfigError('WORKFLOW_RECOVERY_UNSAFE: exact unclaimed intake and no epoch required')
            # No admitted lane/controller/resource/event work may be abandoned.
            epochs = config.runtime_root / 'epochs'
            for epoch in epochs.iterdir() if epochs.exists() else ():
                if (epoch / 'lanes').exists() and any((epoch / 'lanes').iterdir()):
                    raise ConfigError('WORKFLOW_RECOVERY_UNSAFE: retained admitted lane history exists')
                if (epoch / 'manager-history').exists():
                    raise ConfigError('WORKFLOW_RECOVERY_UNSAFE: retained native manager archive exists')
                archive = epoch / 'CLOSED_MANAGER_QUEUE.json'
                if archive.exists() and read_record(archive, 'manager-queue/v1').get('events'):
                    raise ConfigError('WORKFLOW_RECOVERY_UNSAFE: retained native event history exists')
            from .leases import lease_records
            if lease_records(config.runtime_root):
                raise ConfigError('WORKFLOW_RECOVERY_UNSAFE: retained resource leases exist')
            queue_path = config.runtime_root / 'manager' / 'QUEUE.json'
            if queue_path.exists() and read_record(queue_path, 'manager-queue/v1').get('events'):
                raise ConfigError('WORKFLOW_RECOVERY_UNSAFE: retained native manager events exist')
            value['state'] = 'ABANDONED'
            _publish(config, value)
        # run_shutdown owns runtime admission itself. The manager-operation lock
        # remains held, excluding intake accept and all native manager commands.
        result = shutdown.run_shutdown()
        result['intake_id'] = intake_id
        return result
