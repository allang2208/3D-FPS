"""活编辑器内：几何截断倒树自检截图 v3（2026-09-29）。

v2 教训（本次修正）：
  1. Python Rotator 构造顺序是 (roll, pitch, yaw)——v2 按 (pitch,yaw,roll) 传参，
     相机 A/B 变成正下方俯视、C 角度错位，三张全是空镜头；
  2. 太阳 Rotator(-35,25,0) 实为 pitch=+25 朝天照，树没被照亮；
  3. 全部朝向改用 look_at() 反算，太阳方向同理。
沿用 v2 的验证模式：export_render_target(world,rt,目录,文件名)、逐帧采集 ~40 帧、
换相位后重摆相机重采。加参照方块（SM_Cube）锚定机位，自检资产/包围盒并写文件日志。
三路：A=切口特写(裁剪开) C=全树中景 B=切口特写(裁剪关,对照)。瞬态，不保存关卡。
"""
import math

import unreal as u

EAL = u.EditorAssetLibrary
TAG = 'SELFCHECK'
OUT = 'D:/FPS3D/FPSGAME/Saved/ProductionTreeHealth'
BASE = u.Vector(0, 0, 50000)
FRAMES_PER_PHASE = 40

LOG_LINES = []


def log(m):
    u.log('%s %s' % (TAG, m))
    LOG_LINES.append(str(m))


def look_at(loc, target):
    d = u.Vector(target.x - loc.x, target.y - loc.y, target.z - loc.z)
    length = math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z)
    pitch = math.degrees(math.asin(d.z / length))
    yaw = math.degrees(math.atan2(d.y, d.x))
    return u.Rotator(0.0, pitch, yaw)  # (roll, pitch, yaw)


world = u.EditorLevelLibrary.get_editor_world()
mesh = EAL.load_asset('/Game/Items/HarvestTimber/SK_CutUpper_A')
if not mesh:
    log('FAIL mesh')
    raise SystemExit(1)

# 清扫上次运行可能残留的瞬态 actor（500 m 高空 200 m 内不该有别的东西）。
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
sky_comp = sky.get_components_by_class(u.SkyLightComponent)[0]
sky_comp.set_editor_property('intensity', 2.0)
try:
    sky_comp.recapture()
except Exception as e:
    log('sky recapture skip (%s)' % e)

# 参照方块：亮灰 SM_Cube 在树旁，用于锚定机位（方块可见而树不可见＝树的问题，反之＝相机问题）。
cube = u.EditorLevelLibrary.spawn_actor_from_class(u.StaticMeshActor, BASE + u.Vector(160, 150, 40), u.Rotator(0, 0, 0))
cube_root = cube.get_editor_property('static_mesh_component')
cube_root.set_static_mesh(EAL.load_asset('/Engine/BasicShapes/Cube'))
cube_root.set_world_scale3d(u.Vector(0.5, 0.5, 0.5))

actor = u.EditorLevelLibrary.spawn_actor_from_class(TREE_CLASS, BASE, u.Rotator(0, 0, 0))
comps = actor.get_components_by_class(u.SkeletalMeshComponent) if actor else []
if not comps:
    log('FAIL no component')
    raise SystemExit(1)
comp = comps[0]
try:
    comp.set_skinned_asset_and_update(mesh, False)
except AttributeError:
    comp.set_skeletal_mesh(mesh, False)
comp.set_bounds_scale(1.15)
asset_name = comp.get_skinned_asset().get_name() if comp.get_skinned_asset() else 'NONE'
log('SKINNED=%s actor_loc=%s' % (asset_name, actor.get_actor_location()))
if asset_name == 'NONE':
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


def apply_params(radius, top):
    for i in range(comp.get_num_materials()):
        parent = comp.get_material(i)
        mid = comp.create_dynamic_material_instance(i, parent)
        if not mid:
            continue
        mid.set_scalar_parameter_value('HarvestCutRadius', radius)
        mid.set_scalar_parameter_value('HarvestFlareTop', top)
        mid.set_scalar_parameter_value('HarvestCutHeight', 42.0)
        mid.set_scalar_parameter_value('HarvestTreeHeight', 3100.0)
        mid.set_scalar_parameter_value('HarvestFade', 1.0)
    log('PARAMS R=%s T=%s' % (radius, top))


# (名字, 材质参数, 相机相对 BASE 位置, 注视点相对 BASE)
PHASES = [
    ('selfcheck_A_clamp_on', (40.0, 90.0), u.Vector(300, 0, 140), u.Vector(0, 0, 100)),
    ('selfcheck_C_crown', (40.0, 90.0), u.Vector(1500, 1500, 1800), u.Vector(0, 0, 1500)),
    ('selfcheck_B_clamp_off', (100000.0, 0.0), u.Vector(300, 0, 140), u.Vector(0, 0, 100)),
]

state = {'phase': -1, 'frames': 0, 'handle': None}


def begin_phase(index):
    name, params, offset, look = PHASES[index]
    apply_params(*params)
    loc = BASE + offset
    try:
        cap.set_actor_location(loc, False, True)
        cap.set_actor_rotation(look_at(loc, BASE + look), False)
    except Exception as e:
        log('CAMERA ERR %s' % e)
    state['frames'] = 0
    log('PHASE %s begin' % name)


def cleanup():
    for a in (actor, cube, cap, sun, sky):
        if a:
            a.destroy_actor()
    with open(OUT + '/selfcheck_DONE.txt', 'w') as f:
        f.write('done v3\n')
    with open(OUT + '/selfcheck_log.txt', 'w') as f:
        f.write('\n'.join(LOG_LINES) + '\n')
    u.log('%s DONE' % TAG)


def on_tick(_delta):
    try:
        if state['phase'] < 0:
            state['phase'] = 0
            begin_phase(0)
            cc.capture_scene()
            return
        cc.capture_scene()
        state['frames'] += 1
        if state['frames'] < FRAMES_PER_PHASE:
            return
        name = PHASES[state['phase']][0]
        ok = u.RenderingLibrary.export_render_target(world, rt, OUT, name + '.png')
        log('EXPORT %s %s' % (name, ok))
        state['phase'] += 1
        if state['phase'] >= len(PHASES):
            u.unregister_slate_post_tick_callback(state['handle'])
            cleanup()
            return
        begin_phase(state['phase'])
    except Exception as e:
        log('TICK ERR %s' % e)
        state['frames'] = FRAMES_PER_PHASE  # 防死循环：下一 tick 直接导出/推进



state['handle'] = u.register_slate_post_tick_callback(on_tick)
log('STARTED v3')
