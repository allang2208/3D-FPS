"""Read the material-save failure boundary without repeating the installation."""
import unreal as u,json,os
from pathlib import Path
mesh=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'pid':os.getpid(),'play_world':world.get_path_name() if world else None,
 'dirty_packages':[p.get_path_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())],
 'slots':[{'slot':str(s.get_editor_property('imported_material_slot_name')),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials]}
Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Revision09/save_state.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
