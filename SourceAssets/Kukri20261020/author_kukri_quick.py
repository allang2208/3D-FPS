"""Author the kukri quick-melee clip "QuickPommel" (pommel strike) from quick_keys.json (fit_pommel.py).

Reference: BV1CeYUeSE7b 89.73-90.97 s (近战动作 #3 刀把), t = 0 at frame 2692.  The right arm follows the fitted keys
(spline as in author_kukri_clips): the blade turns left and the fist leaves the frame to the right, cocks up out of the
right side, comes down from the upper right, drives forward-up into the target with the blade pointing back at the
player and the pommel leading, holds, drops out below and re-raises into the stance.  The left fist jabs across first
(LEFT_KEYS): up from the bottom left, a palm-down hook-jab into the centre with the elbow out past the left edge, then
the hand opens and swings up and out to the left.

V2 (user 10-23: left elbow twisted, blade must point at the player, faster, harder):
  * left arm: V1 aimed only the wrist and let the hanging-arm heuristic pick the hand -- the forearm skin twisted
    120-150 deg against bind and the arm reached 0.98 with the elbow inside the frame.  Now the elbow is pinned out
    past the left edge (pole) and the hand roll/bend is explicit (kukri_rig.left_hand_explicit): skin twist stays
    within the table printed by --left, the reach <= 0.8, the fingers open on the swing-out;
  * right arm: the blade points back at the lens through the strike (fit_pommel.py V2 targets);
  * tempo: TIME_MAP plays the reference 1.267 s in 1.0 s -- wind-up x1.22, the downswing 0.367-0.433 accelerating onto
    the target (speed peaks on arrival), the rebound x1.5, the hold x1.2, the recovery x1.33; contact at 11/30 s (the
    reference's 0.433 s, end of the downswing; V1 used the delayed hit flash at 0.533).  The fist overshoots
    CONTACT_PUSH cm along the pommel on contact and springs back (the hard stop).

Run:  python author_kukri_quick.py [--preview] [--compare] [--left]
Output: Clips/QuickPommel.json + its summary in clips.json; --compare renders the 30 Hz frames under the reference
frames at the mapped reference time (Work/quick/cmp_quick_*.jpg); --left prints the left-arm key table.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize

import author_kukri_clips as AC
from kmath import mesh_to_cam, cam_to_mesh, qrot, qmul, qconj

P = Path(__file__).resolve().parent
WORK = P / 'Work' / 'quick'
REF_START = 2692
REF_LENGTH = 38 / 30
LENGTH = 30 / 30
# The pommel lands at the end of the downswing (reference 0.433 s): the fastest screen motion ends there and the
# reference camera jolt starts on that frame (pitch 3.95 -> 0.87, roll rattle 0.47-0.50); the hit flash at 0.533 is
# the game's delayed effect, 0.433-0.533 is the fist rebounding up-right off the target.
CONTACT_REF = 13 / 30
# clip seconds -> reference seconds: (clip start, clip end, ref start, ref end, ease a) -- a < 1 eases in (the downswing
# leaves the cock at a x the mean speed and lands at (2 - a) x, speed peaking on the contact).
TIME_MAP = [(0.0, 9 / 30, 0.0, 11 / 30, 1.0),          # wind-up and left jab x1.22
            (9 / 30, 11 / 30, 11 / 30, CONTACT_REF, 0.5),  # downswing onto the target
            (11 / 30, 13 / 30, CONTACT_REF, 16 / 30, 1.0), # rebound off the target x1.5
            (13 / 30, 18 / 30, 16 / 30, 22 / 30, 1.0),     # hold x1.2
            (18 / 30, LENGTH, 22 / 30, REF_LENGTH, 1.0)]   # drop and re-raise x1.33
CONTACT = 11 / 30
CONTACT_PUSH = 1.2          # cm along the pommel past the contact pose (the hard stop)
CONTACT_REBOUND = 0.04      # s, peak at 35 %


def ref_time(s):
    for c0, c1, r0, r1, a in TIME_MAP:
        if s <= c1 + 1e-9:
            u = min(max((s - c0) / (c1 - c0), 0.0), 1.0)
            return r0 + (r1 - r0) * (a * u + (1 - a) * u * u)
    return REF_LENGTH


# Left hand: fist centre in the left hand frame (cm; +X fingers, -Y palm), see kukri_rig.left_hand_explicit.
FIST_LOCAL = np.array([8.0, -3.0, -0.5])
# t (reference s), fist centre (camera cm; None = the hanging rest), elbow pole (camera cm), palm direction (camera),
# wrist flex (+ palmar, - extension), deviation (+ ulnar), finger opening 0..1.  Screen positions read on the 0.1-NDC
# grids: 0.067-0.133 the fist rises at the bottom left (-0.4..-0.2, 0.95..0.75), knuckles up; 0.167 the forearm comes
# in from the lower-left corner (-0.2, 0.35); 0.20-0.27 palm-down punch at the centre with the forearm entering from
# the left edge below the middle (elbow out of frame); 0.30 the fist starts back up-left; 0.33 the hand opens, back
# of the glove to the camera, fingers up-right (-0.53, -0.1); 0.37 at the left edge; gone by 0.40.
LEFT_KEYS = [
    (0.000, None, None, None, 0.0, 0.0, 0.0),
    (0.033, None, None, None, 0.0, 0.0, 0.0),
    (0.067, (26.0, -14.0, -19.0), (6.0, -44.0, -40.0), (0.55, 0.25, -0.80), 0.0, 0.0, 0.0),
    (0.100, (27.5, -12.5, -18.5), (8.0, -44.0, -36.0), (0.50, 0.20, -0.85), 0.0, 0.0, 0.0),
    (0.133, (29.5, -9.0, -16.0), (10.0, -44.0, -30.0), (0.40, 0.15, -0.90), 0.0, 4.0, 0.0),
    (0.167, (33.0, -9.0, -9.0), (12.0, -46.0, -20.0), (0.20, 0.05, -1.00), 0.0, 8.0, 0.0),
    (0.200, (38.0, -3.0, -1.5), (12.0, -48.0, -10.0), (0.10, 0.00, -1.00), 0.0, 10.0, 0.0),
    (0.233, (40.0, 0.0, 0.5), (12.0, -48.0, -8.0), (0.10, 0.00, -1.00), 0.0, 10.0, 0.0),
    (0.267, (39.0, -4.0, 2.5), (11.0, -49.0, -8.0), (0.20, 0.00, -1.00), 0.0, 6.0, 0.0),
    (0.300, (35.5, -10.0, 1.5), (9.0, -50.0, -10.0), (0.50, 0.00, -0.85), -10.0, 0.0, 0.15),
    (0.333, (30.0, -21.5, 2.0), (10.0, -50.0, -14.0), (1.00, -0.10, -0.10), -35.0, 0.0, 0.85),
    (0.367, (26.0, -33.5, 4.0), (5.0, -55.0, -16.0), (1.00, -0.20, 0.00), -35.0, 0.0, 1.0),
    (0.400, (22.0, -44.0, -6.0), (0.0, -55.0, -28.0), (0.80, -0.30, -0.30), -15.0, 0.0, 0.6),
    (0.467, None, None, None, 0.0, 0.0, 0.0),
    (REF_LENGTH, None, None, None, 0.0, 0.0, 0.0),
]


class LeftArm:
    """Left jab on the explicit left arm: per key the forearm twist that turns the palm towards its target, then PCHIP
    over fist centre, pole, twist, flex, deviation and finger opening."""

    def __init__(self, R, keys=None, end=None):
        """keys: LEFT_KEYS-style table (default: this clip's jab); end: clamp time of sample (default REF_LENGTH)."""
        self.R = R
        self.world = R.rig.world(R.base_local)
        self.end = REF_LENGTH if end is None else end
        rest = self._rest()
        rows = []
        prev_tw = None
        for t, fist, pole, palm, flex, dev, opening in (LEFT_KEYS if keys is None else keys):
            if fist is None:
                fist, pole, tw, flex, dev = rest
            else:
                tw = self._twist_for(fist, pole, np.asarray(palm, float), flex, dev, prev_tw)
            prev_tw = tw
            rows.append((t, *fist, *pole, tw, flex, dev, opening))
        self.table = np.array(rows, float)
        self.curve = PchipInterpolator(self.table[:, 0], self.table[:, 1:], axis=0)

    def wrist(self, fist, pole, tw, flex, dev):
        """Wrist (camera cm) that puts the fist centre on target for this hand roll and bend."""
        f = cam_to_mesh(fist)
        W = np.asarray(fist, float) - np.array([8.0, 0.0, 0.0])
        for _ in range(6):
            hand, _ = self.R.left_hand_explicit(self.world, tuple(W), pole, tw, flex, dev)
            W = mesh_to_cam(f - qrot(hand.q, FIST_LOCAL))
        return W, hand

    def _palm(self, hand):
        o = cam_to_mesh((0.0, 0.0, 0.0))
        return mesh_to_cam(qrot(hand.q, [0.0, -1.0, 0.0]) + o)

    def _twist_for(self, fist, pole, palm, flex, dev, prev):
        best = None
        for tw0 in range(-180, 180, 15):
            def err(v):
                _, hand = self.wrist(fist, pole, float(v[0]), flex, dev)
                p = self._palm(hand)
                return 1.0 - float(np.dot(p, palm) / np.linalg.norm(palm)) + 1e-5 * float(v[0]) ** 2
            res = minimize(err, [tw0], method='Nelder-Mead', options=dict(xatol=0.2, fatol=1e-6))
            tw = float(res.x[0])
            if prev is not None:
                while tw - prev > 180:
                    tw -= 360
                while tw - prev < -180:
                    tw += 360
            if best is None or res.fun < best[0] - 1e-4:
                best = (res.fun, tw)
        return best[1]

    def _rest(self):
        """The hanging rest of every other clip (kukri_rig.pose default) expressed in the explicit parameters."""
        R = self.R
        K = R.hand_rel.inverse() * R.base['hand_r']
        world, d = R.pose(K, left_target_cam=tuple(AC.IDLE['L']))
        hand = world['hand_l']
        pole = tuple(mesh_to_cam(world['lowerarm_l'].p))
        W = tuple(mesh_to_cam(hand.p))
        fist = tuple(mesh_to_cam(hand.p + qrot(hand.q, FIST_LOCAL)))

        def err(v):
            h, _ = R.left_hand_explicit(self.world, W, pole, *map(float, v))
            dq = abs(float(np.dot(h.q, hand.q)))
            return 1.0 - dq
        res = min((minimize(err, [tw, 0.0, 0.0], method='Nelder-Mead', options=dict(xatol=0.05, fatol=1e-10))
                   for tw in range(-180, 180, 30)), key=lambda r: r.fun)
        tw, flex, dev = map(float, res.x)
        return fist, pole, tw, flex, dev

    def sample(self, t):
        v = self.curve(min(max(t, 0.0), self.end))
        fist, pole, (tw, flex, dev, opening) = tuple(v[0:3]), tuple(v[3:6]), v[6:10]
        W, _ = self.wrist(fist, pole, float(tw), float(flex), float(dev))
        return np.array(W, float), dict(pole=pole, twist=float(tw), flex=float(flex), dev=float(dev),
                                        open=float(np.clip(opening, 0.0, 1.0)))


def clip_quick(D):
    from fit_reference import Fitter      # the fitted keys use the fitter's arm parametrisation
    F = Fitter(D.R)
    data = json.loads((P / 'quick_keys.json').read_text('utf-8'))
    keys = [dict(t=k['t'], hold=(i == 0), x=np.array(k['x'], float)) for i, k in enumerate(data['keys'])]
    keys.append(dict(t=data['length'], hold=True, x=np.array(json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x'], float)))
    left = LeftArm(D.R)
    # Impact stop: the fist runs on along the pommel (grip -> pommel at the contact pose) and springs back.
    xc = np.array(AC.spline(keys, CONTACT_REF, ('x',))['x'], float)
    oc = F.evaluate(xc)
    from kukri_rig import POMMEL
    push = mesh_to_cam(oc['K'].point(POMMEL)) - mesh_to_cam(oc['K'].p)
    push = push / np.linalg.norm(push)

    def sample(s):
        t = ref_time(s)
        x = np.array(AC.spline(keys, t, ('x',))['x'], float)
        if CONTACT <= s < CONTACT + CONTACT_REBOUND:
            u = (s - CONTACT) / CONTACT_REBOUND
            bump = math.sin(0.5 * math.pi * u / 0.35) if u < 0.35 else 0.5 * (1 + math.cos(math.pi * (u - 0.35) / 0.65))
            x[:3] = x[:3] + push * CONTACT_PUSH * bump
        W, phi, psi, du, de, C = F.unpack(x)
        L, Larm = left.sample(t)
        return dict(W=np.array(W, float), E=np.array(F.hint(W, phi, C), float), psi=float(psi), du=float(du),
                    de=float(de), C=np.array(C, float), L=L, LA=Larm)
    return dict(length=LENGTH, loop=False, kind='arm', sample=sample, contact=(CONTACT, CONTACT + 1 / 30),
                preview_step=1 / 30, left=left)


def left_report(R):
    left = LeftArm(R)
    print('left keys (t, fist, pole, twist, flex, dev, open):')
    for row in left.table:
        print('  %.3f fist %s pole %s twist %7.1f flex %6.1f dev %5.1f open %.2f' % (
            row[0], np.round(row[1:4], 1), np.round(row[4:7], 1), row[7], row[8], row[9], row[10]))
    from kukri_rig import ndc
    K = R.hand_rel.inverse() * R.base['hand_r']
    for i in range(0, 61, 2):
        t = i / 60 * 0.8
        L, Larm = left.sample(t)
        world, d = R.pose(K, left_target_cam=tuple(L), left_arm=Larm)
        l = d['left']
        S, E, W = (mesh_to_cam(world[n].p) for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
        bend = math.degrees(math.acos(np.dot((E - S) / np.linalg.norm(E - S), (W - E) / np.linalg.norm(W - E))))
        print('  t %.3f reach %.2f bend %5.1f skin twist %6.1f wrist %5.1f roll_u %6.1f | elbow ndc %s fist ndc %s' % (
            t, l['reach'], bend, l['twist_deg'], l['wrist_deg'], l['roll_u'], np.round(ndc(E), 2),
            np.round(ndc(mesh_to_cam(world['hand_l'].p + qrot(world['hand_l'].q, FIST_LOCAL))), 2)))


def compare(names, out_dir):
    import cv2
    ref_dir = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020\pommel_frames")
    cells = []
    for name in names:
        s = int(name.split('_')[1]) / 1000.0
        t = ref_time(s)
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
        cv2.putText(ref, 'ref t=%.3f' % (round(t * 30) / 30), (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 255), 2)
        cv2.putText(ours, 'ours %.3f' % s, (8, 24), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 255, 255), 2)
        cells.append(np.vstack([ref, ours]))
    for old in WORK.glob('cmp_quick_*.jpg'):
        old.unlink()
    for s in range(0, len(cells), 6):
        chunk = cells[s:s + 6]
        while len(chunk) % 3:
            chunk.append(np.zeros_like(chunk[0]))
        cv2.imwrite(str(WORK / ('cmp_quick_%d.jpg' % (s // 6))),
                    np.vstack([np.hstack(chunk[r:r + 3]) for r in range(0, len(chunk), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 82])


def main():
    if '--left' in sys.argv:
        from kukri_rig import KukriRig
        left_report(KukriRig())
        return
    AC.CLIPS['QuickPommel'] = clip_quick
    summary, previews = AC.author(['QuickPommel'], '--preview' in sys.argv or '--compare' in sys.argv)
    clips_path = P / 'clips.json'
    meta = json.loads(clips_path.read_text('utf-8'))
    meta.setdefault('clips', {}).update({k: dict(v, source='author_kukri_quick.py V2') for k, v in summary.items()})
    clips_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    if previews:
        from preview_tools import write_poses, render
        WORK.mkdir(parents=True, exist_ok=True)
        write_poses(previews, WORK / 'quick_previews.json')
        for line in render(WORK / 'quick_previews.json', WORK / 'previews', 480):
            if 'KUKRI_PREVIEW' not in line:
                print(line)
        if '--compare' in sys.argv:
            compare(sorted(previews, key=lambda n: int(n.split('_')[1])), WORK / 'previews')


if __name__ == '__main__':
    main()
