"""Author the kukri heavy-strike clips "HeavyCharge" (2.0 s) and "HeavyRelease" (35/30 s) from heavy_keys.json (fit_heavy.py).

Reference: BV1CeYUeSE7b 115.60-117.00 s (近战动作（跳跃）#12 ↙), t = 0 at frame 3468.  The right arm follows the fitted keys
(spline as in author_kukri_clips).  V2 (2026-10-24): the charge cocks the kukri like a hammer -- the blade laid back over the
right shoulder behind the player, the pommel forward -- and the release is a straight back-chop from there (fit_heavy.py).  The open left hand balances the raise like the reference: it comes in from the bottom
left (0.07 s), reaches into the centre with the fingers up and the back of the hand to the camera (0.13-0.20 s), and sweeps
out to the lower left as the right fist settles at the upper right (0.27-0.33 s), back to its lowered rest by 0.40 s.
During the re-raise of the release the left fist shows at the lower-left corner (reference 1.13-1.30 s).
LEFT_* hold the reference hand centres (NDC) and depths (cm); the hand orientation is solved per key on the rig's explicit
left arm (kukri_rig.left_hand_explicit: bind forearm/hand relation + twist, flex, deviation), as in author_kukri_upper.py.

Run:  python author_kukri_heavy.py [--preview] [--compare]
Output: Clips/HeavyCharge.json, Clips/HeavyRelease.json + their summaries in clips.json; --compare puts the 30 Hz frames
under the reference frames (Work/heavy/cmp_heavy_*.jpg).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize

import author_kukri_clips as AC
from kmath import cam_to_mesh, qrot

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'heavy'
REF_START = 3468
TAN = math.tan(math.radians(75.0) / 2)
# Charge: the open balance hand (centre NDC x right / y down, depth cm).  Fingers up and a little forward-right, the palm
# facing away from the camera (the reference shows the back of the glove with its wrist light).
CHARGE_LEFT = dict(
    keys=[(0.067, (-0.15, 0.85), 30.0), (0.100, (-0.05, 0.55), 31.0), (0.133, (0.05, 0.18), 32.0), (0.167, (-0.05, 0.05), 33.0),
          (0.200, (-0.30, -0.02), 33.0), (0.233, (-0.33, 0.20), 32.0), (0.267, (-0.55, 0.42), 30.0), (0.300, (-0.82, 0.72), 28.0)],
    out=(0.333, (20.0, -36.0, -42.0)), rest_at=0.40,
    fingers=(0.35, 0.25, 0.90), palm=(0.90, 0.15, -0.10), open=0.9)
# Release: the closed left fist resting at the lower-left corner while the right arm re-raises (reference 1.13-1.30 s).
RELEASE_LEFT = dict(
    keys=[(0.867, (-0.80, 0.82), 26.0), (0.933, (-0.74, 0.74), 26.0), (1.000, (-0.72, 0.74), 26.0), (1.067, (-0.80, 0.86), 26.0)],
    out=(1.133, (18.0, -34.0, -46.0)), rest_at=35 / 30, start_at=0.767,
    fingers=(0.55, 0.65, 0.35), palm=(0.15, 0.45, -0.88), open=0.0)


def _wrist(ndc_xy, depth):
    x, y = ndc_xy[0] - 0.07, ndc_xy[1] + 0.12
    return (depth, x * depth * TAN * 16 / 9, -y * depth * TAN)


def solve_left(R, world, wrist, prev, fingers, palm):
    """Twist, flex and deviation that turn the explicit left hand to the wanted finger and palm directions."""
    want_f = cam_to_mesh(np.asarray(fingers, float)); want_f /= np.linalg.norm(want_f)
    want_y = -cam_to_mesh(np.asarray(palm, float)); want_y -= want_f * np.dot(want_y, want_f); want_y /= np.linalg.norm(want_y)
    pole = tuple(np.asarray(wrist) + np.array([-10.0, -15.0, -20.0]))

    def cost(v):
        hand, _ = R.left_hand_explicit(world, wrist, pole, v[0], v[1], v[2])
        f = qrot(hand.q, [1, 0, 0]); y = qrot(hand.q, [0, 1, 0])
        c = (1 - np.dot(f, want_f)) + (1 - np.dot(y, want_y))
        c += 0.002 * max(0.0, abs(v[1]) - 30) ** 2 + 0.002 * max(0.0, abs(v[2]) - 25) ** 2
        c += 0.00002 * ((v[0] - prev[0]) ** 2) if prev is not None else 0.0
        return c
    starts = [prev] if prev is not None else []
    starts += [np.array([a, 0.0, 0.0]) for a in range(-180, 180, 30)]
    best = min((minimize(cost, s, method='Nelder-Mead', options=dict(xatol=.05, fatol=1e-7, maxiter=2000)) for s in starts),
               key=lambda r: r.fun)
    return best.x, pole, best.fun


def left_track(R, spec, label):
    """Per-key (twist, flex, dev) on the stance body, unwrapped; PCHIP over the keys; wrist from/to the lowered rest."""
    world = R.rig.world({n: t.copy() for n, t in R.base_local.items()})
    reach = [(t, _wrist(n, d)) for t, n, d in spec['keys']] + [spec['out']]
    rows, prev = [], None
    for t, wrist in reach:
        v, pole, c = solve_left(R, world, wrist, prev, spec['fingers'], spec['palm'])
        if prev is not None:
            while v[0] - prev[0] > 180:
                v[0] -= 360
            while v[0] - prev[0] < -180:
                v[0] += 360
        rows.append((t, wrist, pole, v, c))
        prev = v
        print('%s left %.3f wrist %s twist %6.1f flex %5.1f dev %5.1f fit %.4f' % (label, t, np.round(wrist, 1), v[0], v[1], v[2], c))
    start = spec.get('start_at', 0.0)
    ts = [r[0] for r in rows]
    pos = PchipInterpolator([start] + ts + [spec['rest_at']], np.array([AC.IDLE['L']] + [r[1] for r in rows] + [AC.IDLE['L']], float), axis=0)
    ang = PchipInterpolator(ts, np.array([r[3] for r in rows], float), axis=0)
    pol = PchipInterpolator(ts, np.array([r[2] for r in rows], float), axis=0)
    return dict(pos=pos, ang=ang, pol=pol, ts=ts, start=start, rest=spec['rest_at'], open=spec['open'])


def left_sample(track, t, out):
    """Explicit left arm inside the keyed span; the angles hold their end values while the wrist leaves / returns."""
    s, e, ts = track['start'], track['rest'], track['ts']
    if not (s < t < e):
        return
    out['L'] = np.array(track['pos'](t), float)
    tt = min(max(t, ts[0]), ts[-1])
    v = track['ang'](tt)
    w = min(1.0, (t - s) / (ts[0] - s), (e - t) / (e - ts[-1]))
    out['LA'] = dict(pole=tuple(track['pol'](tt)), twist=float(v[0]), flex=float(v[1]), dev=float(v[2]),
                     open=track['open'] * max(0.0, min(1.0, w)))


def _arm(F, keys, t):
    x = AC.spline(keys, t, ('x',))['x']
    W, phi, psi, du, de, C = F.unpack(x)
    return dict(W=np.array(W, float), E=np.array(F.hint(W, phi, C), float), psi=float(psi), du=float(du),
                de=float(de), C=np.array(C, float), L=np.array(AC.IDLE['L'], float))


def clip_charge(D):
    from fit_reference import Fitter
    F = Fitter(D.R)
    data = json.loads((P / 'heavy_keys.json').read_text('utf-8'))
    raw = data['charge']
    keys = [dict(t=k['t'], hold=(i == 0 or i == len(raw) - 1), x=np.array(k['x'], float)) for i, k in enumerate(raw)]
    track = left_track(D.R, CHARGE_LEFT, 'charge')

    def sample(t):
        out = _arm(F, keys, t)
        left_sample(track, t, out)
        return out
    return dict(length=data['charge_length'], loop=False, kind='arm', sample=sample, preview_step=1 / 30)


def clip_release(D):
    from fit_reference import Fitter
    F = Fitter(D.R)
    data = json.loads((P / 'heavy_keys.json').read_text('utf-8'))
    keys = [dict(t=k['t'], hold=(i == 0), x=np.array(k['x'], float)) for i, k in enumerate(data['release'])]
    keys.append(dict(t=data['release_length'], hold=True,
                     x=np.array(json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x'], float)))
    track = left_track(D.R, RELEASE_LEFT, 'release')

    def sample(t):
        out = _arm(F, keys, t)
        left_sample(track, t, out)
        return out
    return dict(length=data['release_length'], loop=False, kind='arm', sample=sample, contact=tuple(data['contact']),
                preview_step=1 / 60)    # the back-chop crosses the frame in ~3 author frames at 30 Hz


# Release author time -> reference frame for the comparison sheets (the cock and the cut are compressed onto 4 frames).
RELEASE_REF = [(0.0, 3479), (0.033, 3479), (0.100, 3480), (0.133, 3482), (0.833, 3500), (0.967, 3504), (1.000, 3505),
               (1.067, 3507), (35 / 30, 3510)]


def ref_frame(name):
    clip, ms = name.split('_')
    t = int(ms) / 1000.0
    if clip == 'HeavyCharge':
        # The cock (0.20-0.40) is the reference's hidden lift into the 0.367 frame; the load holds that frame.
        return REF_START + int(round(t * 30)) if t <= 0.167 else REF_START + 11
    return int(round(np.interp(t, [a for a, _ in RELEASE_REF], [b for _, b in RELEASE_REF])))


def compare(names, out_dir):
    import cv2
    ref_dir = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020\heavy_frames")
    cells = []
    for name in names:
        ref = cv2.imread(str(ref_dir / ('f%05d.png' % ref_frame(name))))
        ours = cv2.imread(str(out_dir / (name + '.png')))
        if ref is None or ours is None:
            continue
        w = ours.shape[1]
        ref = cv2.resize(ref, (w, w * 9 // 16))
        for im in (ref, ours):
            h = im.shape[0]
            for k in range(1, 4):
                cv2.line(im, (k * w // 4, 0), (k * w // 4, h), (90, 90, 90), 1)
                cv2.line(im, (0, k * h // 4), (w, k * h // 4), (90, 90, 90), 1)
        cv2.putText(ref, 'ref f%d' % ref_frame(name), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 255), 2)
        cv2.putText(ours, name, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
        cells.append(np.vstack([ref, ours]))
    for s in range(0, len(cells), 6):
        chunk = cells[s:s + 6]
        while len(chunk) % 3:
            chunk.append(np.zeros_like(chunk[0]))
        cv2.imwrite(str(WORK / ('cmp_heavy_%d.jpg' % (s // 6))),
                    np.vstack([np.hstack(chunk[r:r + 3]) for r in range(0, len(chunk), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 82])


# Frames shown in the comparison: the raise and the start of the load; the release around the cut and the re-raise.
COMPARE_CHARGE = (0.0, 0.067, 0.133, 0.167, 0.200, 0.233, 0.267, 0.300, 0.400, 1.200, 2.000)
COMPARE_RELEASE = (0.0, 0.017, 0.033, 0.050, 0.067, 0.083, 0.100, 0.133, 0.833, 0.967, 1.067, 1.133)


def main():
    AC.CLIPS['HeavyCharge'] = clip_charge
    AC.CLIPS['HeavyRelease'] = clip_release
    preview = '--preview' in sys.argv or '--compare' in sys.argv
    summary, previews = AC.author(['HeavyCharge', 'HeavyRelease'], preview)
    clips_path = P / 'clips.json'
    meta = json.loads(clips_path.read_text('utf-8'))
    meta.setdefault('clips', {}).update({k: dict(v, source='author_kukri_heavy.py') for k, v in summary.items()})
    clips_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    if previews:
        keep = {('HeavyCharge_%03d' % int(round(t * 1000))) for t in COMPARE_CHARGE}
        keep |= {('HeavyRelease_%03d' % int(round(t * 1000))) for t in COMPARE_RELEASE}
        previews = {k: v for k, v in previews.items() if k in keep}
        from preview_tools import write_poses, render
        WORK.mkdir(parents=True, exist_ok=True)
        write_poses(previews, WORK / 'heavy_previews.json')
        for line in render(WORK / 'heavy_previews.json', WORK / 'previews', 480):
            if 'KUKRI_PREVIEW' not in line:
                print(line)
        if '--compare' in sys.argv:
            order = sorted(previews, key=lambda n: (n.startswith('HeavyRelease'), int(n.split('_')[1])))
            compare(order, WORK / 'previews')


if __name__ == '__main__':
    main()
