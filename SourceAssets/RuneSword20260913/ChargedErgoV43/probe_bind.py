"""Check whether the arms mesh data matches the armature rest pose."""
import bpy
import numpy as np
from pathlib import Path

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']

print('arms object matrix_world:', [round(v, 5) for row in arms.matrix_world for v in row])
print('arms scale:', list(arms.scale), 'rig scale:', list(rig.scale))
print('arms parent:', arms.parent.name if arms.parent else None)
print('vertex count data/evaluated:', len(arms.data.vertices))

rest = np.array([v.co for v in arms.data.vertices], dtype=np.float64)
edges = np.array([tuple(e.vertices) for e in arms.data.edges], dtype=np.int64)
mask = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1) > 1e-6
edges = edges[mask]
rest_len = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)


def evaluated_ratio(label):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = arms.evaluated_get(depsgraph)
    co = np.array([v.co for v in evaluated.data.vertices], dtype=np.float64)
    current = np.linalg.norm(co[edges[:, 0]] - co[edges[:, 1]], axis=1)
    ratio = current / rest_len
    print('%-22s edges=%d  min=%.4f  mean=%.4f  p99=%.4f  max=%.4f'
          % (label, len(ratio), ratio.min(), ratio.mean(),
             np.quantile(ratio, .99), ratio.max()))
    return ratio


rig.data.pose_position = 'REST'
scene.frame_set(0)
bpy.context.view_layer.update()
evaluated_ratio('armature REST')

rig.data.pose_position = 'POSE'
action = bpy.data.actions['A_RuneSword_HeavyCharge']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()
evaluated_ratio('HeavyCharge f0')
scene.frame_set(168)  # 0.35 s
bpy.context.view_layer.update()
evaluated_ratio('HeavyCharge 350ms')
scene.frame_set(960)
bpy.context.view_layer.update()
evaluated_ratio('HeavyCharge 2000ms')

# Reference: an unmodified copy of the mesh (no armature) must give ratio 1.
copy = arms.copy()
copy.data = arms.data.copy()
copy.modifiers.clear()
scene.collection.objects.link(copy)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()
co = np.array([v.co for v in copy.evaluated_get(depsgraph).data.vertices], dtype=np.float64)
current = np.linalg.norm(co[edges[:, 0]] - co[edges[:, 1]], axis=1)
print('no-armature copy ratio min=%.6f mean=%.6f max=%.6f'
      % ((current / rest_len).min(), (current / rest_len).mean(), (current / rest_len).max()))
print('PROBE_BIND_DONE', flush=True)
