"""Normal editor exit for the previously authorized formal build, if clean."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
subsystem=u.get_editor_subsystem(u.UnrealEditorSubsystem)
state={'project':u.Paths.project_dir(),
    'dirty_content':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    'game_running':bool(subsystem and subsystem.get_game_world())}
state['normal_exit_requested']=not(state['dirty_content'] or state['dirty_maps'] or state['game_running'])
(P/'editor_exit_receipt.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
if state['normal_exit_requested']:u.SystemLibrary.quit_editor()
