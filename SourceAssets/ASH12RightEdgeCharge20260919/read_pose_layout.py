"""Read existing camera and contact poses for right-edge trajectory authoring."""
import json
from pathlib import Path
import bpy
from mathutils import Vector

OUT = Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(OUT.parent / 'ASH12ReloadRefine20260919/ASH12_Reload_Reference_Editable.blend'))
rig = bpy.data.objects['SK_M4_Infima']
scene = bpy.context.scene

def pose(action_name, time):
    action = bpy.data.actions[action_name]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    frame = time * 60
    scene.frame_set(int(frame), subframe=frame % 1.)
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}

aim = pose('ASH12_aim', 0)
forward = (aim['WPN_FrontSight'].translation - aim['WPN_RearSight'].translation).normalized()
up = (Vector((0, 0, 1)) - forward * forward.z).normalized()
right = forward.cross(up).normalized()
eye = aim['WPN_RearSight'].translation - forward * .18 - right * .07 + up * .07
report = {'eye': list(eye), 'right': list(right), 'forward': list(forward), 'up': list(up), 'poses': {}}
for t in (1.91, 2.06, 2.20, 2.34, 2.54, 2.60, 2.91, 3.10):
    p = pose('ASH12_Reference_reload_empty', t)
    data = {}
    for name in ('upperarm_r', 'lowerarm_r', 'hand_r', 'WPN_ChargingHandle'):
        v = p[name].translation - eye
        data[name] = [round(v.dot(a), 4) for a in (right, forward, up)]
    report['poses'][str(t)] = data
(OUT / 'pose_layout.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('AUTHORING_LAYOUT ' + json.dumps(report))
