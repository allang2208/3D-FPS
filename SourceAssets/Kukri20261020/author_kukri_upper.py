"""Author the kukri uppercut clip "Uppercut" (38/30 s) from upper_keys.json (fit_upper.py).

Reference: BV1CeYUeSE7b 106.20-107.30 s (近战动作（滑铲）#9 上撩), t = 0 at frame 3186.  The right arm follows the fitted
keys (spline as in author_kukri_clips).  The open left hand balances the slide: it comes up from the bottom left palm
down with the fingers spread forward-right (0.03 s), reaches into the lower centre-left (0.07 s), sweeps out to the left
while the right fist winds up low (0.10-0.30 s) and drops out of the bottom left as the cut rises (0.33 s), back to its
lowered rest below the frame by 0.47 s.  LEFT_REACH holds the reference wrist positions (camera cm: x forward,
y right, z up) read from the hand positions at the depths noted; the hand orientation is solved per key on the
rig's explicit left arm (kukri_rig.left_hand_explicit: bind forearm/hand relation + twist, flex, deviation).

Run:  python author_kukri_upper.py [--preview] [--compare]
Output: Clips/Uppercut.json + its summary in clips.json; --compare puts the 30 Hz frames under the reference frames
(Work/upper/cmp_upper_*.jpg).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize

import author_kukri_clips as AC
from kmath import cam_to_mesh, mesh_to_cam, qrot

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'upper'
REF_START = 3186
FINGERS = (0.80, 0.45, 0.30)       # forward, right, up: fingers spread towards the screen centre
PALM = (0.20, 0.10, -0.97)         # palm facing the floor
OPEN = 0.9
# Reference left-hand centres (NDC, x right / y down) and their depth (cm); the wrist sits ~(-0.07, +0.12) NDC from the hand
# centre (metacarpals), so the targets below are the wrist positions converted to camera cm (x forward, y right, z up).
LEFT_HAND_NDC = [
    (0.033, (-0.25, 0.62), 30.0), (0.067, (-0.12, 0.45), 32.0), (0.100, (-0.42, 0.55), 32.0), (0.133, (-0.45, 0.42), 32.0),
    (0.167, (-0.38, 0.48), 31.0), (0.200, (-0.60, 0.32), 30.0), (0.233, (-0.78, 0.33), 29.0), (0.267, (-0.88, 0.32), 28.0),
    (0.300, (-0.95, 0.58), 27.0), (0.333, (-1.10, 0.85), 26.0),
]
TAN = math.tan(math.radians(75.0) / 2)


def _wrist(ndc_xy, depth):
    x, y = ndc_xy[0] - 0.07, ndc_xy[1] + 0.12
    return (depth, x * depth * TAN * 16 / 9, -y * depth * TAN)


LEFT_REACH = [(t, _wrist(n, d)) for t, n, d in LEFT_HAND_NDC] + [(0.400, (22.0, -36.0, -40.0))]
REST_AT = 0.467


def solve_left(R, world, wrist, prev):
    """Twist, flex and deviation that turn the explicit left hand palm-down with the fingers forward-right."""
    want_f = cam_to_mesh(np.asarray(FINGERS, float)); want_f /= np.linalg.norm(want_f)
    want_y = -cam_to_mesh(np.asarray(PALM, float)); want_y -= want_f * np.dot(want_y, want_f); want_y /= np.linalg.norm(want_y)
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


def left_track(R):
    """Per-key (twist, flex, dev) on the stance body, unwrapped; PCHIP over the keys."""
    world = R.rig.world({n: t.copy() for n, t in R.base_local.items()})
    rows, prev = [], None
    for t, wrist in LEFT_REACH:
        v, pole, c = solve_left(R, world, wrist, prev)
        if prev is not None:
            while v[0] - prev[0] > 180:
                v[0] -= 360
            while v[0] - prev[0] < -180:
                v[0] += 360
        rows.append((t, wrist, pole, v, c))
        prev = v
        print('left %.3f wrist %s twist %6.1f flex %5.1f dev %5.1f fit %.4f' % (t, wrist, v[0], v[1], v[2], c))
    ts = [r[0] for r in rows]
    pos = PchipInterpolator([0.0] + ts + [REST_AT], np.array([AC.IDLE['L']] + [r[1] for r in rows] + [AC.IDLE['L']], float), axis=0)
    ang = PchipInterpolator(ts, np.array([r[3] for r in rows], float), axis=0)
    pol = PchipInterpolator(ts, np.array([r[2] for r in rows], float), axis=0)
    return pos, ang, pol, ts


def clip_upper(D):
    from fit_reference import Fitter      # the fitted keys use the fitter's arm parametrisation
    F = Fitter(D.R)
    data = json.loads((P / 'upper_keys.json').read_text('utf-8'))
    keys = [dict(t=k['t'], hold=(i == 0), x=np.array(k['x'], float)) for i, k in enumerate(data['keys'])]
    keys.append(dict(t=data['length'], hold=True, x=np.array(json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x'], float)))
    pos, ang, pol, ts = left_track(D.R)

    def sample(t):
        x = AC.spline(keys, t, ('x',))['x']
        W, phi, psi, du, de, C = F.unpack(x)
        out = dict(W=np.array(W, float), E=np.array(F.hint(W, phi, C), float), psi=float(psi), du=float(du),
                   de=float(de), C=np.array(C, float), L=np.array(pos(min(t, REST_AT)), float))
        if 0.0 < t < REST_AT:
            # Explicit left arm from the first frame (the hand is below the frame there); the angles hold their end
            # values outside the keyed span while the wrist travels from / back to the rest.
            tt = min(max(t, ts[0]), ts[-1])
            v = ang(tt)
            w = min(1.0, t / ts[0], (REST_AT - t) / (REST_AT - ts[-1]))
            out['LA'] = dict(pole=tuple(pol(tt)), twist=float(v[0]), flex=float(v[1]), dev=float(v[2]), open=OPEN * max(0.0, min(1.0, w)))
        return out
    return dict(length=data['length'], loop=False, kind='arm', sample=sample, contact=tuple(data['contact']), preview_step=1 / 30)


def compare(names, out_dir):
    import cv2
    ref_dir = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020\upper_frames")
    cells = []
    for name in names:
        t = int(name.split('_')[1]) / 1000.0
        ref = cv2.imread(str(ref_dir / ('f%05d.png' % (REF_START + int(round(t * 30))))))
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
        cv2.putText(ref, 'ref t=%.3f' % t, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 255), 2)
        cv2.putText(ours, 'ours', (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
        cells.append(np.vstack([ref, ours]))
    for s in range(0, len(cells), 6):
        chunk = cells[s:s + 6]
        while len(chunk) % 3:
            chunk.append(np.zeros_like(chunk[0]))
        cv2.imwrite(str(WORK / ('cmp_upper_%d.jpg' % (s // 6))),
                    np.vstack([np.hstack(chunk[r:r + 3]) for r in range(0, len(chunk), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 82])


def main():
    AC.CLIPS['Uppercut'] = clip_upper
    summary, previews = AC.author(['Uppercut'], '--preview' in sys.argv or '--compare' in sys.argv)
    clips_path = P / 'clips.json'
    meta = json.loads(clips_path.read_text('utf-8'))
    meta.setdefault('clips', {}).update({k: dict(v, source='author_kukri_upper.py') for k, v in summary.items()})
    clips_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    if previews:
        from preview_tools import write_poses, render
        WORK.mkdir(parents=True, exist_ok=True)
        write_poses(previews, WORK / 'upper_previews.json')
        for line in render(WORK / 'upper_previews.json', WORK / 'previews', 480):
            if 'KUKRI_PREVIEW' not in line:
                print(line)
        if '--compare' in sys.argv:
            compare(sorted(previews, key=lambda n: int(n.split('_')[1])), WORK / 'previews')


if __name__ == '__main__':
    main()
