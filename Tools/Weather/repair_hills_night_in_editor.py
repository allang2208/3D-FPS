"""Use the existing idle editor, save hills only, then restore its current map."""
from pathlib import Path
import runpy
import unreal as u

editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('A game session is active; no map changes were made')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():
    raise RuntimeError('Unsaved map edits are present; no map changes were made')
world = editor.get_editor_world()
previous = world.get_path_name().split('.')[0]
camera = editor.get_level_viewport_camera_info()
runpy.run_path('D:/FPS3D/FPSGAME/Tools/Weather/repair_hills_night.py', run_name='__main__')
if previous != '/Game/GameMaps/L_TemperateHills_Initial':
    if not u.EditorLoadingAndSavingUtils.load_map(previous):
        raise RuntimeError('Hills saved, but could not restore the previous editor map')
editor.set_level_viewport_camera_info(camera[0], camera[1])
print('HILLS_NIGHT_EDITOR_RESTORED ' + previous)
