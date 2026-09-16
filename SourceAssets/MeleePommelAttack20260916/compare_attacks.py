"""Compare the new counterweight strike against the accepted slash and thrust.

Same rig, same solver family: this shows whether the fourth hit's shoulder
travel, elbow bend and view clearance sit inside the range the accepted clips
already use.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Vector

P = Path(__file__).parent
BLEND = P / 'AzureRunesword_PommelStrikeV46.blend'
FPS = 480
FAMILY = {
    'Slash1': [0.80, 0.90, 0.965, 1.05],
    'Slash2': [0.80, 0.90, 0.965, 1.05],
    'Thrust': [0.42, 0.52, 0.58, 0.70],
    'PommelStrike': [0.58, 0.72, 0.92, 0.98],
}

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']


def pose_at(clip, seconds):
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    frame = seconds * FPS
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def metrics(pose):
    def bend(side):
        upper = pose['upperarm_' + side].translation
        lower = pose['lowerarm_' + side].translation
        hand = pose['hand_' + side].translation
        return math.degrees((lower - upper).normalized().angle((hand - lower).normalized()))
    base = pose['Blade_Base'].translation
    tip = pose['Blade_Tip'].translation
    axis = tip - base
    t = max(0.0, min(1.0, -axis.dot(base) / axis.length_squared))
    closest = base + axis * t
    return {
        'elbow_l': round(bend('l'), 1),
        'elbow_r': round(bend('r'), 1),
        'blade_to_aim_m': round(math.hypot(closest.x, closest.z), 3),
        'blade_base_forward_m': round(base.y, 3),
        'blade_tip': [round(v, 3) for v in tip],
    }


report = {'clips': {}}
for clip, times in FAMILY.items():
    entry = {'times': times, 'samples': []}
    for seconds in times:
        pose = pose_at(clip, seconds)
        row = metrics(pose)
        row['seconds'] = seconds
        row['clavicle_l_cm'] = round(pose['clavicle_l'].translation.length * 100, 2)
        row['upperarm_l'] = [round(v, 3) for v in pose['upperarm_l'].translation]
        entry['samples'].append(row)
    report['clips'][clip] = entry

for clip, entry in report['clips'].items():
    print('== %s' % clip)
    for row in entry['samples']:
        print('   %.3f s  elbow %5.1f/%5.1f  blade->aim %.3f m  base_y %.3f  tip %s  clavL %.1f cm  upperarmL %s'
              % (row['seconds'], row['elbow_l'], row['elbow_r'], row['blade_to_aim_m'],
                 row['blade_base_forward_m'], row['blade_tip'], row['clavicle_l_cm'], row['upperarm_l']))
(P / 'attack_comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('COMPARE_DONE')
