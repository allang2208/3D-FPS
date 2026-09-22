"""Render preview shots of the dungeon prototype from the built geometry.

Loads /Game/GameMaps/L_Dungeon_Prototype in a headless process, drops a
SceneCapture2D at a few eye positions, and exports PNGs to Saved/DungeonPreview/.
Read-only with respect to the map: nothing is added to or saved into the level.

Run:
  "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" \
     D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
     -script=D:/FPS3D/FPSGAME/SourceAssets/DungeonKit20260920/preview_dungeon.py \
     -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path
import unreal as u

LEVEL = '/Game/GameMaps/L_Dungeon_Prototype'
OUT = Path(u.Paths.project_dir()) / 'Saved' / 'DungeonPreview'
OUT.mkdir(parents=True, exist_ok=True)

editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
if not editor.load_level(LEVEL):
    raise RuntimeError('load_level failed')

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
actors = u.get_editor_subsystem(u.EditorActorSubsystem)

CELL = 300.0
record = {'shots': []}

# Eye positions in cell coordinates, looking along +X or +Y (yaw degrees).
# yaw 0 = +X, 90 = +Y, 180 = -X, 270 = -Y (UE: yaw 0 faces +X).
def shot(name, eye_cells, yaw, pitch=-8.0, fov=95.0):
    eye = u.Vector(eye_cells[0] * CELL, eye_cells[1] * CELL, eye_cells[2])
    capture = actors.spawn_actor_from_class(u.SceneCapture2D, eye, u.Rotator(0.0, pitch, yaw))
    cam = capture.get_component_by_class(u.SceneCaptureComponent2D)
    cam.set_editor_property('capture_every_frame', False)
    cam.set_editor_property('capture_on_movement', False)
    cam.set_editor_property('always_persist_rendering_state', True)
    cam.set_editor_property('capture_source', u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    cam.set_editor_property('fov_angle', fov)
    try:
        settings = cam.get_editor_property('post_process_settings')
        settings.set_editor_property('override_auto_exposure_method', True)
        settings.set_editor_property('auto_exposure_method', u.AutoExposureMethod.AEM_MANUAL)
        settings.set_editor_property('override_auto_exposure_bias', True)
        settings.set_editor_property('auto_exposure_bias', 8.0)
        settings.set_editor_property('override_auto_exposure_apply_physical_camera_exposure', True)
        settings.set_editor_property('auto_exposure_apply_physical_camera_exposure', False)
        cam.set_editor_property('post_process_settings', settings)
    except Exception as e:
        record['shots'].append({'shot': name, 'exposure_note': str(e)})
    target = u.RenderingLibrary.create_render_target2d(world, 960, 540, u.TextureRenderTargetFormat.RTF_RGBA8)
    cam.set_editor_property('texture_target', target)
    cam.capture_scene()
    u.RenderingLibrary.export_render_target(world, target, str(OUT), name + '.png')
    actors.destroy_actor(capture)
    record['shots'].append({'shot': name, 'eye_cells': eye_cells, 'yaw': yaw, 'file': name + '.png'})
    u.log(f'DUNGEON_SHOT {name} -> {OUT / (name + ".png")}')


# Same layout the build script used (cell = 300 cm):
#   floor 0: entry[0-1] corridor[2-3] combat[4-5] stairs[6-7]
#   floor 1: boss[0-3]  corridor[4-5] landing[6-7]
shot('01_entry_from_west', (0.15, 1.0, 165.0), 0.0)
shot('02_entry_to_corridor', (1.15, 1.0, 165.0), 0.0)
shot('03_corridor0', (2.15, 1.0, 165.0), 0.0)
shot('04_combat', (4.15, 1.0, 165.0), 0.0)
shot('05_stairs_room', (6.15, 1.0, 165.0), 0.0)
shot('06_stairs_up', (6.4, 1.0, 200.0), 0.0)
shot('07_landing1', (6.15, 1.0, CELL + 165.0), 0.0)
shot('08_corridor1', (4.15, 1.0, CELL + 165.0), 0.0)
shot('09_boss', (0.15, 1.0, CELL + 165.0), 0.0)
shot('10_overview', (3.5, -3.0, 900.0), 70.0, pitch=-38.0, fov=75.0)

out = OUT / 'shots.json'
out.write_text(json.dumps(record, indent=2), encoding='utf-8')
u.log('DUNGEON_PREVIEW_OK ' + json.dumps(record))