"""Replace the original frame as one assembly; no overlapping cover plates."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/FacilityFlow20261007/EntryFrameFit20261009'
REVISION='entry_frame_depth_fit_20261009'
OLD='/Game/Dungeons/FacilityFlow20261007/FrontEntry20261008/Meshes/SM_FrontEntry_PortalFrames'
NEW=BASE+'/Meshes/SM_EntryFrameFit_PortalFrames'
def apply_module(module):
    for p in module['parts']:
        if p['mesh'] in (OLD,NEW):p['mesh']=NEW
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-{OLD})|{NEW})
    module['front_frame_fit_revision']=REVISION
def extend(catalog,contract_hash):
    out=copy.deepcopy(catalog)
    m=next(m for m in out['modules'] if m['id']==out['facility_flow']['reception'])
    apply_module(m);out['facility_flow']['layout_bank']['contract_sha1']=contract_hash(out)
    return out
