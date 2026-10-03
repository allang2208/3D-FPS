"""Preserve all room state; change only the office roof asset and two tool bays."""
import copy
ROOF='/Game/Dungeons/StationWorkshop20261003/RefineV4/Meshes/SM_SW_Roof_FittedV4'
ROOF_NAMES={'SM_SW_Roof','SM_SW_Roof_FittedV4'}
TOOL_POSITIONS={'FreightTransfer.Tools.West':[55,-1300,0],'FreightTransfer.Tools.East':[1745,-1030,0]}

def fitted(value):
    if isinstance(value,str) and value.startswith('/Game/') and value.split('.')[0].split('/')[-1] in ROOF_NAMES:return ROOF
    if isinstance(value,list):return [fitted(v) for v in value]
    if isinstance(value,dict):
        out={k:fitted(v) for k,v in value.items()}
        identity=out.get('container_id','')
        key=identity.removeprefix('StationLine.').removesuffix('.Drawer')
        if key in TOOL_POSITIONS:out['position']=copy.deepcopy(TOOL_POSITIONS[key])
        if out.get('id')=='StationWorkshop.MaintenanceCeiling':out['cast_shadows']=False
        return out
    return value

def apply(rules):
    out=fitted(rules);out.update(revision=4,ceiling_surface='Planar matte concrete slab, fitted to wall outer bounds; bottom 320 cm, top 336 cm')
    return out

def extend(catalog):
    out=fitted(catalog)
    for module in out['modules']:
        if module['id']=='AbandonedTransitStation' and 'station_workshop' in module:
            module['station_workshop']=apply(module['station_workshop'])
    out.update(station_workshop_revision=4,freight_tool_bay_revision=2)
    return out
