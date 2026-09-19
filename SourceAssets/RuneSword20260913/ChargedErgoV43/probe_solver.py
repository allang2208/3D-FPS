"""Shape of the elbow metric against the humeral roll, and the solved value."""
import bpy, json, sys
from pathlib import Path

P = Path(__file__).parent
sys.path.insert(0, str(P))
import shoulder_transport as st

SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
V44 = P / 'AzureRunesword_ChargedShoulderV44.blend'
FPS = 480.0
TIMES = {'HeavyCharge': (0.20, 0.35, 0.65, 2.00),
         'HeavyRelease': (0.075, 0.40, 0.60, 0.80)}
GRID = (-95, -75, -50, -25, 0, 25, 50, 75, 95)


def load(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    return scene, rig, {b.name: b.matrix_local.copy() for b in rig.data.bones}


def metric_at(pose, rest, roll):
    modified = dict(pose)
    modified[st.UP] = st.rolled_humerus(pose, rest, roll)
    return st.elbow_roll(modified, rest)


report = {}
for clip, times in TIMES.items():
    scene, rig, rest = load(SOURCE)
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    solved_rows = {}
    for t in times:
        scene.frame_set(int(round(t * FPS)))
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        applied, residual, _ = st.solve_roll(pose, rest, cap=95.0)
        solved_rows[t] = {'curve': {r: round(metric_at(pose, rest, r), 1) for r in GRID},
                          'solved': round(applied, 2), 'residual': round(residual, 2)}
    scene, rig, rest = load(V44)
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    for t in times:
        scene.frame_set(int(round(t * FPS)))
        bpy.context.view_layer.update()
        pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
        solved_rows[t]['v44_metric'] = round(st.elbow_roll(pose, rest), 2)
    report[clip] = solved_rows

(P / 'solver_probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for clip, rows in report.items():
    print('===', clip)
    for t, entry in rows.items():
        print('  t=%.3f solved=%7.2f residual=%7.2f v44=%7.2f  curve=%s'
              % (t, entry['solved'], entry['residual'], entry['v44_metric'],
                 entry['curve']))
print('PROBE_SOLVER_DONE')
