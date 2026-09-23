"""Complete cabinet authoring while preserving the already saved map placement."""
import unreal as u,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
LE=u.get_editor_subsystem(u.LevelEditorSubsystem)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world() or UE.get_editor_world().get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':raise RuntimeError('Preserve editor context')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map state')
runpy.run_path(str(ROOT/'Scripts/import_cabinet.py'),run_name='__main__')
if not LE.save_current_level():raise RuntimeError('Save updated cabinet references')
print('MAINTENANCE_CABINET_EDGE_FINISH_SAVED')
