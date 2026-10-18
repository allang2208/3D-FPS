"""Read the reported thumb deformation on the current Traversal binding. No rendering."""
import json, math, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'SourceAssets/LambNaturalGrip20261016/Authoring'))
import review_pose as R
import numpy as np

motion = json.loads((OUT/'Before/Content/ColdSteelData/potion_use_motion.json').read_text())['roasted_large_lamb']
_, obj, before, _ = R.solve(motion, 2.75, False)
after = {n: m.copy() for n, m in before.items()}
report = {}
for side in ('l', 'r'):
    rows = []
    for segment in range(1, 4):
        name = f'thumb_{segment:02}_{side}'
        p = R.parent[name]
        nxt = f'thumb_{segment+1:02}_{side}'
        direction = (R.rest[nxt].translation-R.rest[name].translation if nxt in R.rest else
            R.rest[name].to_3x3()@R.rest[p].to_3x3().inverted()@(R.rest[name].translation-R.rest[p].translation))
        local_axis = R.rest[name].to_3x3().inverted()@direction.normalized()
        inherited = after[p]@R.local[name]
        old_rotation = before[name].to_quaternion()
        native_rotation = inherited.to_quaternion()
        desired_axis = old_rotation@local_axis
        swing = (native_rotation@local_axis).rotation_difference(desired_axis)
        after[name] = R.mat((swing@native_rotation).to_matrix(), inherited.translation)
        twist = after[name].to_quaternion().inverted()@old_rotation
        if twist.w < 0: twist.negate()
        old_local = R.local[name].to_quaternion().inverted()@before[p].to_quaternion().inverted()@old_rotation
        if old_local.w < 0: old_local.negate()
        rows.append({'bone':name,
            'removed_axial_roll_deg':math.degrees(twist.angle),
            'old_local_delta_deg':math.degrees(old_local.angle),
            'joint_position_change_cm':(after[name].translation-before[name].translation).length,
            'target_axis_change_deg':math.degrees((after[name].to_quaternion()@local_axis).angle(desired_axis))})
    report[side] = rows

# Inspect the same affected skin as the user-reported deformation, without
# invoking UE or any preview renderer. All other bones retain the before pose.
skin_points = {}
for label, pose in [('before', before), ('after', after)]:
    verts = np.zeros((len(R.pos), 3))
    for name in R.order:
        if np.any(R.weights[name]):
            verts += (R.pos@np.array(pose[name]@R.inv[name]).T)[:, :3]*R.weights[name][:, None]
    skin_points[label] = verts
triangles = np.array(R.skin['triangles'])
edges = np.unique(np.sort(np.concatenate([triangles[:, [0,1]], triangles[:, [1,2]], triangles[:, [2,0]]]), axis=1), axis=0)
rest_points = np.array(R.skin['positions'])
report['skin'] = {}
for side in ('l', 'r'):
    affected = sum((R.weights[f'thumb_{j:02}_{side}'] for j in range(1,4)), np.zeros(len(R.pos))) > .05
    relevant = edges[affected[edges].any(axis=1)]
    lengths = np.linalg.norm(rest_points[relevant[:,0]]-rest_points[relevant[:,1]], axis=1)
    useful = lengths > .01
    relevant, lengths = relevant[useful], lengths[useful]
    row = {}
    for label, points in skin_points.items():
        ratio = np.linalg.norm(points[relevant[:,0]]-points[relevant[:,1]], axis=1)/lengths
        row[label] = dict(zip(['min','p05','median','p95','max'], map(float, np.quantile(ratio, [0,.05,.5,.95,1]))))
    row['changed_thumb_vertices'] = int(affected.sum())
    report['skin'][side] = row
report['scope'] = 'Offline thumb-frame and mixed-skin diagnosis only; no render, UE runtime, game or multiplayer acceptance.'
(OUT/'diagnosis.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
