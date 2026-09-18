"""M4 枪托砸击：读待机帧的枪根局部坐标系、握把关系与枪口/枪托位置。

只读，不改源文件。
"""
import bpy
from pathlib import Path
from mathutils import Vector

DIR = Path(__file__).resolve().parent
SRC = DIR.parent / 'M4TacticalToss20260910' / 'M4_Hand_MAT_Editable.blend'

bpy.ops.wm.open_mainfile(filepath=str(SRC))
rig = bpy.data.objects['SK_M4_Infima']
scene = bpy.context.scene


def sample(action_name, frame):
    act = bpy.data.actions[action_name]
    rig.animation_data_create()
    rig.animation_data.action = act
    rig.animation_data.action_slot = act.slots[0]
    scene.frame_set(int(frame))
    bpy.context.view_layer.update()
    return {b.name: rig.pose.bones[b.name].matrix.copy() for b in rig.pose.bones}


idle = sample('M4_idle', 0)
w = idle['WPN_root']
print('[GRIP] rig bones=%d' % len(rig.pose.bones), flush=True)
print('[GRIP] WPN_root translation=%s' % (w.translation.to_tuple(3),), flush=True)
for axis, vec in (('X', w.col[0].xyz), ('Y', w.col[1].xyz), ('Z', w.col[2].xyz)):
    print('[GRIP] WPN_root local %s -> armature %s' % (axis, tuple(round(v, 3) for v in vec)), flush=True)

for n in ('hand_r', 'hand_l', 'lowerarm_r', 'lowerarm_l', 'upperarm_r', 'upperarm_l', 'clavicle_r', 'clavicle_l'):
    print('[GRIP] %s armature=%s' % (n, tuple(round(v, 4) for v in idle[n].translation)), flush=True)

print('[GRIP] hand_r in gun space = %s' % (tuple(round(v, 4) for v in (w.inverted() @ idle['hand_r']).translation),), flush=True)
print('[GRIP] hand_l in gun space = %s' % (tuple(round(v, 4) for v in (w.inverted() @ idle['hand_l']).translation),), flush=True)

for n in ('WPN_SOCKET_Muzzle', 'WPN_SOCKET_Eject', 'WPN_SOCKET_Magazine', 'WPN_Trigger', 'WPN_RearSight', 'WPN_FrontSight'):
    if n in idle:
        local = (w.inverted() @ idle[n]).translation
        print('[GRIP] %s in gun space = %s  dist=%.4f' % (n, tuple(round(v, 4) for v in local), local.length), flush=True)

print('[GRIP] armature object matrix=%s' % (tuple(round(v, 3) for v in rig.matrix_world.translation),), flush=True)
