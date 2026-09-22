"""Read the installed cloth asset and any already-running Witch, without starting play."""
import unreal as u,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Spike20260922');out.mkdir(exist_ok=True)
mesh=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
result={'cloth':[]}
def read(obj,name):
    try:return obj.get_editor_property(name)
    except Exception as e:return str(e)
for cloth in mesh.get_editor_property('mesh_clothing_assets'):
    row={'name':cloth.get_name(),'properties':{}}
    for name in ('lod_data','lod_map','used_bone_names','used_bone_indices','reference_bone_index','physics_asset','cloth_configs'):
        value=read(cloth,name);row['properties'][name]=str(value)
        if name=='lod_data' and not isinstance(value,str):
            row['lod_properties']=[]
            for lod in value:
                row['lod_properties'].append({n:str(read(lod,n)) for n in ('physical_mesh_data','point_weight_maps','use_multiple_influences','smooth_transition','skinning_kernel_radius')})
    result['cloth'].append(row)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();result['pie_active']=bool(world)
if world:
    result['instances']=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.WitchRebuiltMonster):
        comp=actor.get_component_by_class(u.SkeletalMeshComponent)
        result['instances'].append({'name':actor.get_name(),'actor_transform':str(actor.get_actor_transform()),'mesh_transform':str(comp.get_world_transform()),
            'cloth_blend':comp.get_editor_property('cloth_blend_weight'),'suspended':comp.is_clothing_simulation_suspended(),
            'mesh_bounds':str(comp.get_local_bounds())})
result['dirty_candidate']=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Monsters/WitchRebuilt')]
(out/'installed_before.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
