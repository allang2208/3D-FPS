"""Offline SVD near-camera diagnosis; no runtime or visual acceptance claim.

Uses native compressed poses and the source-code PSO/LPVO/hip calibration.
The numeric support solve mirrors FPSOutfitArmClearance.cpp. Source hands and
weapon bones are immutable; report projected upper-arm intrusion separately
from topology/LOD defects.
"""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from garment_motion import matrix, prepare, posed
from garment_pipeline import read, write

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/ChainmailCameraClearance20260929'


def smooth(a, b, value):
    t = np.clip((value - a) / (b - a), 0., 1.)
    return t * t * (3. - 2. * t)


def swing(a, b):
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    v, dot = np.cross(a, b), np.dot(a, b)
    if dot < -.999999:
        axis = np.cross(a, [0., 0., 1.])
        if np.linalg.norm(axis) < 1.e-6:
            axis = np.cross(a, [0., 1., 0.])
        return Rotation.from_rotvec(axis / np.linalg.norm(axis) * np.pi).as_matrix()
    skew = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + skew + skew @ skew / (1. + dot)


def camera_frame(bones, optic):
    if optic == 'hip':
        result = np.eye(4)
        result[:3, :3] = Rotation.from_euler('z', 90, degrees=True).as_matrix()
        result[:3, 3] = [6., 7., -7.]
        return result
    root = bones['WPN_root']
    if optic == 'lpvo':
        mount = np.eye(4)
        mount[:3, :3] = Rotation.from_euler('z', 90, degrees=True).as_matrix() * .01
        mount[:3, 3] = [.0000364, .020, .086]
        optical = root @ mount
        rear = (optical @ [-12.15, 0., 4., 1.])[:3]
        forward, up = optical[:3, 0], optical[:3, 2]
        eye = 28.
    else:
        rear = bones['WPN_RearSight'][:3, 3]
        forward = bones['WPN_FrontSight'][:3, 3] - rear
        up, eye = root[:3, 2], 7.
    forward = forward / np.linalg.norm(forward)
    right = np.cross(up, forward)
    right /= np.linalg.norm(right)
    result = np.eye(4)
    result[:3, :3] = np.array([forward, right, np.cross(forward, right)])
    result[:3, 3] = [eye, 0., 0.] - result[:3, :3] @ rear
    return result


def correct(bones, frame):
    result = {name: value.copy() for name, value in bones.items()}
    inverse = np.linalg.inv(frame)
    details = []
    for side, sign in [('l', -1), ('r', 1)]:
        upper, lower, hand = ['upperarm_' + side, 'lowerarm_' + side, 'hand_' + side]
        shoulder, elbow, wrist = [(frame @ bones[n])[:3, 3] for n in [upper, lower, hand]]
        weight = smooth(-4., 4., shoulder[0]) * smooth(-12., -4., shoulder[2]) * (1. - smooth(24., 40., abs(shoulder[1])))
        if weight < 1.e-8:
            continue
        ul, ll = np.linalg.norm(elbow - shoulder), np.linalg.norm(wrist - elbow)
        if ul < 1. or ll < 1.:
            continue
        desired = np.array([min(shoulder[0], -10.), sign * max(sign * shoulder[1], 18.), min(shoulder[2], -18.)])
        target = shoulder + (desired - shoulder) * weight
        if np.linalg.norm(shoulder - wrist) < 1.e-8 or np.linalg.norm(target - wrist) < 1.e-8:
            continue
        reach_rotation = swing(shoulder - wrist, target - wrist)
        target = wrist + reach_rotation @ (shoulder - wrist)
        solved = wrist + reach_rotation @ (elbow - wrist)
        h = bones[hand][:3, 3]
        mesh_reach_rotation = inverse[:3, :3] @ reach_rotation @ frame[:3, :3]
        delta = np.eye(4)
        delta[:3, :3] = mesh_reach_rotation
        delta[:3, 3] = h - mesh_reach_rotation @ h
        for name in bones:
            if name.endswith('_' + side) and name.startswith(('clavicle_', 'upperarm', 'lowerarm')):
                result[name] = delta @ bones[name]
        details.append(dict(side=side, weight=float(weight), shoulder_before=shoulder.tolist(),
            shoulder_after=target.tolist(), upper_length_error=abs(float(np.linalg.norm(solved-target)-ul)),
            lower_length_error=abs(float(np.linalg.norm(wrist-solved)-ll))))
    return result, details


def intrusion(points, frame, upper_ids):
    p = points[upper_ids] @ frame[:3, :3].T + frame[:3, 3]
    # A fixed central view cone above the crosshair; counts are not pixels.
    visible = (p[:, 0] > .5) & (np.abs(p[:, 1]) < p[:, 0]) & (p[:, 2] > 0.) & (p[:, 2] < p[:, 0] * .55)
    return int(np.sum(visible))


def main(historical=False):
    if historical:
        poses = read(P/'SourceAssets/SVDOutfitSpike20260929/poses.json')
        d = read(P/'SourceAssets/SVDRuntimeDiagnosis20260929/ue_chainmail_shirt_rig_meshes_LOD0.json')
    else:
        poses = read(R/'SVD/poses.json')['poses']
        d = read(R/'SVD/LOD0.json')
    data = prepare(d)
    upper = np.array([i for i, w in enumerate(d['weights']) if sum(v for n, v in w.items() if n.startswith(('clavicle', 'upperarm'))) > .65])
    rows = []
    for pose in poses:
        mats = {n: matrix(t) for n, t in pose['bones'].items()}
        if historical and not {'upperarm_l', 'upperarm_r'}.issubset(mats):
            continue
        optics = ['pso', 'lpvo'] if pose['clip'].endswith('_aim') else ['hip']
        if '_aim_fire' in pose['clip']:
            continue
        for optic in optics:
            frame = camera_frame(mats, optic)
            solved, details = correct(mats, frame)
            immutable = [n for n in mats if n.startswith(('hand_', 'thumb_', 'index_', 'middle_', 'ring_', 'pinky_', 'WPN_'))]
            error = max(float(np.max(np.abs(mats[n] - solved[n]))) for n in immutable)
            rows.append(dict(clip=pose['clip'], time=pose['time'], optic=optic,
                upper_intrusion_before=intrusion(posed(data, mats), frame, upper),
                upper_intrusion_after=intrusion(posed(data, solved), frame, upper),
                hand_weapon_matrix_error=error, corrections=details))
    summary = dict(samples=len(rows), before_affected=sum(r['upper_intrusion_before']>0 for r in rows),
        after_affected=sum(r['upper_intrusion_after']>0 for r in rows),
        max_immutable_error=max(r['hand_weapon_matrix_error'] for r in rows),
        max_bone_length_error=max((max(a['upper_length_error'],a['lower_length_error']) for r in rows for a in r['corrections']),default=0),
        historical_inputs=historical, runtime_visual='pending',
        scope='Offline fixed upper-view cone, compressed poses, no live IK/WPO or rendered occlusion acceptance')
    write(R/('historical-camera-diagnosis.json' if historical else 'camera-diagnosis.json'), dict(summary=summary, rows=rows))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--historical', action='store_true')
    main(parser.parse_args().historical)
