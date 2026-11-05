"""Rigid palm registration and native-length arm fitting for Kaitlin clips."""
import json
from pathlib import Path
import os
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(os.environ['FPSGAME_PROJECT']).resolve()
W = Path(__file__).resolve().parent
K = P / 'SourceAssets/KaitlinPlayer20261023'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))


def unit(x):
    return x / max(float(np.linalg.norm(x)), 1e-12)


def mul(a, b):
    return (R.from_quat(a) * R.from_quat(b)).as_quat()


def rotate(q, v):
    return R.from_quat(q).apply(v)


def compose(a, b):
    return np.r_[a[:3] + rotate(a[3:7], b[:3]), mul(a[3:7], b[3:7])]


def inverse(a):
    q = R.from_quat(a[3:7]).inv().as_quat()
    return np.r_[rotate(q, -a[:3]), q]


def frame(x, y):
    x = unit(x)
    y = unit(y - x * np.dot(x, y))
    return R.from_matrix(np.column_stack((x, y, np.cross(x, y)))).as_quat()


def skeleton(data):
    bones = data['bones']
    names = [b['name'] for b in bones]
    parents = [b['parent'] for b in bones]
    world = np.array([list(b['position']) + R.from_matrix(np.array(b['axes']).T).as_quat().tolist() for b in bones])
    local = np.array([compose(inverse(world[p]), world[i]) if p >= 0 else world[i] for i, p in enumerate(parents)])
    return {'names': names, 'parents': parents, 'index': {n:i for i,n in enumerate(names)}, 'world': world,
            'local': np.column_stack((local, np.ones((len(local), 3))))}


def bodies():
    cfg = read(P / 'Content/ColdSteelData/player_body.json')
    captured = read(K / 'FitInputs/captured.json')
    return (skeleton(read(K / 'FitInputs' / captured[cfg['body_mesh']]['file'])),
            skeleton(read(K / 'NativeGeometry/MHC_Kaitlin_Body.json')))


def fk(local, skel):
    world = np.array(local).copy()
    for i, p in enumerate(skel['parents']):
        if p >= 0:
            world[i, :3] = world[p, :3] + rotate(world[p, 3:7], local[i, :3] * world[p, 7:])
            world[i, 3:7] = mul(world[p, 3:7], local[i, 3:7])
            world[i, 7:] = world[p, 7:] * local[i, 7:]
    return world


def expand(sample, skel):
    frames = np.repeat(skel['local'][None], len(sample['frames']), axis=0)
    for i, name in enumerate(sample['names']):
        frames[:, skel['index'][name]] = np.array(sample['frames'])[:, i]
    return frames


def palm_mount(source, target, side):
    points = []
    for skel in (source, target):
        ix = skel['index']
        hand = skel['world'][ix['hand_' + side]]
        points.append(np.array([compose(inverse(hand), skel['world'][ix[n + '_01_' + side]])[:3]
                                for n in ('index', 'middle', 'pinky')]))
    a, b = points
    q = mul(frame(b[1], b[0] - b[2]), R.from_quat(frame(a[1], a[0] - a[2])).inv().as_quat())
    return np.r_[b.mean(0) - rotate(q, a.mean(0)), q]


if __name__ == '__main__':
    male, female = bodies()
    mounts = {s:palm_mount(male, female, s) for s in ('l', 'r')}
    report = []
    for path in sorted((W / 'Captured').glob('*.json')):
        row = read(path)
        if not row['samples']['target']:
            report.append({'roles': row['roles'], 'missing': True})
            continue
        source = expand(row['samples']['source'], male)
        target = expand(row['samples']['target'], female)
        errors = []
        rotations = []
        for a, b in zip(source, target):
            a, b = fk(a, male), fk(b, female)
            relation = compose(inverse(a[male['index']['hand_r'], :7]), a[male['index']['hand_l'], :7])
            expected = compose(compose(mounts['r'], relation), inverse(mounts['l']))
            actual = compose(inverse(b[female['index']['hand_r'], :7]), b[female['index']['hand_l'], :7])
            errors.append(float(np.linalg.norm(expected[:3] - actual[:3])))
            rotations.append(float(np.degrees((R.from_quat(expected[3:7]).inv() * R.from_quat(actual[3:7])).magnitude())))
        report.append({'roles': row['roles'], 'key': path.stem,
                       'pair_error_cm': errors, 'pair_rotation_degrees': rotations,
                       'markers': row['samples']['source']['markers']})
    (W / 'contact_diagnosis.json').write_text(json.dumps({'mounts': {s:m.tolist() for s,m in mounts.items()}, 'clips':report}, indent=2), encoding='utf-8')
    for row in report:
        print(row['roles'][0], 'missing' if row.get('missing') else round(max(row['pair_error_cm']), 3))
