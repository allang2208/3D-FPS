"""Read only the state needed to choose a safe native build window."""
import os, json, unreal
dirty=unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()+unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
print(json.dumps({'pid':os.getpid(),'project':unreal.Paths.project_dir(),'dirty':[p.get_name() for p in dirty],
    'game_world':bool(unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world())}))
