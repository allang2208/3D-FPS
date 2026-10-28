"""Bake the dual-kukri locomotion clips (Clips/Dual{Idle,Walk,Run}.json, 120 fps) in the Kukri20261020 clip format.

DualIdle  3.0 s  hold = pose_keys.json (fit_idle.py).  Breathing tracked on the reference stills 2.3-4.1 s
                 (Reference/track_idle.py): the fists and blades move rigidly, the camera does not move.
                 * spread: the fists part and close in opposition, left x -15..+7 px, right +10..-4 px (1080p),
                   open at 2.6 s, closed at 3.9-4.0 s -> one cycle per loop;
                 * rise/fall: both together, +-5..6 px, down 3.2 s / up 3.9 s -> second harmonic, lowest 0.6 s
                   after the widest spread.  Pixel amplitudes become wrist offsets at each fist's depth.
DualWalk  0.9 s  the idle hold plus the single Walk's sway (Kukri20261020 clip_walk): step bob 0.85 cm at 2x,
                 body sway 0.95 cm at 1x and 0.4 cm fore/aft at 2x, moving the whole rig rigidly so the crossed
                 blades keep the hold's clearance (R1 moved each wrist and its opposed arm pump pushed the blades
                 0.5 cm into each other; moving both wrists still re-aimed the hands through the arm solve); the
                 runtime scales the rate with speed (360 cm/s = 1x).
DualRun   2/3 s  hold = run_keys.json (R4: right arm fit_run_r4.py, left arm fit_run.py R3; reference 握持姿势 奔跑
                 17.5 s).  Reference sprint (16.75-18.4 s,
                 Reference/track_run.py): the left fist swings right+down / left+up about 140 x 80 px peak to peak
                 once per stride, the raised right fist moves less and against it.  The loop keeps the single Run's
                 2/3 s stride (same clock as the game's sprint) with that amplitude and phase, plus a 2x step bob.
The left kukri rides on hand_l with a constant relation (mirror of the accepted right grip), written to
left_kukri.json for the runtime attach (the arms skeleton has one weapon chain, WPN_root = right kukri).

Run:  python -I author_clips.py [DualIdle DualWalk DualRun] [--preview]
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from dual_rig import DualRig, ndc, TIP  # noqa: E402
from kmath import T, mesh_to_cam, cam_to_mesh  # noqa: E402

FPS = 120
TAN_V = math.tan(math.radians(75.0) / 2)
OUT = P / 'Clips'


def px_to_cm(px_x, px_y, depth):
    """Screen px (1920x1080, x right, y down) at a depth -> camera (right, up) cm."""
    return px_x / 960.0 * depth * TAN_V * 16 / 9, -px_y / 540.0 * depth * TAN_V


def load(name):
    keys = json.loads((P / name).read_text('utf-8'))
    conv = lambda d: {k: (np.array(v, float) if isinstance(v, list) else v if isinstance(v, str) or v is None else float(v))
                      for k, v in d.items()}
    return conv(keys['right']), conv(keys['left_mirrored'])


def offset(prm, fwd=0.0, right=0.0, up=0.0, mirrored=False, **deltas):
    """Copy of an arm parameter set moved by an ACTUAL camera offset (cm); the left arm lives in mirrored space."""
    q = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in prm.items()}
    q['W'] = q['W'] + np.array([fwd, -right if mirrored else right, up])
    for k, v in deltas.items():
        q[k] = q[k] + v
    return q


def idle_sample(t, base):
    r0, l0 = base
    L = 3.0
    spread = math.cos(2 * math.pi * t / L)                     # +1 = widest
    low = math.cos(2 * math.pi * (t - 0.6) / (L / 2))          # +1 = lowest
    out = []
    for prm, px, mirrored in ((r0, 7.0, False), (l0, -11.0, True)):
        depth = float(prm['W'][0])
        dx, _ = px_to_cm(px * spread, 0.0, depth)                # widest: left fist left, right fist right
        _, dz = px_to_cm(0.0, 5.5 * low, depth)
        out.append(offset(prm, right=dx, up=dz, mirrored=mirrored))
    return out


def walk_sample(t, base):
    r0, l0 = base
    L = 0.9
    a = 2 * math.pi * t / L
    bob = 0.85 * math.sin(2 * a - math.pi / 2)
    sway = 0.95 * math.sin(a)
    surge = 0.40 * math.sin(2 * a + 0.4)
    return [offset(r0), offset(l0), (surge, sway, bob)]


def run_sample(t, base):
    r0, l0 = base
    L = 80 / FPS
    a = 2 * math.pi * t / L
    s = math.sin(a)
    bob = 0.9 * math.sin(2 * a - math.pi / 2)
    ld = float(l0['W'][0])
    rd = float(r0['W'][0])
    lx, _ = px_to_cm(70.0, 0.0, ld)
    _, lz = px_to_cm(0.0, 40.0, ld)
    rx, _ = px_to_cm(30.0, 0.0, rd)
    _, rz = px_to_cm(0.0, 25.0, rd)
    # Left fist right+down while the right fist goes left+up (and back); the fists pump fore/aft against each other.
    # R4: the right fist sits ~21 cm from the eye (thrust-ahead hold), where 1 cm of depth pump alone swept it ~80 px;
    # the reference right fist moves less than the left, so its pump is halved.
    return [offset(r0, fwd=0.5 * s, right=-rx * s, up=-rz * s + bob, psi=2.0 * math.sin(a + 0.6), de=2.0 * math.sin(a + 1.0)),
            offset(l0, fwd=-1.0 * s, right=lx * s, up=lz * s + bob, mirrored=True, psi=2.0 * math.sin(a + 0.6), de=2.0 * math.sin(a + 1.0))]


def pose_at(D, spec, t, base):
    """Clip pose at t: the arm samples, then the optional rigid offset of the whole rig (third item, camera cm)."""
    out = spec['sample'](t, base)
    right, left = out[0], out[1]
    for prm in (right, left):
        prm['W'] = tuple(prm['W'])
    world, Kr, Kl, info = D.pose(right, left)
    if len(out) > 2:
        d = cam_to_mesh(out[2])
        world = {n: T(x.p + d, x.q, x.s) for n, x in world.items()}
        Kr, Kl = T(Kr.p + d, Kr.q, Kr.s), T(Kl.p + d, Kl.q, Kl.s)
    return world, Kr, Kl, info


CLIPS = {
    'DualIdle': dict(length=3.0, keys='pose_keys.json', sample=idle_sample),
    'DualWalk': dict(length=0.9, keys='pose_keys.json', sample=walk_sample),
    'DualRun': dict(length=80 / FPS, keys='run_keys.json', sample=run_sample),
}


def bake(D, name, spec, preview):
    R = D.R
    base = load(spec['keys'])
    n = int(round(spec['length'] * FPS))
    frames, diags, prev_q, rel_l, previews = [], [], None, None, {}
    for i in range(n + 1):
        t = 0.0 if i == n else i / FPS   # exact seam
        world, Kr, Kl, info = pose_at(D, spec, t, base)
        rel = Kl.relative_to(T(world['hand_l'].p, world['hand_l'].q, (1, 1, 1)))
        rel_l = rel if rel_l is None else rel_l
        lk = R.local_keys(world, prev_q)
        prev_q = {b: v[1] for b, v in lk.items()}
        frames.append({b: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for b, v in lk.items()})
        dr, dl = info['right'], info['left_virtual']
        side = lambda d, K: dict(reach=round(d['reach'], 3), twist=round(math.degrees(d['theta']), 1), ext=round(d['ext'], 1),
                                 uln=round(d['uln'], 1), grip=[round(v, 4) for v in ndc(mesh_to_cam(K.p))],
                                 tip=[round(v, 4) for v in ndc(mesh_to_cam(K.point(TIP)))])
        diags.append(dict(t=round(t, 4), right=side(dr, Kr), left=side(dl, Kl),
                          left_kukri_drift_cm=round(float(np.linalg.norm(rel.p - rel_l.p)), 5)))
        if preview and i % max(1, n // 6) == 0:
            previews['%s_%04d' % (name.lower(), int(round(t * 1000)))] = dict(
                bones={b: x.pack() for b, x in world.items()}, kukri_r=Kr.pack(), kukri_l=Kl.pack())
    OUT.mkdir(exist_ok=True)
    data = dict(name=name, fps=FPS, length=spec['length'], loop=True, contact=None, bones=R.rig.names, frames=frames, diagnostics=diags)
    (OUT / (name + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    rng = {}
    for s in ('right', 'left'):
        for k in ('reach', 'twist', 'ext', 'uln'):
            vals = [d[s][k] for d in diags]
            rng['%s_%s' % (s, k)] = [min(vals), max(vals)]
        for k in ('grip', 'tip'):
            xs, ys = [d[s][k][0] for d in diags], [d[s][k][1] for d in diags]
            rng['%s_%s_px' % (s, k)] = [round((max(xs) - min(xs)) * 960, 1), round((max(ys) - min(ys)) * 540, 1)]
    rng['left_kukri_drift_cm'] = max(d['left_kukri_drift_cm'] for d in diags)
    print(name, json.dumps(rng), flush=True)
    return rel_l, previews


def main():
    names = [a for a in sys.argv[1:] if not a.startswith('--')] or list(CLIPS)
    D = DualRig()
    previews, rel = {}, None
    for name in names:
        rel, pv = bake(D, name, CLIPS[name], '--preview' in sys.argv)
        previews.update(pv)
    (P / 'left_kukri.json').write_text(json.dumps(dict(
        note='SM_Kukri on hand_l (UE mesh/bone space, cm, unit scale): kukri = rel * hand_l.  Mirror of the accepted right grip '
             '(WPN_root = kukri = hand_rel^-1 * hand_r); runtime: UKukriWeaponComponent OffhandHandToBlade (location / 100, scale 0.01).',
        rel_to_hand_l=dict(location=list(map(float, rel.p)), rotation_wxyz=list(map(float, rel.q)))), indent=1), encoding='utf-8')
    if previews:
        out = P / 'Work' / 'render'
        out.mkdir(parents=True, exist_ok=True)
        (out / 'clips.json').write_text(json.dumps(dict(poses=previews)), encoding='utf-8')
        print('previews written: Work/render/clips.json')


if __name__ == '__main__':
    main()
