"""M4 枪托砸击（快速进战·步枪版）作者源。

Blender --background --factory-startup --python author_quickcombat.py -- Base [Drum ...]

路线与这把枪的换弹/战术冲刺同一约定：**整枪刚体搬运写在 WPN_ 骨上，
双手由握把关系带动**（右手握把、左手护木），全程不松手、不开指。
相对已接受的手枪版（DW715 握把砸击）保持同一节奏家族：
蓄势抬枪（枪口朝上）→ 顶点保持 → 斜下前砸（枪托/机匣端扫过画面中心）→ 跟随 → 回位。

坐标（armature 空间，米）：+Y 前 / +X 右 / +Z 上；
旋转按 Rx(pitch)·Rz(yaw)·Ry(roll)，pitch 正 = 枪口上抬，yaw 正 = 枪口向左摆。
只做制作与导出，不渲染、不做运行时验收。
"""
import ast
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

O = Path(__file__).resolve().parent
S = O.parent

SOURCES = {
    'Base': ('M4ContactImpact20260910/M4_Hand_MAT_Editable.blend', 'M4_idle'),
    'Drum': ('M4ContactImpact20260910/M4_Hand_MAT_Editable.blend', 'M4_idle'),
    'Angled': ('AngledForegrip20260910/WristNatural/A_M4_Foregrip_idle.blend', 'A_M4_Foregrip_idle'),
    'Vertical': ('MannyGraspDonor20260912/Final/m4/vertical/A_M4_Vertical_idle.blend', 'A_M4_Vertical_idle.001'),
    'Canted': ('VREGripExtensions20260912/Final/m4/canted/A_M4_Canted_idle.blend', 'A_M4_Canted_idle.001'),
    'Prism': ('VREGripExtensions20260912/Final/m4/prism/A_M4_Prism_idle.blend', 'A_M4_Prism_idle.001'),
}

_argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
profiles = [a for i, a in enumerate(_argv) if not a.startswith('--') and (i == 0 or _argv[i - 1] != '--variant')] or ['Base']
FRAME_HZ = 60.0
SAMPLE_HZ = 120
CLIP = 'quickcombat'
DURATION = 0.72
# 时间轴按比例放宽到 0.72 s（参考视频一个完整挥击周期约 1.0 s，含镜头摆动；
# 本工程取更干脆的一档）。比例与运行时常数一致：0.058/0.244/0.348/0.511。
TIMES = [0.00, 0.058, 0.186, 0.244, 0.348, 0.383, 0.511, 0.72]
CONTACT = TIMES[4]      # 接触/命中判定时刻（秒），与运行时时钟同源
DESTINATION = '/Game/Weapons/M4StockMelee20260918'

# 动作表：局部轴见文件头。offset 单位米，armature 空间 (右, 前, 上)。
# 两版共用同一条时间轴（0.30 接触、0.30→0.33 顿帧、0.62 收势），
# 所以运行时 `QuickCombatRifleMotion.h` 的比例常数不用改。
#
#   A：枪口上抬 → 整枪越过竖向前下扫（枪口领先）
#   B：枪托上抬（枪口下沉）→ 枪托自右上扫过画面中心（枪托领先，默认）
# 30 fps 原生帧复核（2026-09-18）：参考里画面上方出现的是**木质枪托与枪绳**，
# 枪口朝左下出画 → 采用 B；A 保留作为可切换的对照候选。
MOTION_A = {
    'times': TIMES,
    'pitch': [0.0, 10.0, 54.0, 58.0, -18.0, -22.0, -26.0, 0.0],
    'yaw': [0.0, -3.0, -11.0, -12.0, 8.0, 9.0, 6.0, 0.0],
    'roll': [0.0, 2.0, 9.0, 10.0, -6.0, -7.0, -4.0, 0.0],
    'offset': [(0.0, 0.0, 0.0), (0.020, 0.030, 0.010), (0.085, 0.130, 0.035), (0.088, 0.134, 0.038),
               (0.045, 0.155, -0.045), (0.045, 0.160, -0.050), (0.030, 0.175, -0.065), (0.0, 0.0, 0.0)],
    'ease': ['smooth', 'decel', 'accel', 'linear', 'decel', 'smooth', 'smooth'],
}

MOTION_B = {
    'times': TIMES,
    # pitch 负 = 枪口下沉、枪托抬到镜前；roll 负 = 抬起来的枪托向画面左侧扫。
    # 参数由 tune_motion.py 按参考帧的枪托屏幕轨迹反解后手工顺过（避免 roll/pitch 抖动）。
    'pitch': [0.0, -6.0, -70.0, -74.0, -78.0, -78.0, -70.0, 0.0],
    'yaw': [0.0, 2.0, 6.0, 2.0, -18.0, -24.0, -30.0, 0.0],
    'roll': [0.0, 2.0, 8.0, 4.0, -18.0, -22.0, -26.0, 0.0],
    'offset': [(0.0, 0.0, 0.0), (0.02, 0.20, 0.00), (0.06, 0.34, 0.02), (0.06, 0.35, 0.02),
               (0.02, 0.36, 0.02), (0.01, 0.37, 0.02), (0.00, 0.38, 0.02), (0.0, 0.0, 0.0)],
    'ease': ['smooth', 'decel', 'accel', 'linear', 'decel', 'smooth', 'smooth'],
}

# C（默认）：横向横扫——用户 2026-09-18 指正「是横向枪托攻击，不是上下劈」。
# 俯仰基本不动、偏航做大：枪口在蓄势时甩到画面左侧，接触瞬间扫过画面中心，跟随继续向右；
# 枪托（贴镜头、本就在画面外下方）反向扫过，不进入取景。整枪仍刚体搬运，双手不松手。
MOTION_C = {
    'times': TIMES,
    'pitch': [0.0, 2.0, 5.0, 5.0, -3.0, -4.0, -3.0, 0.0],
    'yaw': [0.0, 24.0, 46.0, 46.0, -12.0, -22.0, -36.0, 0.0],
    'roll': [0.0, 4.0, 10.0, 11.0, -8.0, -10.0, -8.0, 0.0],
    'offset': [(0.0, 0.0, 0.0), (0.01, 0.05, 0.01), (0.02, 0.12, 0.02), (0.02, 0.12, 0.02),
               (0.00, 0.18, 0.00), (-0.01, 0.19, 0.00), (-0.02, 0.20, 0.00), (0.0, 0.0, 0.0)],
    'ease': ['smooth', 'decel', 'accel', 'linear', 'decel', 'smooth', 'smooth'],
}

variant = 'C'
if '--variant' in sys.argv:
    variant = sys.argv[sys.argv.index('--variant') + 1].upper()
MOTION = {'A': MOTION_A, 'B': MOTION_B}.get(variant, MOTION_C)


def log(*args):
    print('[M4QC]', *args, flush=True)


def ease(kind, u):
    u = max(0.0, min(1.0, u))
    if kind == 'accel':
        return u * u
    if kind == 'decel':
        return 1.0 - (1.0 - u) * (1.0 - u)
    if kind == 'linear':
        return u
    return u * u * (3.0 - 2.0 * u)


def keyed(t, channel):
    times = MOTION['times']
    values = MOTION[channel]
    if t <= times[0]:
        return values[0]
    for i in range(len(times) - 1):
        if t <= times[i + 1]:
            u = ease(MOTION['ease'][i], (t - times[i]) / max(1e-6, times[i + 1] - times[i]))
            a, b = values[i], values[i + 1]
            if isinstance(a, tuple):
                return tuple(a[k] + (b[k] - a[k]) * u for k in range(len(a)))
            return a + (b - a) * u
    return values[-1]


receipt = {'clip': CLIP, 'variant': variant, 'duration': DURATION, 'contact': CONTACT, 'sample_rate': SAMPLE_HZ,
           'coordinates': 'armature: +Y forward, +X right, +Z up; metres',
           'convention': 'WPN_ bones carry the rigid rifle motion; both hands ride the grip relations',
           'reference': 'BV13K421e7Rw 1:05-1:07 AK47 stock melee (motion language only)',
           'status': 'Authored and exported; not rendered or tested', 'profiles': {}}

for profile in profiles:
    source, source_action = SOURCES[profile]
    dest = O / profile
    (dest / 'Animations').mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.open_mainfile(filepath=str(S / source))
    rig = bpy.data.objects['SK_M4_Infima']
    rig.data.pose_position = 'POSE'
    scene = bpy.context.scene
    scene.render.fps = int(FRAME_HZ)

    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    names = list(rest)
    lr = {n: (rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n]) for n in names}

    action = bpy.data.actions[source_action]
    rig.animation_data_create()
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    idle = {b.name: b.matrix.copy() for b in rig.pose.bones}

    # 与战术冲刺同一发布口径：UE 待机带 12 mm 前移（弹鼓再加 20 mm），
    # 不在 M4_idle 里，需要补到左臂链上。
    if profile in ('Base', 'Drum'):
        shift = idle['WPN_root'].to_3x3() @ Vector((0, -0.032 if profile == 'Drum' else -0.012, 0))
        for n in names:
            ancestor = n
            while ancestor and ancestor != 'clavicle_l':
                ancestor = parent[ancestor]
            if ancestor or n == 'ik_hand_l':
                idle[n].translation += shift

    tree = ast.parse((S / 'DanWesson71520260913/author_weapon.py').read_text(encoding='utf-8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef)
                                 and n.name == 'hand_at'], type_ignores=[]), '<arm solver>', 'exec'))

    def weapon_delta(t, base):
        pivot = base['hand_r'].translation.copy()
        rotation = (Matrix.Rotation(math.radians(keyed(t, 'pitch')), 4, 'X')
                    @ Matrix.Rotation(math.radians(keyed(t, 'yaw')), 4, 'Z')
                    @ Matrix.Rotation(math.radians(keyed(t, 'roll')), 4, 'Y'))
        offset = Vector(keyed(t, 'offset'))
        return Matrix.Translation(pivot + offset) @ rotation @ Matrix.Translation(-pivot)

    def pose_quickcombat(t):
        pose = {n: idle[n].copy() for n in names}
        delta = weapon_delta(t, idle)
        for n in names:
            if n.startswith('WPN_'):
                pose[n] = delta @ idle[n]
        hand_at(pose, idle, 'r', delta @ idle['hand_r'])
        hand_at(pose, idle, 'l', delta @ idle['hand_l'])
        return pose

    frames = [i * (FRAME_HZ / SAMPLE_HZ) for i in range(int(round(DURATION * SAMPLE_HZ)) + 1)]
    rows, previous = [], {}
    for frame in frames:
        pose = pose_quickcombat(frame / FRAME_HZ)
        row = {}
        for n in names:
            basis = lr[n].inverted() @ (pose[parent[n]].inverted() @ pose[n] if parent[n] else pose[n])
            loc, q, sc = basis.decompose()
            if n in previous and previous[n].dot(q) < 0:
                q.negate()
            previous[n] = q.copy()
            row[n] = (loc, q, sc)
        rows.append(row)

    clip_action = bpy.data.actions.new('M4_QuickCombat_%s' % profile)
    clip_action.use_fake_user = True
    rig.animation_data.action = clip_action
    for n in names:
        bone = rig.pose.bones[n]
        bone.rotation_mode = 'QUATERNION'
        for prop in ('location', 'rotation_quaternion', 'scale'):
            bone.keyframe_insert(prop, frame=0)
    curves = {(c.data_path, c.array_index): c
              for c in clip_action.layers[0].strips[0].channelbag(clip_action.slots[0]).fcurves}
    for n in names:
        for prop, field, count in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
            for axis in range(count):
                curve = curves[(f'pose.bones["{n}"].{prop}', axis)]
                curve.keyframe_points.clear()
                curve.keyframe_points.add(len(frames))
                curve.keyframe_points.foreach_set(
                    'co', [v for f, row in zip(frames, rows) for v in (f, row[n][field][axis])])
                for key in curve.keyframe_points:
                    key.interpolation = 'LINEAR'
                curve.update()
    rig.animation_data.action_slot = clip_action.slots[0]
    scene.frame_start, scene.frame_end = 0, int(round(DURATION * FRAME_HZ))
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    fbx = dest / 'Animations' / ('A_M4_QuickCombat_%s.fbx' % profile)
    bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'ARMATURE'},
                             axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_step=.5,
                             bake_anim_simplify_factor=0)
    log('exported %s frames=%d' % (fbx.name, len(frames)))

    BUTT_GUN_LOCAL = Vector((0.0, 0.26, 0.0))   # 枪托底在枪局部空间的位置（+Y 为枪根向后）

    # 握把不变量自检：枪始终在双手里（与换弹 clip 同一约定）
    checks = []
    for t in MOTION['times']:
        scene.frame_set(int(round(t * FRAME_HZ)))
        bpy.context.view_layer.update()
        root = rig.pose.bones['WPN_root'].matrix
        wr = root.translation
        hr = rig.pose.bones['hand_r'].matrix.translation
        hl = rig.pose.bones['hand_l'].matrix.translation
        mz = rig.pose.bones['WPN_SOCKET_Muzzle'].matrix.translation
        butt = root @ BUTT_GUN_LOCAL
        checks.append({'t': t, 'd_right': round((wr - hr).length, 4), 'd_left': round((wr - hl).length, 4),
                       'muzzle': [round(v, 3) for v in mz], 'butt': [round(v, 3) for v in butt]})
        log('t=%.2f dR=%.4f dL=%.4f muzzle=(%.3f,%.3f,%.3f) butt=(%.3f,%.3f,%.3f)' % (
            t, (wr - hr).length, (wr - hl).length, mz.x, mz.y, mz.z, butt.x, butt.y, butt.z))

    bpy.ops.wm.save_as_mainfile(filepath=str(dest / ('M4_QuickCombat_%s_Editable.blend' % profile)))
    receipt['profiles'][profile] = {'source': source, 'source_action': source_action,
                                    'action': clip_action.name, 'fbx': str(fbx),
                                    'grip_invariant': checks}

(O / 'animation.json').write_text(json.dumps({
    'sample_rate': SAMPLE_HZ, 'clip': CLIP, 'duration': DURATION, 'contact': CONTACT,
    'motion': MOTION, 'space': receipt['coordinates'], 'convention': receipt['convention'],
    'destination': DESTINATION, 'profiles': sorted(receipt['profiles']),
    'testing': 'Not performed; user testing'}, indent=2), encoding='utf-8')
(O / 'authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
log('M4_QUICKCOMBAT_AUTHORED %s' % ','.join(profiles))
