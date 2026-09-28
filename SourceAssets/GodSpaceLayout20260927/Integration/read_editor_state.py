import json
import unreal as u
e=u.get_editor_subsystem(u.UnrealEditorSubsystem)
print(json.dumps({'editor_world':str(e.get_editor_world()),'game_world':str(e.get_game_world()),'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'dirty_content':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]},ensure_ascii=False))
