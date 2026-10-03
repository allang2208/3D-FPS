"""Ore vein variant visual check (2026-09-30), slate post-tick state machine.

ExecutePythonScript blocks the editor main loop, so synchronous sleeps never let
the async screenshot pipeline run. Instead drive everything from
register_slate_post_tick_callback: aim viewport -> settle frames -> high-res
screenshot -> wait for file -> next angle -> write log and quit.

Launch: UnrealEditor.exe <uproject> -ExecutePythonScript=<this> -unattended -nop4 -nosplash
Rotator ctor order is (roll, pitch, yaw); orientations via look_at().
"""
import math
import os
import time

import unreal as u

EAL = u.EditorAssetLibrary
TAG = 'OREVIS'
OUT = 'D:/FPS3D/FPSGAME/Saved/OreVeinRocks'
BASE = u.Vector(0, 0, 30000)
SETTLE_FRAMES = 40
SHOT_TIMEOUT_S = 30

LOG = []


def log(m):
    u.log('%s %s' % (TAG, m))
    LOG.append(str(m))


def look_at(loc, target):
    d = u.Vector(target.x - loc.x, target.y - loc.y, target.z - loc.z)
    length = math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    pitch = math.degrees(math.asin(d.z / length))
    yaw = math.degrees(math.atan2(d.y, d.x))
    return u.Rotator(0.0, pitch, yaw)  # (roll, pitch, yaw)


world = u.EditorLevelLibrary.get_editor_world()

for cls in (u.DirectionalLight, u.SkyLight, u.StaticMeshActor):
    for a in u.GameplayStatics.get_all_actors_of_class(world, cls):
        if (a.get_actor_location() - BASE).length() < 15000:
            a.destroy_actor()

variants = [
    ('Plain', '/Game/UnrealNormandy/StaticMeshes/SM_LS_Rock_00A'),
    ('Iron', '/Game/WorldGeneration/TemperateHills/OreRocks/SM_LS_Rock_00A_Iron'),
    ('Copper', '/Game/WorldGeneration/TemperateHills/OreRocks/SM_LS_Rock_00A_Copper'),
    ('Silver', '/Game/WorldGeneration/TemperateHills/OreRocks/SM_LS_Rock_00A_Silver'),
    ('Gold', '/Game/WorldGeneration/TemperateHills/OreRocks/SM_LS_Rock_00A_Gold'),
]
spacing = 350
origin_x = -2 * spacing

for i, (name, path) in enumerate(variants):
    mesh = EAL.load_asset(path)
    if not mesh:
        log('FAIL mesh %s' % name)
        raise SystemExit(1)
    actor = u.EditorLevelLibrary.spawn_actor_from_class(
        u.StaticMeshActor, BASE + u.Vector(origin_x + i * spacing, 0, 0), u.Rotator(0, 0, 0))
    actor.set_actor_scale3d(u.Vector(1.4, 1.4, 1.4))
    actor.get_components_by_class(u.StaticMeshComponent)[0].set_static_mesh(mesh)
    log('placed %s' % name)

floor_actor = u.EditorLevelLibrary.spawn_actor_from_class(
    u.StaticMeshActor, BASE - u.Vector(0, 0, 10), u.Rotator(0, 0, 0))
floor_actor.set_actor_scale3d(u.Vector(8, 8, 1))
floor_actor.get_components_by_class(u.StaticMeshComponent)[0].set_static_mesh(
    EAL.load_asset('/Engine/BasicShapes/Plane'))

sun = u.EditorLevelLibrary.spawn_actor_from_class(
    u.DirectionalLight, BASE + u.Vector(2200, -1200, 2800),
    look_at(BASE + u.Vector(2200, -1200, 2800), BASE))
sun.get_components_by_class(u.DirectionalLightComponent)[0].set_editor_property('intensity', 10.0)
sky = u.EditorLevelLibrary.spawn_actor_from_class(u.SkyLight, BASE + u.Vector(0, 0, 4000), u.Rotator(0, 0, 0))
sky_comp = sky.get_components_by_class(u.SkyLightComponent)[0]
sky_comp.set_editor_property('mobility', u.ComponentMobility.MOVABLE)
sky_comp.set_editor_property('intensity', 1.5)

os.makedirs(OUT, exist_ok=True)
shots = [
    ('overview', BASE + u.Vector(400, -1600, 500)),
    ('close_left', BASE + u.Vector(origin_x + 150, -900, 260)),
    ('close_right', BASE + u.Vector(2 * spacing + 150, -900, 260)),
]

state = {'index': 0, 'phase': 'settle', 'frames': 0, 'deadline': 0.0}


def finish():
    from pathlib import Path as P
    P(OUT + '/log.txt').write_text('\n'.join(LOG))
    u.log('%s DONE' % TAG)
    u.unregister_slate_post_tick_callback(handle)
    u.SystemLibrary.quit_editor()


def on_tick(delta):
    try:
        # Keep the viewport dirty so the editor keeps ticking/rendering while idle.
        u.EditorLevelLibrary.editor_invalidate_viewports()
        state['frames'] += 1
        if state['frames'] == 1:
            log('TICK1 index=%d phase=%s' % (state['index'], state['phase']))
        if state['index'] >= len(shots):
            finish()
            return
        name, eye = shots[state['index']]
        dest = OUT + '/' + name + '.png'
        if state['phase'] == 'settle':
            if state['frames'] == 1:
                rot = look_at(eye, BASE + u.Vector(0, 0, 120))
                u.EditorLevelLibrary.set_level_viewport_camera_info(eye, rot)
            elif state['frames'] >= SETTLE_FRAMES:
                u.AutomationLibrary.take_high_res_screenshot(1280, 720, dest)
                state['phase'] = 'wait'
                state['deadline'] = time.time() + SHOT_TIMEOUT_S
            return
        # phase == 'wait'
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            log('SHOT %s ok (%d bytes)' % (name, os.path.getsize(dest)))
        elif time.time() > state['deadline']:
            log('SHOT %s TIMEOUT' % name)
        else:
            return
        state['index'] += 1
        state['phase'] = 'settle'
        state['frames'] = 0
    except Exception as e:
        log('TICK_ERROR %s' % e)
        state['index'] = len(shots) + 1
        finish()


handle = u.register_slate_post_tick_callback(on_tick)
u.log('%s running (tick state machine)' % TAG)
