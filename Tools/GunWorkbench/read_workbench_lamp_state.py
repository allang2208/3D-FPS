"""Read only the active workbench reference and its existing lamp source."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/GunWorkbenchLampRestore20260928')
ROOT.mkdir(parents=True,exist_ok=True)
palette=u.load_asset('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
entry=next(e for e in palette.get_editor_property('components') if str(e.get_editor_property('id'))=='gun_workbench_table')
def mesh_info(mesh):
    return {'path':mesh.get_path_name(),'materials':[{'slot':str(s.material_slot_name),'asset':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.get_editor_property('static_materials')]}
result={'palette_mesh':mesh_info(entry.get_editor_property('mesh')),'original_lamp':{},'instances':[]}
for name in ('SM_WBK_Bench_TaskLamp','SM_WBK_LampFlex'):
    mesh=u.load_asset('/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit/Meshes/'+name)
    result['original_lamp'][name]=mesh_info(mesh) if mesh else None
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
game=editor.get_game_world();result['pie_active']=bool(game)
for world in [editor.get_editor_world(),game]:
    if not world:continue
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.VoxelBuildPrefabActor):
        for component in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=component.static_mesh
            if mesh and 'GunWorkbench' in mesh.get_path_name():
                result['instances'].append({'actor':actor.get_path_name(),'mesh':mesh.get_path_name(),
                    'scale':str(component.get_world_scale()),'materials':[component.get_material(i).get_path_name() if component.get_material(i) else None for i in range(component.get_num_materials())]})
(ROOT/'source-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
