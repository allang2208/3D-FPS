import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Revision06');root.mkdir(exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
actors=[]
if world:
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.WitchRebuiltMonster):
        m=a.get_component_by_class(u.SkeletalMeshComponent)
        actors.append({'name':a.get_name(),'location':str(a.get_actor_location()),'mesh':m.get_path_name(),'cloth_suspended':m.is_clothing_simulation_suspended(),'disable_cloth':m.get_editor_property('disable_cloth_simulation'),'cloth_api':[x for x in dir(m) if 'cloth' in x]})
mesh=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
cloth=[]
for c in mesh.get_editor_property('mesh_clothing_assets'):
    cfg=[]
    for k,v in c.get_editor_property('cloth_configs').items():
        fields={}
        for key in ('iteration_count','max_iteration_count','subdivision_count','use_self_collisions','use_ccd','self_collision_thickness','collision_thickness','use_bending_elements'):
            try: fields[key]=v.get_editor_property(key)
            except Exception: pass
        cfg.append({'type':v.get_class().get_name(),'settings':fields})
    cloth.append({'name':c.get_name(),'configs':cfg})
materials=[]
for slot in mesh.get_editor_property('materials'):
    mat=slot.material_interface
    materials.append({'slot':str(slot.get_editor_property('imported_material_slot_name')),'material':mat.get_path_name() if mat else None})
report={'world':world.get_path_name() if world else None,'witches':actors,'cloth':cloth,'materials':materials,'dirty_candidate':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if '/WitchRebuilt' in p.get_path_name()]}
(root/'state_before.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8');print(json.dumps(report,default=str))
