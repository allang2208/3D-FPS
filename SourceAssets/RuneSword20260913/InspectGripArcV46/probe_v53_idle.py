"""Measure the idle grip the next inspect has to leave and return to."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P / 'AzureRunesword_InspectTwirlV47.blend'
if not SOURCE.exists():
    SOURCE = P / 'AzureRunesword_InspectGripArcV46.blend'

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
sword = bpy.data.objects['RuneSword_Blade']
arms = bpy.data.objects['SK_Manny_Arms_Export']
action = bpy.data.actions['A_RuneSword_Inspect']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.render.fps = 120
scene.frame_set(0)
bpy.context.view_layer.update()

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
weapon = pose['WPN_root']
transform = weapon @ rest['WPN_root'].inverted()
depsgraph = bpy.context.evaluated_depsgraph_get()
posed = sword.evaluated_get(depsgraph).to_mesh()
points = [sword.matrix_world @ v.co for v in posed.vertices]
sword.evaluated_get(depsgraph).to_mesh_clear()
centre = sum(points, Vector()) / len(points)
# Blade axis: the longest extent of the mesh in weapon space.
local = [(transform.inverted() @ p) for p in points]
spans = []
for axis in range(3):
    coords = [p[axis] for p in local]
    spans.append((max(coords) - min(coords), axis, min(coords), max(coords)))
spans.sort(reverse=True)
length, axis, low, high = spans[0]
basis = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))][axis]
direction = (transform.to_3x3() @ basis).normalized()
tip = max(points, key=lambda p: (p - centre).dot(direction))
pommel = min(points, key=lambda p: (p - centre).dot(direction))
# Width: largest distance from the axis.
width = 0.0
for p in points:
    offset = p - centre
    along = offset.dot(direction)
    radial = (offset - direction * along).length
    width = max(width, radial)

hand_r = pose['hand_r'].translation
hand_l = pose['hand_l'].translation
report = {
    'source': str(SOURCE),
    'action': action.name,
    'frame_range': list(action.frame_range),
    'tip': [round(v, 4) for v in tip],
    'pommel': [round(v, 4) for v in pommel],
    'centre': [round(v, 4) for v in centre],
    'blade_length_m': round((tip - pommel).length, 4),
    'half_width_m': round(width, 4),
    'tip_depth_y': round(tip.y, 4),
    'pommel_depth_y': round(pommel.y, 4),
    'hand_r': [round(v, 4) for v in hand_r],
    'hand_l': [round(v, 4) for v in hand_l],
    'hand_r_depth_y': round(hand_r.y, 4),
    'hand_l_depth_y': round(hand_l.y, 4),
    'axis_world': [round(v, 4) for v in direction],
}
# Sample left-hand depth through the clip to find the off-screen hold.
samples = []
for frame in range(0, int(action.frame_range[1]) + 1, 12):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    left = rig.pose.bones['hand_l'].matrix.translation
    right = rig.pose.bones['hand_r'].matrix.translation
    samples.append({
        'frame': frame,
        'seconds': round(frame / 120.0, 3),
        'hand_l': [round(v, 4) for v in left],
        'hand_r_y': round(right.y, 4),
    })
report['samples'] = samples
out = P / 'probe_v53_idle.json'
out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print('V53_IDLE_PROBED', out)
