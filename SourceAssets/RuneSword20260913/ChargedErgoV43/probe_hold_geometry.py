"""Objective audit of the charged hold pose: joint angles and arm/sword clearance."""
import bpy, json, math
import numpy as np
from mathutils import Vector, kdtree
from pathlib import Path

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 480.0
TIMES = (1.40, 1.60, 1.80, 1.90, 2.00)
LEFT = ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_twist_01_l',
        'upperarm_twist_02_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l',
        'thumb_01_l', 'thumb_02_l', 'thumb_03_l', 'index_01_l', 'index_02_l', 'index_03_l',
        'middle_01_l', 'middle_02_l', 'middle_03_l', 'ring_01_l', 'ring_02_l', 'ring_03_l',
        'pinky_01_l', 'pinky_02_l', 'pinky_03_l')
RIGHT = tuple(n[:-1] + 'r' for n in LEFT if n.endswith('_l'))

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
sword = bpy.data.objects['RuneSword_Blade']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
groups = {g.name: g.index for g in arms.vertex_groups}
weights = np.zeros((len(arms.data.vertices), len(groups)), dtype=np.float64)
for vertex in arms.data.vertices:
    for g in vertex.groups:
        weights[vertex.index, g.group] = g.weight


def zone(names):
    mask = np.zeros(len(arms.data.vertices), dtype=bool)
    for name in names:
        if name in groups:
            mask |= weights[:, groups[name]] > .5
    return mask


left_mask, right_mask = zone(LEFT), zone(RIGHT)
action = bpy.data.actions['A_RuneSword_HeavyCharge']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]

rows = []
for t in TIMES:
    scene.frame_set(int(round(t * FPS)))
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    A = pose['upperarm_l'].translation
    E = pose['lowerarm_l'].translation
    H = pose['hand_l'].translation
    ud, fd = (E - A).normalized(), (H - E).normalized()

    def local_angle(name):
        bone = rig.pose.bones[name]
        q = bone.rotation_quaternion
        return math.degrees(2 * math.atan2(math.sqrt(q.x ** 2 + q.y ** 2 + q.z ** 2), abs(q.w)))

    depsgraph = bpy.context.evaluated_depsgraph_get()
    arm_co = np.array([v.co for v in arms.evaluated_get(depsgraph).data.vertices], dtype=np.float64)
    sword_co = np.array([v.co for v in sword.evaluated_get(depsgraph).data.vertices],
                        dtype=np.float64)
    tree = kdtree.KDTree(len(sword_co))
    for i, co in enumerate(sword_co):
        tree.insert(Vector(co), i)
    tree.balance()
    left_ids = np.where(left_mask)[0]
    right_co = arm_co[right_mask]
    rtree = kdtree.KDTree(len(right_co))
    for i, co in enumerate(right_co):
        rtree.insert(Vector(co), i)
    rtree.balance()
    sword_gap = min(tree.find(Vector(arm_co[i]))[2] for i in left_ids[::5])
    right_gap = min(rtree.find(Vector(arm_co[i]))[2] for i in left_ids[::5])

    rows.append({
        'seconds': t,
        'elbow_flex_deg': math.degrees(ud.angle(fd)),
        'right_elbow_flex_deg': math.degrees(
            (pose['lowerarm_r'].translation - pose['upperarm_r'].translation).normalized().angle(
                (pose['hand_r'].translation - pose['lowerarm_r'].translation).normalized())),
        'left_hand_vs_forearm_deg': local_angle('hand_l'),
        'left_lowerarm_local_deg': local_angle('lowerarm_l'),
        'left_upperarm_local_deg': local_angle('upperarm_l'),
        'left_forearm_vs_hilt_axis_deg': math.degrees(fd.angle(
            (pose['WPN_root'].to_quaternion() @ Vector((0, 0, 1))).normalized())),
        'elbow_below_shoulder_m': (A - E).z,
        'right_elbow_below_shoulder_m': (pose['upperarm_r'].translation
                                         - pose['lowerarm_r'].translation).z,
        'wrist_above_shoulder_m': (H.z - A.z),
        'shoulder_wrist_m': (H - A).length,
        'elbow_to_shoulder_m': (E - A).length,
        'elbow_above_line_m': ((E - A).cross(H - A).length / (H - A).length),
        'left_to_sword_min_gap_cm': sword_gap * 100.0,
        'left_to_right_arm_min_gap_cm': right_gap * 100.0,
    })

(P / 'hold_geometry.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
for row in rows:
    print('t=%.2f  L_flex=%5.1f R_flex=%5.1f  L_elbow_rel_shoulder_z=%7.3f  R=%7.3f  '
          'wrist_above_shoulder=%6.3f  elbow_off_line=%6.3f  gap_sword=%5.2fcm'
          % (row['seconds'], row['elbow_flex_deg'], row['right_elbow_flex_deg'],
             -row['elbow_below_shoulder_m'], -row['right_elbow_below_shoulder_m'],
             row['wrist_above_shoulder_m'], row['elbow_above_line_m'],
             row['left_to_sword_min_gap_cm']))
print('PROBE_HOLD_GEOMETRY_DONE')
