"""Compare the V43 revision against its source.

Kinematics must be untouched (positions, directions, lengths, grip). The
axial rotation is expected to move from the elbow onto the forearm, and the
elbow-seam skin shear is expected to drop.
"""
import bpy, json, math, sys
import numpy as np
from mathutils import Quaternion, Vector
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twist_distribution as td

OLD = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
NEW = P / 'AzureRunesword_ChargedErgoV43.blend'
FPS = 480.0
CLIPS = ('HeavyCharge', 'HeavyRelease', 'Slash1')
STRIDE = 4
FOREARM_BONES = ('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l')
UPPER_BONES = ('upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l')


def axial_deg(delta, no_roll, axis):
    relative = delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


def sample(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    groups = {g.name: g.index for g in arms.vertex_groups}

    weights = np.zeros((len(arms.data.vertices), len(groups)), dtype=np.float64)
    for vertex in arms.data.vertices:
        for g in vertex.groups:
            weights[vertex.index, g.group] = g.weight
    dominant = {name: weights[:, index] > .5 for name, index in groups.items()}

    coords = np.array([v.co for v in arms.data.vertices], dtype=np.float64)
    edges = np.array([tuple(e.vertices) for e in arms.data.edges], dtype=np.int64)
    lengths = np.linalg.norm(coords[edges[:, 0]] - coords[edges[:, 1]], axis=1)
    keep = lengths > 1e-6
    edges, rest_len = edges[keep], lengths[keep]

    def mask_of(names):
        result = np.zeros(len(coords), dtype=bool)
        for name in names:
            if name in dominant:
                result |= dominant[name]
        return result

    upper_mask = mask_of(UPPER_BONES)
    fore_mask = mask_of(FOREARM_BONES)
    seam = np.where(
        (upper_mask[edges[:, 0]] & fore_mask[edges[:, 1]])
        | (fore_mask[edges[:, 0]] & upper_mask[edges[:, 1]]))[0]
    inside = np.where(fore_mask[edges[:, 0]] & fore_mask[edges[:, 1]])[0]

    result = {'path': str(path), 'seam_edges': len(seam), 'forearm_edges': len(inside),
              'clips': {}}
    for clip in CLIPS:
        action = bpy.data.actions['A_RuneSword_' + clip]
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        start, end = map(int, action.frame_range)
        frames = []
        for f in range(start, end + 1, STRIDE):
            scene.frame_set(f)
            bpy.context.view_layer.update()
            pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
            info = td.forearm_roll(pose, rest)
            no_roll, axis = info['no_roll'], info['axis']
            entry = {
                'seconds': f / FPS,
                'positions': {b.name: pose[b.name].translation.copy() for b in rig.pose.bones},
                'hand_rotation': pose[td.HAND].to_quaternion().copy(),
                'upper_dir': (pose['lowerarm_l'].translation
                              - pose['upperarm_l'].translation).normalized(),
                'fore_dir': (pose[td.HAND].translation - pose[td.LO].translation).normalized(),
                'upper_len': (pose['lowerarm_l'].translation
                              - pose['upperarm_l'].translation).length,
                'fore_len': (pose[td.HAND].translation - pose[td.LO].translation).length,
                'roll': {},
            }
            for name in (td.LO,) + FOREARM_BONES[1:]:
                delta = pose[name].to_quaternion() @ rest[name].to_quaternion().inverted()
                entry['roll'][name] = axial_deg(delta, no_roll, axis)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            deformed = np.array([v.co for v in arms.evaluated_get(depsgraph).data.vertices],
                                dtype=np.float64)
            ratio = np.linalg.norm(deformed[edges[:, 0]] - deformed[edges[:, 1]], axis=1) / rest_len
            entry['seam_p999'] = float(np.quantile(ratio[seam], .999))
            entry['seam_max'] = float(ratio[seam].max())
            entry['forearm_p999'] = float(np.quantile(ratio[inside], .999))
            frames.append(entry)
        result['clips'][clip] = frames
    return result


old = sample(OLD)
new = sample(NEW)

summary = {}
for clip in CLIPS:
    a, b = old['clips'][clip], new['clips'][clip]
    worst_position = worst_bone = None
    worst_position_value = 0.0
    worst_hand = worst_upper = worst_fore = worst_length = 0.0
    rolls = {name: {'before': 0.0, 'after': 0.0} for name in FOREARM_BONES}
    seam_before = seam_after = 0.0
    forearm_before = forearm_after = 0.0
    for x, y in zip(a, b):
        for name, value in x['positions'].items():
            delta = (value - y['positions'][name]).length * 1000.0
            if delta > worst_position_value:
                worst_position_value, worst_bone = delta, name
        hand = x['hand_rotation'].rotation_difference(y['hand_rotation'])
        worst_hand = max(worst_hand, math.degrees(2 * math.atan2(
            math.sqrt(hand.x ** 2 + hand.y ** 2 + hand.z ** 2), abs(hand.w))))
        worst_upper = max(worst_upper, math.degrees(x['upper_dir'].angle(y['upper_dir'])))
        worst_fore = max(worst_fore, math.degrees(x['fore_dir'].angle(y['fore_dir'])))
        worst_length = max(worst_length, abs(x['upper_len'] - y['upper_len']) * 1000.0,
                           abs(x['fore_len'] - y['fore_len']) * 1000.0)
        for name in FOREARM_BONES:
            rolls[name]['before'] = max(rolls[name]['before'], abs(x['roll'][name]))
            rolls[name]['after'] = max(rolls[name]['after'], abs(y['roll'][name]))
        seam_before = max(seam_before, x['seam_p999'])
        seam_after = max(seam_after, y['seam_p999'])
        forearm_before = max(forearm_before, x['forearm_p999'])
        forearm_after = max(forearm_after, y['forearm_p999'])
    summary[clip] = {
        'samples': len(a),
        'max_bone_position_delta_mm': worst_position_value,
        'worst_bone': worst_bone,
        'max_hand_world_rotation_delta_deg': worst_hand,
        'max_upperarm_direction_delta_deg': worst_upper,
        'max_forearm_direction_delta_deg': worst_fore,
        'max_arm_length_delta_mm': worst_length,
        'axial_deg_abs_max': rolls,
        'elbow_seam_p999_before': seam_before,
        'elbow_seam_p999_after': seam_after,
        'forearm_p999_before': forearm_before,
        'forearm_p999_after': forearm_after,
    }

(P / 'verification.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
for clip, entry in summary.items():
    print('===', clip, '(%d samples)' % entry['samples'])
    print('   bone position delta %10.6f mm (%s)' % (entry['max_bone_position_delta_mm'],
                                                     entry['worst_bone']))
    print('   hand world rot      %10.6f deg' % entry['max_hand_world_rotation_delta_deg'])
    print('   direction delta     upper %8.6f / forearm %8.6f deg'
          % (entry['max_upperarm_direction_delta_deg'], entry['max_forearm_direction_delta_deg']))
    print('   arm length delta    %10.6f mm' % entry['max_arm_length_delta_mm'])
    for name, values in entry['axial_deg_abs_max'].items():
        print('   %-20s axial %6.1f -> %6.1f deg' % (name, values['before'], values['after']))
    print('   elbow seam p999     %6.3f -> %6.3f' % (entry['elbow_seam_p999_before'],
                                                     entry['elbow_seam_p999_after']))
    print('   forearm p999        %6.3f -> %6.3f' % (entry['forearm_p999_before'],
                                                     entry['forearm_p999_after']))
print('VERIFY_TWIST_DONE')
