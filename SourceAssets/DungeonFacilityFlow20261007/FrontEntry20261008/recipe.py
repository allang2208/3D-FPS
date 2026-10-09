"""Reception front closure, corrected signage and clear entrance approach."""
from pathlib import Path
import copy,json
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/FacilityFlow20261007/FrontEntry20261008'
REVISION='reception_front_grille_clearance_20261008'
GRILLE='/Game/Dungeons/AtmosphereV2/GateWater/Meshes/SM_DungeonRefinedGrille'
REPLACEMENTS={
    '/Game/Dungeons/ReceptionHall20261006/Meshes/SM_Reception_PortalFrames':'PortalFrames',
    '/Game/Dungeons/FacilityFlow20261007/Meshes/SM_FacilityFlow_RelocatedSigns':'Signs',
    '/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/SM_RH2_Hardware':'Mounts',
    '/Game/Dungeons/ReceptionHall20261006/Refine20261007/Meshes/SM_RH2_LoungeDetails':'LoungeDetails',
}

def apply_module(module):
    man=json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']
    parts=[]
    for p in module['parts']:
        if p['mesh'] in REPLACEMENTS or p['mesh'].startswith(BASE+'/') or p.get('id')=='ReceptionClosedFrontGrille':continue
        p=copy.deepcopy(p)
        x,y,z=p['position'];name=p['mesh'].rsplit('/',1)[-1]
        if name in ('SM_RH2_Sofa','SM_Staff_CoffeeTable') and -2350<x<-2050 and z<100 and abs(p['yaw']+90)<.01:
            # Absolute targets make repeat imports stable. Identify both existing
            # west-wall groups, including the previously blocked central doorway.
            p['position'][1]=1050 if y>400 else -1050
        parts.append(p)
    for item in man:
        parts.append(dict(mesh=item['mesh'],position=[0,0,0],yaw=0,scale=[1,1,1],collision=item['collision'],cast_shadow=item['cast_shadow'],fluid=False,materials=[]))
    # Original grille uses a world-baked source pivot (10.5,3.91,0) metres.
    # Rotation -90 makes its existing front face look east into the hall.
    # Scale fits the accepted welded kit to the 4 m x 3.4 m closed front portal.
    parts.append(dict(id='ReceptionClosedFrontGrille',mesh=GRILLE,position=[-2057,934.5,0],yaw=-90,
        scale=[.89,1,1.12],collision=True,cast_shadow=True,fluid=False,materials=[]))
    module['parts']=parts
    module['runtime_assets']=sorted((set(module.get('runtime_assets',[]))-set(REPLACEMENTS))|{GRILLE}|{m['mesh'] for m in man}|{v for m in man for v in m['materials'].values()})
    module['front_entry_revision']=REVISION

def extend(catalog,contract_hash):
    old=contract_hash(catalog)
    if old!=catalog['facility_flow']['layout_bank']['contract_sha1']:raise RuntimeError('Preserve unrelated layout-bank changes')
    result=copy.deepcopy(catalog)
    module=next(m for m in result['modules'] if m['id']==result['facility_flow']['reception'])
    apply_module(module)
    bank=result['facility_flow']['layout_bank'];bank['contract_sha1']=contract_hash(result)
    bank['front_entry_update']=dict(revision=REVISION,source_contract_sha1=old,placement_data_changed=False,sockets_changed=False,regression_run=False)
    return result
