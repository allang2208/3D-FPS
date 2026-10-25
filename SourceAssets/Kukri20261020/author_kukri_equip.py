"""Author the V2 draw clip "Equip" (toss and catch, 0.80 s) from equip_keys.json (fit_equip.py).

Reference: BV1CeYUeSE7b 52.13-52.93 s (切刀 #5 抛刀).  The right hand flicks the kukri up from below the frame (release
0.083 s), the knife tumbles ~290 deg over the top right on a fitted ballistic arc, the open hand
rises palm-to-camera under it and catches the handle at 13/30 s, the fist closes (0.47 s), rolls the blade edge-on
while dropping to the lower right (0.53 s) and settles into the stance.

The knife leaves the hand in this clip: WPN_root carries the authored flight between the release and the catch.
UKukriArmsMeshComponent fades its fist->grip lock out with the authored deviation from the hammer grip (locked below
0.6 cm, free above 2.5 cm), so the flight plays as authored at runtime.  Every other clip keeps the knife in the fist.

Run:  python author_kukri_equip.py [--preview] [--compare]
Output: Clips/Equip.json (local bone keys, UE convention, same format as author_kukri_clips.py) and the Equip
summary in clips.json.  --preview renders the 30 Hz frames with render_preview.py; --compare puts them under the
reference frames (Work/equip/cmp_equip_*.jpg).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

from kukri_rig import KukriRig, ndc, TIP, POMMEL, BLADE_BASE
from kmath import T, mesh_to_cam, qslerp, qaxis, qrot, qmul, qconj
from fit_equip import EquipFitter, Flight, LENGTH, TR, TC, WORK

P = Path(__file__).resolve().parent
FPS = 120
OUT = P / 'Clips'
IDLE_L = (16.0, -24.0, -64.0)          # left hand lowered out of frame (author_kukri_clips.IDLE['L'])
MID = np.array([2.5, 0.0, 16.0])
OPEN = 0.88                            # right fingers towards the flat bind hand while open
FINGER_OPEN = (0.070, TR + 0.012)      # the fingers spring open as the knife leaves (below the frame)
# Catch (V2.1): the fingers wrap the handle one after another from the contact, index first, thumb last over the top
# (start, seconds).  V2 closed all of them in 0.035 s at TC, which read as a snap.
FINGER_CLOSE = {'index': (TC - 0.008, 0.10), 'middle': (TC - 0.003, 0.10), 'ring': (TC + 0.002, 0.10),
                'pinky': (TC + 0.007, 0.10), 'thumb': (TC + 0.017, 0.09)}
# V2.1 contact.  V2 switched from the flight to the grip in one frame (knife 364 -> 19 cm/s, 747 -> 157 deg/s at TC)
# and the hand did not react.  Now the handle meets the palm one frame before TC (CONTACT, ~3 cm from the grip):
#   * the hand takes an impulse there -- KICK_SHARE of the knife's speed and spin relative to it -- as a critically
#     damped give along the knife's travel and a wrist yield about its spin axis (pivot at the wrist), back by ~0.6 s
#     and faded to exactly zero before the stance;
#   * in the kicked hand's frame the knife settles into the grip relation by SEATED with a cubic that starts on the
#     flight's relative position, speed and spin, so the knife itself never jumps: its world speed and spin carry
#     through the contact and drop with the hand.
#   * the runtime grip lock (UKukriArmsMeshComponent: <= 0.6 cm locked, >= 2.5 cm free) would pull the last
#     centimetres of that settle in early; the authored offset is pre-scaled so the shown knife follows the cubic.
CONTACT = 51 / 120
SEATED = 54 / 120
KICK_SHARE = 0.30          # fraction of the relative speed / spin the hand takes at the impact
KICK_RATE = 22.0           # 1/s; the give peaks 1/KICK_RATE after the contact
CUSHION_FADE = (0.62, 0.76)
LOCK_HOLD, LOCK_FREE, LOCK_DEG_CM = 0.6, 2.5, 0.25   # KukriGrip::HoldBand / ReleaseBand / DegreeToCm


def spline(keys, t, names):
    """Non-uniform Catmull-Rom per parameter; 'hold' keys (and the ends) have zero velocity (author_kukri_clips)."""
    t = min(max(t, keys[0]['t']), keys[-1]['t'])
    i = len(keys) - 2
    for j in range(len(keys) - 1):
        if keys[j]['t'] <= t < keys[j + 1]['t']:
            i = j
            break
    a, b = keys[i], keys[i + 1]
    h = b['t'] - a['t']
    u = (t - a['t']) / h if h > 0 else 0.0

    def tangent(j):
        k = keys[j]
        if k['hold'] or j == 0 or j == len(keys) - 1:
            return {n: k[n] * 0 for n in names}
        p, q = keys[j - 1], keys[j + 1]
        return {n: (q[n] - p[n]) / (q['t'] - p['t']) for n in names}
    ma, mb = tangent(i), tangent(i + 1)
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1
    h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2
    h11 = u ** 3 - u ** 2
    return {n: h00 * a[n] + h10 * h * ma[n] + h01 * b[n] + h11 * h * mb[n] for n in names}


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (x * 6 - 15) + 10)


def finger_of(bone):
    head = bone.split('_')[0]
    return head if head in FINGER_CLOSE else 'middle'


def finger_open(t, finger='middle'):
    start, seconds = FINGER_CLOSE[finger]
    if t < FINGER_OPEN[0]:
        return 0.0
    if t < start:
        return OPEN * smooth((t - FINGER_OPEN[0]) / (FINGER_OPEN[1] - FINGER_OPEN[0]))
    return OPEN * (1.0 - smooth((t - start) / seconds))


def rotvec(q):
    q = np.asarray(q, float)
    q = q if q[0] >= 0 else -q
    s = float(np.linalg.norm(q[1:]))
    return np.zeros(3) if s < 1e-12 else q[1:] / s * 2.0 * math.atan2(s, q[0])


def from_rotvec(r):
    a = float(np.linalg.norm(r))
    return np.array([1.0, 0.0, 0.0, 0.0]) if a < 1e-12 else qaxis(r / a, a)


def hermite_to_rest(p0, v0, t, t0, t1):
    """Cubic from (p0, v0) at t0 to rest (0, 0) at t1."""
    h = t1 - t0
    u = min(max((t - t0) / h, 0.0), 1.0)
    return (2 * u ** 3 - 3 * u ** 2 + 1) * p0 + (u ** 3 - 2 * u ** 2 + u) * h * v0


def lock_free(dev):
    x = min(max((dev - LOCK_HOLD) / (LOCK_FREE - LOCK_HOLD), 0.0), 1.0)
    return x * x * (3 - 2 * x)


def lock_compensation(dev):
    """Scale s >= 1 for an authored knife offset of deviation dev (cm) such that the runtime lock, which shows
    lock_free(s * dev) of an authored offset, shows exactly the intended one: s * lock_free(s * dev) = 1."""
    if dev >= LOCK_FREE or dev <= 1e-6:
        return 1.0
    lo, hi = LOCK_HOLD, LOCK_FREE      # y = s * dev solves y * lock_free(y) = dev
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if mid * lock_free(mid) < dev else (lo, mid)
    return 0.5 * (lo + hi) / dev


class EquipClip:
    def __init__(self, R=None):
        self.R = R or KukriRig()
        self.F = EquipFitter(self.R)
        self.data = json.loads((P / 'equip_keys.json').read_text('utf-8'))
        self.flight = Flight(T.packed(self.data['catch_frame']), self.data['flight']['p'])
        self.held = T.packed(self.data['release_hold'])     # knife relative to the flicking fist's grip frame
        ks = self.data['keys']
        self.keys = [dict(t=k['t'], hold=(i == 0), x=np.array(k['x'], float)) for i, k in enumerate(ks)]
        stance = json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x']
        self.keys.append(dict(t=LENGTH, hold=True, x=np.array(stance, float)))
        rig = self.R.rig
        self.fingers = [n for n in rig.descendants('hand_r') if n != 'hand_r' and not n.startswith('ik_')]
        self.order = [n for n in rig.names if n in self.fingers]
        self.contact()

    def contact(self):
        """Knife speed and spin relative to the hand when the handle meets the palm -> the hand's impulse; then the knife
        state relative to the kicked hand, which the settle starts from (so the knife's world motion is continuous)."""
        e = 1.0 / 960.0
        k = [self.flight.frame(t) for t in (CONTACT - e, CONTACT)]
        h = [self.arm_frame(t) for t in (CONTACT - e, CONTACT)]
        v = (k[1].p - k[0].p) / e - (h[1].p - h[0].p) / e
        w = rotvec(qmul(k[1].q, qconj(k[0].q))) / e - rotvec(qmul(h[1].q, qconj(h[0].q))) / e
        self.contact_speed, self.contact_spin = float(np.linalg.norm(v)), math.degrees(float(np.linalg.norm(w)))
        self.kick_v, self.kick_w = KICK_SHARE * v, KICK_SHARE * w     # hand impulse (cm/s, rad/s, mesh space)
        rel = [self.flight.frame(t).relative_to(self.arm(t)[0]) for t in (CONTACT, CONTACT + e)]
        self.rel_p0, self.rel_r0 = rel[0].p, rotvec(rel[0].q)
        self.rel_v0 = (rel[1].p - rel[0].p) / e
        self.rel_w0 = (rotvec(rel[1].q) - rotvec(rel[0].q)) / e       # the cubic runs on the rotation vector

    def arm_x(self, t):
        return spline(self.keys, t, ('x',))['x']

    def arm_raw(self, t):
        x = self.arm_x(t)
        W, phi, psi, du, de, C = self.F.unpack(x)
        K, E = self.R.arm_to_kukri(W, self.F.hint(W, phi, C), psi, de, du, C)
        return K, E, C

    def arm_frame(self, t):
        return self.arm_raw(t)[0]

    def cushion(self, t, K):
        """Hand give after the impact, x(tau) = v0 tau exp(-k tau) (critically damped, starting at the impulse speed):
        a shift along the knife's travel and a wrist rotation about its spin axis (pivot at the wrist)."""
        tau = t - CONTACT
        if tau <= 0 or not hasattr(self, 'kick_v'):
            return K
        fade = 1.0 - smooth((t - CUSHION_FADE[0]) / (CUSHION_FADE[1] - CUSHION_FADE[0]))
        g = tau * math.exp(-KICK_RATE * tau) * fade
        rot = from_rotvec(self.kick_w * g)
        wrist = (self.R.hand_rel * K).p
        return T(qrot(rot, K.p - wrist) + wrist + self.kick_v * g, qmul(rot, K.q), K.s)

    def arm(self, t):
        K, E, C = self.arm_raw(t)
        return self.cushion(t, K), E, C

    def knife(self, t, K_hand):
        if t < TR:
            return self.held * K_hand, 'held'
        if t < CONTACT:
            return self.flight.frame(t), 'flight'
        if t < SEATED:
            # settles into the grip in the hand's frame, starting on the flight's relative position, spin and speed
            p = hermite_to_rest(self.rel_p0, self.rel_v0, t, CONTACT, SEATED)
            r = hermite_to_rest(self.rel_r0, self.rel_w0, t, CONTACT, SEATED)
            s = lock_compensation(float(np.linalg.norm(p)) + math.degrees(float(np.linalg.norm(r))) * LOCK_DEG_CM)
            return T(p * s, from_rotvec(r * s), (1, 1, 1)) * K_hand, 'contact'
        return K_hand, 'grip'

    def sample(self, t):
        R = self.R
        K_hand, E, C = self.arm(t)
        world, diag = R.pose(K_hand, left_target_cam=IDLE_L, clav_r=tuple(C), pole_r=E, pole_r_weight=1.0)
        a = finger_open(t)
        rig = R.rig
        for n in self.order:
            an = finger_open(t, finger_of(n))
            if an <= 1e-4:
                continue
            par = rig.parents[rig.index[n]]
            lb, lr = R.base_local[n], R.ref_local[n]
            qr = lr.q if np.dot(lb.q, lr.q) >= 0 else -lr.q
            world[n] = T(lb.p, qslerp(lb.q, qr, an), lb.s) * world[par]
        K, mode = self.knife(t, K_hand)
        b = R.base
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for n in R.wpn_desc:
            if n == 'WPN_root':
                continue
            par = R.rig.parents[R.rig.index[n]]
            world[n] = R.base_local[n] * world[par]
        world['Blade_Base'] = T(K.point(BLADE_BASE), K.q, b['Blade_Base'].s)
        world['Blade_Tip'] = T(K.point(TIP), K.q, b['Blade_Tip'].s)
        d = dict(mode=mode, open=round(a, 3), hand=diag, shown=runtime_knife(K, K_hand))
        d['knife'] = {k: ndc(mesh_to_cam(K.point(v))) for k, v in (('pom', POMMEL), ('guard', BLADE_BASE), ('tip', TIP))}
        d['knife_depth'] = min(float(mesh_to_cam(K.point(v))[0]) for v in (POMMEL, BLADE_BASE, TIP, MID))
        vis = self.F.arm_visibility(self.arm_x(t))
        d['arm_margin'] = min(vis) if vis else 9.0
        return world, K, d


def angle_deg(q0, q1):
    d = qmul(q1, qconj(q0))
    return math.degrees(2.0 * math.atan2(float(np.linalg.norm(d[1:])), abs(float(d[0]))))


def runtime_knife(K_knife, K_hand):
    """What UKukriArmsMeshComponent shows: the grip lock fades with the authored deviation (<= 0.6 cm locked,
    >= 2.5 cm free, 1 deg = 0.25 cm)."""
    free = lock_free(float(np.linalg.norm(K_knife.p - K_hand.p)) + angle_deg(K_hand.q, K_knife.q) * LOCK_DEG_CM)
    return T(K_hand.p + (K_knife.p - K_hand.p) * free, qslerp(K_hand.q, K_knife.q, free), (1, 1, 1))


def catch_report(clip, t0=0.375, t1=0.60):
    """Per 120 Hz frame around the catch: knife speed and spin (authored and as displayed with the runtime grip lock),
    hand speed, finger opening.  Speeds are frame differences (cm/s, deg/s, mesh space)."""
    ts = [i / FPS for i in range(int(round(t0 * FPS)) - 1, int(round(t1 * FPS)) + 1)]
    rows = []
    for t in ts:
        Kh = clip.arm(t)[0]
        Kk, mode = clip.knife(t, Kh)
        rows.append((t, Kh, Kk, runtime_knife(Kk, Kh), mode))
    print('  t      mode     knife cm/s  deg/s | shown cm/s  deg/s | hand cm/s  deg/s | index thumb')
    out, prev_v = [], None
    for (ta, ha, ka, sa, _), (tb, hb, kb, sb, m) in zip(rows, rows[1:]):
        dt = tb - ta
        r = dict(t=round(tb, 4), mode=m, v=float(np.linalg.norm(kb.p - ka.p)) / dt, w=angle_deg(ka.q, kb.q) / dt,
                 vs=float(np.linalg.norm(sb.p - sa.p)) / dt, ws=angle_deg(sa.q, sb.q) / dt,
                 vh=float(np.linalg.norm(hb.p - ha.p)) / dt, wh=angle_deg(ha.q, hb.q) / dt,
                 vel=(sb.p - sa.p) / dt)
        r['dv'] = 0.0 if prev_v is None else float(np.linalg.norm(r['vel'] - prev_v))
        prev_v = r['vel']
        out.append(r)
        print('  %.4f %-8s %7.1f %6.0f | %7.1f %6.0f | %7.1f %6.0f | %.2f  %.2f' % (
            tb, m, r['v'], r['w'], r['vs'], r['ws'], r['vh'], r['wh'], finger_open(tb, 'index'), finger_open(tb, 'thumb')))
    worst = max(out[1:], key=lambda r: r['dv'])
    print('  largest frame-to-frame change of the shown knife velocity: %.0f cm/s at %.4f s' % (worst['dv'], worst['t']))
    return out


def author(preview=False):
    clip = EquipClip()
    R = clip.R
    R.reset_twist_memory()
    n = int(round(LENGTH * FPS))
    frames, diags, previews, prev_q = [], [], {}, None
    for i in range(n + 1):
        t = i / FPS
        world, K, d = clip.sample(t)
        keys = R.local_keys(world, prev_q)
        prev_q = {b: v[1] for b, v in keys.items()}
        frames.append({b: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for b, v in keys.items()})
        r = d['hand']['right']
        diags.append(dict(t=round(t, 4), mode=d['mode'], open=d['open'], reach=round(r['reach'], 3), rho=round(r['rho'], 1),
                          twist=round(math.degrees(r['theta']), 1), ext=round(r['ext'], 1), uln=round(r['uln'], 1),
                          grip=[round(v, 3) for v in d['hand']['grip_ndc']], elbow=[round(v, 2) for v in d['hand']['elbow_ndc']],
                          knife={k: [round(v, 3) for v in p] for k, p in d['knife'].items()}, knife_depth=round(d['knife_depth'], 1),
                          arm_margin=round(d['arm_margin'], 3)))
        if t < 0.19 and (d['arm_margin'] < 1.0 or (d['mode'] != 'grip' and t < 0.105 and
                                                   min(max(p[1], abs(p[0])) for p in d['knife'].values() if p[0] == p[0]) < 1.0)):
            print('  visible before the reference shows it: t %.3f arm margin %.3f knife %s' % (
                t, d['arm_margin'], {k: [round(v, 2) for v in p] for k, p in d['knife'].items()}))
        if preview and i % (FPS // 30) == 0:
            # the knife as the game shows it (runtime grip lock applied)
            previews['Equip_%03d' % int(round(t * 1000))] = (world, d['shown'])
    data = dict(name='Equip', fps=FPS, length=LENGTH, loop=False, contact=None, release=TR, catch=TC,
                bones=R.rig.names, frames=frames, diagnostics=diags)
    (OUT / 'Equip.json').write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    worst = dict(max_reach=max(x['reach'] for x in diags), rho=[min(x['rho'] for x in diags), max(x['rho'] for x in diags)],
                 twist=[min(x['twist'] for x in diags), max(x['twist'] for x in diags)],
                 twist_rate=max(abs(diags[i + 1]['twist'] - diags[i]['twist']) * FPS for i in range(len(diags) - 1)),
                 ext=[min(x['ext'] for x in diags), max(x['ext'] for x in diags)],
                 uln=[min(x['uln'] for x in diags), max(x['uln'] for x in diags)],
                 knife_min_depth=min(x['knife_depth'] for x in diags))
    print('Equip', json.dumps(worst), flush=True)
    clips_path = P / 'clips.json'
    meta = json.loads(clips_path.read_text('utf-8'))
    meta.setdefault('clips', {})['Equip'] = dict(length=LENGTH, loop=False, frames=n + 1, contact=None, release=TR, catch=TC,
                                                 source='author_kukri_equip.py', ranges=worst)
    clips_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return diags, previews


def compare(names, out_dir):
    """Reference frame (top) over our preview (bottom) per 30 Hz frame, 6 per sheet."""
    import cv2
    ref_dir = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020\equip_frames")
    cells = []
    for name in names:
        t = int(name.split('_')[1]) / 1000.0
        ref = cv2.imread(str(ref_dir / ('f%05d.png' % (1564 + int(round(t * 30))))))
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
        cv2.imwrite(str(WORK / ('cmp_equip_%d.jpg' % (s // 6))),
                    np.vstack([np.hstack(chunk[r:r + 3]) for r in range(0, len(chunk), 3)]), [cv2.IMWRITE_JPEG_QUALITY, 82])


if __name__ == '__main__':
    diags, previews = author('--preview' in sys.argv or '--compare' in sys.argv)
    if previews:
        from preview_tools import write_poses, render
        WORK.mkdir(parents=True, exist_ok=True)
        write_poses(previews, WORK / 'equip_previews.json')
        for line in render(WORK / 'equip_previews.json', WORK / 'previews', 480):
            if 'KUKRI_PREVIEW' not in line:
                print(line)
        if '--compare' in sys.argv:
            compare(sorted(previews), WORK / 'previews')
