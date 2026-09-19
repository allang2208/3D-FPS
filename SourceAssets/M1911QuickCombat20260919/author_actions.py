"""M1911 快速进战·握把砸击（2026-09-19）

照 DanWesson715QuickCombat20260918 的作者管线为 1911 出同语言 clip：
松握 → 右手持枪上提蓄势（枪口上仰）→ 斜下砸（握把底领先）→ 跟随回弹 → 左回握。
**动作表与 715 逐值相同**（0.55s、接触 0.26s），运行时 QuickCombatPistolMotion.h
的分段比例常量对两把枪同时成立。作者约定不变：持枪运动写在 WPN_root 上、
由枪带动右手（`hand_at(p, idle, 'r', G @ RIGHT_GRIP)`），左手同一解算器做
松握→下垂出镜→回握。全部逐帧 120 Hz 烘焙。

坐标（armature 空间，米）：-Y 前 / +Z 上 / +X 左（右肩在 -X 侧）。
基座是 M1911RearRain20260913 的 RearFinish 可编辑源（运行网格同源）。

2026-09-19 修订：1911 装配的臂架系与 715 相差 180°（枪口 +Y、右手 +X），
动作表里以臂架空间分量直用的量（left / pole_r / 躯干平移 gun*.25）必须经
ALIGN 共轭，否则左右/前后镜像——首版 clip 因此被用户判"动作语言不一致"。
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

DIR = Path(__file__).resolve().parent
SRC_BLEND = DIR.parent / 'M1911RearRain20260913' / 'M1911_RearFinish_Editable.blend'
OUT_BLEND = DIR / 'M1911_QuickCombat_Editable.blend'
DURATION = 0.55
FRAME_HZ = 60.0
SAMPLE_HZ = 120
CLIP = 'quickcombat'
DESTINATION = '/Game/Weapons/M1911/QuickCombat20260919/Animations'


def log(*args):
    print('[QC1911]', *args, flush=True)


# ---------------------------------------------------------------- 骨架与基准
bpy.ops.wm.open_mainfile(filepath=str(SRC_BLEND))
rig = bpy.data.objects['SK_M1911_Manny']
scene = bpy.context.scene
scene.render.fps = int(FRAME_HZ)
names = [b.name for b in rig.data.bones]
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
lr = {n: (rest[parent[n]].inverted() @ rest[n] if parent[n] else rest[n]) for n in names}
gunlocal = {n: rest['WPN_root'].inverted() @ rest[n] for n in names if n.startswith('WPN_')}


def sample_action(name, frame):
    act = bpy.data.actions[name]
    rig.animation_data_create()
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(int(round(frame)))
    bpy.context.view_layer.update()
    return {n: rig.pose.bones[n].matrix.copy() for n in names}


idle = sample_action('M1911_Contact_idle', 0)
# 基准必须是**运行时 idle**：M1911WeaponAssets::AnimationPath("idle") → Contact20260913/A_M1911_idle。
# 老一代 M1911_idle 的装配朝向差 180°（枪口 +Y/右手 +X）且枪收在胸口（wpn.y=+0.144），
# Contact idle 与 715 的 idle 在臂架空间逐位一致（枪口 -Y/右手 -X/枪前伸 wpn.y=-0.390）——
# 前两版拿老 idle 当基准，导致镜像(第一版)与 54cm 起手跳变(第二版)，这是"动作语言不一致"
# 与"还是不对"的真正根因。
RIGHT_GRIP = idle['WPN_root'].inverted() @ idle['hand_r']   # 右手相对枪根的握把关系
LEFT_GRIP = idle['WPN_root'].inverted() @ idle['hand_l']     # 左手支撑位（相对枪根）
log('idle sampled: hand_r=%s hand_l=%s wpn=%s' %
     (idle['hand_r'].translation.to_tuple(3), idle['hand_l'].translation.to_tuple(3),
      idle['WPN_root'].translation.to_tuple(3)))
# 枪根局部坐标系诊断：动作表要求局部 X=左 / Y=后 / Z=上（枪口在局部 -Y 侧）。
# 与 715 同约定才允许直接沿用同一张动作表；主轴不是 -Y 就停下来人工适配。
muzzle_local = (idle['WPN_root'].inverted() @ idle['WPN_SOCKET_Muzzle']).translation
_abs = (abs(muzzle_local.x), abs(muzzle_local.y), abs(muzzle_local.z))
dominant = ('x', 'y', 'z')[_abs.index(max(_abs))]
log('muzzle in WPN_root local: (%.3f, %.3f, %.3f) dominant=-%s' %
     (muzzle_local.x, muzzle_local.y, muzzle_local.z, dominant))
assert dominant == 'y' and muzzle_local.y < 0, \
    'WPN_root local convention mismatch: muzzle should sit on local -Y (got %s)' % (muzzle_local,)

# ---------------------------------------------------------------- 装配朝向对齐
# 动作表的"身体相对"正则系（715 装配）：-Y 前 / +Z 上 / +X 左。1911 的 Manny 装配
# 在它自己的臂架空间里整体朝向相反（枪口 +Y、右手在 +X，2026-09-19 实测差 180°）。
# 枪本体偏移/倾角在枪局部系合成，身体相对方向天然一致；但**以臂架空间分量直用的量
# （左手偏移 left / 肘极 pole_r / 躯干平移 gun*.25）必须共轭**，否则左右/前后镜像——
# 这就是首版"动作语言不一致"的根因（左手甩向枪口方向、抬肘方向反、重心前后反）。
forward = (idle['WPN_SOCKET_Muzzle'].translation - idle['WPN_root'].translation)
forward.z = 0.0
forward.normalize()                      # 本枪身体朝前方向（臂架空间）
canon_forward = Vector((0.0, -1.0, 0.0))  # 正则系身体朝前
align_yaw = math.degrees(math.atan2(
    canon_forward.x * forward.y - canon_forward.y * forward.x,
    canon_forward.x * forward.x + canon_forward.y * forward.y))
ALIGN = Matrix.Rotation(math.radians(align_yaw), 4, 'Z')   # 正则系 → 本枪臂架系
# 自检：对齐后右手必须落在正则系的 -X 侧（右肩在 -X），否则共轭方向反了。
hand_r_canon = ALIGN.inverted() @ idle['hand_r'].translation
log('assembly align yaw=%.1fdeg (canon->local), right hand canon x=%+.3f (expect <0)' %
     (align_yaw, hand_r_canon.x))
assert hand_r_canon.x < 0.02, \
    'assembly alignment wrong: right hand should sit on canon -X after alignment (got %s)' % (hand_r_canon.to_tuple(3),)


# ---------------------------------------------------------------- 解算器
def hand_at(p, old, side, H, pole_offset=None):
    """把 hand_<side>（含五指）放到 H，并用原骨长反解肩肘。pole_offset 抬起/压低肘部。

    与 DanWesson715QuickCombat20260918 的 `hand_at` 同构（那份又与各枪换弹源同构）。
    """
    hn = 'hand_' + side
    delta = H @ old[hn].inverted()
    for n in names:
        if n == hn or (n.endswith('_' + side) and n.startswith(('thumb', 'index', 'middle', 'ring', 'pinky'))):
            p[n] = delta @ old[n]
    un, fn = 'upperarm_' + side, 'lowerarm_' + side
    shoulder = old[un].translation.copy()
    elbow, wrist, target = old[fn].translation, old[hn].translation, H.translation.copy()
    l1 = (elbow - shoulder).length
    l2 = (wrist - elbow).length
    v = target - shoulder
    distance = v.length
    axis = v.normalized()
    reach = (l1 + l2) * .985
    if distance > reach:
        shoulder += axis * (distance - reach)
        distance = reach
    distance = max(abs(l1 - l2) + .0001, distance)
    pole = (elbow - old[un].translation).copy()
    if pole_offset is not None:
        pole += Vector(pole_offset)
    pole -= axis * pole.dot(axis)
    if pole.length < 1e-6:
        pole = Vector((0, 0, -1)) - axis * axis.dot(Vector((0, 0, -1)))
    pole.normalize()
    along = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
    e = shoulder + axis * along + pole * math.sqrt(max(0.0, l1 * l1 - along * along))
    p['clavicle_' + side] = old['clavicle_' + side].copy()
    p['clavicle_' + side].translation += shoulder - old[un].translation
    for n, pos, direction, was in [(un, shoulder, e - shoulder, elbow - old[un].translation),
                                   (fn, e, target - e, wrist - elbow)]:
        p[n] = Matrix.LocRotScale(pos, was.rotation_difference(direction) @ old[n].to_quaternion(),
                                  old[n].to_scale())
    for n in names:
        if n.endswith('_' + side) and n.startswith(('upperarm_twist', 'lowerarm_twist')):
            base = un if n.startswith('upperarm') else fn
            p[n] = p[base] @ old[base].inverted() @ old[n]
    if 'ik_hand_' + side in p:
        p['ik_hand_' + side] = H.copy()


def apply_scale(p, n, weight):
    """把该骨相对父级的基（basis）向静止姿态混合，用作「松握」。"""
    basis = lr[n].inverted() @ (p[parent[n]].inverted() @ p[n])
    loc, q, sc = basis.decompose()
    q = q.slerp(lr[n].to_quaternion(), weight)
    p[n] = p[parent[n]] @ lr[n] @ Matrix.LocRotScale(loc, q, sc)


# ---------------------------------------------------------------- 动作表
# 与 DanWesson715QuickCombat20260918/author_actions.py 逐值相同（两枪共用同一张表，
# 改节拍必须两边同步并复核 QuickCombatPistolMotion.h 的分段比例）。
# t 单位秒；局部轴 X=左 / Y=后 / Z=上（与枪根局部一致）。
MOTION = {
    'times': [0.00, 0.06, 0.18, 0.21, 0.26, 0.29, 0.40, 0.55],
    'tilt': [0.0, 24.0, 82.0, 82.0, 58.0, 58.0, 50.0, 0.0],      # 枪口上仰角（绕枪的 X 轴负转）
    'gun': [(0.0, 0.0, 0.0), (-0.03, -0.02, 0.03), (-0.07, 0.12, 0.26), (-0.07, 0.12, 0.26),
            (-0.01, -0.22, -0.07), (-0.01, -0.225, -0.075), (0.0, -0.28, -0.10), (0.0, 0.0, 0.0)],
    'left': [(0.0, 0.0, 0.0), (0.02, 0.02, -0.06), (0.07, 0.08, -0.26), (0.07, 0.08, -0.26),
             (0.07, 0.08, -0.25), (0.07, 0.08, -0.25), (0.07, 0.08, -0.24), (0.0, 0.0, 0.0)],
    'left_pitch': [0.0, 12.0, 35.0, 35.0, 35.0, 35.0, 33.0, 0.0],  # 左手随下垂的掌向下俯仰
    'relax': [0.0, 0.35, 0.85, 1.0, 1.0, 1.0, 1.0, 0.0],           # 松握混合权重
    'yaw': [0.0, 2.0, 8.0, 8.0, 11.0, 11.0, 8.0, 0.0],             # 躯干偏航（正=右肩前送）
    'pole_r': [(0.0, 0.0, 0.0), (-0.02, 0.02, 0.03), (-0.07, 0.03, 0.11), (-0.07, 0.03, 0.11),
               (0.02, -0.03, -0.05), (0.02, -0.03, -0.05), (0.03, -0.04, -0.06), (0.0, 0.0, 0.0)],
    'ease': ['smooth', 'smooth', 'decel', 'accel', 'linear', 'decel', 'smooth', 'smooth'],
}


def _ease(kind, u):
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
            u = _ease(MOTION['ease'][i], (t - times[i]) / max(1e-6, times[i + 1] - times[i]))
            a, b = values[i], values[i + 1]
            if isinstance(a, tuple):
                return tuple(a[k] + (b[k] - a[k]) * u for k in range(len(a)))
            return a + (b - a) * u
    return values[-1]


# ---------------------------------------------------------------- 姿态
def pose_quickcombat(t):
    p = {n: idle[n].copy() for n in names}
    gun = keyed(t, 'gun')
    yaw = keyed(t, 'yaw')
    # 躯干：小偏航（右肩前送）+ 枪位移的 25%（重心随动作前送/回收），整体施加到全身。
    # 偏航绕 Z 与装配朝向无关（两系同轴，身体相对意义一致）；平移分量是正则系量，需共轭。
    body = Matrix.Rotation(math.radians(yaw), 4, 'Z') @ Matrix.Translation(ALIGN @ (Vector(gun) * .25))
    for n in names:
        p[n] = body @ p[n]
    # 枪根：局部偏移 + 枪口上仰（绕枪自身 X 轴负转）
    tilt = keyed(t, 'tilt')
    G = p['WPN_root'] @ Matrix.LocRotScale(Vector(gun), Matrix.Rotation(-math.radians(tilt), 3, 'X'),
                                           Vector((1, 1, 1)))
    p['WPN_root'] = G
    for n, L in gunlocal.items():
        if n != 'WPN_root':
            p[n] = G @ L
    # 右手：握把关系不变（枪带动手）；肘极做抬肘/压肘（表值是正则系量，共轭到本枪臂架系）
    hand_at(p, idle, 'r', G @ RIGHT_GRIP, ALIGN @ Vector(keyed(t, 'pole_r')))
    # 左手：0–0.06s 仍挂在枪上，之后锚定在空间里下垂（下垂偏移是正则系量，共轭）
    left = ALIGN @ Vector(keyed(t, 'left'))
    attach = max(0.0, min(1.0, t / 0.06))
    anchor = G @ LEFT_GRIP
    hand_rot = idle['hand_l'].to_quaternion() @ Matrix.Rotation(-math.radians(keyed(t, 'left_pitch')), 3, 'X').to_quaternion()
    H = Matrix.LocRotScale(anchor.translation.lerp(idle['hand_l'].translation, attach) + left,
                           hand_rot, Vector((1, 1, 1)))
    hand_at(p, idle, 'l', H)
    # 左手指松握（向左手指静止姿态混合）
    relax = keyed(t, 'relax')
    if relax > 0.001:
        for n in names:
            if n.endswith('_l') and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
                apply_scale(p, n, relax * 0.45)
    return p


# ---------------------------------------------------------------- 烘焙与导出
(DIR / 'Animations').mkdir(exist_ok=True)
frames = [i * (FRAME_HZ / SAMPLE_HZ) for i in range(int(round(DURATION * SAMPLE_HZ)) + 1)]
samples, previous = [], {}
for f in frames:
    p = pose_quickcombat(f / FRAME_HZ)
    row = {}
    for n in names:
        basis = lr[n].inverted() @ (p[parent[n]].inverted_safe() @ p[n] if parent[n] else p[n])
        loc, q, sc = basis.decompose()
        if n in previous and previous[n].dot(q) < 0:
            q.negate()
        previous[n] = q.copy()
        row[n] = (loc, q, sc)
    samples.append(row)

action = bpy.data.actions.new('M1911_' + CLIP)
action.use_fake_user = True
rig.animation_data_create()
rig.animation_data.action = action
for n in names:
    b = rig.pose.bones[n]
    b.rotation_mode = 'QUATERNION'
    for prop in ['location', 'rotation_quaternion', 'scale']:
        b.keyframe_insert(prop, frame=0)
curves = {(c.data_path, c.array_index): c for c in action.layers[0].strips[0].channelbag(action.slots[0]).fcurves}
for n in names:
    for prop, field, count in [('location', 0, 3), ('rotation_quaternion', 1, 4), ('scale', 2, 3)]:
        for axis in range(count):
            c = curves[(f'pose.bones["{n}"].{prop}', axis)]
            c.keyframe_points.clear()
            c.keyframe_points.add(len(frames))
            c.keyframe_points.foreach_set('co', [v for f, row in zip(frames, samples) for v in (f, row[n][field][axis])])
            for key in c.keyframe_points:
                key.interpolation = 'LINEAR'
            c.update()
rig.animation_data.action_slot = action.slots[0]
scene.frame_start = 0
scene.frame_end = int(round(DURATION * FRAME_HZ))
scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=str(DIR / 'Animations' / ('A_M1911_' + CLIP + '.fbx')),
                         use_selection=True, object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z',
                         add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
                         bake_anim_use_nla_strips=False, bake_anim_step=.5, bake_anim_simplify_factor=0)
log('exported A_M1911_%s.fbx frames=%d' % (CLIP, len(frames)))

(DIR / 'animation.json').write_text(json.dumps({
    'sample_rate': SAMPLE_HZ,
    'clip': CLIP,
    'duration': DURATION,
    'contact': 0.26,
    'motion': MOTION,
    'space': 'armature: -Y forward / +Z up / +X left; gun-local offsets (X left, Y back, Z up)',
    'convention': 'WPN_root drives the right hand through the fixed grip relation (same as reload clips); motion table identical to DanWesson715QuickCombat20260918',
    'destination': DESTINATION,
    'testing': 'Not performed; user testing',
}, indent=2), encoding='utf-8')

# 关键帧读数自检（不含渲染）：|WPN_root − hand_r| 全程恒定 = 枪不跟手在作者源层面不可能出现
bpy.context.view_layer.update()
for t in MOTION['times']:
    scene.frame_set(int(round(t * FRAME_HZ)))
    bpy.context.view_layer.update()
    wr = rig.pose.bones['WPN_root'].matrix.translation
    hr = rig.pose.bones['hand_r'].matrix.translation
    hl = rig.pose.bones['hand_l'].matrix.translation
    mz = rig.pose.bones['WPN_SOCKET_Muzzle'].matrix.translation
    log('t=%.2f gun=(%.3f,%.3f,%.3f) muzzle=(%.3f,%.3f,%.3f) handR=(%.3f,%.3f,%.3f) handL=(%.3f,%.3f,%.3f) dR=%.3f dL=%.3f'
        % (t, wr.x, wr.y, wr.z, mz.x, mz.y, mz.z, hr.x, hr.y, hr.z, hl.x, hl.y, hl.z,
           (wr - hr).length, (wr - hl).length))

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
log('M1911_QUICKCOMBAT_AUTHORING_COMPLETE')
