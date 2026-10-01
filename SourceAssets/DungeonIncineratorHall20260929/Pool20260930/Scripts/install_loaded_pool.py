"""Update only the already loaded, clean production world through the batch bridge."""
import runpy
from pathlib import Path
import unreal as u
source=u.find_object(None,'/Game/GameMaps/L_Dungeon_Randomized.L_Dungeon_Randomized')
if not source or source==u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Only edit the original saved world, never the running world')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if any('gamemaps/l_dungeon_randomized' in p.get_name().lower() for p in dirty):raise RuntimeError('Preserve unsaved production dungeon edits')
runpy.run_path(str(Path(__file__).with_name('install_pool.py')),init_globals={'ALLOW_EDITOR_BATCH':True},run_name='__main__')
