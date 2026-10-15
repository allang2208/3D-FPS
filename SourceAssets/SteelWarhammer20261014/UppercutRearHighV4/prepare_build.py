"""Finish the previously authorized normal exit only when this editor is clean."""
import unreal as u,json,os
from pathlib import Path
P=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=P.parents[2]:raise RuntimeError('Wrong project')
subsystem=u.get_editor_subsystem(u.UnrealEditorSubsystem)
state={'editor_pid':os.getpid(),'expected_editor':os.getpid()==144528,
       'dirty_content':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
       'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
       'game_running':bool(subsystem and subsystem.get_game_world())}
state['normal_exit_requested']=state['expected_editor'] and not(state['dirty_content'] or state['dirty_maps'] or state['game_running'])
(P/'editor_exit_receipt.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
if state['normal_exit_requested']:u.SystemLibrary.quit_editor()
