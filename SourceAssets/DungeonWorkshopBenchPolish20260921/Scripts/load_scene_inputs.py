from pathlib import Path
import runpy,unreal as u
ROOT=Path(__file__).resolve().parents[1];TARGET='/Game/GameMaps/L_Dungeon_Prototype'
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve session')
dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if not ED.load_level(TARGET):raise RuntimeError('Dungeon load failed')
runpy.run_path(str(ROOT/'Scripts/read_inputs.py'),run_name='__main__')
