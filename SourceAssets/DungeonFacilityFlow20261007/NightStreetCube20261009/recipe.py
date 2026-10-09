"""Replace the finite street photograph with a complete, locally owned cube."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/FacilityFlow20261007/NightStreetCube20261009'
REVISION='reception_continuous_street_cube_20261009'
MATERIAL=BASE+'/Materials/M_Reception_IndustrialNightCube'
OLD_BACKGROUND='/Game/Dungeons/FacilityFlow20261007/NightStreet20261009/Meshes/SM_ReceptionNight_Background'
BACKGROUND=BASE+'/Meshes/SM_ReceptionCube_Background'
OLD_MATERIALS={
 '/Game/Dungeons/FacilityFlow20261007/NightStreet20261009/Materials/M_NightStreet_Background',
 '/Game/Dungeons/FacilityFlow20261007/NightStreetEdgeFix20261009/Materials/M_NightStreet_BackgroundV2'}

def apply_module(module):
    meshes=json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']
    module['parts']=[p for p in module['parts'] if p['mesh']!=OLD_BACKGROUND and not p['mesh'].startswith(BASE+'/Meshes/')]
    for item in meshes:
        module['parts'].append(dict(mesh=item['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],collision=False,cast_shadow=item['cast_shadow'],fluid=False,materials=[]))
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-OLD_MATERIALS-{OLD_BACKGROUND})|{MATERIAL}|{m['mesh'] for m in meshes}|{p for m in meshes for p in m['materials'].values()})
    module['night_street_cube_revision']=REVISION

def extend(catalog,contract_hash):
    old=contract_hash(catalog)
    if old!=catalog['facility_flow']['layout_bank']['contract_sha1']:raise RuntimeError('Preserve unrelated layout-bank changes')
    result=copy.deepcopy(catalog)
    module=next(m for m in result['modules'] if m['id']==result['facility_flow']['reception'])
    if not any(p['mesh'] in (OLD_BACKGROUND,BACKGROUND) for p in module['parts']):raise RuntimeError('Expected installed reception background mesh')
    apply_module(module)
    bank=result['facility_flow']['layout_bank'];bank['contract_sha1']=contract_hash(result)
    bank['night_street_cube_update']=dict(revision=REVISION,source_contract_sha1=old,placement_data_changed=False,sockets_changed=False,bounds_changed=False,regression_run=False)
    return result
