"""Where do the arm mesh and the sword mesh actually touch at the spin start?"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twirl_model as model

SOURCE = P / 'AzureRunesword_InspectGripArcV46.blend'
FPS = 120.0
SECONDS = 0.350

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
sword = bpy.data.objects['RuneSword_Blade']
arms = bpy.data.objects['SK_Manny_Arms_Export']
action = bpy.data.actions['A_RuneSword_Inspect']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(int(SECONDS * FPS))
bpy.context.view_layer.update()

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
geometry = model.sword_geometry(rest['WPN_root'], sword)
transform = rig.pose.bones['WPN_root'].matrix @ rest['WPN_root'].inverted()
world_pommel = transform @ geometry['low']
world_tip = transform @ geometry['high']

# Right-hand bones only, so the nearest arm vertex is not the left hand.
right_groups = {group.index for group in arms.vertex_groups
                if group.name.endswith('_r')}
hand_indices = []
for vertex in arms.data.vertices:
    if any(group.group in right_groups and group.weight > 0.5
           for group in vertex.groups):
        hand_indices.append(vertex.index)

depsgraph = bpy.context.evaluated_depsgraph_get()
posed_arms = arms.evaluated_get(depsgraph).to_mesh()
posed_sword = sword.evaluated_get(depsgraph).to_mesh()
arm_points = [(hand_indices[i // 6], arms.matrix_world @ posed_arms.vertices[hand_indices[i // 6]].co)
              for i in range(len(hand_indices) * 6)]
sword_points = [sword.matrix_world @ vertex.co for vertex in posed_sword.vertices]

best = None
for index, point in arm_points[::7]:
    for sword_point in sword_points[::3]:
        distance = (point - sword_point).length
        if best is None or distance < best[0]:
            best = (distance, point, sword_point, index)
arms.evaluated_get(depsgraph).to_mesh_clear()
sword.evaluated_get(depsgraph).to_mesh_clear()

distance, arm_point, sword_point, vertex_index = best
nearest, t = model.nearest_on_segment(world_pommel, world_tip, sword_point)
report = {
    'seconds': SECONDS,
    'min_arm_to_sword_m': round(distance, 4),
    'arm_vertex_index': vertex_index,
    'arm_point': [round(v, 4) for v in arm_point],
    'sword_point': [round(v, 4) for v in sword_point],
    'sword_point_station_t': round(t, 4),
    'distance_from_sword_axis_to_contact_m': round((sword_point - nearest).length, 4),
    'sword_extends_z': [round(world_pommel.z, 4), round(world_tip.z, 4)],
    'right_hand_vertex_count': len(hand_indices),
}
(P / 'probe_mesh_contact.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for key, value in report.items():
    print('%-38s %s' % (key, value))
print('PROBE_MESH_CONTACT_DONE')
