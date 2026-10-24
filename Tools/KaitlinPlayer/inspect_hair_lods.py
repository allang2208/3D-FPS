"""Read only: compare native and runtime long-hair geometry/LOD settings."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME'); W=P/'SourceAssets/KaitlinHairLOD20261024'; W.mkdir(exist_ok=True)
path='/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Grooms/Hair_L_Straight.Hair_L_Straight'
asset=u.load_asset(path)

def prop(obj,key):
    try:
        value=obj.get_editor_property(key)
        if hasattr(value,'get_path_name'): return value.get_path_name()
        if hasattr(value,'export_text'): return value.export_text()
        if isinstance(value,(str,bool,int,float)) or value is None: return value
        return [x.export_text() if hasattr(x,'export_text') else str(x) for x in value]
    except Exception as exc: return {'unavailable':str(exc)}

def component(obj):
    result={'path':obj.get_path_name(),'class':obj.get_class().get_name()}
    for key in ('use_cards','groom_groups_desc','binding_asset','physics_asset','simulation_settings','lod_bias','forced_lod'):
        result[key]=prop(obj,key)
    result['materials']=[obj.get_material(i).get_path_name() if obj.get_material(i) else None for i in range(obj.get_num_materials())]
    return result

report={'asset':path,'settings':{},'native':[],'instances':[],'lod_sync':[]}
for key in ('hair_groups_lod','hair_groups_rendering','hair_groups_physics','hair_groups_cards','hair_groups_meshes','hair_groups_info','enable_global_interpolation'):
    report['settings'][key]=prop(asset,key)
bp=u.load_asset('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/BP_Kaitlin.BP_Kaitlin')
sub=u.get_engine_subsystem(u.SubobjectDataSubsystem); lib=u.SubobjectDataBlueprintFunctionLibrary
for handle in sub.k2_gather_subobject_data_for_blueprint(bp):
    obj=lib.get_object_for_blueprint(lib.get_data(handle),bp)
    if isinstance(obj,u.GroomComponent) and obj.get_editor_property('groom_asset')==asset:
        report['native'].append(component(obj))
for obj in u.ObjectIterator(u.GroomComponent):
    if obj.get_editor_property('groom_asset')==asset and obj.get_world():
        report['instances'].append(component(obj))
for obj in u.ObjectIterator(u.LODSyncComponent):
    owner=obj.get_owner()
    if owner and 'FPSGAMECharacter' in owner.get_class().get_name():
        report['lod_sync'].append({key:prop(obj,key) for key in ('num_lods','forced_lod','min_lod','components_to_sync','custom_lod_mapping')})
(W/'inspection.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('KAITLIN_HAIR_LOD_READ',len(report['native']),'native',len(report['instances']),'instances',str(W/'inspection.json'))
