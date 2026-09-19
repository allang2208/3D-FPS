"""Compare the new two-hand idle against the shipped single-hand idle on the same rig.

Blender --background --python <this> -- <blend> <out.json>
Read-only: tool sway envelope, chest sway, and hand-to-handle distance for both clips.
"""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=str(Path(args[0])))
out = Path(args[1])
scene = bpy.context.scene
rig = bpy.data.objects['SK_Harvest_Axe_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
report = {}

for clip in ['A_Harvest_Axe_Idle', 'A_Harvest_Axe_Idle2H']:
    action = bpy.data.actions.get(clip)
    if not action:
        report[clip] = {'missing': True}
        continue
    rig.animation_data.action = action
    frames = round(action.frame_range[1])
    tool_positions, chest_positions, hand_r_perp, hand_l_perp = [], [], [], []
    for frame in range(0, frames + 1, 5):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        wpn = rig.pose.bones['WPN_root'].matrix
        origin = wpn.to_translation()
        axis = (wpn.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
        tool_positions.append(origin)
        chest_positions.append(rig.pose.bones['spine_04'].matrix.to_translation())
        for side, bucket in [('r', hand_r_perp), ('l', hand_l_perp)]:
            delta = rig.pose.bones['hand_' + side].matrix.to_translation() - origin
            bucket.append((delta - axis * delta.dot(axis)).length)
    def envelope(points):
        return [round(max(p[i] for p in points) - min(p[i] for p in points), 5) for i in range(3)]
    report[clip] = {'frames': frames, 'tool_position_envelope_m': envelope(tool_positions),
                    'chest_position_envelope_m': envelope(chest_positions),
                    'hand_r_perp_to_handle_m': [round(min(hand_r_perp), 4), round(max(hand_r_perp), 4)],
                    'hand_l_perp_to_handle_m': [round(min(hand_l_perp), 4), round(max(hand_l_perp), 4)]}

out.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
print('IDLE_COMPARE_DONE')