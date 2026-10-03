"""Read only the editor state needed to choose the native build path."""
import unreal
import json
print(json.dumps({
    'project': unreal.Paths.project_dir(),
    'pie': unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is not None,
    'dirty_maps': [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    'dirty_content': [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
}, ensure_ascii=False))
