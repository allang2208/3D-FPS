# Offscreen diagnostic render of the two tool viewmodels, run in a SEPARATE
# hidden UnrealEditor instance (-ExecutePythonScript -RenderOffscreen), the same
# pattern as SourceAssets/RuneSword20260913/FistBraceGuardV21/review_in_ue.py.
# Read-only on assets: creates a blank map in its own process, renders, quits.
import json
import math
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Saved/Production/tool-enhance-viewmodel-diag'
OUT.mkdir(parents=True, exist_ok=True)
RECEIPT = ROOT / 'Saved/Production/tool-enhance-viewmodel-diag.json'

TARGETS = [('pick', '/Game/Items/ProductionTools/RusticPickaxe20260919/SK_RusticPickaxe'),
           ('axe', '/Game/Items/ProductionTools/GripMotion20260913/SK_Harvest_Axe')]

state = {'shot': 0, 'frame': 0, 'started': time.monotonic()}
callback = None
receipt = []
spawned = []


def spawn(cls, pos=(0, 0, 0), rot=None):
    actor = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(
        cls, u.Vector(*pos), rot or u.Rotator())
    spawned.append(actor)
    return actor


def finish(error=None):
    global callback
    if callback:
        u.unregister_slate_post_tick_callback(callback)
        callback = None
    if error:
        RECEIPT.write_text(json.dumps({'error': error}, indent=2), encoding='utf-8')
    else:
        RECEIPT.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    u.SystemLibrary.quit_editor()


try:
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
    for cmd in ['r.TextureStreaming 0', 'r.AntiAliasingMethod 2', 'r.ScreenPercentage 100',
                't.IdleWhenNotForeground 0']:
        u.SystemLibrary.execute_console_command(world, cmd)

    actors = []
    for tag, path in TARGETS:
        actor = spawn(u.SkeletalMeshActor, pos=(0, 0, 0))
        comp = actor.skeletal_mesh_component
        comp.set_mobility(u.ComponentMobility.MOVABLE)
        comp.set_skeletal_mesh_asset(u.load_asset(path))
        comp.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
        comp.set_enable_animation(False)
        comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        comp.set_cast_shadow(False)
        actor.set_actor_location(u.Vector(0, 0, 0) if tag == 'pick' else u.Vector(0, 140, 0), False, False)
        actors.append((tag, actor))

    focus = u.Vector(0, 70, 10)
    for pos, power, width in (((0, -120, 140), 800, 200), ((140, 160, 80), 450, 150), ((-150, 40, 90), 550, 150)):
        light = spawn(u.RectLight, pos)
        light.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos), focus), False)
        lc = light.get_component_by_class(u.RectLightComponent)
        lc.set_mobility(u.ComponentMobility.MOVABLE)
        lc.set_intensity(power)
        lc.set_source_width(width)
        lc.set_source_height(width)
        lc.set_attenuation_radius(900.)
    sky = spawn(u.SkyLight)
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_intensity(1.0)
    cube = u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap')
    if cube:
        sky.light_component.set_editor_property('source_type', u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
        sky.light_component.set_editor_property('cubemap', cube)

    capture = spawn(u.SceneCapture2D, pos=(0, -230, 60))
    cc = capture.get_component_by_class(u.SceneCaptureComponent2D)
    rt = u.RenderingLibrary.create_render_target2d(world, 1280, 720,
                                                   u.TextureRenderTargetFormat.RTF_RGBA8,
                                                   u.LinearColor(.05, .06, .08, 1))
    fov = math.degrees(2 * math.atan(math.tan(math.radians(60) * .5) * 16 / 9))
    for key, value in [('texture_target', rt),
                       ('capture_source', u.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                       ('capture_every_frame', False), ('capture_on_movement', False),
                       ('fov_angle', fov), ('always_persist_rendering_state', True)]:
        cc.set_editor_property(key, value)
    pp = cc.get_editor_property('post_process_settings')
    pp.override_auto_exposure_method = True
    pp.auto_exposure_method = u.AutoExposureMethod.AEM_MANUAL
    pp.auto_exposure_bias = 0.0
    pp.override_bloom_intensity = True
    pp.bloom_intensity = 0.1
    cc.set_editor_property('post_process_settings', pp)

    shots = [
        ('diag_both', u.Vector(0, -230, 60), focus, 60.),
        ('diag_pick_close', u.Vector(-40, -130, 95), u.Vector(0, 0, 70), 35.),
        ('diag_axe_close', u.Vector(-40, 10, 95), u.Vector(0, 140, 70), 35.),
    ]

    def tick(delta):
        try:
            f = state['frame']
            state['frame'] += 1
            shot = shots[state['shot']]
            if f == 0:
                cc.set_editor_property('camera_cut_this_frame', True)
                cc.set_world_location(shot[1], False, False)
                cc.set_world_rotation(u.MathLibrary.find_look_at_rotation(shot[1], shot[2]), False, False)
                cc.set_editor_property('fov_angle', shot[3])
            elif f == 4:
                cc.capture_scene()
            elif f >= 10:
                u.RenderingLibrary.export_render_target(world, rt, str(OUT), shot[0] + '.png')
                receipt.append({'image': shot[0] + '.png',
                                'seconds': round(time.monotonic() - state['started'], 2)})
                state['shot'] += 1
                state['frame'] = 0
                if state['shot'] == len(shots):
                    finish()
        except Exception:
            finish(traceback.format_exc())

    callback = u.register_slate_post_tick_callback(tick)
except Exception:
    finish(traceback.format_exc())
