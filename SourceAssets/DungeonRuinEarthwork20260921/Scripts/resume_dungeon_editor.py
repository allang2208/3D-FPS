"""Resume the dungeon editor after the user's explicit approval to end current play."""
from pathlib import Path
import runpy
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonRuinEarthwork20260921')
TARGET = '/Game/GameMaps/L_Dungeon_Prototype'


def main():
    level_editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if level_editor.is_in_play_in_editor():
        level_editor.editor_request_end_play()
        print('DUNGEON_RECOVERY_END_PLAY_REQUESTED; resume after end-play finishes')
        return
    if editor.get_game_world():
        raise RuntimeError('Game world is still shutting down; no map change made')
    world = editor.get_editor_world()
    if not world or world.get_path_name().split('.')[0] != TARGET:
        dirty = u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        if dirty:
            raise RuntimeError('Preserve unsaved map edits: ' + ', '.join(p.get_name() for p in dirty))
        if not level_editor.load_level(TARGET):
            raise RuntimeError('Could not load saved dungeon')
    runpy.run_path(str(ROOT / 'Scripts/read_recovery_state.py'), run_name='__main__')
    print('DUNGEON_EDITOR_RESUMED; no imports or gameplay started')


main()
