"""Compare saved catalog/blueprints with authored spawn regions. No game simulation."""
import collections
import itertools
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/FacilitySpawnAudit20261017'
catalog = json.loads((OUT / 'saved_catalog.json').read_text(encoding='utf-8'))
inputs = json.loads((OUT / 'saved_inputs.json').read_text(encoding='utf-8'))
modules = {m['id']: m for m in catalog['modules']}
sources = ROOT / 'Source/FPSGAME/Dungeons'

def source_array(file, name, kind='box'):
    text = (sources / file).read_text(encoding='utf-8-sig')
    body = re.search(r'\b' + name + r'\[\]\s*=\s*\{(.*?)\};', text, re.S)[1]
    points = [tuple(float(v.strip()) for v in a.split(',')) for a in re.findall(r'FVector\(([^()]*)\)', body)]
    return list(zip(points[::2], points[1::2])) if kind == 'box' else points

def distance2(point, box):
    lo, hi = box
    return sum(max(lo[i]-point[i], 0, point[i]-hi[i])**2 for i in range(3))

def boxes(module, key):
    return [(b['min'], b['max']) for b in module.get(key, [])]

def region(module, name, box, margin=0, explicit=False):
    lo, hi = box
    # Interior points at the same height, with the species' authored edge margin.
    low = [lo[0]+margin, lo[1]+margin, lo[2]]
    high = [hi[0]-margin, hi[1]-margin, hi[2]]
    if high[0] < low[0] or high[1] < low[1]:
        return dict(module=module, region=name, error='insufficient authored width')
    points = [(low[0]+(high[0]-low[0])*x/10, low[1]+(high[1]-low[1])*y/10, lo[2])
              for x, y in itertools.product(range(11), repeat=2)]
    m = modules[module]
    cells = boxes(m, 'cells') or [(m['min'], m['max'])]
    masks = boxes(m, 'walk_mask')
    in_room = [p for p in points if min(distance2(p, b) for b in cells) <= 400.0001]
    old = sum(not masks or min(distance2(p, b) for b in masks) <= 400.0001 for p in in_room)
    return dict(module=module, region=name, local_min=lo, local_max=hi, margin_cm=margin,
                samples=len(points), room_pass=len(in_room), catalog_walk_pass=old,
                current_scope='explicit authored floor' if explicit else 'catalog walk mask',
                current_pass=len(in_room) if explicit else old)

regions = []
def add_array(module, file, name, margin, explicit=False):
    for i, b in enumerate(source_array(file, name)):
        regions.append(region(module, name+'.'+str(i), b, margin, explicit))

def add_points(module, file, name, jitter, explicit=False):
    for i, p in enumerate(source_array(file, name, 'point')):
        regions.append(region(module, name+'.'+str(i),
            (tuple(p[k]-jitter[k] for k in range(3)), tuple(p[k]+jitter[k] for k in range(3))), explicit=explicit))

for module, margin in [('FacilityReceptionHall',205),('FacilityTransit',205),
                       ('MedicalDoctorOffice',74),('AbandonedIsolationWard',74),
                       ('AbandonedAnatomyTheatre',265),('ShoredBreach',79)]:
    m=modules[module]
    floors=boxes(m,'walk_mask') or boxes(m,'cells') or [(m['min'],m['max'])]
    if module.startswith('Facility'):
        floors=[max(floors,key=lambda b:(b[1][0]-b[0][0])*(b[1][1]-b[0][1]))]
    for i,(lo,hi) in enumerate(floors):
        # The C++ random-floor branch skips narrow cells before choosing a point.
        if hi[0]-lo[0]<=2*margin or hi[1]-lo[1]<=2*margin:continue
        regions.append(region(module,'generic_floor.'+str(i),((lo[0],lo[1],0),(hi[0],hi[1],0)),margin))

add_array('MedicalDoctorOffice', 'FacilityMedicalEncounter.cpp', 'MedicalOfficeRooms', 105, True)
add_array('AbandonedIsolationWard', 'FacilityMedicalEncounter.cpp', 'Bays', 105, True)
for module, name, margin in [('FreightTransfer_WarehouseLink','TransferFloors',69),
                             ('AbandonedCargoWarehouse','WarehouseAisles',160),
                             ('AbandonedTransitStation','StationGround',160)]:
    add_array(module,'FacilityFreightEncounter.cpp',name,margin)
regions.append(region('AbandonedTransitStation','StationBoss',((300,-1100,0),(1220,-550,0)),250))
for i in range(4):
    regions.append(region('AbandonedTransitStation','Bellow.upper.'+str(i),((2225,-1600+i*800,480),(2765,-800+i*800,480)),160))
add_array('EcoNursery','FacilityEcologyEncounter.cpp','NurseryFloors',69,True)
add_array('EcoHydroponics','FacilityEcologyEncounter.cpp','HydroFloors',69,True)
add_points('EcoHydroponics','FacilityEcologyEncounter.cpp','HydroSpirals',(85,65,0),True)
add_points('EcoBiosphere','FacilityEcologyEncounter.cpp','BiosphereSpirals',(85,65,0),True)
regions.append(region('EcoBiosphere','Crown',((-1900,-450,0),(-1550,-80,0)),explicit=True))
add_array('SwitchgearGallery','FacilityPowerEncounter.cpp','PowerSwitchgearFloors',69)
add_array('GeneratorHall','FacilityPowerEncounter.cpp','PowerGeneratorFloors',69)
regions.append(region('AccumulatorControl','Coffer',((-850,700,0),(850,900,0))))
for name in ['HallSlags','BasementSpawns']:
    add_points('AbandonedIncineratorHall','FacilityIncinerationEncounter.cpp',name,(100,70,0))
add_points('AbandonedFlueGasStation','FacilityIncinerationEncounter.cpp','FlueSpawns',(100,70,0))
for module,name in [('StaffDormitory','LivingDormitoryFloors'),('StaffChangingShowers','LivingChangingFloors'),('StaffRecreation','LivingRecreationFloors')]:
    add_array(module,'FacilityStaffLivingEncounter.cpp',name,90)
regions.append(region('StaffChangingShowers','Lurker.left',((-870,-15,0),(-430,15,0))))
regions.append(region('StaffChangingShowers','Lurker.right',((430,-15,0),(870,15,0))))
regions.append(region('StaffRecreation','BlindSupplicant',((-1200,555,0),(1200,645,0))))
regions.append(region('BossPumpHall','HeQue',((-180,-2150,0),(180,-1600,0))))
for module in ['FacilityReceptionHall','FacilityTransit']:
    for i in [0,1]:
        box = (((-1600,1050 if i else -1650,450),(1400,1650 if i else -1050,450))
               if module=='FacilityReceptionHall' else
               ((-2400,1050 if i else -1800,420),(-1600,1800 if i else -1050,420)))
        regions.append(region(module,'Bellow.upper.'+str(i),box,142))

doors=[]
for module in ['FacilityReceptionHall','FacilityTransit','AbandonedTransitStation']:
    groups=collections.defaultdict(list)
    for part in modules[module]['parts']:
        if part.get('fixture_id') and part.get('mesh','').split('/')[-1] in ['SM_Entry_DoorLeaf','SM_Entry_DoorLeafRight']:
            groups[part['fixture_id']].append(part)
    for key, parts in groups.items():
        if len(parts)!=2:
            doors.append(dict(module=module,id=key,leaf_count=len(parts)));continue
        left=next(p for p in parts if p['mesh'].endswith('/SM_Entry_DoorLeaf'))
        center=[sum(p['position'][i] for p in parts)/2 for i in range(3)]
        angle=math.radians(left.get('yaw',0));pos=(center[0]-65*math.cos(angle),center[1]-65*math.sin(angle),center[2])
        row=region(module,key,(pos,pos));doors.append(row)

themes={r['id']:r['sequence'] for r in catalog['themed_routes']['routes']}
layout_rows=[]
for key,entry in catalog['facility_flow']['layout_bank']['entries'].items():
    errors=[];counts=collections.Counter(p['module'] for p in entry['pieces'])
    for sequence in themes.values():
        for module in sequence:
            if counts[module]!=1: errors.append(module+': count='+str(counts[module]))
    for module in ['FacilityReceptionHall','FacilityTransit','BossPumpHall']:
        if counts[module]!=1:errors.append(module+': count='+str(counts[module]))
    if any(abs(p['yaw']/90-round(p['yaw']/90))>1e-5 for p in entry['pieces'] if p['module'] in set(sum(themes.values(),[]))):
        errors.append('non-cardinal combat-room yaw')
    for route,pair in entry['route_pairs'].items():
        members=[p['module'] for p in entry['pieces'] if p['route']==route and p['module'] in set(sum(themes.values(),[]))]
        # Piece array order is construction order: the layout builder can work
        # backward from the merge. It is not a traversal sequence.
        if collections.Counter(members)!=collections.Counter(themes[pair[0]]+themes[pair[1]]):
            errors.append(route+': incomplete or incorrect theme membership')
    layout_rows.append(dict(key=key,errors=errors))

nav_rows=[]
for cls in inputs['classes']:
    if not cls['loaded']:
        nav_rows.append(dict(path=cls['path'],error='class missing'));continue
    radius=cls['capsule_radius'];height=cls['capsule_half_height']*2
    if not cls['update_nav_from_collision']:
        radius=max(radius,cls['agent']['agent_radius']);height=max(height,cls['agent']['agent_height'])
    bypass=('LurkerM08' in cls['path'] or 'HangingBellM09' in cls['path'])
    profiles=[n['name'] for n in inputs['navigation'] if n['agent_radius']>=radius and n['agent_height']>=height]
    nav_rows.append(dict(path=cls['path'],required_radius=radius,required_height=height,
                         physical_surface_or_ceiling=bypass,dimension_compatible_profiles=profiles))

result=dict(scope='Saved-data/static audit, no collision queries, generated nav projection or gameplay test',
            modules=len(modules),supported_combat_rooms=21,classes=len(inputs['classes']),regions=regions,service_doors=doors,
            baked_layouts=layout_rows,navigation=nav_rows,
            missing_encounters=['Distribution','Drainage','VentilationLoop','AbandonedDataArchive'],
            current_completely_rejected_regions=[r for r in regions+doors if r.get('current_pass',0)==0],
            layouts_with_errors=[r for r in layout_rows if r['errors']])
(OUT/'static_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:result[k] for k in ['modules','supported_combat_rooms','classes','current_completely_rejected_regions','layouts_with_errors']},ensure_ascii=False))
print('region_groups=%d service_doors=%d layout_entries=%d' % (len(regions),len(doors),len(layout_rows)))
