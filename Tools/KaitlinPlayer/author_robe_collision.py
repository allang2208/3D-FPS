"""Derive cloth collision volumes from Kaitlin's own complete rest surface."""
import json
from pathlib import Path
import numpy as np
from body_surface_fit import regions

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
body = json.loads((WORK / 'NativeGeometry/MHC_Kaitlin_Body.json').read_text())
points, region = np.asarray(body['positions']), regions(body)
bones = {b['name']: b for b in body['bones']}
segments = [('pelvis', 'spine_02', 'torso'), ('spine_02', 'spine_04', 'torso'), ('spine_04', 'neck_01', 'torso')]
for side in ('l', 'r'):
    segments.extend((first + '_' + side, last + '_' + side, group + '_' + side)
                    for first, last, group in [('thigh', 'calf', 'thigh'), ('calf', 'foot', 'calf'),
                                               ('foot', 'ball', 'foot'), ('upperarm', 'lowerarm', 'upperarm'),
                                               ('lowerarm', 'hand', 'lowerarm'), ('hand', 'middle_01', 'hand')])
capsules = []
for first, last, group in segments:
    bone = bones[first]
    a, b = np.asarray(bone['position']), np.asarray(bones[last]['position'])
    axis = (b - a) / np.linalg.norm(b - a)
    x = np.array([1., 0., 0.])
    if abs(axis @ x) > .85:
        x = np.array([0., 1., 0.])
    x = x - axis * (x @ axis)
    x /= np.linalg.norm(x)
    y = np.cross(axis, x)
    selected = points[region == group]
    along = (selected - a) @ axis
    length = np.linalg.norm(b - a)
    for low, high in ((.04, .42), (.32, .74), (.64, .98)):
        local = selected[(along >= low * length) & (along <= high * length)]
        if len(local) < 6:
            continue
        xy = np.c_[(local - a) @ x, (local - a) @ y]
        lo, hi = np.percentile(xy, 4, axis=0), np.percentile(xy, 96, axis=0)
        center, radii = (lo + hi) * .5, (hi - lo) * .5
        radius = max(.4, float(min(radii)) - .2)
        wide = int(np.argmax(radii))
        spread = max(0., float(radii[wide]) - radius - .2)
        for offset in ((-spread, spread) if spread > .5 else (0.,)):
            cross = center.copy()
            cross[wide] += offset
            center_world = a + x * cross[0] + y * cross[1]
            start = center_world + axis * (low * length + radius * .5)
            end = center_world + axis * (high * length - radius * .5)
            if (end - start) @ axis < 0:
                start = end = (start + end) * .5
            inverse = np.linalg.inv(bone['axes'])
            capsules.append({'bone': first, 'radius': radius,
                             'start': ((start - a) @ inverse).tolist(), 'end': ((end - a) @ inverse).tolist()})
(WORK / 'robe_collision.json').write_text(json.dumps({'source_body': body['source'],
    'method': 'native_surface_cross_sections_in_each_bone_frame', 'capsules': capsules}, indent=2), encoding='utf-8')
print('KAITLIN_ROBE_COLLISION_AUTHORED', len(capsules), flush=True)
