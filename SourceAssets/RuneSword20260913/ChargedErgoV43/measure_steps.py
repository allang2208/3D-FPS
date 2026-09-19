"""Frame-to-frame rotation steps of the left arm chain across the charged attack."""
import bpy, json, math
from pathlib import Path

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 480.0
BONES = ('clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']


def q_of(pose, name):
    return pose[name].to_quaternion()


def angle(a, b):
    d = a.rotation_difference(b)
    return math.degrees(2 * math.atan2(math.sqrt(d.x * d.x + d.y * d.y + d.z * d.z), abs(d.w)))


report = {}
for clip in ('HeavyCharge', 'HeavyRelease', 'Slash1'):
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    start, end = map(int, action.frame_range)
    previous = None
    steps = []
    for f in range(start, end + 1):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        if previous is not None:
            steps.append({'frame': f, 'seconds': f / FPS,
                          **{n: angle(previous[n], q_of(pose, n)) for n in BONES}})
        previous = {n: q_of(pose, n) for n in BONES}
    entry = {}
    for name in BONES:
        worst = max(steps, key=lambda s: s[name])
        entry[name] = {'max_step_deg': worst[name], 'at_seconds': worst['seconds'],
                       'mean_step_deg': sum(s[name] for s in steps) / len(steps)}
    report[clip] = entry

(P / 'left_arm_steps.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for clip, entry in report.items():
    print('===', clip)
    for name, value in entry.items():
        print('   %-22s max step %6.2f deg/2.08ms at %.3f s   mean %.2f'
              % (name, value['max_step_deg'], value['at_seconds'], value['mean_step_deg']))
print('STEPS_DONE')
