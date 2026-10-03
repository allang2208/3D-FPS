"""Offline curve diagnosis for the user-reported recovery hitch; no rendering."""
import json
import math
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).parent))
import author_library_sweep_v27 as author

args = sys.argv[sys.argv.index('--')+1:]
source, output = Path(args[0]), Path(args[1])
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = author.v20.original_rig()
ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
bones = ('pelvis','spine_05','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r')
result = dict(source=str(source), fps=60, scope='Reported recovery curve diagnosis only', clips={})
for role in ('SweepLeft','SweepRight'):
    action = next(a for a in bpy.data.actions if a.name.startswith('A_M07_'+role+'_LibrarySweepV27'))
    frames = author.v17.cache_action(rig, action, 121, ordered)
    metrics = {}
    for name in bones:
        angles, steps = [], []
        for i in range(1,121):
            a,b = frames[i-1][name], frames[i][name]
            dot = min(1.,abs(a.to_quaternion().dot(b.to_quaternion())))
            angles.append(math.degrees(2.*math.acos(dot))*60.)
            steps.append((b.translation-a.translation).length*60.)
        at = max(range(60,120), key=lambda i: angles[i])
        metrics[name] = dict(recovery_peak_angular_deg_s=angles[at], peak_seconds=(at+1)/60.,
            recovery_peak_linear_cm_s=max(steps[60:]),
            stationary_tail_mean_angular_deg_s=sum(angles[78:96])/18.)
    # Small per-bone matrices let this diagnosis compare the accepted prefix
    # exactly without launching an editor, PIE or a separate test suite.
    result['clips'][role] = dict(metrics=metrics,
        accepted_prefix={n:[[list(row) for row in frames[i][n]] for i in range(61)] for n in frames[0]})
if len(args) > 2:
    before = json.loads(Path(args[2]).read_text(encoding='utf-8'))
    comparison = {}
    for role in result['clips']:
        old, new = before['clips'][role], result['clips'][role]
        difference = max(abs(a-b) for name in old['accepted_prefix']
                         for f1,f2 in zip(old['accepted_prefix'][name],new['accepted_prefix'][name])
                         for row1,row2 in zip(f1,f2) for a,b in zip(row1,row2))
        comparison[role] = dict(accepted_prefix_max_matrix_difference=difference,
            recovery={name:dict(before=old['metrics'][name], after=new['metrics'][name])
                      for name in ('pelvis','spine_05','hand_l','hand_r')})
    result['comparison'] = comparison
    print('M07_RECOVERY_CURVE_COMPARISON '+json.dumps(comparison))
output.write_text(json.dumps(result), encoding='utf-8')
print('M07_RECOVERY_DIAGNOSIS_SAVED '+str(output))
