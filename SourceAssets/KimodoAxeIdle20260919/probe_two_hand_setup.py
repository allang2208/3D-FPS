"""Probe the viewmodel authoring scene for the two-handed idle build.

Blender --background --python <this> -- <blend> <kimodo.glb> <out.json>
Read-only diagnostics: reads the accepted grasp relation from the existing Idle clip, checks
which bones actually have skin weights, and measures the Kimodo held-object sway signal.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

args = sys.argv[sys.argv.index('--') + 1:]
blend = Path(args[0])
glb = Path(args[1])
out = Path(args[2])
report = {}

bpy.ops.wm.open_mainfile(filepath=str(blend))
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
tool = next(o for o in scene.objects if o.type == 'MESH' and o.name.startswith('Harvest_Axe'))

action = rig.animation_data.action if rig.animation_data else None
report['action'] = action.name if action else None
scene.frame_set(0)
bpy.context.view_layer.update()

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
report['wpn_root_at_f0'] = [round(v, 5) for v in pose['WPN_root'].to_translation()]
report['wpn_root_quat'] = [round(v, 5) for v in pose['WPN_root'].to_quaternion()]
grasp = pose['WPN_root'].inverted() @ pose['hand_r']
report['grasp_translation'] = [round(v, 5) for v in grasp.to_translation()]
report['grasp_quat'] = [round(v, 5) for v in grasp.to_quaternion()]

finger_prefixes = ('index', 'middle', 'ring', 'pinky', 'thumb')
right_fingers = [b.name for b in rig.data.bones if b.name.endswith('_r') and b.name.startswith(finger_prefixes)]
left_fingers = [b.name for b in rig.data.bones if b.name.endswith('_l') and b.name.startswith(finger_prefixes)]
report['right_fingers'] = right_fingers
report['left_fingers'] = left_fingers
right_relative = {n: pose['hand_r'].inverted() @ pose[n] for n in right_fingers}
report['right_relative_translations'] = {n: [round(v, 4) for v in m.to_translation()] for n, m in right_relative.items()}

# Which bones actually deform the visible arms? Spine weights decide if torso sway is visible.
groups = sorted({g.name for g in arms.vertex_groups})
report['arms_groups'] = groups
report['arms_group_families'] = sorted({g.split('_')[0] for g in groups})

# Tool mesh in local (grip-centred) coordinates: sample the handle at several heights.
tool_verts = [v.co.copy() for v in tool.data.vertices]
report['tool_verts'] = len(tool_verts)
sections = {}
for z in [-0.30, -0.26, -0.20, -0.16, -0.14, -0.10, -0.06, 0.0]:
    band = [v for v in tool_verts if abs(v.z - z) < .01]
    if band:
        sections[z] = {'count': len(band),
                       'x': [round(min(v.x for v in band), 4), round(max(v.x for v in band), 4)],
                       'y': [round(min(v.y for v in band), 4), round(max(v.y for v in band), 4)]}
report['tool_sections'] = sections

# --- Kimodo sway signal ---------------------------------------------------
bpy.ops.import_scene.gltf(filepath=str(glb))
kimodo = next(o for o in scene.objects if o.type == 'ARMATURE' and o.name.startswith('Kimodo'))
samples = []
for frame in range(90):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    entry = {'frame': frame}
    for name in ['Chest', 'LeftHand', 'RightHand']:
        bone = kimodo.pose.bones[name]
        world = kimodo.matrix_world @ bone.matrix
        entry[name] = {'pos': [round(v, 5) for v in world.translation],
                       'quat': [round(v, 6) for v in world.to_quaternion()]}
    samples.append(entry)
report['kimodo_frames'] = len(samples)
report['kimodo_mid_range'] = [
    round(max((s['LeftHand']['pos'][i] + s['RightHand']['pos'][i]) * .5 for s in samples) -
          min((s['LeftHand']['pos'][i] + s['RightHand']['pos'][i]) * .5 for s in samples), 5)
    for i in range(3)]
report['kimodo_chest_pos_range'] = [
    round(max(s['Chest']['pos'][i] for s in samples) - min(s['Chest']['pos'][i] for s in samples), 5)
    for i in range(3)]
chest_q0 = Quaternion(samples[0]['Chest']['quat'])
report['kimodo_chest_rot_delta_deg'] = round(math.degrees(
    (chest_q0.inverted() @ Quaternion(samples[-1]['Chest']['quat'])).angle), 3)
maximum = 0.0
for s in samples:
    maximum = max(maximum, math.degrees((chest_q0.inverted() @ Quaternion(s['Chest']['quat'])).angle))
report['kimodo_chest_rot_max_deg'] = round(maximum, 3)

out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))