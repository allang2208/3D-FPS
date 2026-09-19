"""诊断"还是不对"：
1) 1911 的老 idle(M1911_idle) vs 运行时 idle(M1911_Contact_idle) 差多少——QC 基准是否取错代;
2) 715 的 QC 基座 idle(PalmClearance 源 DW715_idle) vs 运行时 idle(Upgrade 源 DW715_idle) 是否一致;
3) "直接复用"实测：把 715 的 DW715_quickcombat action 按骨名搬到 1911 rig 上，看枪/手落到哪。
"""
import bpy, math
from mathutils import Vector

FRAME_HZ = 60.0


def log(*args):
    print('[DIAG]', *args, flush=True)


def sample(rig, scene, action_name, t=0.0):
    act = bpy.data.actions[action_name]
    rig.animation_data_create()
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(int(round(t * FRAME_HZ)))
    bpy.context.view_layer.update()
    g = lambda b: rig.pose.bones[b].matrix
    return (g('WPN_root').translation.copy(), g('WPN_SOCKET_Muzzle').translation.copy(),
            g('hand_r').translation.copy(), g('hand_l').translation.copy())


def show(tag, w, m, r, l):
    log('%s wpn=(%.3f,%.3f,%.3f) muzzle=(%.3f,%.3f,%.3f) handR=(%.3f,%.3f,%.3f) handL=(%.3f,%.3f,%.3f)'
        % (tag, w.x, w.y, w.z, m.x, m.y, m.z, r.x, r.y, r.z, l.x, l.y, l.z))


# ---- 1) 1911：老 idle vs Contact idle（运行时） ----
bpy.ops.wm.open_mainfile(filepath=r'D:\FPS3D\FPSGAME\SourceAssets\M1911RearRain20260913\M1911_RearFinish_Editable.blend')
rig = bpy.data.objects['SK_M1911_Manny']
scene = bpy.context.scene
scene.render.fps = 60
poses = {}
for name in ('M1911_idle', 'M1911_Contact_idle', 'M1911_P9_idle'):
    if name in bpy.data.actions:
        poses[name] = sample(rig, scene, name)
        show(name, *poses[name])
a, b = poses.get('M1911_idle'), poses.get('M1911_Contact_idle')
if a and b:
    log('M1911_idle − Contact_idle（运行时基准差）: dwpn=%.3f dmuzzle=%.3f dhandR=%.3f dhandL=%.3f'
        % ((a[0]-b[0]).length, (a[1]-b[1]).length, (a[2]-b[2]).length, (a[3]-b[3]).length))

# ---- 2) 715：PalmClearance 源 idle vs Upgrade 源 idle ----
bpy.ops.wm.open_mainfile(filepath=r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715Upgrade20260914\DanWesson715_Upgrade_Editable.blend')
rig7 = bpy.data.objects['SK_DW715_Manny']
up = sample(rig7, scene, 'DW715_idle')
show('715 Upgrade idle(运行时)', *up)
bpy.ops.wm.open_mainfile(filepath=r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715PalmClearance20260915\DanWesson715_PalmClearance_Editable.blend')
pc = sample(bpy.data.objects['SK_DW715_Manny'], scene, 'DW715_idle')
show('715 PalmClearance idle(QC基座)', *pc)
log('715 两代 idle 差: dwpn=%.3f dmuzzle=%.3f dhandR=%.3f dhandL=%.3f'
    % ((up[0]-pc[0]).length, (up[1]-pc[1]).length, (up[2]-pc[2]).length, (up[3]-pc[3]).length))

# ---- 3) 直接复用实测：把 715 的 quickcombat 搬到 1911 rig ----
bpy.ops.wm.open_mainfile(filepath=r'D:\FPS3D\FPSGAME\SourceAssets\M1911RearRain20260913\M1911_RearFinish_Editable.blend')
rig = bpy.data.objects['SK_M1911_Manny']
with bpy.data.libraries.load(r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715QuickCombat20260918\DanWesson715_QuickCombat_Editable.blend', link=False) as (src, _):
    src_actions = [a for a in src.actions if a == 'DW715_quickcombat']
bpy.ops.wm.append(
    filepath=r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715QuickCombat20260918\DanWesson715_QuickCombat_Editable.blend\Action/DW715_quickcombat',
    directory=r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715QuickCombat20260918\DanWesson715_QuickCombat_Editable.blend\Action',
    filename='DW715_quickcombat')
act = bpy.data.actions.get('DW715_quickcombat')
assert act, 'append failed'
contact = poses['M1911_Contact_idle'] if 'M1911_Contact_idle' in bpy.data.actions else None
for t in (0.0, 0.18, 0.26, 0.55):
    w, m, r, l = sample(rig, scene, 'DW715_quickcombat', t)
    show('1911rig←715clip t=%.2f' % t, w, m, r, l)
    if contact and t == 0.0:
        log('与运行时 idle(Contact) 的落点差: dwpn=%.3f dmuzzle=%.3f dhandR=%.3f dhandL=%.3f'
            % ((w-contact[0]).length, (m-contact[1]).length, (r-contact[2]).length, (l-contact[3]).length))
log('DIAG_DONE')
