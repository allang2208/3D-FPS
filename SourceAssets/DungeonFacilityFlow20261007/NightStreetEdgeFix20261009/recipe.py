"""Replace only the night-background material; geometry and layout are retained."""
from pathlib import Path
import copy,json,runpy
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/FacilityFlow20261007/NightStreetEdgeFix20261009'
REVISION='reception_night_inside_edge_feather_20261009'
MATERIAL=BASE+'/Materials/M_NightStreet_BackgroundV2'
BACKGROUND='/Game/Dungeons/FacilityFlow20261007/NightStreet20261009/Meshes/SM_ReceptionNight_Background'
OLD_MATERIAL='/Game/Dungeons/FacilityFlow20261007/NightStreet20261009/Materials/M_NightStreet_Background'

def apply_module(module):
    for part in module['parts']:
        if part['mesh']==BACKGROUND:part['materials']=[MATERIAL]
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-{OLD_MATERIAL})|{MATERIAL})
    module['night_street_edge_revision']=REVISION
    cube=ROOT.parent/'NightStreetCube20261009/install-receipt.json'
    if cube.exists() and json.loads(cube.read_text('utf8')).get('stage')=='map_saved':
        runpy.run_path(str(cube.parent/'recipe.py'))['apply_module'](module)

def extend(catalog,contract_hash):
    old=contract_hash(catalog)
    if old!=catalog['facility_flow']['layout_bank']['contract_sha1']:raise RuntimeError('Preserve unrelated layout-bank changes')
    result=copy.deepcopy(catalog)
    module=next(m for m in result['modules'] if m['id']==result['facility_flow']['reception'])
    if not any(p['mesh']==BACKGROUND or p['mesh'].endswith('/SM_ReceptionCube_Background') for p in module['parts']):raise RuntimeError('Expected installed reception night background')
    apply_module(module)
    bank=result['facility_flow']['layout_bank'];bank['contract_sha1']=contract_hash(result)
    bank['night_street_edge_update']=dict(revision=REVISION,source_contract_sha1=old,placement_data_changed=False,sockets_changed=False,bounds_changed=False,regression_run=False)
    return result
