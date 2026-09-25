"""Locally shape the accepted V3 wrist; keep its binding and face order intact.

Runs with Python/numpy. This writes authoring data, not a pose test or render.
All distances are native UE centimetres.
"""
import json
from pathlib import Path

import numpy as np

PROJECT = Path('D:/FPS3D/FPSGAME')
BASE = PROJECT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4'
SOURCE = BASE / 'RefinedSkinV3'
ROOT = BASE / 'WristContourV4'
ROOT.mkdir(parents=True, exist_ok=True)
original = json.loads((SOURCE / 'M4_original.json').read_text())
shape = json.loads((SOURCE / 'M4_bare_shape.json').read_text())
if original.get('surface_winding') != 'ue_native':
    raise RuntimeError('Use the corrected, native-winding V3 source')

positions = np.asarray(shape['positions'], dtype=np.float64)
result = positions.copy()
triangles = np.asarray(original['triangles'])
skin = np.zeros(len(positions), dtype=bool)
skin[triangles[np.asarray(shape['triangle_materials']) == 2].ravel()] = True


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def smoother(t):
    t = np.clip(t, 0., 1.)
    return t * t * t * (t * (t * 6 - 15) + 10)


def envelope(t, peak=-.65):
    # Flat first/second derivatives keep the original cut-boundary transitions.
    return np.where(t < peak, smoother((t + 4.3) / (peak + 4.3)),
                    smoother((2.7 - t) / (2.7 - peak)))


report = {'base': str(SOURCE), 'range_cm': [-4.3, 2.7],
          'width_reduction_at_peak': .21, 'depth_reduction_at_peak': .23,
          'peak_cm': -.65, 'sides': {}, 'runtime_tested': False}
frames = {}
for side in ('l', 'r'):
    frame = shape['anatomy'][side]
    origin = np.asarray(frame['wrist'])
    forward = unit(np.asarray(frame['forward']))
    dorsal = np.asarray(frame['dorsal'])
    dorsal = unit(dorsal - forward * np.dot(dorsal, forward))
    radial = unit(np.cross(dorsal, forward))
    thumb = next(d for d in frame['digits'] if d['digit'] == 'thumb' and d['segment'] == 1)
    if np.dot(np.asarray(thumb['head']) - origin, radial) < 0:
        radial = -radial
    local = positions - origin
    longitudinal = local @ forward
    y, z = local @ radial, local @ dorsal
    belongs = positions[:, 0] < 0 if side == 'l' else positions[:, 0] > 0
    mask = skin & belongs & (longitudinal > -4.3 + 1e-5) & (longitudinal < 2.7 - 1e-5)
    # V3's evenly sampled inner rings give a stable geometric centreline. Do not
    # shrink about the bone origin: it is offset from the original wrist skin.
    stations = np.linspace(-4.3, 2.7, 13)[1:-1]
    centres = []
    for station in stations:
        ring = mask & (np.abs(longitudinal - station) < .015)
        centres.append([y[ring].mean(), z[ring].mean()])
    fit = np.polyfit(stations, np.asarray(centres), 1)
    t = longitudinal[mask]
    centre = t[:, None] * fit[0] + fit[1]
    cross, depth = y[mask] - centre[:, 0], z[mask] - centre[:, 1]
    theta = np.arctan2(depth, cross)
    e = envelope(t)
    cross_new = cross * (1 - .21 * e)
    depth_new = depth * (1 - .23 * e)

    def angular(center, spread):
        delta = np.arctan2(np.sin(theta - center), np.cos(theta - center))
        return np.exp(-(delta / spread) ** 2)

    # The thumb and little-finger sides have offset, low styloid landmarks.
    # They do not form a circular rim or an artificial cuff.
    relief = e * (.10 * np.exp(-((t + .05) / .80) ** 2) * angular(.12, .42)
                  + .13 * np.exp(-((t + .85) / .72) ** 2) * angular(2.93, .40))
    cross_new += np.cos(theta) * relief
    depth_new += np.sin(theta) * relief

    # Broad, shallow tendon transitions follow the arm length; silhouette is
    # supplied by the taper, not exaggerated material displacement.
    back = np.clip(np.sin(theta), 0., 1.) ** 6
    palm = np.clip(-np.sin(theta), 0., 1.) ** 6
    tendon = (np.exp(-((cross_new - (.64 + .12 * t)) / .38) ** 2)
              + .70 * np.exp(-((cross_new + (.69 - .07 * t)) / .46) ** 2))
    depth_new += .045 * e * back * tendon
    depth_new -= .028 * e * palm * np.exp(-((cross_new - .25) / .36) ** 2)
    result[mask] += ((cross_new - cross)[:, None] * radial
                     + (depth_new - depth)[:, None] * dorsal)
    frames[side] = {'radial': radial.tolist(), 'dorsal': dorsal.tolist(),
                    'centre_slope': fit[0].tolist(), 'centre_intercept': fit[1].tolist()}
    report['sides'][side] = {'authored_vertices': int(mask.sum()), 'stations': []}
    for station in stations:
        ring = mask & (np.abs(longitudinal - station) < .015)
        before = positions[ring] - origin
        after = result[ring] - origin
        report['sides'][side]['stations'].append({
            'longitudinal_cm': float(station),
            'width_before_cm': float(np.ptp(before @ radial)),
            'width_after_cm': float(np.ptp(after @ radial)),
            'depth_before_cm': float(np.ptp(before @ dorsal)),
            'depth_after_cm': float(np.ptp(after @ dorsal))})


def vertex_normals(p):
    corners = p[triangles]
    # UE native winding uses the opposite mathematical cross-product sign.
    face = -unit(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]))
    sums = np.zeros_like(p)
    for k in range(3):
        a = unit(corners[:, (k + 1) % 3] - corners[:, k])
        b = unit(corners[:, (k + 2) % 3] - corners[:, k])
        angle = np.arccos(np.clip(np.sum(a * b, axis=1), -1., 1.))
        np.add.at(sums, triangles[:, k], face * angle[:, None])
    return unit(sums)


# Rotate the existing corner normals with the local surface change. This keeps
# their original smoothing/seam offsets and leaves distant surfaces untouched.
before_normal, after_normal = vertex_normals(positions), vertex_normals(result)
axis = np.cross(before_normal, after_normal)[triangles]
dot = np.sum(before_normal * after_normal, axis=1)[triangles]
normals = np.asarray(shape['normals'])
rotated = normals + np.cross(axis, normals) + np.cross(axis, np.cross(axis, normals)) / np.maximum(1 + dot[..., None], 1e-8)
affected = np.linalg.norm(result - positions, axis=1) > 1e-9
adjacent = np.zeros(len(positions), dtype=bool)
adjacent[triangles[affected[triangles].any(axis=1)].ravel()] = True
new_normals = np.where(adjacent[triangles, None], unit(rotated), normals)
shape.update({'positions': result.tolist(), 'normals': new_normals.tolist(),
              'wrist_contour': frames})
shape['geometry_policy'] = {**shape.get('geometry_policy', {}),
    'wrist_v4': 'Local elliptical taper and shallow asymmetric landmarks; V3 topology, UVs, weights, bind pose and native winding retained',
    'wrist_range_cm': [-4.3, 2.7], 'contact_region': 'No position edits at or beyond +2.7 cm toward the fingers'}
original.update({'positions': shape['positions'], 'normals': shape['normals']})
for name, data in [('M4_original.json', original), ('M4_bare_shape.json', shape)]:
    (ROOT / name).write_text(json.dumps(data, separators=(',', ':')))
(ROOT / 'wrist_contour_authoring.json').write_text(json.dumps(report, indent=2))
print('WRIST_CONTOUR_AUTHORED', str(ROOT), int(affected.sum()))
