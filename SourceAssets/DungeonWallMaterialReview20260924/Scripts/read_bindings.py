"""Read current room bindings and confirm cleanup of owned temporary actors."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
out={'editor_world':UE.get_editor_world().get_path_name(),
     'game_world':str(UE.get_game_world()),
     'remaining_review_actors':[a.get_path_name() for a in AA.get_all_level_actors() if a.get_actor_label()=='Temporary_WallMaterialReview'],
     'dirty_content':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
     'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
     'meshes':{},'textures':{}}
for room in ['Distribution_CombatDoor','Threshold','Transit']:
    for path in ['/Game/Dungeons/RouteRepairs20260922/Meshes/SM_RS_'+room+'_Shell',
                 '/Game/Dungeons/WallDamage20260923/Meshes/SM_RS_'+room+'_Damage0_Tiles']:
        mesh=u.load_asset(path)
        out['meshes'][path]=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name(),
            'parent':s.material_interface.get_base_material().get_path_name()} for s in mesh.get_editor_property('static_materials') if s.material_interface]
for path in ['/Game/Dungeons/AtmosphereV2/Textures/T_Concrete_Normal',
             '/Game/Dungeons/AtmosphereV2/Textures/T_Concrete_BaseColor',
             '/Game/Dungeons/WallDamage20260923/Textures/T_FabExposedConcrete_BaseColor']:
    t=u.load_asset(path)
    out['textures'][path]={p:str(t.get_editor_property(p)) for p in ['lod_bias','max_texture_size','srgb','compression_settings','mip_gen_settings','never_stream']}
(ROOT/'Receipts/current-bindings.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('CURRENT_WALL_BINDINGS',json.dumps(out),flush=True)
