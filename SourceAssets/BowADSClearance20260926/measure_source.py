"""Read source poses/skin to size the ADS camera-space framing adjustment."""
from pathlib import Path
import json
import math
from mathutils import Vector, Matrix

ROOT = Path('D:/FPS3D/FPSGAME')
SOURCE = ROOT/'SourceAssets/DarkBow20260925/ReferenceUpgradeV10/author_actions.py'
ns = {'__file__': str(SOURCE)}
exec(compile(SOURCE.read_text(encoding='utf-8').split('bpy.ops.wm.read_factory_settings(use_empty=True)')[0], str(SOURCE), 'exec'), ns)
rest = Vector((-3.5, -3.9, 2.6))
views = [('previous', Vector((70, 0, 0)), .82, False),
         ('clearance', Vector((78, 10, -12)), .90, True)]
records = []
for seconds in (0., .7, 1.4):
    pose = ns['pose']('Draw', seconds)
    grip = pose['bow_grip']
    local_nock = grip.inverted() @ pose['bow_nock'].translation
    skin = {n: pose[n] @ ns['rest'][n].inverted() for n in pose}
    right_points = []
    for vertex, weights in zip(ns['data']['positions'], ns['data']['weights']):
        if sum(w for n, w in weights.items() if n.endswith('_r')) < .5:
            continue
        p = ns['R'] @ Vector(vertex)
        right_points.append(sum((skin[n] @ p * w for n, w in weights.items()), Vector()))
    for name, target_rest, fov_scale, align in views:
        target_rot = Matrix.Identity(3)
        if align:
            target_rot = (rest-local_nock).normalized().rotation_difference(
                (Vector((3200, 0, 0))-target_rest).normalized()).to_matrix()
        rotation = target_rot @ grip.to_3x3().transposed()
        location = target_rest-target_rot@rest-rotation@grip.translation
        def place(p):
            return rotation@p+location
        transformed = [place(p) for p in right_points]
        # Angular distances are authoring dimensions, not a rendered occlusion test.
        angles = [math.degrees(math.atan2(math.hypot(p.y, p.z), p.x)) for p in transformed if p.x > 1.]
        row = {'view': name, 'draw_seconds': seconds, 'vertical_fov': 75*fov_scale,
               'right_wrist_cm': list(place(pose['hand_r'].translation)),
               'right_elbow_cm': list(place(pose['lowerarm_r'].translation)),
               'nock_cm': list(place(pose['bow_nock'].translation)),
               'right_skin_min_off_axis_degrees': min(angles),
               'right_skin_cm': {'min': [min(p[i] for p in transformed) for i in range(3)],
                                 'max': [max(p[i] for p in transformed) for i in range(3)]}}
        records.append(row)
out = ROOT/'Saved/BowADSClearance20260926'
out.mkdir(parents=True, exist_ok=True)
(out/'source-dimensions.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
print('BOW_ADS_SOURCE_DIMENSIONS '+json.dumps([{k: r[k] for k in ('view','draw_seconds','right_wrist_cm','nock_cm','right_skin_min_off_axis_degrees')} for r in records]))
