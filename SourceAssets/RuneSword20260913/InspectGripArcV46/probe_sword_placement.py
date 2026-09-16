"""Sanity check where the sword actually sits relative to the hand."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P / 'AzureRunesword_InspectGripArcV46.blend'
FPS = 120.0

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
mesh = bpy.data.objects['RuneSword_Blade']
action = bpy.data.actions['A_RuneSword_Inspect']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(int(0.350 * FPS))
bpy.context.view_layer.update()

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
hand = rig.pose.bones['hand_r'].matrix
middle = rig.pose.bones['middle_01_r'].matrix
weapon = rig.pose.bones['WPN_root'].matrix

depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = mesh.evaluated_get(depsgraph)
posed = evaluated.to_mesh()
points = [mesh.matrix_world @ vertex.co for vertex in posed.vertices]
centre = sum(points, Vector()) / len(points)
distances = [((point - hand.translation).length, point) for point in points]
nearest_distance, nearest_point = min(distances, key=lambda entry: entry[0])
extents = [max(getattr(point, axis) for point in points)
           - min(getattr(point, axis) for point in points) for axis in 'xyz']
evaluated.to_mesh_clear()

transform = weapon @ rest['WPN_root'].inverted()
inverse = rest['WPN_root'].inverted()
local = [inverse @ (mesh.matrix_world @ vertex.co) for vertex in mesh.data.vertices]
spans = []
for axis in range(3):
    values = [point[axis] for point in local]
    spans.append((max(values) - min(values), axis, min(values), max(values)))
span, axis_index, low, high = max(spans)
low_point = Vector((0.0, 0.0, 0.0))
high_point = Vector((0.0, 0.0, 0.0))
low_point[axis_index] = low
high_point[axis_index] = high
world_low = transform @ low_point
world_high = transform @ high_point

report = {
    'frame_seconds': 0.350,
    'hand_origin': [round(v, 4) for v in hand.translation],
    'middle_head': [round(v, 4) for v in middle.translation],
    'weapon_origin': [round(v, 4) for v in weapon.translation],
    'mesh_world_center': [round(v, 4) for v in centre],
    'mesh_posed_extents_m': [round(v, 4) for v in extents],
    'rest_span_m': round(span, 4),
    'rest_span_axis': axis_index,
    'world_low': [round(v, 4) for v in world_low],
    'world_high': [round(v, 4) for v in world_high],
    'nearest_vertex_to_hand_m': round(nearest_distance, 4),
    'nearest_vertex': [round(v, 4) for v in nearest_point],
    'mesh_object_matrix_world': [round(v, 4) for row in mesh.matrix_world for v in row],
    'rig_matrix_world': [round(v, 4) for row in rig.matrix_world for v in row],
}
(P / 'probe_sword_placement.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for key, value in report.items():
    print('%-26s %s' % (key, value))
print('PROBE_SWORD_PLACEMENT_DONE')
