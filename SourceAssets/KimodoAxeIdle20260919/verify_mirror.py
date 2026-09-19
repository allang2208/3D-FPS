"""Verify the left-hand mirror math on the real ready pose before rebuilding.

Blender --background --python <this> -- <blend>
Read-only checks: the mirrored right-hand pose must land symmetrically across the plane that
contains the handle axis and passes through the grip point.
"""
import bpy
import sys
from math import isclose
from pathlib import Path
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(args[0])))
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions['A_Harvest_Axe_Idle']
scene.frame_set(0)
bpy.context.view_layer.update()

wpn = rig.pose.bones['WPN_root'].matrix.copy()
hand_r = rig.pose.bones['hand_r'].matrix.copy()
grip = wpn.to_translation()
axis = (wpn.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
to_hand = hand_r.to_translation() - grip
perp = to_hand - axis * to_hand.dot(axis)
normal = perp.normalized()
print('grip', [round(v, 4) for v in grip])
print('axis', [round(v, 4) for v in axis])
print('hand_r', [round(v, 4) for v in hand_r.to_translation()])
print('perp_dist', round(perp.length, 4))

# Reflection across the plane through `grip` with normal `normal`.
reflection = Matrix.Identity(4)
for row in range(3):
    for column in range(3):
        reflection[row][column] -= 2.0 * normal[row] * normal[column]
reflection.translation = 2.0 * normal * normal.dot(grip)
mirrored_point = reflection @ hand_r.to_translation()
print('mirrored_hand_r', [round(v, 4) for v in mirrored_point])
delta = mirrored_point - grip
m_along = delta.dot(axis)
m_perp = (delta - axis * m_along).length
print('mirrored along', round(m_along, 4), 'perp', round(m_perp, 4), '(expect ~0.0 and ~0.0784)')
print('reflection self-inverse:', (reflection @ reflection - Matrix.Identity(4)).median_scale if hasattr(reflection @ reflection - Matrix.Identity(4), 'median_scale') else 'n/a')
diff = reflection @ reflection - Matrix.Identity(4)
print('R@R - I max abs:', max(abs(diff[r][c]) for r in range(4) for c in range(4)))

# Mirror a full pose: M' = R M R must map mirrored local points to mirrored world points.
mirrored_pose = reflection @ hand_r @ reflection
probe_local = Vector((0.0, 0.05, 0.0))          # a point 5 cm up the hand's local Y
world = hand_r @ probe_local
mirrored_world = reflection @ world
via_pose = mirrored_pose @ (reflection @ probe_local)[:3] if False else mirrored_pose @ (reflection.to_3x3() @ probe_local)
print('pose consistency err:', round((mirrored_world - via_pose).length, 6))
print('MIRROR_CHECK_DONE')