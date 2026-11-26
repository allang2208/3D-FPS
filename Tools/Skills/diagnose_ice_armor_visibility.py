"""Read the current Ice Armor assets and any existing PIE components; never start PIE."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
OUT=ROOT/'SourceAssets/IceArmor20261017/VisibilityV3';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/Skills/IceArmor20261017/CrystalV2/'
def path(obj):return obj.get_path_name() if obj else None
def prop(obj,key):
    try:return obj.get_editor_property(key)
    except Exception as ex:return 'UNAVAILABLE: '+str(ex)
data={'materials':{},'meshes':{},'world':None,'players':[]}
for name in ('M_IceArmor_World','M_IceArmor_Lens','M_IceArmor_Chip'):
    m=u.load_asset(BASE+name)
    row={'asset':path(m),'settings':{k:str(prop(m,k)) for k in ('blend_mode','two_sided','disable_depth_test','translucency_pass','refraction_method')}}
    row['scalars']={str(k):u.MaterialEditingLibrary.get_material_default_scalar_parameter_value(m,k) for k in u.MaterialEditingLibrary.get_scalar_parameter_names(m)}
    data['materials'][name]=row
for name in ('SM_IceArmor_Clusters','SK_IceArmor_Torso_0','SK_IceArmor_Torso_1','SK_IceArmor_Torso_2','SK_IceArmor_Arms_0','SK_IceArmor_Legs_0'):
    m=u.load_asset(BASE+name);row={'asset':path(m)}
    if isinstance(m,u.StaticMesh):row.update(bounds=str(m.get_bounds()),material=path(m.get_material(0)))
    else:row.update(materials=[path(v.material_interface) for v in m.get_editor_property('materials')],skeleton=path(m.skeleton))
    data['meshes'][name]=row
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();data['world']=path(w)
if w:
    for actor in u.GameplayStatics.get_all_actors_of_class(w,u.Character):
        comps=actor.get_components_by_class(u.FPSIceArmorComponent)
        for c in comps:
            row={'owner':path(actor),'state':str(prop(c,'state')),'components':[]}
            for field in ('lens_mesh','armor_material','lens_material','mist_system'):
                value=prop(c,field);row[field]=path(value) if isinstance(value,u.Object) else str(value)
            for m in actor.get_components_by_class(u.MeshComponent):
                mats=[m.get_material(i) for i in range(m.get_num_materials())]
                if not any(v and ('IceArmor' in path(v) or 'IceArmor' in str(prop(v,'parent'))) for v in mats):continue
                row['components'].append({'component':path(m),'visible':m.is_visible(),'hidden':str(prop(m,'hidden_in_game')),'location':str(m.get_world_location()),'scale':str(m.get_world_scale()),'materials':[path(v) for v in mats],'parameters':[str(prop(v,'scalar_parameter_values')) for v in mats]})
            data['players'].append(row)
(OUT/'before.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
print('ICE_ARMOR_VISIBILITY_READBACK '+json.dumps(data,ensure_ascii=False),flush=True)
