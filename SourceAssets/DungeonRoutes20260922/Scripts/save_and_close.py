"""One mutex-held asset batch followed by normal editor exit for the native build."""
import unreal as u,runpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world():raise RuntimeError('Preserve newly started play')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
foreign=[p.get_name() for p in dirty if not p.get_name().startswith('/Game/Dungeons/Routes20260922/')]
if foreign:raise RuntimeError('Preserve unsaved edits '+str(foreign))
del dirty
runpy.run_path(str(ROOT/'Scripts/import_threshold.py'),run_name='__main__')
runpy.run_path(str(ROOT/'Scripts/route_fluid_materials.py'),run_name='__main__')
runpy.run_path(str(ROOT.parent/'DungeonSlimeSheet20260922/Scripts/install_scene.py'),run_name='__main__')
runpy.run_path(str(ROOT/'Scripts/read_start_layout.py'),run_name='__main__')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if dirty:raise RuntimeError('Preserve remaining unsaved packages '+str([p.get_name() for p in dirty]))
u.SystemLibrary.execute_console_command(UE.get_editor_world(),'QUIT_EDITOR')
print('DUNGEON_NATIVE_BUILD_EDITOR_EXIT_REQUESTED')
