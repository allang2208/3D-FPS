"""环拍找茬：SK_CutUpper_A 基座 8 方位+俯拍，定位用户图中倒木基部的突出物（2026-09-29）。

复用 selfcheck v3 的全部修复：look_at 反算朝向（Rotator=roll,pitch,yaw 顺序坑）、
SceneCapture2D 根组件 MOVABLE、set_actor_location(loc,False,True)/set_actor_rotation(rot,False)
传全参（无默认参必抛 TypeError 且被 Slate 吞）、回调整体 try/except 落日志。
参数与生产一致：R=40/T=90/H=42/TreeHeight=3100。瞬态，先清扫后工作，不保存关卡。
"""
import math

import unreal as u

EAL = u.EditorAssetLibrary
TAG = 'ORBIT'
OUT = 'D:/FPS3D/FPSGAME/Saved/ProductionTreeHealth'
BASE = u.Vector(0, 0, 50000)
FRAMES_PER_PHASE = 25


def log(m):
    u.log('%s %s' % (TAG, m))
    print('%s %s' % (TAG, m))


def look_at(loc, target):
    d = u.Vector(target.x - loc.x, target.y - loc.y, target.z - loc.z)
    length = math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    return u.Rotator(0.0, math.degrees(math.asin(d.z / length)), math.degrees(math.atan2(d.y, d.x)))


world = u.EditorLevelLibrary.get_editor_world()
if world is None:
    # 无世界时安全加载主地图（原子防踩：有世界就中止，绝不覆盖他人会话）
    les = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if les and les.get_editor_world() is None:
        u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/DayNight_Lighting')
        world = u.EditorLevelLibrary.get_editor_world()
    if world is None:
        log('FAIL no world even after load attempt')
        raise SystemExit(1)
mesh = EAL.load_asset('/Game/Items/HarvestTimber/SK_CutUpper_A')
if not mesh:
    log('FAIL mesh')
    raise SystemExit(1)

TREE_CLASS = u.load_object(None, '/Script/FPSGAME.ProductionFallingTree')
for cls in (u.DirectionalLight, u.SkyLight, u.SceneCapture2D, u.StaticMeshActor, TREE_CLASS):
    try:
        for a in u.GameplayStatics.get_all_actors_of_class(world, cls):
            if (a.get_actor_location() - BASE).length() < 20000:
                log('SWEEP stale %s' % a.get_name())
                a.destroy_actor()
    except Exception as e:
        log('SWEEP skip (%s)' % e)

sun = u.EditorLevelLibrary.spawn_actor_from_class(
    u.DirectionalLight, BASE + u.Vector(2600, -1400, 3200),
    look_at(BASE + u.Vector(2600, -1400, 3200), BASE + u.Vector(0, 0, 400)))
sky = u.EditorLevelLibrary.spawn_actor_from_class(u.SkyLight, BASE + u.Vector(0, 0, 4000), u.Rotator(0, 0, 0))
sun_comp = sun.get_components_by_class(u.DirectionalLightComponent)[0]
sun_comp.set_editor_property('intensity', 12.0)

actor = u.EditorLevelLibrary.spawn_actor_from_class(TREE_CLASS, BASE, u.Rotator(0, 0, 0))
comp = actor.get_components_by_class(u.SkeletalMeshComponent)[0]
try:
    comp.set_skinned_asset_and_update(mesh, False)
except AttributeError:
    comp.set_skeletal_mesh(mesh, False)
comp.set_bounds_scale(1.15)
if not comp.get_skinned_asset():
    log('FAIL skinned asset not set')
    raise SystemExit(1)

cap = u.EditorLevelLibrary.spawn_actor_from_class(u.SceneCapture2D, BASE, u.Rotator(0, 0, 0))
cap.get_editor_property('root_component').set_editor_property('mobility', u.ComponentMobility.MOVABLE)
cc = cap.get_editor_property('capture_component2d')
cc.set_editor_property('mobility', u.ComponentMobility.MOVABLE)
rt = u.RenderingLibrary.create_render_target2d(world, 1280, 720, u.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
cc.set_editor_property('texture_target', rt)
cc.set_editor_property('fov_angle', 55.0)
cc.set_editor_property('capture_source', u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)

for i in range(comp.get_num_materials()):
    parent = comp.get_material(i)
    mid = comp.create_dynamic_material_instance(i, parent)
    if not mid:
        continue
    mid.set_scalar_parameter_value('HarvestCutRadius', 40.0)
    mid.set_scalar_parameter_value('HarvestFlareTop', 90.0)
    mid.set_scalar_parameter_value('HarvestCutHeight', 42.0)
    mid.set_scalar_parameter_value('HarvestTreeHeight', 3100.0)
    mid.set_scalar_parameter_value('HarvestFade', 1.0)
    # 2026-09-29 内壁舌头掩码（与 C++ StubYawDeg/TolDeg/ZMaxCm 的 A 变体一致）
    mid.set_scalar_parameter_value('HarvestStubYaw', 337.5)
    mid.set_scalar_parameter_value('HarvestStubYawTol', 25.0)
    mid.set_scalar_parameter_value('HarvestStubZMax', 210.0)
log('PARAMS applied')

# 8 方位（半径 320，高度 140，注视点 (0,0,90)）+ 1 个高俯角 + 1 个垂直于嫌疑扇区(≈330°)的近景
PHASES = []
for k in range(8):
    ang = math.radians(k * 45.0)
    PHASES.append(('orbit_%d' % k, u.Vector(320 * math.cos(ang), 320 * math.sin(ang), 140), u.Vector(0, 0, 90)))
PHASES.append(('orbit_top', u.Vector(420, 0, 520), u.Vector(0, 0, 0)))
PHASES.append(('orbit_close75', u.Vector(260 * math.cos(math.radians(75)), 260 * math.sin(math.radians(75)), 120), u.Vector(0, 0, 120)))

state = {'phase': -1, 'frames': 0, 'handle': None, 'log': []}


def log2(m):
    state['log'].append(str(m))


def cleanup():
    for a in (actor, cap, sun, sky):
        if a:
            a.destroy_actor()
    with open(OUT + '/orbit_DONE.txt', 'w') as f:
        f.write('done\n')
    with open(OUT + '/orbit_log.txt', 'w') as f:
        f.write('\n'.join(state['log']) + '\n')


def on_tick(_delta):
    try:
        if state['phase'] < 0:
            state['phase'] = 0
            name, offset, look = PHASES[0]
            loc = BASE + offset
            cap.set_actor_location(loc, False, True)
            cap.set_actor_rotation(look_at(loc, BASE + look), False)
            state['frames'] = 0
            log('PHASE %s' % name)
            cc.capture_scene()
            return
        cc.capture_scene()
        state['frames'] += 1
        if state['frames'] < FRAMES_PER_PHASE:
            return
        name = PHASES[state['phase']][0]
        u.RenderingLibrary.export_render_target(world, rt, OUT, name + '.png')
        log('EXPORT %s' % name)
        log2('EXPORT %s' % name)
        state['phase'] += 1
        if state['phase'] >= len(PHASES):
            u.unregister_slate_post_tick_callback(state['handle'])
            cleanup()
            log('DONE')
            return
        noffset, nlook = PHASES[state['phase']][1], PHASES[state['phase']][2]
        loc = BASE + noffset
        cap.set_actor_location(loc, False, True)
        cap.set_actor_rotation(look_at(loc, BASE + nlook), False)
        state['frames'] = 0
        loc_read = cap.get_actor_location()
        log2('PHASE %s cam_readback=(%.0f,%.0f,%.0f)' % (
            PHASES[state['phase']][0], loc_read.x, loc_read.y, loc_read.z))
        log('PHASE %s' % PHASES[state['phase']][0])
    except Exception as e:
        log('TICK ERR %s' % e)
        log2('TICK ERR %s' % e)
        state['frames'] = FRAMES_PER_PHASE


state['handle'] = u.register_slate_post_tick_callback(on_tick)
log('STARTED')
