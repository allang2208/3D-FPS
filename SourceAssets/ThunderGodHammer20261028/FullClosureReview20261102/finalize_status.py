"""Consolidate existing receipts; completion means audit completion, not zero findings."""
from pathlib import Path
from datetime import datetime
import json
import re

OUT = Path(__file__).parent
read = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
status = read(OUT / 'review-status.json')
run = OUT / 'Listen-20261103-114146'
receipt = read(run / 'receipt.json')
host = read(run / 'host.json')
launches = [read(run / ('launch-' + role + '.json')) for role in ('host', 'observer')]
patterns = r'Network checksum mismatch|NetChecksumMismatch|NetworkFailure|Assertion failed|Fatal error'
errors = [line for path in run.glob('*.log') for line in path.read_text(encoding='utf-8', errors='replace').splitlines() if re.search(patterns, line, re.I)]
assert receipt['passed'] and host['passed'] and host['completed'] == 15
assert all(row['exit_code'] == 0 for row in receipt['exits'])
assert len({row['code_sha256'] for row in launches}) == 1 and not errors
status.update(
    completed=True,
    status='audit_completed_with_open_visual_finding',
    updated=datetime.now().astimezone().isoformat(),
    completion_meaning='Requested audit and reporting complete; the cold-join visual finding below remains unresolved.',
    pending=[],
)
status['builds'] = {target: read(OUT / ('build-' + target + '.json')) for target in ('FPSGAMEEditor', 'FPSGAME')}
status['confirmed_gameplay_fixes'] = [
    'Pending hammer customization survives stale profile mirrors and resolves matching receipts/rejections.',
    'Near-boundary remote full-charge release waits on cancellable server timer before committing once.',
    'Respawn binds and resets the new pawn profile before initial replication; old-life mirrors and ledgers still reset.',
]
status['package']['ufs_data_and_icons'] = read(OUT / 'staged-data-check.json')
status['render_audio_performance']['scope'] = 'Local first-person/workbench, empty-scene timings and captured audio only. Remote presentation has a separate open cold-load finding. Human sound preference not evaluated.'
status['remote_presentation'] = {
    'run': run.name,
    'functional_passed': True,
    'functional_cases': 15,
    'process_exits': receipt['exits'],
    'same_code_on_both_peers': True,
    'dll_sha256': launches[0]['code_sha256'],
    'network_checksum_failure_assert_fatal_matches': errors,
    'screenshots': len(list((run / 'ObserverFrames').glob('*.png'))),
    'grounded_hammer_reviewed': 'ObserverFrames/remote_000.png',
    'recalled_equipped_hammer_reviewed': 'ObserverFrames/remote_010.png',
    'ground_and_final_held_state_visible': True,
    'cold_join_visual_transition_passed': False,
    'fixture': read(OUT / 'headless-host-scope.json'),
    'scope': 'Two frozen Editor-Cmd peers, real host input and observer rendering; no reconnect/travel coverage in this final capture.',
}
status['open_findings'] = [{
    'id': 'remote-cold-join-presentation',
    'priority': 'P2',
    'resolved': False,
    'observation': 'During cold late join, remote head is temporarily missing/displaced and held weapon appears late; final frame recovers complete head and correct hammer grip.',
    'evidence': [run.name + '/ObserverFrames/remote_' + n + '.png' for n in ('005', '006', '007', '008', '009', '010')],
    'log_evidence': 'observer.log 03:43:32.154 still waits for SKM_Jason_head skinned asset readiness.',
    'cause_status': 'Not isolated or repaired; adjacent to first appearance asset loading. Not proven to be caused by hammer logic or packet loss.',
    'next_scope': 'Character appearance/equipment visibility during first async load.',
}]
status['resource_interrupted_captures'] = list(dict.fromkeys(status['resource_interrupted_captures'] + ['Listen-20261103-112953', 'Listen-20261103-113158']))
status['excluded_capture_attempts'] = {
    'Packaged-Listen-20261103-111720': 'Mixed target builds captured concurrent network component edits; checksum mismatch; owned run stopped and excluded.',
    'Listen-20261103-113856': 'Artificial missing-body catalog triggered appearance null access; discarded fixture, real body restored in final run.',
}
status['remote_partial']['superseded_by'] = run.name
status['limits'] = [
    'Same-machine real UDP with injected latency/loss, not cross-machine internet testing.',
    'Dedicated authority used Editor-Cmd, not a separately packaged Server target.',
    'Hammer-scoped Development package and empty scene, not full-game release or combat performance certification.',
    'Audio preference and full continuous animation judgement remain subjective.',
]
diagnosis_path = OUT / 'ColdJoinDiagnosis20261103/diagnosis.json'
if diagnosis_path.exists():
    diagnosis = read(diagnosis_path)
    finding = status['open_findings'][0]
    finding.update(
        observation='Confirmed missing head during initial cold appearance load. Body is visible before the independently loaded head is created; final frame has complete appearance.',
        cause_status=diagnosis['confirmed_cause'],
        corrections=diagnosis['corrections'],
        next_scope='Initial character appearance readiness and targeted preparation; no gameplay fix implemented by the diagnosis.',
        diagnosis='ColdJoinDiagnosis20261103/README.md',
    )
    status['followup_diagnosis'] = {
        'completed': True,
        'method': diagnosis['method'],
        'sources_matching_preserved_snapshot': sum(row['identical_text'] for row in diagnosis['source_comparison']),
        'source_files_compared': len(diagnosis['source_comparison']),
        'new_runtime_tests': False,
        'functional_fix_applied': False,
        'remaining': diagnosis['unresolved'],
    }
fix_delivery = OUT / 'ColdJoinFix20261103/delivery.json'
if fix_delivery.exists():
    delivery = read(fix_delivery)
    status['cold_join_fix'] = delivery
    status['open_findings'][0].update(
        code_fix_applied=True,
        runtime_verified=False,
        status=delivery['status'],
        next_scope='User cold-start late-join and appearance-switch visual check; prior screenshots are not post-fix evidence.',
        implementation='ColdJoinFix20261103/README.md',
    )
(OUT / 'review-status.json').write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')
print('Audit complete; 3 gameplay fixes, 1 open visual finding; final remote 15/15, both exits 0.')
