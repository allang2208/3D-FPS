"""Rebuild the two reception door veils from their actual body anchors."""
from pathlib import Path
import copy,json,math
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/ReceptionDoorVeil20261012'
REVISION='reception_black_spawn_recess_20261012'
MODULE='FacilityReceptionHall'

def apply_module(module):
    if module['id']!=MODULE:return []
    module['parts']=[p for p in module['parts'] if p.get('door_veil_revision')!=REVISION]
    bodies=[p for p in module['parts'] if p['mesh'].endswith('/SM_Entry_DoorBody') and p.get('fixture_id','').startswith(MODULE+'.service.')]
    if len(bodies)!=2:raise RuntimeError('Reception must retain its two actual service doors')
    removed_lights=[]
    for body in bodies:
        for suffix in ('BlackLiner','FogCurtain'):
            module['parts'].append(dict(id=body['fixture_id']+'.'+suffix,
                mesh=BASE+'/Meshes/SM_ReceptionDoor_'+suffix,position=body['position'].copy(),yaw=body['yaw'],scale=body['scale'].copy(),
                materials=[],collision=False,affects_navigation=False,cast_shadow=False,fluid=True,
                max_draw_distance_cm=2600 if suffix=='FogCurtain' else 0,
                parent_fixture_id=body['fixture_id'],door_veil_revision=REVISION))
        # Remove only lights actually authored INSIDE this doorway volume;
        # the gallery fixtures above the 3m doorway keep their existing layout.
        angle=math.radians(body['yaw']);c,s=math.cos(angle),math.sin(angle)
        for light in list(module['lights']):
            p=light['position'];dx,dy,dz=[p[i]-body['position'][i] for i in range(3)]
            lx,ly=dx*c+dy*s,-dx*s+dy*c
            if 0<=lx<=150 and abs(ly)<=110 and 0<=dz<=300:
                removed_lights.append(light.get('id',str(p)));module['lights'].remove(light)
    paths=[BASE+'/Meshes/SM_ReceptionDoor_'+s for s in ('BlackLiner','FogCurtain')]
    module['runtime_assets']=list(dict.fromkeys(module.get('runtime_assets',[])+paths))
    return removed_lights

def reapply_catalog(catalog,contract_hash):
    receipt=ROOT/'Receipts/install.json'
    if not receipt.exists() or json.loads(receipt.read_text('utf8')).get('stage')!='map_saved':return catalog
    out=copy.deepcopy(catalog)
    apply_module(next(m for m in out['modules'] if m['id']==MODULE))
    out['facility_flow']['layout_bank']['contract_sha1']=contract_hash(out)
    return out
