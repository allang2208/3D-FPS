"""Normal editor exit for the required new-class build, after current-user approval.
Never discards or saves unrelated dirty packages, and never ends an active PIE.
"""
import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921')
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=root.parent.parent/'FPSGAME.uproject':
    raise RuntimeError('Connected editor is not FPSGAME; left open')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is active; normal build exit deferred')
dirty=[p.get_path_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())]
if dirty:
    (root/'build_exit_blocked.json').write_text(json.dumps({'unsaved_packages':dirty,'action':'None; retained for current user'},indent=2),encoding='utf-8')
    raise RuntimeError('Unsaved packages retained. See build_exit_blocked.json; editor not closed')
print('No unsaved packages; requesting normal exit for the new Witch candidate class build')
u.SystemLibrary.quit_editor()
