"""Apply the authorized normal PIE/editor shutdown, preserving dirty packages."""
import unreal as u,json,os
from pathlib import Path
P=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=P.parents[2]:raise RuntimeError('Wrong project')
sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
state={'editor_pid':os.getpid(),'expected_editor':os.getpid()==38976,
       'dirty_content':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
       'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
       'game_running':bool(sub and sub.get_game_world()),'action':'preserve'}
if state['expected_editor'] and not(state['dirty_content'] or state['dirty_maps']):
    state['action']='end_play' if state['game_running'] else 'normal_exit'
(P/'editor_exit_receipt.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
if state['action']=='end_play':u.EditorLevelLibrary.editor_end_play()
elif state['action']=='normal_exit':u.SystemLibrary.quit_editor()
