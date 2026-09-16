"""Confirm V47 leaves the rest of the clip alone and matches V46 at the joins."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import twirl_model as model

SOURCES = {
    'v46': P / 'AzureRunesword_InspectGripArcV46.blend',
    'v47': P / 'AzureRunesword_InspectTwirlV47.blend',
}
FPS = 120.0
CHECKS = (0.350, 0.650, 0.300, 0.700, 1.000, 2.000, 2.900)

report = {}
for label, path in SOURCES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    mesh = bpy.data.objects['RuneSword_Blade']
    action = bpy.data.actions['A_RuneSword_Inspect']
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    geometry = model.sword_geometry(rest['WPN_root'], mesh)
    rows = {}
    for seconds in CHECKS:
        frame = seconds * FPS
        scene.frame_set(int(frame), subframe=frame - int(frame))
        bpy.context.view_layer.update()
        full = rig.pose.bones['WPN_root'].matrix @ rest['WPN_root'].inverted()
        rows['%.3f' % seconds] = {
            'pommel': [round(v, 5) for v in (full @ geometry['low'])],
            'tip': [round(v, 5) for v in (full @ geometry['high'])],
            'hand': [round(v, 5) for v in rig.pose.bones['hand_r'].matrix.translation],
            'left_hand': [round(v, 5) for v in rig.pose.bones['hand_l'].matrix.translation],
        }
    report[label] = rows

(P / 'probe_v46_v47_ends.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('%-8s %-34s %-34s %-30s' % ('t (s)', 'pommel', 'tip', 'hand'))
for seconds in CHECKS:
    key = '%.3f' % seconds
    for label in ('v46', 'v47'):
        row = report[label][key]
        print('%-8s %-34s %-34s %-30s' % (key + ' ' + label, row['pommel'],
                                          row['tip'], row['hand']))
    difference = max(abs(a - b) for a, b in
                     zip(report['v46'][key]['pommel'] + report['v46'][key]['tip'],
                         report['v47'][key]['pommel'] + report['v47'][key]['tip']))
    print('%-8s max sword difference %.6f m' % ('', difference))
print('PROBE_V46_V47_ENDS_DONE')
