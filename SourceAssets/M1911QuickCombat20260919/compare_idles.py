"""对比 715 与 1911 的 idle 基准与已烘焙砸击 clip 的绝对轨迹，量化动作语言差异。

同一 Blender 会话内先后打开两份可编辑源（mathutils 拷贝跨文件存活），
在 8 个关键时间点采样 WPN_root 的绝对位姿与手部位置，输出两枪差值。
"""
import bpy, math
from mathutils import Matrix, Vector

SEVEN15 = r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715QuickCombat20260918\DanWesson715_QuickCombat_Editable.blend'
M1911 = r'D:\FPS3D\FPSGAME\SourceAssets\M1911QuickCombat20260919\M1911_QuickCombat_Editable.blend'
TIMES = [0.00, 0.06, 0.18, 0.21, 0.26, 0.29, 0.40, 0.55]
FRAME_HZ = 60.0


def log(*args):
    print('[CMP]', *args, flush=True)


def sample(rig, scene, action_name, t):
    act = bpy.data.actions[action_name]
    rig.animation_data_create()
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(int(round(t * FRAME_HZ)))
    bpy.context.view_layer.update()
    wpn = rig.pose.bones['WPN_root'].matrix.copy()
    mz = rig.pose.bones['WPN_SOCKET_Muzzle'].matrix.translation.copy()
    hr = rig.pose.bones['hand_r'].matrix.translation.copy()
    hl = rig.pose.bones['hand_l'].matrix.translation.copy()
    el = rig.pose.bones['lowerarm_r'].matrix.translation.copy()
    return wpn, mz, hr, hl, el


def dump(tag, path, idle_action, clip_action):
    bpy.ops.wm.open_mainfile(filepath=path)
    rig = bpy.data.objects['SK_DW715_Manny' if '715' in tag else 'SK_M1911_Manny']
    scene = bpy.context.scene
    scene.render.fps = 60
    wpn, mz, hr, hl, el = sample(rig, scene, idle_action, 0.0)
    e = wpn.to_euler('XYZ')
    log('%s idle: wpn_pos=(%.3f,%.3f,%.3f) wpn_euler=(%.1f,%.1f,%.1f)deg' %
        (tag, wpn.translation.x, wpn.translation.y, wpn.translation.z,
         math.degrees(e.x), math.degrees(e.y), math.degrees(e.z)))
    log('%s idle: muzzle=(%.3f,%.3f,%.3f) hand_r=(%.3f,%.3f,%.3f) hand_l=(%.3f,%.3f,%.3f)' %
        (tag, mz.x, mz.y, mz.z, hr.x, hr.y, hr.z, hl.x, hl.y, hl.z))
    out = {}
    for t in TIMES:
        w, m, r, l, e = sample(rig, scene, clip_action, t)
        out[t] = (w, m, r, l, e)
    return out


a = dump('715', SEVEN15, 'DW715_idle', 'DW715_quickcombat')
b = dump('1911', M1911, 'M1911_idle', 'M1911_quickcombat')

# 1911 装配相对 715 绕 Z 翻转 180°：把 1911 的采样转回 715 的正则系再比，
# 差值才是"动作语言"差异（不含装配朝向差与各枪自己的 idle 框架差）。
fa = (a[0.0][1] - a[0.0][0].translation).normalized()   # 715 idle 枪口方向
fb = (b[0.0][1] - b[0.0][0].translation).normalized()   # 1911 idle 枪口方向
angle = math.degrees(fa.xy.angle(fb.xy)) if fa.xy.length > 1e-6 and fb.xy.length > 1e-6 else 0.0
ALIGN = Matrix.Rotation(math.radians(angle), 4, 'Z') if fa.xy.dot(fb.xy) < 0 else Matrix.Identity(4)
log('idle 枪口方向: 715=%s 1911=%s → 对齐角=%.1f°' % (fa.to_tuple(2), fb.to_tuple(2), angle))

log('--- 动作增量差（715 Δ − 1911 Δ，正则系，米）---')
inv = ALIGN.inverted()
# delta = t 时刻位置 − 各自 idle 位置（正则系）。两枪 idle 框架差异被消掉，
# delta 之差 = 纯动作语言差异；验收线：全时段 < ~3cm（枪/左手/肘）。
ga, ma_, ra_, la_, ea_ = a[0.0]
gb_, mb_, rb_, lb_, eb_ = b[0.0]
gb = inv @ gb_
lb, eb = inv @ lb_, inv @ eb_
for t in TIMES:
    wa, mz_a, hr_a, hl_a, el_a = a[t]
    wb, mz_b, hr_b, hl_b, el_b = b[t]
    wb, hl_b, el_b = inv @ wb, inv @ hl_b, inv @ el_b
    d_gun = (wa.translation - ga.translation) - (wb.translation - gb.translation)
    d_handL = (hl_a - la_) - (hl_b - lb)
    d_elbow = (el_a - ea_) - (el_b - eb)
    log('t=%.2f dΔgun=(%+.3f,%+.3f,%+.3f) |%.3f | dΔhandL=%.3f dΔelbow=%.3f'
        % (t, d_gun.x, d_gun.y, d_gun.z, d_gun.length, d_handL.length, d_elbow.length))
log('COMPARE_DONE')
