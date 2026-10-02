"""Author a relaxed door-guard thumb using the V7 skin and native hinges.

Only three thumb rotations are returned; this does not publish an animation,
change the shared donor fist, run Unreal, render, or perform acceptance tests.
The existing four-finger fist and the wrist/arm chain are input constraints.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation

sys.dont_write_bytecode = True
P = Path(__file__).resolve().parent
ROOT = P.parents[3]
THUMBS = ['thumb_01_l', 'thumb_02_l', 'thumb_03_l']
SOURCE = P.parent / 'BeforeAuthored/full-pose.json'
SKIN = ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/Authored/M4.json'
ANATOMY = ROOT / 'SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json'


def unit(v):
    return v / np.linalg.norm(v)


def swing(a, b):
    a, b = unit(a), unit(b)
    cross = np.cross(a, b)
    size = np.linalg.norm(cross)
    return (np.eye(3) if size < 1.e-10 else
            Rotation.from_rotvec(cross / size * math.atan2(size, a @ b)).as_matrix())


def source_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def author():
    source = json.loads(SOURCE.read_text(encoding='utf-8'))
    skin = json.loads(SKIN.read_text(encoding='utf-8'))
    anatomy = json.loads(ANATOMY.read_text(encoding='utf-8'))['anatomy']['l']
    digits = {x['bone']: x for x in anatomy['digits']}
    rest = {n: np.asarray(m, dtype=float) for n, m in source['rest'].items()}
    parent = source['parent']
    guard = next(p for p in source['poses'] if p['name'] == 'Prepare')
    # Work in the canonical rest hand frame; only the guard's hand-relative
    # finger assembly is needed. The parent later applies its own arm revision.
    canonical_hand = rest['hand_l']
    inverse_guard_hand = np.linalg.inv(np.asarray(guard['component']['hand_l']))
    old = {n: m.copy() for n, m in rest.items()}
    for n in source['order']:
        old[n] = canonical_hand @ inverse_guard_hand @ np.asarray(guard['component'][n])
    origin = canonical_hand[:3, 3]
    forward = unit(rest['middle_01_l'][:3, 3] - origin)
    radial = rest['index_01_l'][:3, 3] - rest['pinky_01_l'][:3, 3]
    radial = unit(radial - forward * (radial @ forward))
    palmar = np.cross(radial, forward)
    palm = np.column_stack((forward, radial, palmar))
    native_local = {n: np.linalg.inv(rest[parent[n]]) @ rest[n] for n in THUMBS}

    # Native CMC opposition consists of a swing followed by a bounded axial
    # turn. The prior donor forced the CMC dorsal onto the distal nail frame,
    # adding about 127 degrees of axial roll to the fleshy thumb root.
    native_axis = unit(rest['thumb_02_l'][:3, 3] - rest['thumb_01_l'][:3, 3])
    old_axis = unit(old['thumb_02_l'][:3, 3] - old['thumb_01_l'][:3, 3])
    old_swing = swing(native_axis, old_axis)
    old_twist = old['thumb_01_l'][:3, :3] @ (old_swing @ rest['thumb_01_l'][:3, :3]).T
    old_roll_degrees = math.degrees(Rotation.from_matrix(old_twist).as_rotvec() @ old_axis)
    # Use cumulative palm direction rather than local Euler channels. Reduce
    # the donor's 47.5-degree palmar CMC fold to 35 degrees, with 18 degrees of
    # radial opening. MP and IP are then flexed on their actual native hinges.
    cmc_palmar_fold = 35.0
    cmc_radial_opening = 18.0
    a, f = map(math.radians, (cmc_radial_opening, cmc_palmar_fold))
    desired_axis = unit(forward * math.cos(a) * math.cos(f)
                        + radial * math.sin(a) * math.cos(f)
                        + palmar * math.sin(f))
    cmc_swing = swing(native_axis, desired_axis)

    weights = skin['weights']
    positions = np.asarray(skin['positions'], dtype=float)
    inverse_rest = {n: np.linalg.inv(m) for n, m in rest.items()}
    tip_ids = []
    for i, w in enumerate(weights):
        if w.get('thumb_03_l', 0.0) < .70:
            continue
        delta = positions[i] - rest['thumb_03_l'][:3, 3]
        if delta @ np.asarray(digits['thumb_03_l']['dorsal']) < -.20:
            tip_ids.append(i)
    # Keep the distal pad vertices, excluding the proximal blended web.
    tip_ids = np.asarray(tip_ids, dtype=int)
    tip_native_longitudinal = ((positions[tip_ids] - rest['thumb_03_l'][:3, 3])
                               @ np.asarray(digits['thumb_03_l']['axis']))
    tip_ids = tip_ids[tip_native_longitudinal > np.percentile(tip_native_longitudinal, 55.)]
    bar_ids = np.asarray([i for i, w in enumerate(weights)
                          if sum(v for n, v in w.items() if n.startswith(('index_', 'middle_'))
                                 and n.endswith('_l') and 'metacarpal' not in n) > .75], dtype=int)

    def deform_vertices(ids, pose):
        values = np.zeros((len(ids), 3))
        for k, i in enumerate(ids):
            v = np.append(positions[i], 1.)
            for n, amount in weights[i].items():
                values[k] += (pose[n] @ inverse_rest[n] @ v)[:3] * amount
        return values

    fixed_bar = deform_vertices(bar_ids, old)
    bar_coordinates = (fixed_bar - origin) @ palm
    # Restrict to the exterior between the index and middle fingers. This
    # avoids the earlier tip-only fit which stretched across toward the ring.
    requested_anchor = np.asarray([8.9, 1.75, 5.85])
    bar_region = ((bar_coordinates[:, 0] > 7.0) & (bar_coordinates[:, 0] < 10.6)
                  & (bar_coordinates[:, 1] > .65) & (bar_coordinates[:, 1] < 3.6)
                  & (bar_coordinates[:, 2] > 4.8))
    eligible_bar = fixed_bar[bar_region]
    eligible_coordinates = bar_coordinates[bar_region]
    nearest = int(np.argmin(np.sum((eligible_coordinates - requested_anchor)**2, axis=1)))
    surface_anchor = eligible_bar[nearest]
    target_pad = surface_anchor + palmar * .14

    def pose_thumb(x):
        cmc_roll, mp_flex, ip_flex = np.radians(x)
        pose = {n: m.copy() for n, m in old.items()}
        root = pose['thumb_01_l']
        root[:3, :3] = (Rotation.from_rotvec(desired_axis * cmc_roll).as_matrix()
                        @ cmc_swing @ rest['thumb_01_l'][:3, :3])
        # Distal joints follow the CMC opposition as a chain. Each bend uses
        # the rig's existing across axis; there is no independent nail roll.
        for n, angle in zip(THUMBS[1:], (mp_flex, ip_flex)):
            par = parent[n]
            current = pose[par] @ native_local[n]
            parent_delta = pose[par][:3, :3] @ rest[par][:3, :3].T
            hinge = unit(parent_delta @ np.asarray(digits[n]['across']))
            current[:3, :3] = Rotation.from_rotvec(hinge * angle).as_matrix() @ current[:3, :3]
            pose[n] = current
        return pose

    # The rig's CMC opposition is signed negative about this native long axis.
    # Retain that side of opposition while removing the donor's excess roll.
    reference = np.asarray([-90., 22., 12.])

    def residual(x):
        pose = pose_thumb(x)
        pad = deform_vertices(tip_ids, pose).mean(axis=0)
        return np.concatenate(((pad - target_pad), (x - reference) * .025))

    # This bounded fit is production pose construction on canonical geometry;
    # it is not a UE readback, visual check, runtime test, or acceptance result.
    result = least_squares(residual, reference, bounds=([-105., 4., 3.], [-65., 55., 30.]),
                           max_nfev=65, ftol=1.e-9, xtol=1.e-9, gtol=1.e-9)
    authored = pose_thumb(result.x)
    local = {n: np.linalg.inv(authored[parent[n]]) @ authored[n] for n in THUMBS}
    rotations = {n: Rotation.from_matrix(local[n][:3, :3]).as_quat().tolist() for n in THUMBS}
    pad = deform_vertices(tip_ids, authored).mean(axis=0)
    old_pad = deform_vertices(tip_ids, old).mean(axis=0)
    data = dict(schema='door_guard_thumb_rotation_patch_v1', revision=2026100209,
                authored_status='three_thumb_rotations_ready_for_parent_merge',
                rotation_format='quaternion_xyzw', bone_names=THUMBS,
                local_rotation_xyzw=rotations,
                local_matrices={n: local[n].tolist() for n in THUMBS},
                frozen_bones='Every bone other than thumb_01_l/thumb_02_l/thumb_03_l',
                application_keys=source['key_names'][1:-1],
                entry_recovery_contract='Leave first/last example keys unchanged; existing live entry/recovery interpolates into/out of corrected guard',
                source=str(SOURCE), source_sha256=source_hash(SOURCE), source_revision=source['revision'],
                canonical_skin=str(SKIN), canonical_skin_sha256=source_hash(SKIN),
                native_digit_anatomy=str(ANATOMY), native_digit_anatomy_sha256=source_hash(ANATOMY),
                method='Bounded native CMC swing/opposition and MP/IP hinge flexion; canonical skinned pad construction; no local Euler fit or independent nail roll',
                cmc_palmar_fold_degrees=cmc_palmar_fold, cmc_radial_opening_degrees=cmc_radial_opening,
                native_joint_parameters_degrees=dict(zip(['cmc_axis_roll','mp_additional_flex','ip_additional_flex'], result.x.tolist())),
                previous_cmc_axis_roll_degrees=old_roll_degrees,
                cmc_axis_roll_bounds_degrees=[-105.,-65.], mp_flex_bounds_degrees=[4.,55.], ip_flex_bounds_degrees=[3.,30.],
                authoring_surface_anchor_palm_cm=((surface_anchor-origin)@palm).tolist(),
                authoring_target_pad_palm_cm=((target_pad-origin)@palm).tolist(),
                previous_pad_centroid_palm_cm=((old_pad-origin)@palm).tolist(),
                authored_pad_centroid_palm_cm=((pad-origin)@palm).tolist(),
                actual_canonical_pad_vertex_count=int(len(tip_ids)),
                geometry_weights_rest_scales_lengths_translations_changed=False,
                wrist_or_arm_authored=False, source_donor_modified=False,
                runtime_tested=False, rendered=False, ue_launched=False, imported=False,
                note='Numerical authoring records describe the constructed candidate only; final hand shape remains for user testing')
    (P / 'thumb-rotations.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
    print('DOOR_GUARD_THUMB_AUTHOR_SAVED', len(THUMBS), result.x.tolist(), flush=True)


def apply_to_pose_data(data, patch=None):
    """Update thumb rotations and component transforms after the arm merge.

    The caller retains all translations/scales and rebuilds any header/Blend.
    This does not change global donor fists or unrelated gameplay actions.
    """
    patch = patch or json.loads((P / 'thumb-rotations.json').read_text(encoding='utf-8'))
    keys = set(patch['application_keys'])
    for pose in data['poses']:
        if pose['name'] not in keys:
            continue
        for n, q in patch['local_rotation_xyzw'].items():
            matrix = np.asarray(pose['local'][n], dtype=float)
            matrix[:3, :3] = Rotation.from_quat(q).as_matrix()
            pose['local'][n] = matrix.tolist()
        # Rebuild only the thumb chain from the merged hand transform. The
        # caller may have changed the wrist or arm, which remains authoritative.
        for n in THUMBS:
            pose['component'][n] = (np.asarray(pose['component'][data['parent'][n]])
                                    @ np.asarray(pose['local'][n])).tolist()
    data['door_guard_thumb_patch'] = {k: patch[k] for k in (
        'revision','source','canonical_skin','method','local_rotation_xyzw',
        'native_joint_parameters_degrees','previous_cmc_axis_roll_degrees')}
    return data


if __name__ == '__main__':
    author()
