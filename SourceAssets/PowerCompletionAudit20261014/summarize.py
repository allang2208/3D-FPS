"""Consolidate the requested audit evidence without running additional tests."""
from pathlib import Path
from datetime import datetime, timezone
import json
import re

ROOT=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text('utf-8-sig'))
assets=read(ROOT/'assets.json')
data=read(ROOT/'data.json')
automation=read(ROOT/'Automation/index.json')
clock=read(ROOT/'ClockAutomation/index.json')
build=read(ROOT/'Receipts/build.json')
task_exit=read(ROOT/'task-contract-exit.json')
log=(ROOT/'task-contract.log').read_text('utf-8-sig',errors='replace')
matches=re.findall(r'\[TaskTrackingContract\] checks=(\d+) failures=(\d+)',log)
if not matches:raise RuntimeError('Missing task contract completion evidence')
checks,failures=map(int,matches[-1])
if (assets['failures'] or data['failures'] or automation['failed'] or automation['succeeded']!=2
    or clock['failed'] or clock['succeeded']!=1
    or task_exit['exit_code'] or failures or checks<34
    or not {'FPSGAMEEditor','FPSGAME'} <= {b['target'] for b in build['results'] if b['exit_code']==0}):
    raise RuntimeError('Audit incomplete or contains failed checks')
report=dict(
    status='requested_source_asset_and_contract_review_complete',
    completed_utc=datetime.now(timezone.utc).isoformat(),
    scope='Power area: three combat rooms, boss objective/gates, fourteen search containers, three new collectibles',
    confirmed_runtime_logic_defects=[dict(
        issue='Hanging bell client presentation accumulated local delta after OnRep_State and did not follow later authoritative clock/timestamp corrections',
        status='fixed',file='Source/FPSGAME/Monsters/HangingBellM09.cpp',
        fix='Remote Tick derives StateSeconds from replicated StateStartedAt and current GameState server time; authority timing remains unchanged')],
    closed_coverage_gaps=['Power boss shared-progress tests now cover independent regional completion, serialization, stale updates, late binding/join and new-run reset'],
    source_review=dict(
        room_rosters=['6-8 researchers/technicians','6-8 researchers/technicians plus 4 hanging bells','2 hanging bells plus 1 vortex coffer'],
        authority='Server owns encounter generation, damage/death, boss completion and regional gate state',
        containers='One-time server loot generation; run-scoped stable keys; revision-checked transfers; journal commits; shared open-state snapshot',
        inventory='Individual player profiles remain separate; only container contents are shared',
        monster_presentation='Researcher/technician, hanging bell and vortex coffer replication paths reviewed, including attack/death clocks'),
    evidence=dict(saved_map_assets=dict(checks=len(assets['checks']),failures=0),
        item_data_cook_and_icons=dict(checks=len(data['checks']),failures=0),
        scene_search=dict(succeeded=automation['succeeded'],failed=automation['failed'],
            tests=[t['fullTestPath'] for t in automation['tests']]),
        task_contract=dict(checks=checks,failures=failures),native_builds=build['results']),
    tests_run=True,player_save_slots_used=False,dual_client_gameplay_tested=False,
    remaining_live_coverage=['Host/client simultaneous pickup and UI refresh','Late join/reconnect during combat','Teammate admission and both gate openings in a live session','Delay/loss and packaged cross-machine play'])
report['evidence']['hanging_bell_clock']=dict(succeeded=clock['succeeded'],failed=clock['failed'],
    fixture='Real AHangingBellM09 Tick with simulated-proxy role and controlled GameState clock in a transient world; no network connection')
(ROOT/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('POWER_REVIEW_COMPLETE assets=%d data=%d automation=%d clock=%d task=%d failures=0'%(
    len(assets['checks']),len(data['checks']),automation['succeeded'],clock['succeeded'],checks))
