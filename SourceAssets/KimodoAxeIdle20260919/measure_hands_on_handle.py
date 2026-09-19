"""Measure how well each hand sits on the axe handle in the built two-hand idle.

Blender --background --python <this> -- <blend> <action_name>
Read-only: for every frame, distance from each hand bone to the handle centreline.
"""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(args[0])))
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
name = args[1] if len(args) > 1 else 'A_Harvest_Axe_Idle2H'
rig.animation_data.action = bpy.data.actions[name]

def hand_axis_distance(bone_name, frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    wpn = rig.pose.bones['WPN_root'].matrix
    origin = wpn.to_translation()
    axis = (wpn.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    hand = rig.pose.bones[bone_name].matrix.to_translation()
    delta = hand - origin
    along = delta.dot(axis)
    perp = (delta - axis * along).length
    return along, perp

print('frame   hand_r(along,perp)      hand_l(along,perp)')
rows = []
for frame in range(0, scene.frame_end + 1, 50):
    r = hand_axis_distance('hand_r', frame)
    l = hand_axis_distance('hand_l', frame)
    rows.append((frame, r, l))
    print(f'{frame:5d}   ({r[0]:+.3f}, {r[1]:.3f})       ({l[0]:+.3f}, {l[1]:.3f})')

# Fingertip check: the middle finger tip should be roughly one palm-width from the axis.
def tip_distance(bone_name, frame):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    wpn = rig.pose.bones['WPN_root'].matrix
    origin = wpn.to_translation()
    axis = (wpn.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    tip = rig.pose.bones[bone_name].matrix @ Vector((0.0, rig.pose.bones[bone_name].length, 0.0))
    delta = tip - origin
    along = delta.dot(axis)
    return along, (delta - axis * along).length

scene.frame_set(0)
bpy.context.view_layer.update()
for bone in ['middle_03_r', 'middle_03_l', 'thumb_03_r', 'thumb_03_l']:
    along, perp = tip_distance(bone, 0)
    print(f'{bone:14s} tip along {along:+.3f} perp {perp:.3f}')
print('HAND_AXIS_CHECK_DONE')