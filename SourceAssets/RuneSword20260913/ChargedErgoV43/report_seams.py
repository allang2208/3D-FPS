"""Report the elbow-seam and wrist-seam axial shear before and after V43."""
import bpy, json, math, sys
from mathutils import Vector
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twist_distribution as td

BLENDS = {'authored': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
          'v43': P / 'AzureRunesword_ChargedErgoV43.blend'}
TIMES = {'HeavyCharge': (0.0, 0.20, 0.35, 0.65, 1.00, 1.40, 2.00),
         'HeavyRelease': (0.075, 0.15, 0.40, 0.60, 0.80, 1.00),
         'Slash1': (0.10, 0.35, 0.65, 0.85, 1.20)}
FPS = 480.0
BONES = (td.LO, td.TWIST_01, td.TWIST_02)


def axial(delta, no_roll, axis):
    relative = delta @ no_roll.inverted()
    vector = Vector((relative.x, relative.y, relative.z))
    angle = 2.0 * math.atan2(vector.dot(axis), relative.w)
    return math.degrees((angle + math.pi) % (2.0 * math.pi) - math.pi)


table = {}
for label, path in BLENDS.items():
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    rows = {}
    for clip, times in TIMES.items():
        action = bpy.data.actions['A_RuneSword_' + clip]
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        for t in times:
            scene.frame_set(int(t * FPS))
            bpy.context.view_layer.update()
            pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
            info = td.forearm_roll(pose, rest)
            entry = {'elbow_axis_deg': math.degrees(info['roll'])}
            for name in BONES:
                delta = pose[name].to_quaternion() @ rest[name].to_quaternion().inverted()
                entry[name] = axial(delta, info['no_roll'], info['axis'])
            hand_delta = pose[td.HAND].to_quaternion() @ rest[td.HAND].to_quaternion().inverted()
            entry['hand_seam_deg'] = entry[td.TWIST_01] - axial(hand_delta, info['no_roll'], info['axis'])
            rows['%s %.3f' % (clip, t)] = entry
    table[label] = rows

(P / 'seam_report.json').write_text(json.dumps(table, indent=2), encoding='utf-8')

print('%-22s %10s | %-34s | %-34s' % ('clip time', 'weight-free', 'elbow seam (twist_02)', 'wrist seam (twist_01 vs hand)'))
for key in table['authored']:
    a, b = table['authored'][key], table['v43'][key]
    print('%-22s %10.1f | %8.1f -> %-8.1f        | %8.1f -> %-8.1f'
          % (key, a['elbow_axis_deg'], a[td.TWIST_02], b[td.TWIST_02],
             a['hand_seam_deg'], b['hand_seam_deg']))
print('REPORT_SEAMS_DONE')
