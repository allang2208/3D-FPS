"""M4 枪托砸击：作者源结构探明（只读，不改源文件）。

输出：物体、骨架骨名分组、动作清单与时长、WPN_ 骨、待机动作的握把关系读数。
"""
import bpy
from pathlib import Path

DIR = Path(__file__).resolve().parent
SRC = DIR.parent / 'M4TacticalToss20260910' / 'M4_Hand_MAT_Editable.blend'

bpy.ops.wm.open_mainfile(filepath=str(SRC))

print('[INSPECT] file=%s' % SRC, flush=True)
print('[INSPECT] objects=%s' % [(o.name, o.type) for o in bpy.data.objects], flush=True)
print('[INSPECT] armatures=%s' % [o.name for o in bpy.data.objects if o.type == 'ARMATURE'], flush=True)

for ob in [o for o in bpy.data.objects if o.type == 'ARMATURE']:
    bones = [b.name for b in ob.data.bones]
    wpn = [b for b in bones if b.startswith('WPN_')]
    print('[INSPECT] rig=%s bones=%d wpn=%s' % (ob.name, len(bones), wpn), flush=True)
    print('[INSPECT] rig=%s key_bones=%s' % (
        ob.name, [b for b in bones if b in ('root', 'pelvis', 'spine_03', 'clavicle_l', 'clavicle_r',
                                            'hand_l', 'hand_r', 'head') or b.startswith(('upperarm_', 'lowerarm_'))]),
        flush=True)
    print('[INSPECT] rig=%s finger_head=%s' % (
        ob.name, [b for b in bones if b.split('_')[0] in ('thumb', 'index', 'middle', 'ring', 'pinky')
                  and b.rsplit('_', 1)[-1] in ('l', 'r')][:24]), flush=True)

for act in sorted(bpy.data.actions, key=lambda a: a.name):
    try:
        span = act.frame_range
    except Exception:
        span = None
    print('[INSPECT] action=%s range=%s users=%d fake=%s' % (
        act.name, tuple(round(v, 2) for v in span) if span else None, act.users, act.use_fake_user), flush=True)

scene = bpy.context.scene
print('[INSPECT] fps=%s frame_start=%s frame_end=%s' % (scene.render.fps, scene.frame_start, scene.frame_end), flush=True)
