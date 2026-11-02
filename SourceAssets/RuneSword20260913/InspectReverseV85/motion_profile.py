"""Per-frame motion profile of an Inspect (blend or FBX): sword / hand / forearm angular speed and hand speed.

blender -b --factory-startup --python motion_profile.py -- <blend|fbx> <out.json>
World-space (armature object applied), so blends and FBX imports compare directly.
"""
import json
import math
import sys
from pathlib import Path

import bpy

argv = sys.argv[sys.argv.index('--') + 1:]
src = argv[0]
if src.lower().endswith('.fbx'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=src)
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
else:
    bpy.ops.wm.open_mainfile(filepath=src)
    rig = bpy.data.objects['SK_RuneSword_Rig']
s = bpy.context.scene
act = rig.animation_data.action
first, last = int(act.frame_range[0]), int(act.frame_range[1])
fps = s.render.fps / s.render.fps_base
ROT = ('WPN_root', 'hand_r', 'lowerarm_r', 'upperarm_r', 'hand_l')
POS = ('WPN_root', 'hand_r', 'hand_l', 'lowerarm_r')
mats = {n: [] for n in set(ROT) | set(POS)}
for f in range(first, last + 1):
    s.frame_set(f)
    for n in mats:
        mats[n].append(rig.matrix_world @ rig.pose.bones[n].matrix)
out = {'src': src, 'fps': fps, 'frames': last - first + 1, 't': [i / fps for i in range(last - first + 1)]}
for n in ROT:
    sp = [0.0]
    for a, b in zip(mats[n], mats[n][1:]):
        d = a.to_quaternion().rotation_difference(b.to_quaternion()).angle * 57.29578
        sp.append(min(d, 360.0 - d) * fps)
    out[n + '_deg_s'] = sp
for n in POS:
    sp = [0.0]
    for a, b in zip(mats[n], mats[n][1:]):
        sp.append((b.translation - a.translation).length * fps)
    out[n + '_m_s'] = sp
    out[n + '_pos'] = [tuple(round(v, 5) for v in m.translation) for m in mats[n]]
# Blade line as the eye reads it: the WPN_root local axis that points up at the idle frame (bone axes differ between
# a blend and an FBX import), and its on-screen angle (view +Y, so screen = X/Z). The guard roll about the blade
# axis adds to the bone's angular speed but barely moves the blade line.
from mathutils import Vector  # noqa: E402
m0 = mats['WPN_root'][0].to_3x3().normalized()
blade_local = max((Vector(v) for v in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))),
                  key=lambda v: (m0 @ v).z)
dirs = [(m.to_3x3().normalized() @ blade_local).normalized() for m in mats['WPN_root']]
line, scr = [0.0], [0.0]
for a, b in zip(dirs, dirs[1:]):
    line.append(math.degrees(a.angle(b, 0.0)) * fps)
    d = math.degrees(math.atan2(b.z, b.x) - math.atan2(a.z, a.x))
    scr.append(((d + 180.0) % 360.0 - 180.0) * fps)
out['blade_line_deg_s'] = line
out['blade_screen_deg_s'] = scr
# Accumulated sword turn (deg) for the clock shape.
acc, tot = [0.0], 0.0
for v in out['WPN_root_deg_s'][1:]:
    tot += v / fps
    acc.append(tot)
out['WPN_root_turn_deg'] = acc
Path(argv[1]).write_text(json.dumps(out))
print('PROFILE', src, out['frames'], round(tot, 1))
