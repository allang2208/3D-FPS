"""Run only after current-user approval to close the clean duplicate editor."""
import unreal as u,os
from pathlib import Path
if os.getpid()!=87008:raise RuntimeError('Not the identified duplicate editor; left open')
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=Path('D:/FPS3D/FPSGAME/FPSGAME.uproject'):raise RuntimeError('Wrong project; left open')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; left open')
dirty=[p.get_path_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())]
if dirty:raise RuntimeError('Unsaved work retained; editor left open: '+str(dirty))
# Fabric09 master/instances are saved; failed mesh-slot save is reproducible
# using finish_fabric09.py in the retained editor. No other package is saved.
print('Clean duplicate FPSGAME editor; requesting normal exit after user approval')
u.SystemLibrary.quit_editor()
