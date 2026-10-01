"""Blender (background): seated (ASH12_idle frame 0) offsets of every weapon bone relative
to WPN_root, in the root's rest (bind) space. Read-only; writes Bake/seated_pose.json.

blender -b <A762_AccessoryReady_Editable.blend> -P probe_seated_pose.py

The runtime mesh stores bind-pose vertices; parts bound to a bone other than WPN_root
(magazine, bolt, ...) render at  D_bone @ v  relative to the receiver, where
D_bone = (P_root R_root^-1)^-1 (P_bone R_bone^-1). Coordinates: Blender armature metres;
UE mesh cm = (100x, -100y, 100z).
"""
import json
from pathlib import Path
import bpy

HERE = Path(__file__).parent
r = bpy.data.objects['SK_M4_Infima']
r.animation_data.action = bpy.data.actions['ASH12_idle']
r.animation_data.action_slot = r.animation_data.action.slots[0]
r.data.pose_position = 'POSE'
bpy.context.scene.frame_set(0)
bpy.context.view_layer.update()


def delta(bone):
    return r.pose.bones[bone].matrix @ r.data.bones[bone].matrix_local.inverted()


root = delta('WPN_root')
out = {'action': 'ASH12_idle', 'frame': 0, 'bones': {}, 'objects': {}}
for b in r.data.bones:
    if not b.name.startswith('WPN'):
        continue
    d = root.inverted() @ delta(b.name)
    out['bones'][b.name] = [list(row) for row in d]
    t = d.translation
    moved = abs(t.x) + abs(t.y) + abs(t.z) > 1e-5 or any(abs(d[i][j] - (i == j)) > 1e-5 for i in range(3) for j in range(3))
    if moved:
        print('SEATED', b.name, 'translation_cm', [round(t.x * 100, 3), round(-t.y * 100, 3), round(t.z * 100, 3)], flush=True)
(HERE / 'Bake' / 'seated_pose.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print('ASH12_SEATED_POSE_WRITTEN',flush=True)
