"""Cumulative palm-frame fist authoring and V7 skinned-surface measurements.

This is part of producing the requested hand repair, not a render or a game
test. Accepted PowerFist V2 supplies semantic palm directions; native staff
rest matrices, finger bone lengths and the actual V7 skin stay authoritative.
"""
import json
import math
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
SOURCE = ROOT / 'SourceAssets/ApprenticeStaff20260927/RightCarryV14/full-pose.json'
SKIN = ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json'
REFERENCE = ROOT / 'SourceAssets/LeftHandPowerFist20260923/fist_profile_v2.json'
ANATOMY = ROOT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json'
NATIVE_DIGITS = {d['bone']: d for d in json.loads(ANATOMY.read_text(encoding='utf-8'))['anatomy']['l']['digits']}
S = np.diag([1., -1., 1.])


def unit(v):
    return v / np.linalg.norm(v)


def reflected(m):
    out = np.eye(4)
    out[:3, :3] = S @ m[:3, :3] @ S
    out[:3, 3] = S @ m[:3, 3]
    return out


def palm_frame(forward, normal):
    x = unit(forward)
    z = unit(normal - x * (normal @ x))
    return np.column_stack((x, np.cross(x, z), z))


def axis_dorsal_frame(direction, dorsal):
    x = unit(direction)
    z = unit(dorsal - x * (dorsal @ x))
    return np.column_stack((x, np.cross(z, x), z))


def closed_pose(rest, parents, order, profile):
    # Use the same reflected Blender handedness as the accepted closed fist.
    # Profiles are cumulative directions in the palm, not local Euler angles.
    br = {n: reflected(m) for n, m in rest.items()}
    origin = br['hand_l'][:3, 3]
    normal = unit(np.cross(br['pinky_01_l'][:3, 3] - origin,
                           br['index_01_l'][:3, 3] - origin))
    palm = palm_frame(br['middle_01_l'][:3, 3] - origin, normal)
    pose = {n: m.copy() for n, m in br.items()}
    for n in order:
        par = parents[n]
        local = np.linalg.inv(br[par]) @ br[n]
        m = pose[par] @ local
        parts = n.split('_')
        if parts[0] in profile and len(parts) == 3 and parts[1].isdigit():
            k = int(parts[1]) - 1
            digit = profile[parts[0]]
            nxt = f'{parts[0]}_{k + 2:02d}_l'
            direction = (br[nxt][:3, 3] - br[n][:3, 3] if nxt in br else
                         br[n][:3, :3] @ br[par][:3, :3].T
                         @ (br[n][:3, 3] - br[par][:3, 3]))
            angle = math.radians(digit['spread'][k])
            neutral = palm_frame(palm @ np.asarray([math.cos(angle), math.sin(angle), 0.]), normal)
            target = Rotation.from_rotvec(neutral[:, 1] * math.radians(digit['flex'][k])).as_matrix() @ neutral
            m[:3, :3] = target @ palm_frame(direction, normal).T @ br[n][:3, :3]
            if parts[0] == 'thumb' and profile.get('_thumb_nail_outside', False):
                # An opposed thumb is not another folded index finger. Native
                # nail/pad orientation must roll with opposition. Keep the
                # nail on the exterior and the pad against collected digits.
                native = NATIVE_DIGITS[n]
                radial = -palm[:, 1]
                desired_dorsal = normal + radial * (.55, .18, 0.)[k]
                m[:3, :3] = (axis_dorsal_frame(target[:, 0], desired_dorsal)
                             @ axis_dorsal_frame(S @ np.asarray(native['axis']),
                                                S @ np.asarray(native['dorsal'])).T
                             @ br[n][:3, :3])
        pose[n] = m
    return {n: reflected(m) for n, m in pose.items()}


def make_surface(skin, rest):
    positions = np.asarray(skin['positions'], dtype=float)
    triangles = np.asarray(skin['triangles'], dtype=int)
    weights = skin['weights']
    bone_ids = {n: i for i, n in enumerate(rest)}
    slots = max(len(v) for v in weights)
    indices = np.zeros((len(weights), slots), dtype=int)
    amounts = np.zeros((len(weights), slots), dtype=float)
    for i, weights_i in enumerate(weights):
        for j, (n, w) in enumerate(weights_i.items()):
            indices[i, j], amounts[i, j] = bone_ids[n], w
    homogeneous = np.column_stack((positions, np.ones(len(positions))))
    inverse = np.asarray([np.linalg.inv(m) for m in rest.values()])

    def skin_pose(pose):
        deform = np.asarray(list(pose.values())) @ inverse
        transformed = np.einsum('vsij,vj->vsi', deform[indices], homogeneous)
        return np.sum(transformed[:, :, :3] * amounts[:, :, None], axis=1)

    regions = {}
    for d in ('thumb', 'index', 'middle', 'ring', 'pinky', 'palm'):
        values = np.asarray([sum(w for n, w in v.items() if n.endswith('_l')
                         and ((d == 'palm' and (n == 'hand_l' or 'metacarpal' in n))
                              or (d != 'palm' and n.startswith(d + '_') and 'metacarpal' not in n)))
                             for v in weights])
        regions[d] = np.flatnonzero(values > .70)
    thumb_tip = np.flatnonzero([v.get('thumb_03_l', 0.) > .85 for v in weights])
    region_faces = {d: triangles[np.isin(triangles, ids).all(axis=1)] for d, ids in regions.items()}
    return skin_pose, regions, region_faces, thumb_tip


def surface_record(vertices, pose, rest, regions, thumb_tip):
    origin = rest['hand_l'][:3, 3]
    f = unit(rest['middle_01_l'][:3, 3] - origin)
    a = unit(rest['index_01_l'][:3, 3] - rest['pinky_01_l'][:3, 3] - f
             * ((rest['index_01_l'][:3, 3] - rest['pinky_01_l'][:3, 3]) @ f))
    palm = np.column_stack((f, a, np.cross(a, f)))
    bounds = {}
    for d, ids in regions.items():
        coords = (vertices[ids] - origin) @ palm
        bounds[d] = {'min_cm': coords.min(axis=0).tolist(), 'max_cm': coords.max(axis=0).tolist()}
    target = np.concatenate((regions['index'], regions['middle']))
    distances, _ = cKDTree(vertices[target]).query(vertices[thumb_tip])
    return {'purpose': 'actual V7 surface during requested authoring; not runtime acceptance',
            'palm_axes': 'forward, radial toward thumb, palmar',
            'surface_bounds_palm_cm': bounds,
            'thumb_tip_nearest_index_middle_vertices_cm': {
                'minimum': float(distances.min()), 'p10': float(np.percentile(distances, 10.)),
                'median': float(np.median(distances))},
            'finger_joints_palm_cm': {n: ((pose[n][:3, 3] - origin) @ palm).tolist()
                                     for n in pose if n.endswith('_l') and n.startswith(
                                         ('index_', 'middle_', 'ring_', 'pinky_', 'thumb_'))},
            'bone_scale_changed': False, 'skin_changed': False}


if __name__ == '__main__':
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    rest = {n: np.asarray(m) for n, m in source['rest'].items()}
    order = [n for n in source['order'] if n.endswith('_l')]
    profile = json.loads(REFERENCE.read_text(encoding='utf-8'))
    skin = json.loads(SKIN.read_text(encoding='utf-8'))
    skin_pose, regions, faces, tip = make_surface(skin, rest)
    pose = closed_pose(rest, source['parent'], order, profile)
    result = surface_record(skin_pose(pose), pose, rest, regions, tip)
    (P / 'reference-v7-surface.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
