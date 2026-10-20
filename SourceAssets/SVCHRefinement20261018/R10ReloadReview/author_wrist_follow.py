"""Keep the R9 magazine anchor and native hand pose; let the arm bend plane follow it."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar

O = Path(__file__).parent
R9 = O.parent / 'R9ReloadGrip'
env = {'__file__': str(R9 / 'author_reload_grip.py')}
code = (R9 / 'author_reload_grip.py').read_text().split("report={'method'")[0]
exec(compile(code, str(R9 / 'author_reload_grip.py'), 'exec'), env)
globals().update({k: v for k, v in env.items() if k not in ('O', '__file__', '__builtins__')})
profile = json.loads((R9 / 'profile_reload_grip.json').read_text())
original = json.loads((R9 / 'Inputs/profile_before.json').read_text())
report = {'method': 'Keep R9 hand-magazine relation; solve nearest arm bend plane using native wrist orientation',
          'source_fingers_mesh_rest_weights_unchanged': True, 'clips': {}}


def frame(axis, normal):
    axis = unit(axis)
    normal = unit(normal - axis * (normal @ axis))
    return np.column_stack((axis, np.cross(normal, axis), normal))


def arm_follow(old, hand):
    p = old.copy()
    ci, ui, li, hi = [NI[x + '_l'] for x in ('clavicle', 'upperarm', 'lowerarm', 'hand')]
    shoulder, elbow, wrist = [old[j, :3, 3].copy() for j in (ui, li, hi)]
    target = hand[:3, 3]
    l1, l2 = np.linalg.norm(elbow - shoulder), np.linalg.norm(wrist - elbow)
    if np.linalg.norm(target - shoulder) > l1 + l2 - .4:
        c = old[ci, :3, 3]
        radius, d = np.linalg.norm(shoulder - c), np.linalg.norm(target - c)
        axis = unit(target - c)
        side = unit(shoulder - c - axis * ((shoulder - c) @ axis))
        cosine = np.clip((radius * radius + d * d - (l1 + l2 - .4) ** 2) / (2 * radius * d), -1, 1)
        shoulder = c + axis * radius * cosine + side * radius * np.sqrt(max(0, 1 - cosine * cosine))
        p[ci] = aimed(old[ci], old[ui, :3, 3], c, shoulder)
    axis = unit(target - shoulder)
    d = np.linalg.norm(target - shoulder)
    pole = unit(elbow - shoulder - axis * ((elbow - shoulder) @ axis))
    along = (l1 * l1 - l2 * l2 + d * d) / (2 * max(d, 1e-9))
    radius = np.sqrt(max(0, l1 * l1 - along * along))
    old_normal = unit(np.cross(elbow - old[ui, :3, 3], wrist - elbow))
    upper_frame = frame(elbow - old[ui, :3, 3], old_normal)
    lower_frame = frame(wrist - elbow, old_normal)
    old_fore = R.from_matrix(rigid(old[li])[:3, :3])
    old_hand = R.from_matrix(rigid(old[hi])[:3, :3])
    hand_rotation = R.from_matrix(rigid(hand)[:3, :3])
    source_wrist = old_fore.inv() * old_hand

    def candidate(angle):
        direction = R.from_rotvec(axis * angle).apply(pole)
        e = shoulder + axis * along + direction * radius
        normal = unit(np.cross(e - shoulder, target - e))
        du = frame(e - shoulder, normal) @ upper_frame.T
        dl = frame(target - e, normal) @ lower_frame.T
        fore_rotation = R.from_matrix(dl) * old_fore
        delta = fore_rotation.inv() * hand_rotation * source_wrist.inv()
        return e, du, dl, delta

    # Rotate the bend plane instead of assigning the registration rotation to
    # the wrist. A small source-pole penalty keeps the nearest continuous arc.
    result = minimize_scalar(lambda a: candidate(a)[3].magnitude() ** 2 + .035 * a * a,
                             bounds=(-np.deg2rad(70), np.deg2rad(70)), method='bounded')
    e, upper, lower, delta = candidate(result.x)
    for n in left_chain:
        j = NI[n]
        if n.startswith('upperarm'):
            p[j, :3, :3] = upper @ old[j, :3, :3]
            p[j, :3, 3] = shoulder + upper @ (old[j, :3, 3] - old[ui, :3, 3])
        elif n.startswith('lowerarm'):
            p[j, :3, :3] = lower @ old[j, :3, :3]
            p[j, :3, 3] = e + lower @ (old[j, :3, 3] - old[li, :3, 3])
    p[hi] = hand
    fore_new = R.from_matrix(rigid(p[li])[:3, :3])
    q = delta.as_quat()
    if q[3] < 0:
        q = -q
    fore_axis = old_fore.inv().apply(unit(wrist - elbow))
    roll = 2 * np.arctan2(q[:3] @ fore_axis, q[3])
    for name, share in (('lowerarm_twist_01_l', 1.), ('lowerarm_twist_02_l', .5)):
        j = NI[name]
        change = fore_new * R.from_rotvec(fore_axis * roll * share) * fore_new.inv()
        p[j, :3, :3] = change.as_matrix() @ p[j, :3, :3]
    return p, float(np.rad2deg(result.x)), float(np.rad2deg(delta.magnitude()))


for role in ('reload', 'reload_empty'):
    clip = motion['clips'][role]
    base = np.asarray(clip['frames'])
    entry = next(c for c in profile['clips'] if c['base'] == clip['path'])
    native = next(c for c in original['clips'] if c['base'] == clip['path'])
    tracks = {n: [] for n in left_chain}
    diagnostics = []
    for i, time in enumerate(clip['times']):
        current = old_pose(base[i], entry, time)
        baseline = old_pose(base[i], native, time)
        world = comp(matrices(current))
        source = comp(matrices(baseline))
        active = ease(18, 49, time * 120) * (1 - ease(244, 302, time * 120))
        if active > 1e-9:
            new, angle, wrist_delta = arm_follow(source, world[HAND])
        else:
            new, angle, wrist_delta = world, 0., 0.
        authored = current.copy()
        for n in left_chain:
            j = NI[n]
            local = np.linalg.solve(new[PI[j]], new[j])
            rot = R.from_matrix(rigid(local)[:3, :3])
            delta = rot * R.from_quat(base[i, j, 3:7]).inv()
            values = [*(current[j, :3] - base[i, j, :3]), *delta.as_quat(), *(current[j, 7:] - base[i, j, 7:])]
            if tracks[n] and np.dot(tracks[n][-1][3:7], values[3:7]) < 0:
                values[3:7] = [-v for v in values[3:7]]
            tracks[n].append(values)
            authored[j, 3:7] = rot.as_quat()
        actual = comp(matrices(authored))
        diagnostics.append({'frame': i, 'bend_plane_deg': angle, 'wrist_delta_deg': wrist_delta,
                            'anchor_error_cm': float(np.linalg.norm(actual[HAND, :3, 3] - world[HAND, :3, 3]))})
    entry['tracks'] = [t for t in entry['tracks'] if t['bone'] not in left_chain]
    for name, values in tracks.items():
        entry['tracks'].append({'bone': name, 'times': clip['times'], 'values': np.round(values, 10).ravel().tolist()})
    report['clips'][role] = diagnostics
    print('ARM_FOLLOW', role, 'max_wrist_delta_deg', max(r['wrist_delta_deg'] for r in diagnostics),
          'anchor_error_cm', max(r['anchor_error_cm'] for r in diagnostics), flush=True)
(O / 'profile_wrist_follow.json').write_text(json.dumps(profile, separators=(',', ':')))
(O / 'authoring_receipt.json').write_text(json.dumps(report, indent=2))
print('ARM_FOLLOW_AUTHORED', flush=True)
