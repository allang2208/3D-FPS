"""Retain the saved elevated control-room revision in subject/draft rebuilds."""
import importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'UpperControlRoom20261005'

def manifest():
    if not (ROOT/'manifest.json').exists():return None
    receipt=ROOT/'Receipts/install.json'
    state=json.loads(receipt.read_text('utf8')) if receipt.exists() else {}
    if state.get('stage') not in ('assets_saved','map_saved'):
        raise RuntimeError('Complete UpperControlRoom20261005/install.py before rebuilding the upper control room')
    return json.loads((ROOT/'manifest.json').read_text('utf8'))

def patch_world():
    if not manifest():return {}
    spec=importlib.util.spec_from_file_location('power_upper_control_install',ROOT/'install.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.patch_loaded_map()

def remap_draft(draft):
    data=manifest()
    if not data:return draft
    sys.path.insert(0,str(ROOT))
    from layout import interaction_specs,BASE
    scene=json.loads((ROOT.parent/'Config/scene.json').read_text('utf8'))
    module=next(m for m in draft['modules'] if m['id']=='AccumulatorControl')
    by_name={i['name']:i for i in data['meshes'] if i['previous_mesh']}
    for part in module['parts']:
        name=part['mesh'].split('/')[-1].split('.')[0]
        if name in by_name:
            item=by_name[name];part['mesh']=item['mesh'];part['collision']=item['collision'];part['cast_shadow']=item['cast_shadow']
            part.pop('materials',None)
    runtime=[s for s in module['runtime_actors'] if not s.get('id','').startswith('UpperControl')]
    dependencies=set(module.get('runtime_assets',[]))
    def position(p):return [p[0]*100,-p[1]*100,p[2]*100]
    specs=interaction_specs(scene)
    for s in specs['glass']:
        prefix=BASE+'/Meshes/SM_Power_UpperControl'+s['kind']
        paths=dict(pane=prefix+'PaneV5',fracture=prefix+'FractureV5',
            fracture_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassFragmentsV5',
            impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',
            sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0')
        runtime.append(dict(id=s['id'],type='glass_window',position=position(s['position_m']),yaw=-s['yaw_deg'],
            dimensions_cm=[s['width_m']*100,s['height_m']*100,.8],**paths))
        dependencies.update(paths.values())
    for s in specs['doors']:
        runtime.append(dict(id=s['id'],type='solid_door',position=position(s['position_m']),yaw=-s['yaw_deg'],
            leaf=s['leaf_mesh'],positive_hinge=s['positive_hinge'],open_seconds=.55,auto_close_seconds=0))
        dependencies.add(s['leaf_mesh'])
    module['runtime_actors']=runtime;module['runtime_assets']=sorted(dependencies)
    module['upper_control_revision']='20261005'
    module['route_intent']['upper_control_room']=dict(floor_cm=384,stairs_width_cm=240,
        front_balcony_clear_width_cm=204,side_door_clear_width_cm=230,
        design='Two side entrances, front observation balcony, rear cross-aisle and ground-level through route')
    draft['module_asset_paths']=sorted(set(draft['module_asset_paths'])|dependencies|{i['mesh'] for i in data['meshes']}|
        {p for i in data['meshes'] for p in i['materials'].values()})
    draft['upper_control_revision']='UpperControlRoom20261005'
    return draft
