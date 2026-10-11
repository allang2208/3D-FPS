"""R9: station-based forearm roll, with the installed palm and strike preserved."""
import copy
from support_geometry import *

# Re-encode hand local keys because its forearm parent changes. Its author-world
# transform and every finger remain the installed R8 values.
WRITE[:] = ['lowerarm_r', 'lowerarm_aux_r', 'lowerarm_twist_02_r',
            'lowerarm_twist_01_r', 'hand_r']


def forearm_frames(p):
    a, e, h = [p[n][:3, 3] for n in ('upperarm_r', 'lowerarm_r', 'hand_r')]
    fore = h - e
    hinge = unit(np.cross(e - a, fore))
    neutral = basis(fore, hinge) @ FF.T
    palm = (rot(p['hand_r']) * rot(rest['hand_r']).inv()).as_matrix()
    palm_axis, axis = unit(palm @ rf), unit(fore)
    cross = np.cross(palm_axis, axis)
    align = R.identity().as_matrix() if np.linalg.norm(cross) < 1e-9 else turn(
        cross, np.arctan2(np.linalg.norm(cross), np.clip(palm_axis @ axis, -1, 1)))
    distal = align @ palm
    roll = R.from_matrix(distal @ neutral.T).as_rotvec() @ axis
    return e, fore, neutral, roll


def solve(family):
    source, local = decode(family)
    frames = [forearm_frames(p) for p in source]
    rolls = np.unwrap([f[3] for f in frames])
    output = {n: [] for n in WRITE}
    poses = []
    for i, p in enumerate(source):
        q = {n: m.copy() for n, m in p.items()}
        w = blend[i]
        if w > 1e-8:
            e, fore, neutral, _ = frames[i]
            axis = unit(fore)
            proximal = turn(axis, rolls[i] * .35) @ neutral
            du = (rot(p['upperarm_r']) * rot(rest['upperarm_r']).inv()).as_matrix()
            for n in WRITE[:-1]:
                offset = rest[n][:3, 3] - rest['lowerarm_r'][:3, 3]
                station = offset @ rf / (rf @ rf)
                # The actual skin stations are elbow, 1/3, 2/3. Spread only
                # axial pronation; never translate a mid-arm station toward a
                # wrist-anchored frame or pass the whole wrist bend to it.
                amount = .35 + .65 * ease(station / (2 / 3))
                driver = turn(axis, rolls[i] * amount) @ neutral
                if n == 'lowerarm_aux_r':
                    driver = mix(du, proximal, .5)
                position = e + station * fore + driver @ (offset - station * rf)
                target = driver @ rot(rest[n]).as_matrix()
                q[n][:3, :3] = mix(rot(p[n]).as_matrix(), target, w) * np.linalg.norm(p[n][:3, :3], axis=0)
                q[n][:3, 3] = p[n][:3, 3] * (1 - w) + position * w
        packed = encode(q)
        for n in WRITE:
            output[n].append(packed[n])
        poses.append({n: m.tolist() for n, m in q.items()})
    for n in WRITE:
        local[n] = np.array(output[n])
    return local, poses


result = copy.deepcopy(D)
result.update(revision='Super90QuickMelee-RightArmR9-20261010', write_bones=WRITE,
              runtime_tested=False, ownership_curve=json.loads(
                  (O.parent / 'RightArmR8/animation_patch.json').read_text())['ownership_curve'])
base, poses = solve('base')
allposes = {'base': poses}
result['base_tracks'] = [track(t['bone'], base[t['bone']]) if t['bone'] in WRITE else t for t in D['base_tracks']]
zero = np.array([0, 0, 0, 0, 0, 0, 1, 0, 0, 0])
for family in D['profiles']:
    local, poses = solve(family)
    allposes[family] = poses
    tracks = [t for t in D['profiles'][family]['clip']['tracks'] if t['bone'] not in WRITE]
    for n in WRITE:
        quat = (R.from_quat(local[n][:, 3:7]) * R.from_quat(base[n][:, 3:7]).inv()).as_quat()
        quat[quat[:, 3] < 0] *= -1
        delta = np.c_[local[n][:, :3] - base[n][:, :3], quat, local[n][:, 7:] - base[n][:, 7:]]
        if np.max(np.abs(delta - zero)) > 1e-7:
            tracks.append(track(n, delta))
    result['profiles'][family]['clip']['tracks'] = tracks
(O / 'animation_patch.json').write_text(json.dumps(result, separators=(',', ':')))
(O / 'authored_poses.json').write_text(json.dumps(allposes, separators=(',', ':')))
print('SUPER90_RIGHT_ARM_R9_AUTHORED', len(allposes), 'families', flush=True)
