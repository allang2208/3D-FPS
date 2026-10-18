"""Scoped offline diagnosis of the reported spit and camera-framing defects.

Uses original mesh triangles, UE Euler composition and the production Hermite /
quaternion interpolation. Does not run the game, render images, or modify saves.
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REL = 'Content/ColdSteelData/potion_use_motion.json'
before = json.loads((OUT/'Before'/REL).read_text(encoding='utf-8-sig'))
after = json.loads((ROOT/REL).read_text(encoding='utf-8-sig'))


def rotation(euler):
    p, y, r = euler
    return Rotation.from_euler('Z', y, degrees=True) * Rotation.from_euler('Y', -p, degrees=True) * Rotation.from_euler('X', -r, degrees=True)


def ease(t):
    t = np.clip(t, 0, 1)
    return np.clip(t*t*t*(t*(t*6-15)+10), 0, 1)


def sample(motion, age):
    keys = motion['keys']
    for i in range(1, len(keys)):
        if age > keys[i]['time']:
            continue
        a, b = keys[i-1], keys[i]
        dt = b['time']-a['time']
        t = np.clip((age-a['time'])/dt, 0, 1)

        def tangent(j):
            if j in (0, len(keys)-1):
                return np.zeros(3)
            p0, p1, p2 = [np.array(keys[k]['grip']) for k in (j-1, j, j+1)]
            if np.all(abs(p1-p0) <= .01) or np.all(abs(p1-p2) <= .01):
                return np.zeros(3)
            return (p2-p0)/(keys[j+1]['time']-keys[j-1]['time'])

        grip = ((2*t**3-3*t*t+1)*np.array(a['grip']) + (t**3-2*t*t+t)*dt*tangent(i-1)
                + (-2*t**3+3*t*t)*np.array(b['grip']) + (t**3-t*t)*dt*tangent(i))
        rot = Slerp([0, 1], Rotation.concatenate([rotation(a['rotation']), rotation(b['rotation'])]))([ease(t)])[0]
        return grip, rot*rotation(motion['object_rotation'])
    return np.array(keys[-1]['grip']), rotation(keys[-1]['rotation'])*rotation(motion['object_rotation'])


def framing(motion, vertices):
    frames = []
    t = motion['times']
    for age in np.arange(t['duration']*.275, t['contact']+.001, 1/60):
        grip, rot = sample(motion, age)
        points = rot.apply(vertices-np.array(motion['grip_in_object']))+grip
        x, y, z = points.T
        # Native baseline is 75deg vertical. Also include 60deg for tighter views.
        row = {'age': round(float(age), 4), 'grip_x_cm': float(grip[0])}
        for fov in (60, 75):
            h = x*math.tan(math.radians(fov/2))
            visible = (x > 1) & (abs(z) < h) & (abs(y) < h*16/9)
            row[f'visible_vertices_percent_vfov{fov}'] = round(float(visible.mean()*100), 3)
        if motion.get('two_handed'):
            right = rot.apply(np.array(motion['right_grip_in_object'])-motion['grip_in_object'])+grip
            row['hands_on_correct_sides'] = bool(grip[1] < right[1])
            axis = rot.apply([1, 0, 0])
            row['rack_roll_degrees'] = float(np.degrees(np.arctan2(abs(axis[2]), abs(axis[1]))))
        frames.append(row)
    summary = {}
    for fov in (60, 75):
        field = f'visible_vertices_percent_vfov{fov}'
        summary[f'average_visible_vertices_percent_vfov{fov}'] = round(float(np.mean([r[field] for r in frames])), 2)
    summary['minimum_grip_x_cm'] = round(min(r['grip_x_cm'] for r in frames), 3)
    if motion.get('two_handed'):
        summary['hands_on_correct_sides'] = all(r['hands_on_correct_sides'] for r in frames)
        summary['maximum_rack_roll_degrees'] = round(max(r['rack_roll_degrees'] for r in frames), 3)
    return {'summary': summary, 'frames': frames}


def intersections(vertices, faces, y, z):
    tri = vertices[np.array(faces)]
    a, e1, e2 = tri[:, 0], tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0]
    den = e1[:, 1]*e2[:, 2]-e2[:, 1]*e1[:, 2]
    with np.errstate(divide='ignore', invalid='ignore'):
        u = ((y-a[:, 1])*e2[:, 2]-(z-a[:, 2])*e2[:, 1])/den
        v = (e1[:, 1]*(z-a[:, 2])-e1[:, 2]*(y-a[:, 1]))/den
        hits = a[:, 0]+u*e1[:, 0]+v*e2[:, 0]
    mask = (abs(den) > 1e-8) & (u >= 0) & (v >= 0) & (u+v <= 1)
    xs = np.unique(np.round(hits[mask], 5))
    return [list(map(float, pair)) for pair in zip(xs[::2], xs[1::2])]


report = {'method': 'Offline source-mesh geometry, not rendered gameplay acceptance', 'foods': {}}
for item, folder, file, anchor in [
        ('roasted_lamb_ribs', 'LambRibs20261014', 'lamb-geometry.json', [-.6, 2.3]),
        ('roasted_large_lamb', 'LargeLamb20261014', 'large-lamb-geometry.json', [-4, 2.7])]:
    geo = json.loads((ROOT/'SourceAssets'/folder/file).read_text())
    vertices = np.array(geo['vertices'])
    center = (np.array(geo['low'])+geo['high'])/2
    entry = {'before': framing(before[item], vertices), 'after': framing(after[item], vertices),
             'spit_before_x_intervals_cm': intersections(vertices, geo['faces'], *center[1:]),
             'spit_after_x_intervals_cm': intersections(vertices, geo['faces'], *anchor),
             'clocks_unchanged': before[item]['times'] == after[item]['times']}
    # Spit radius .85cm; look at the actual circle in the meat at every supported
    # display count. Both raw/roasted assets use these same original vertices.
    entry['spit_radius_samples'] = []
    for count in range(1, 6):
        scale = min(1, 52/(count*(geo['high'][0]-geo['low'][0])))
        lengths = []
        for angle in np.arange(0, 2*math.pi, math.pi/8):
            spans = intersections(vertices, geo['faces'],
                                  anchor[0]+.85*math.cos(angle)/scale,
                                  anchor[1]+.85*math.sin(angle)/scale)
            lengths.append(max((b-a for a, b in spans), default=0)*scale)
        entry['spit_radius_samples'].append({'display_count': count,
                                             'minimum_inside_length_cm': round(min(lengths), 3)})
    assert entry['clocks_unchanged']
    assert entry['spit_after_x_intervals_cm']
    assert entry['after']['summary']['average_visible_vertices_percent_vfov75'] > 70
    report['foods'][item] = entry
    print(item, json.dumps({k: v['summary'] for k, v in entry.items() if k in ('before', 'after')}))
    print('SPIT', json.dumps({k: v for k, v in entry.items() if k.startswith('spit_')}))
assert report['foods']['roasted_large_lamb']['after']['summary']['hands_on_correct_sides']
assert report['foods']['roasted_large_lamb']['after']['summary']['maximum_rack_roll_degrees'] < 1
assert all(before[k] == after[k] for k in before if k not in report['foods'])
(OUT/'geometry-review.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
