"""Fit the Chapel Nun's relaxed standing loop to the innkeeper's native rig."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation


PROJECT = Path(__file__).resolve().parents[3]
DONOR = PROJECT / 'SourceAssets/ChapelNun20261115/IdleRelaxedR3/authored.json'


def unit(v):
    return v / np.linalg.norm(v)


def forward_kinematics(frame, parents):
    matrices = np.tile(np.eye(4), (len(frame), 1, 1))
    matrices[:, :3, :3] = Rotation.from_quat(frame[:, 3:7]).as_matrix() * frame[:, None, 7:10]
    matrices[:, :3, 3] = frame[:, :3]
    for i, parent in enumerate(parents):
        if parent >= 0:
            matrices[i] = matrices[parent] @ matrices[i]
    return matrices


def rotation(matrix):
    axes = matrix[:3, :3]
    return Rotation.from_matrix(axes / np.linalg.norm(axes, axis=0))


def body_frame(positions, left, right, feet, toes):
    up = np.array([0., 0., 1.])  # Both reference snapshots use UE component space.
    across = positions[left] - positions[right]
    across = unit(across - up * np.dot(across, up))
    forward = unit(np.cross(up, across))
    toe_direction = np.mean(positions[toes] - positions[feet], axis=0)
    if np.dot(forward, toe_direction) < 0:
        forward *= -1
    return np.column_stack((across, forward, up))


def swing(current, desired):
    a, b = unit(current), unit(desired)
    axis = np.cross(a, b)
    length = np.linalg.norm(axis)
    if length < 1e-9:
        return Rotation.identity()
    return Rotation.from_rotvec(axis / length * math.atan2(length, np.dot(a, b)))


def bake(reference, source):
    names, parents = reference['names'], reference['parents']
    native = np.array(reference['reference'])
    rest = forward_kinematics(native, parents)
    source_rest = forward_kinematics(np.asarray(source['frames'][0]), source['parents'])
    s = {n: i for i, n in enumerate(source['names'])}
    t = {n: i for i, n in enumerate(names)}
    arm_names = ('upperarm', 'lowerarm', 'hand', 'middle_01')
    target_basis = body_frame(rest[:, :3, 3], t['upperarm_l'], t['upperarm_r'],
                              [t['foot_l'], t['foot_r']], [t['ball_l'], t['ball_r']])
    source_basis = body_frame(source_rest[:, :3, 3], s['upperarm_l'], s['upperarm_r'],
                              [s['foot_l'], s['foot_r']], [s['ball_l'], s['ball_r']])
    component_map = target_basis @ source_basis.T

    # Reduce the donor's five spine segments to the three in the Meshy rig.
    torso = [(t['spine_01'], s['spine_02']), (t['spine_02'], s['spine_03']), (t['spine_03'], s['spine_05'])]
    torso += [(t[n], s[n]) for n in ('neck_01', 'head', 'clavicle_l', 'clavicle_r')]
    moving = sorted({b for b, _ in torso} | {t[n+'_'+side] for side in ('l', 'r') for n in arm_names[:-1]})
    tracks = {n: [] for n in moving}
    count = len(source['frames'])
    for index, source_frame in enumerate(source['frames'][:-1]):
        source_world = forward_kinematics(np.asarray(source_frame), source['parents'])
        frame = native.copy()
        world = rest.copy()

        def set_world_rotation(b, desired):
            frame[b, 3:7] = (rotation(world[parents[b]]).inv() * desired).as_quat()

        phase = 2 * math.pi * index / (count - 1)
        inhale = ((math.sin(3*phase) + .12*math.sin(6*phase-.35)) * (1+.05*math.sin(phase+.6)))
        for bone, src in torso:
            d = rotation(source_world[src]) * rotation(source_rest[src]).inv()
            delta = Rotation.from_matrix(component_map @ d.as_matrix() @ component_map.T)
            set_world_rotation(bone, delta * rotation(rest[bone]))
            if bone == t['spine_03']:
                # One small vertical expansion of the rib cage; legs remain grounded.
                shift = target_basis[:, 2] * (.22 * inhale)
                frame[bone, :3] += np.linalg.solve(world[parents[bone], :3, :3], shift)
            world = forward_kinematics(frame, parents)

        for suffix in ('l', 'r'):
            chain = [t[n+'_'+suffix] for n in arm_names]
            donor_chain = [s[n+'_'+suffix] for n in arm_names]
            # If the sculpt's own arms already hang low, preserve its sleeve and
            # apron clearance while borrowing the relaxed flexion and wrist motion.
            upper_rest = unit(rest[chain[1], :3, 3] - rest[chain[0], :3, 3])
            keep_pose = .55 * np.clip((-upper_rest[2] - .55) / .38, 0., 1.)
            for j, (bone, child) in enumerate(zip(chain, chain[1:])):
                donor, next_donor = donor_chain[j:j+2]
                current = world[child, :3, 3] - world[bone, :3, 3]
                model = unit(rest[child, :3, 3] - rest[bone, :3, 3])
                relaxed = component_map @ unit(source_rest[next_donor, :3, 3] - source_rest[donor, :3, 3])
                animated = component_map @ unit(source_world[next_donor, :3, 3] - source_world[donor, :3, 3])
                desired = unit((1-keep_pose)*relaxed + keep_pose*model) + animated - relaxed
                set_world_rotation(bone, swing(current, desired) * rotation(world[bone]))
                world = forward_kinematics(frame, parents)
        for b in moving:
            tracks[b].append(frame[b].copy())

    result = {}
    for b, keys in tracks.items():
        keys.append(keys[0].copy())
        for last, key in zip(keys, keys[1:]):
            if np.dot(last[3:7], key[3:7]) < 0:
                key[3:7] *= -1
        result[names[b]] = np.asarray(keys).tolist()
    return dict(rate=source['rate'], frame_count=count-1, tracks=result)


if __name__ == '__main__':
    rig_path, clip_path = map(Path, sys.argv[1:3])
    result = bake(json.loads(rig_path.read_text()), json.loads(DONOR.read_text(encoding='utf-8')))
    clip_path.write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
