import difflib
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/FacilitySpawnRecheck20261018'
read = lambda p: json.loads(p.read_bytes())
common = {'BP_FacelessReceptionist_C', 'BP_FacelessResearcher_C', 'BP_FacelessSecurity_C'}
cargo = {'BP_CargoPorter_C', 'BP_CargoTechnician_C'}
power = {'BP_FacelessResearcher_C', 'BP_CargoTechnician_C'}
living = {'BP_LivingStaffMale_C', 'BP_LivingStaffFemaleA_C', 'BP_LivingStaffFemaleB_C'}
elites = {'BP_MantisM27_C', 'BP_SpiralPillarM14_C', 'BP_LurkerM08_C'}
# Independently recorded room contracts; each row partitions all allowed species.
rules = {
 'FacilityReceptionHall': [(common,12,15),({'BP_BellowSacLobber_C'},4,4)],
 'FacilityTransit': [(common,12,15),({'BP_BellowSacLobber_C'},4,4),(elites,1,1)],
 'MedicalDoctorOffice': [(common,12,15),({'BP_MantisM27_C'},2,2)],
 'AbandonedIsolationWard': [(common,12,15),({'BP_MantisM27_C'},5,5)],
 'AbandonedAnatomyTheatre': [(common,12,15),({'HangingBellM09'},2,2),({'BP_BoundCongregate_C'},1,1)],
 'FreightTransfer_WarehouseLink': [(cargo,6,8)],
 'AbandonedCargoWarehouse': [(cargo,6,8),({'BP_LurkerM08_C'},3,3)],
 'AbandonedTransitStation': [({'BP_BellowSacLobber_C'},4,4),({'BP_LurkerM08_C'},4,4),({'BP_M10Mawcrawler_C'},1,1)],
 'ShoredBreach': [(cargo,6,8)],
 'AbandonedIncineratorHall': [(cargo,6,8),({'HundredEyedSlagMonster'},4,4),({'BP_MantisM27_C'},2,2)],
 'AbandonedFlueGasStation': [({'HundredEyedSlagMonster'},2,2),({'BP_M66RigPreview_C'},1,1)],
 'EcoNursery': [({'BP_EcologyGardener_C'},6,8)],
 'EcoHydroponics': [({'BP_EcologyGardener_C'},6,8),({'BP_SpiralPillarM14_C'},4,4)],
 'EcoBiosphere': [({'BP_SpiralPillarM14_C'},2,2),({'BP_RootCrownRigPreview_C'},1,1)],
 'SwitchgearGallery': [(power,6,8)],
 'GeneratorHall': [(power,6,8),({'HangingBellM09'},4,4)],
 'AccumulatorControl': [({'HangingBellM09'},2,2),({'BP_VortexCofferM25_C'},1,1)],
 'StaffDormitory': [(living,6,8)],
 'StaffChangingShowers': [(living,10,12),({'BP_MantisM27_C'},2,2),({'BP_LurkerM08_C'},2,2)],
 'StaffRecreation': [(living,6,8),({'BP_MantisM27_C'},2,2),({'BP_BlindSupplicantM07_C'},1,1)],
 'BossPumpHall': [({'BP_HeQue_C'},1,1)],
}
result = {'scope':'offline production assembly, placement, construction collision and death/gate logic',
          'gameplay_tested':False,'multiplayer_tested':False,'asset_packages_saved':False,'runs':[]}
for label in ('sealed-primary','sealed-secondary'):
    d=read(OUT/f'{label}.json'); slots=[s for r in d['rooms'] for s in r['isolated_slots']]
    failures=[]; capacity=[]; objectives=[]; table=[]
    modules=[r['module'] for r in d['rooms']]
    if len(modules)!=21 or set(modules)!=set(rules):failures.append('room coverage')
    for r in d['rooms']:
        counts=Counter(s['class'].split('.')[-1] for s in r['isolated_slots'])
        contract=rules[r['module']];allowed=set().union(*(k for k,_,_ in contract))
        if set(counts)-allowed or any(not lo<=sum(counts[k] for k in keys)<=hi for keys,lo,hi in contract):
            failures.append(f"composition:{r['module']}")
        if not r.get('boundaries_closed_during_placement'):failures.append(f"unsealed:{r['module']}")
        for s in r['isolated_slots']:
            if s['successful_calls']!=s['calls']:failures.append(f"placement:{r['module']}:{s['slot']}")
            if not s.get('construction_survived') or not s.get('constructed_actor_clear') or s.get('construction_called_begin_play') is not False:
                failures.append(f"construction:{r['module']}:{s['slot']}")
            if s.get('penetrating_floor_control_blocked') is False:failures.append(f"control:{r['module']}:{s['slot']}")
        if any(not x['valid'] for x in r['open_service_door_spawns']):failures.append(f"service door:{r['module']}")
        if any(x['successful_calls']!=32 for x in r['objective_variants']):failures.append(f"elite variants:{r['module']}")
        death=r['death_observer_and_objective']
        if death.get('error') or any(v is False for v in death.values()):failures.append(f"death/gates:{r['module']}")
        if 'boundaries' in death:objectives.append({'module':r['module'],'boundaries':death['boundaries']})
        for trial in r['stationary_first_wave']:
            if trial['missing_slots']:
                capacity.append({'module':r['module'],'configured':r['initial_slots'],**trial,
                    'pending_classes':[r['isolated_slots'][i]['class'].split('.')[-1] for i in trial['missing_slots']]})
                if trial['pending_recovered_after_space_release']!=len(trial['missing_slots']):failures.append(f"recovery:{r['module']}")
        table.append({'module':r['module'],'yaw':r['yaw'],'configured':r['initial_slots'],
                      'composition':dict(counts),'packed':[x['admitted'] for x in r['stationary_first_wave']]})
    if d['begin_play_called'] or d['actors_with_begin_play']:failures.append('gameplay unexpectedly initialized')
    receipt=read(OUT/f'{label}_exit.json')
    if not d['complete'] or not d['assembly_ready'] or receipt['exit_code']!=0:failures.append('incomplete commandlet')
    if len(objectives)!=8 or sum(x['boundaries'] for x in objectives)!=16:failures.append('objective/boundary coverage')
    result['runs'].append({'label':label,'seed':d['seed'],'slots':len(slots),'placement_calls':sum(x['calls'] for x in slots),
        'construction_checks':sum(x.get('construction_survived') is True for x in slots),
        'floor_controls':sum('penetrating_floor_control_blocked' in x for x in slots),
        'service_door_checks':sum(len(r['open_service_door_spawns']) for r in d['rooms']),
        'objective_variants':sum(len(r['objective_variants']) for r in d['rooms']),
        'objectives':objectives,'failures':failures,'capacity_observations':capacity,'rooms':table,
        'assembly_metrics':json.loads(d['assembly_metrics'])})
sources=[ROOT/'Source/FPSGAME/Dungeons'/p.name for p in (OUT/'Before').glob('*')]
sources+=list((ROOT/'Source/FPSGAME/Development').glob('FacilitySpawnRecheckCommandlet.*'))
sources+=list((ROOT/'Tools/FacilitySpawnRecheck').glob('*.py'))+list((ROOT/'Tools/FacilitySpawnRecheck').glob('*.ps1'))
sources+=[ROOT/'Binaries/Win64/UnrealEditor-FPSGAME.dll',ROOT/'Docs/Dungeons/facility-spawn-recheck-20261018.md']
result['files']=[{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources if p.exists()]
diff=[]
for name in ('AuthoredDungeonGenerator.h','DungeonThemeEncounter.h','FacilityHallEncounter.h','FacilityHallEncounter.cpp'):
    before=OUT/'Before'/name;after=ROOT/'Source/FPSGAME/Dungeons'/name
    diff.extend(difflib.unified_diff(before.read_text(encoding='utf-8-sig').splitlines(True),
        after.read_text(encoding='utf-8-sig').splitlines(True),fromfile='Before/'+name,tofile='Source/FPSGAME/Dungeons/'+name))
(OUT/'audit-instrumentation.diff').write_text(''.join(diff),encoding='utf-8')
(OUT/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for r in result['runs']:
    print(r['label'],r['seed'],'slots',r['slots'],'calls',r['placement_calls'],'constructed',r['construction_checks'],
          'failures',r['failures'],'capacity',r['capacity_observations'])
