"""Scoped visual overlay; leaves route sockets, bounds and bank placements intact."""
from pathlib import Path
import copy,json,runpy
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/FacilityFlow20261007/NightStreet20261009'
REVISION='reception_night_street_and_printed_faces_20261009'
OLD_SIGNS='/Game/Dungeons/FacilityFlow20261007/FrontEntry20261008/Meshes/SM_FrontEntry_Signs'

def apply_module(module):
    meshes=json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']
    module['parts']=[p for p in module['parts'] if p['mesh']!=OLD_SIGNS and not p['mesh'].startswith(BASE+'/')]
    for item in meshes:
        module['parts'].append(dict(mesh=item['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],collision=item['collision'],cast_shadow=item['cast_shadow'],fluid=False,materials=[]))
    # The old 700 lm enclosed-vestibule light becomes a subdued canopy source.
    for light in module['lights']:
        x,y,z=light['position']
        if abs(x+2550)<1 and abs(y)<1 and abs(z-255)<1:
            light.update(intensity=100.,radius=230.,optimized_radius_cm=230.,color=[.68,.77,.92],indirect_lighting_intensity=.12,volumetric_scattering_intensity=0.)
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-{OLD_SIGNS})|{m['mesh'] for m in meshes}|{v for m in meshes for v in m['materials'].values()})
    module['night_street_revision']=REVISION
    # Reapplying the original scenery must retain its subsequently published
    # material-only boundary repair, including regular full-catalog rebuilds.
    edge=ROOT.parent/'NightStreetEdgeFix20261009/install-receipt.json'
    if edge.exists() and json.loads(edge.read_text('utf8')).get('stage')=='map_saved':
        runpy.run_path(str(edge.parent/'recipe.py'))['apply_module'](module)

def extend(catalog,contract_hash):
    old=contract_hash(catalog)
    if old!=catalog['facility_flow']['layout_bank']['contract_sha1']:raise RuntimeError('Preserve unrelated layout-bank changes')
    result=copy.deepcopy(catalog)
    apply_module(next(m for m in result['modules'] if m['id']==result['facility_flow']['reception']))
    bank=result['facility_flow']['layout_bank'];bank['contract_sha1']=contract_hash(result)
    bank['night_street_update']=dict(revision=REVISION,source_contract_sha1=old,placement_data_changed=False,sockets_changed=False,bounds_changed=False,regression_run=False)
    return result
