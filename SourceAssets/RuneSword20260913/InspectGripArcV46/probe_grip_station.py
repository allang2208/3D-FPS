"""Where, along the sword, does the hand actually touch it at the spin start?"""
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
mesh = bpy.data.objects['RuneSword_Blade']
action = bpy.data.actions['A_RuneSword_Inspect']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(int(SECONDS * FPS))
bpy.context.view_layer.update()

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
geometry = model.sword_geometry(rest['WPN_root'], mesh)
pommel, tip = geometry['low'], geometry['high']
length = geometry['length']
transform = rig.pose.bones['WPN_root'].matrix @ rest['WPN_root'].inverted()
world_pommel = transform @ pommel
world_tip = transform @ tip


def station(point):
    nearest, t = model.nearest_on_segment(world_pommel, world_tip, point)
    return {'distance_m': round((point - nearest).length, 4),
            't': round(t, 4),
            'nearest_world': [round(v, 4) for v in nearest]}


hand = rig.pose.bones['hand_r'].matrix
middle = rig.pose.bones['middle_01_r'].matrix
index = rig.pose.bones['index_01_r'].matrix
pinky = rig.pose.bones['pinky_01_r'].matrix
palm = (hand.translation + middle.translation) / 2.0

depsgraph = bpy.context.evaluated_depsgraph_get()
evaluated = mesh.evaluated_get(depsgraph)
posed = evaluated.to_mesh()
points = [mesh.matrix_world @ vertex.co for vertex in posed.vertices]
nearest_vertex = min(points, key=lambda point: (point - palm).length)
evaluated.to_mesh_clear()

report = {
    'seconds': SECONDS,
    'sword_length_m': round(length, 4),
    'pommel_local': [round(v, 4) for v in pommel],
    'tip_local': [round(v, 4) for v in tip],
    'world_pommel': [round(v, 4) for v in world_pommel],
    'world_tip': [round(v, 4) for v in world_tip],
    'hand_origin_station': station(hand.translation),
    'middle_base_station': station(middle.translation),
    'index_base_station': station(index.translation),
    'pinky_base_station': station(pinky.translation),
    'palm_centre': [round(v, 4) for v in palm],
    'palm_centre_station': station(palm),
    'nearest_vertex_to_palm_station': station(nearest_vertex),
}
(P / 'probe_grip_station.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for key, value in report.items():
    print('%-30s %s' % (key, value))
print('PROBE_GRIP_STATION_DONE')
