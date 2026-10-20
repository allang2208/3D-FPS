"""Read-only commandlet: readback of written clips from the sequence data model (ue_rawpose).
Per pose source, up to 3 clips with a twist write + every clip with a bad-key repair:
- forearm twist shares: twist_01 / twist_02 roll vs hand roll (expected 1.0 / 0.5),
- hands and fingers vs ClipsTrue (pre-pass data model) on the same frames (expected unchanged except repaired keys).
Output Work/verify_raw_sample.json."""
import json, sys, math, hashlib
from pathlib import Path
sys.path.insert(0, 'D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')
import unreal as u
import ue_rawpose as rp

R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9Rollout_20261017')


def qt(q): return (q.x, q.y, q.z, q.w)


def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def qinv(a): return (-a[0], -a[1], -a[2], a[3])


def twist(q, axis):
    x, y, z, w = q
    if w < 0: x, y, z, w = -x, -y, -z, -w
    return math.degrees(2 * math.atan2(x * axis[0] + y * axis[1] + z * axis[2], w))


def ang(a, b):
    d = abs(sum(x * y for x, y in zip(a, b))); return math.degrees(2 * math.acos(min(1.0, d)))


rec_by_path = {}
for f in (R / 'InstalledRaw').glob('*.json'):
    if f.stem.endswith('.failed'): continue
    d = json.loads(f.read_text()); rec_by_path[d['path']] = d
out = []
for b in ('batch1', 'batch2', 'batch3', 'batch4'):
    plan = json.loads((R / (b + '.json')).read_text()); specs = json.loads((R / 'Work' / b / 'twist_specs.json').read_text())
    for ps, vm in plan['viewmodels'].items():
        tf = R / 'ClipsTrue' / (ps + '.json')
        if not tf.exists(): continue
        true = json.loads(tf.read_text()); bones = true['bones']; bi = {x: i for i, x in enumerate(bones)}
        picked = [p for p, c in true['clips'].items() if 'frames' in c and rec_by_path.get(p, {}).get('fixed')]
        tw = [p for p, c in true['clips'].items() if 'frames' in c and rec_by_path.get(p, {}).get('twist') and specs.get(p, {}).get('pose_source') == ps]
        picked += [p for p in tw[:3] if p not in picked]
        mesh = u.load_asset(vm + '.' + vm.split('/')[-1])
        for path in picked:
            seq = u.load_asset(path + '.' + path.split('/')[-1]); c = true['clips'][path]
            n, fr = rp.frame_count(seq); rate = fr.numerator / fr.denominator; spec = specs.get(path); rec = rec_by_path[path]
            fixed_keys = {bn: set(k for a, z in rng for k in range(a, z)) for bn, rng in rec.get('fixed', {}).items()}
            share_err = 0.0; hand_dev = 0.0; finger_dev = 0.0; max_roll = 0.0
            for i, frame in enumerate(c['frames']):
                k = min(n - 1, int(round(i / 15.0 * rate)))
                comp = rp.component(seq, vm, k, mesh)
                for s in 'lr':
                    for bn in ['hand_' + s] + [x for x in bones if x.endswith('_' + s) and any(t in x for t in ('index', 'middle', 'ring', 'pinky', 'thumb'))]:
                        if bn not in comp or bn not in bi or k in fixed_keys.get(bn, ()) or any(k in v for v in fixed_keys.values()): continue
                        dv = ang(qt(comp[bn].rotation), tuple(frame[bi[bn]][3:]))
                        if bn.startswith('hand_'): hand_dev = max(hand_dev, dv)
                        else: finger_dev = max(finger_dev, dv)
                    if spec and s in spec['sides']:
                        sd = spec['sides'][s]; axis = sd['axis_l']
                        qL = qt(comp['lowerarm_' + s].rotation); qH = qt(comp['hand_' + s].rotation)
                        r = twist(qmul(qmul(qinv(qL), qH), qinv(tuple(sd['rel_hand']))), axis)
                        r1 = twist(qmul(qmul(qinv(qL), qt(comp['lowerarm_twist_01_' + s].rotation)), qinv(tuple(sd['rel_t1']))), axis)
                        r2 = twist(qmul(qmul(qinv(qL), qt(comp['lowerarm_twist_02_' + s].rotation)), qinv(tuple(sd['rel_t2']))), axis)
                        max_roll = max(max_roll, abs(r))
                        if abs(r) < 170: share_err = max(share_err, abs(r1 - r), abs(r2 - 0.5 * r))
            row = dict(path=path, pose_source=ps, keys=n, fixed=list(rec.get('fixed', {})), twist=bool(spec), max_hand_roll=round(max_roll, 1),
                       twist_share_err_deg=round(share_err, 2), hand_vs_true_deg=round(hand_dev, 3), finger_vs_true_deg=round(finger_dev, 3))
            out.append(row); print('V9R_VERIFY', json.dumps(row), flush=True)
(R / 'Work/verify_raw_sample.json').write_text(json.dumps(out, indent=1))
print('V9R_VERIFY_COMPLETE', len(out), flush=True)
