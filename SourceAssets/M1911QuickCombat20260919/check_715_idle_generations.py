"""715 自身抽查：PalmClearance 源 DW715_idle（QC 基座）vs Upgrade 源 DW715_idle（运行时 idle）。"""
import bpy

FRAME_HZ = 60.0


def log(*args):
    print('[CK715]', *args, flush=True)


def sample(path, rig_name):
    bpy.ops.wm.open_mainfile(filepath=path)
    rig = bpy.data.objects[rig_name]
    scene = bpy.context.scene
    scene.render.fps = 60
    act = bpy.data.actions['DW715_idle']
    rig.animation_data_create()
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(0)
    bpy.context.view_layer.update()
    g = lambda b: rig.pose.bones[b].matrix.translation.copy()
    return g('WPN_root'), g('hand_r'), g('hand_l')


a = sample(r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715Upgrade20260914\DanWesson715_Upgrade_Editable.blend', 'SK_DW715_Manny')
log('Upgrade(运行时)   wpn=(%.3f,%.3f,%.3f) handR=(%.3f,%.3f,%.3f) handL=(%.3f,%.3f,%.3f)'
    % (a[0].x, a[0].y, a[0].z, a[1].x, a[1].y, a[1].z, a[2].x, a[2].y, a[2].z))
b = sample(r'D:\FPS3D\FPSGAME\SourceAssets\DanWesson715PalmClearance20260915\DanWesson715_PalmClearance_Editable.blend', 'SK_DW715_Manny')
log('PalmClearance(QC基座) wpn=(%.3f,%.3f,%.3f) handR=(%.3f,%.3f,%.3f) handL=(%.3f,%.3f,%.3f)'
    % (b[0].x, b[0].y, b[0].z, b[1].x, b[1].y, b[1].z, b[2].x, b[2].y, b[2].z))
log('两代差: dwpn=%.4f dhandR=%.4f dhandL=%.4f'
    % ((a[0]-b[0]).length, (a[1]-b[1]).length, (a[2]-b[2]).length))
log('CK715_DONE')
