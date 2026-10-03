"""Apply accepted warehouse + indivisible thematic routes after all older extensions."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text('utf-8-sig'))
def normalize(m):
    for p in m['parts']:
        p.setdefault('materials',[]);p.setdefault('fluid',False);p.setdefault('position',[0,0,0]);p.setdefault('yaw',0);p.setdefault('scale',[1,1,1])
    return m

def restrict_freight_to_theme(catalog):
    """Retain authoring assets, but retire the ambiguous ordinary freight family."""
    result=copy.deepcopy(catalog)
    ordinary=set()
    for m in result['modules']:
        if m.get('family_id',m['id'])=='FreightTransfer':
            ordinary.add(m['id'])
            m.setdefault('selection',{})['chance_per_run']=0
        elif m['id']=='FreightTransfer_WarehouseLink':
            # ConfigureThemedRoutes releases this restriction only for a fixed core.
            m['selection']=dict(chance_per_run=1,max_per_run=1,route='FreightThemeOnly')
    result['room_ids']=[room for room in result['room_ids'] if room not in ordinary]
    rules=result['themed_routes']
    rules['transition_families']=[family for family in rules['transition_families'] if family!='FreightTransfer']
    return result

def extend(catalog):
    result=copy.deepcopy(catalog);modules={m['id']:m for m in result['modules']}
    cargo=normalize(read(ROOT/'Config/warehouse-module.json'))
    modules[cargo['id']]=cargo
    freight=copy.deepcopy(modules['FreightTransfer'])
    freight.update(id='FreightTransfer_WarehouseLink',family_id='FreightTransfer_WarehouseLink',role='room',
        revision='themed_freight_real_shutter_20261001',selection=dict(chance_per_run=1,max_per_run=1),
        ports=[copy.deepcopy(freight['ports'][0]),dict(id='warehouse',position=[900,-1980,0],normal=[0,-1,0],width=300,height=280)],
        port_pairs=[[0,1]],side_sockets=[],scene_recipes=[],
        walk_polyline=[[900,0,0],[900,-1050,0],[1400,-1320,0],[1400,-1500,60],[900,-1650,60],[900,-1800,60],[900,-1980,0]],
        walk_mask=[dict(min=[420,-1300,-10],max=[1380,-30,280]),dict(min=[60,-1770,50],max=[1740,-1430,350])])
    freight.pop('closed_port_parts',None)
    freight['anchors']=[a for a in freight['anchors'] if a['role']!='exit']
    freight['min'][1]=-1980;freight['max'][2]=692
    freight['cells'] += [dict(min=[648,-1980,-25],max=[1152,-1800,392]),dict(min=[644,-1822,365],max=[1156,-1716,692])]
    freight['parts']=[p for p in freight['parts'] if not any(t in p['mesh'] for t in ('_Shell','_Frames','_Lift','_Damage','_Tiles'))]
    meshes=read(ROOT/'Authored/manifest.json')['objects']
    for item in meshes:
        if item['kind']=='DoorLeaf':continue
        freight['parts'].append(dict(mesh=item['asset'],position=[0,0,0],yaw=0,scale=[1,1,1],collision=item['collision'],materials=[],fluid=False))
    leaf=next(m['asset'] for m in meshes if m['kind']=='DoorLeaf')
    freight['progression_gate']=dict(mesh=leaf,position=[900,-1772,60],yaw=0,scale=[1,1,1],
        clear_size=[465,22,314],travel=[0,0,330],any_route=False)
    freight['spawn']['sealed_encounter']=False
    modules[freight['id']]=normalize(freight)
    archive=modules['AbandonedDataArchive'];archive['selection']=dict(chance_per_run=1,max_per_run=1,route='Archive')
    archive['spawn']['sealed_encounter']=False
    archive['progression_gate']=dict(mesh=leaf,position=[1400,0,0],yaw=-90,scale=[300/465,1,280/314],
        clear_size=[465,22,314],travel=[0,0,330],any_route=True)
    normalize(modules['AbandonedFlueGasStation'])
    for m in (cargo,modules['AbandonedFlueGasStation']):
        for l in m['lights']:
            l.setdefault('type','point');l['optimized_radius_cm']=l['radius']
            l.setdefault('max_draw_distance_cm',3400);l.setdefault('fade_range_cm',500)
    result['modules']=list(modules.values())
    result['room_ids']=list(dict.fromkeys(result['room_ids']+['AbandonedCargoWarehouse','AbandonedFlueGasStation',freight['id']]))
    result['themed_routes']=dict(version=1,shared_archive='AbandonedDataArchive',
        transition_families=['Distribution','Drainage','ShoredBreach','VentilationLoop'],
        forward_only=[freight['id'],'AbandonedCargoWarehouse'],
        routes=[dict(id='freight',sequence=[freight['id'],'AbandonedCargoWarehouse','AbandonedTransitStation']),
                dict(id='medical',sequence=['Drainage','AbandonedIsolationWard','AbandonedAnatomyTheatre']),
                dict(id='treatment',sequence=['ShoredBreach','AbandonedIncineratorHall','AbandonedFlueGasStation'])],
        approach_transition_count=[1,2],before_after_transition_count=[1,2],boss_access='any_complete_route_then_archive',
        optional_cross_route_loops=False)
    result['mission_rules'].update(grammars=['parallel_three_way'],optional_loop_goal=[0,0],route_estimate_max_cm=42000)
    result['generator_version']=8
    split=ROOT.parent/'DungeonSplitLevels20261001'
    if (split/'Receipts/install.json').exists() and read(split/'Receipts/install.json').get('stage')=='map_saved':
        import runpy
        result=runpy.run_path(str(split/'Scripts/extend_catalog.py'))['extend'](result)
    result=restrict_freight_to_theme(result)
    treatment=ROOT.parent/'DungeonTreatmentTheme20261003'
    if (treatment/'Receipts/install.json').exists() and read(treatment/'Receipts/install.json').get('stage')=='map_saved':
        import runpy
        result=runpy.run_path(str(treatment/'Scripts/extend_catalog.py'))['extend'](result)
    return result

def asset_paths(v):
    if isinstance(v,str) and v.startswith(('/Game/','/Script/')):yield v
    elif isinstance(v,dict):
        for x in v.values():yield from asset_paths(x)
    elif isinstance(v,list):
        for x in v:yield from asset_paths(x)
