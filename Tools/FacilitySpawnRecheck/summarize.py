import json
import sys
from collections import Counter
from pathlib import Path
path=Path(sys.argv[1]) if len(sys.argv)>1 else Path('SourceAssets/FacilitySpawnRecheck20261018/recheck.json')
if not path.exists():
    print('report not available');raise SystemExit(0)
d=json.loads(path.read_bytes())
expected={
 'FacilityReceptionHall':(16,19),'FacilityTransit':(17,20),
 'MedicalDoctorOffice':(14,17),'AbandonedIsolationWard':(17,20),'AbandonedAnatomyTheatre':(15,18),
 'FreightTransfer_WarehouseLink':(6,8),'AbandonedCargoWarehouse':(9,11),'AbandonedTransitStation':(9,9),
 'ShoredBreach':(6,8),'AbandonedIncineratorHall':(12,14),'AbandonedFlueGasStation':(3,3),
 'EcoNursery':(6,8),'EcoHydroponics':(10,12),'EcoBiosphere':(3,3),
 'SwitchgearGallery':(6,8),'GeneratorHall':(10,12),'AccumulatorControl':(3,3),
 'StaffDormitory':(6,8),'StaffChangingShowers':(14,16),'StaffRecreation':(9,11),'BossPumpHall':(1,1)}
print('assembly',d.get('assembly_ready'),'complete',d.get('complete'),'error',d.get('error'))
print('navigation',d.get('navigation_data'))
seen=[]
for r in d.get('rooms',[]):
    seen.append(r['module']);low,high=expected.get(r['module'],(-1,-1))
    bad=[(s['slot'],s['class'].split('.')[-1],s['rejections']) for s in r['isolated_slots'] if not s['successful_calls']]
    doors=[(x['door'],x['member']) for x in r['open_service_door_spawns'] if not x['valid']]
    controls=[s['slot'] for s in r['isolated_slots'] if s.get('penetrating_floor_control_blocked') is False]
    construction=[(s['slot'],s['class']) for s in r['isolated_slots'] if s.get('construction_survived') is False or s.get('constructed_actor_clear') is False or s.get('construction_called_begin_play') is True]
    print(r['module'],'slots',r['initial_slots'],'count_ok',low<=r['initial_slots']<=high,'isolated_fail',bad,'packed',[x['admitted'] for x in r['stationary_first_wave']],'door_fail',doors,'control_fail',controls,'death',r.get('death_observer_and_objective'))
    print(' composition',dict(Counter(s['class'].split('.')[-1] for s in r['isolated_slots'])))
    if construction:print(' construction_fail',construction)
    if any(x['missing_slots'] for x in r['stationary_first_wave']):print(' capacity_details',r['stationary_first_wave'])
    if r.get('objective_variants'):print(' objective_variants',r['objective_variants'])
print('missing_rooms',sorted(set(expected)-set(seen)),'duplicate_rooms',len(seen)-len(set(seen)))
