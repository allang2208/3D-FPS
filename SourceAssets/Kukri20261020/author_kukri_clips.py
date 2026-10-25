"""Author the seven kukri first-person clips on the shared sword arms skeleton.

Reference rhythm and composition: Bilibili BV1CeYUeSE7b (Apex Legends, Bangalore heirloom),
chapters 握持姿势 / 切刀 / 近战 (#1 ↘ diagonal, #2 ← horizontal, #3 刀把 pommel).  Only timing,
direction and framing are taken from the video; every pose is solved on our own rig.

Two key kinds, both evaluated as one kukri grip frame per frame:
  * arm keys  (akey): wrist point, elbow swivel hint, forearm roll psi, wrist deltas -> exact
    anatomical arm; the elbow is pinned (pole weight 1);
  * blade keys (kkey): grip point, blade direction, edge direction; the elbow is solved on the
    reach circle closest to the hand's natural forearm line (pole weight 0).
The hammer grip (accepted sword fist) puts the edge on the knuckle side, so the edge-leading cuts
are: #1 palm-down backhand diagonal with the blade pointing out to the right, #2 palm-up cross-body
draw cut with the blade up.  See Docs/Weapons/kukri-20261020.md.

Run:  python author_kukri_clips.py [ClipName ...] [--preview]
Output: Clips/<Name>.json (local bone keys, UE convention) + clips.json summary.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

from kukri_rig import KukriRig
from kmath import mesh_to_cam, cam_to_mesh

P = Path(__file__).resolve().parent
FPS = 120
OUT = P / 'Clips'
OUT.mkdir(exist_ok=True)

# Ready stance (Work/_refine_idle.py): neutral forearm rotation (rho ~ +5), wrist ext 16 / uln 27.
IDLE = dict(W=(30.0, 20.0, -21.0), E=(25.0, 60.0, -35.0), psi=100.0, du=12.0, de=0.0,
            C=(0.0, 0.0, 0.0), L=(16.0, -24.0, -64.0))
ARM = ('W', 'E', 'psi', 'du', 'de', 'C', 'L')
BLADE = ('G', 'b', 'e', 'P', 'w', 'L', 'C')
MID = np.array([2.5, 0.0, 16.0])       # blade middle in the grip frame (cm)


def arr(v):
    return np.array(v, float) if isinstance(v, (tuple, list, np.ndarray)) else float(v)


def arm_params(**kw):
    k = {n: arr(v) for n, v in IDLE.items()}
    k.update({n: arr(v) for n, v in kw.items()})
    return k


def spline(keys, t, names):
    """Non-uniform Catmull-Rom per parameter; 'hold' keys (and the ends) have zero velocity."""
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


def periodic(base, t, period, terms):
    """Loop offsets on arm params: terms = [(param, axis or None, amplitude, harmonic, phase)]."""
    p = {n: (v.copy() if isinstance(v, np.ndarray) else v) for n, v in base.items() if n in ARM}
    for name, axis, amp, harm, phase in terms:
        v = amp * math.sin(2 * math.pi * harm * t / period + phase)
        if axis is None:
            p[name] += v
        else:
            p[name][axis] += v
    return p


class Designer:
    def __init__(self, R):
        self.R = R

    def akey(self, t, hold=False, **kw):
        prm = arm_params(**kw)
        K, E = self.R.arm_to_kukri(tuple(prm['W']), tuple(prm['E']), prm['psi'], prm['de'], prm['du'], tuple(prm['C']))
        return dict(t=t, hold=hold, G=mesh_to_cam(K.p), b=mesh_to_cam(K.axis(2)), e=mesh_to_cam(K.axis(0)),
                    P=mesh_to_cam(E), w=1.0, L=prm['L'], C=prm['C'])

    def kkey(self, t, hold=False, *, G, b, e, w=0.0, P=(20.0, 40.0, -40.0), L=None, C=(0, 0, 0)):
        b = arr(b) / np.linalg.norm(b)
        e = arr(e)
        e = e - b * np.dot(e, b)
        e = e / np.linalg.norm(e)
        return dict(t=t, hold=hold, G=arr(G), b=b, e=e, P=arr(P), w=float(w),
                    L=arr(L if L is not None else IDLE['L']), C=arr(C))


def solve_arm_sample(R, prm):
    K, E = R.arm_to_kukri(tuple(prm['W']), tuple(prm['E']), prm['psi'], prm['de'], prm['du'], tuple(prm['C']))
    # 'LA' (optional): explicit left arm (kukri_rig.left_hand_explicit), e.g. the uppercut's open balance hand.
    world, diag = R.pose(K, left_target_cam=tuple(prm['L']), clav_r=tuple(prm['C']), pole_r=E, pole_r_weight=1.0,
                         left_press=float(prm.get('Lp', 0.0)), left_arm=prm.get('LA'))
    return world, K, diag


def solve_blade_sample(R, prm):
    K = R.kukri_frame(tuple(prm['G']), prm['b'], prm['e'])
    world, diag = R.pose(K, left_target_cam=tuple(prm['L']), clav_r=tuple(prm['C']),
                         pole_r=cam_to_mesh(prm['P']), pole_r_weight=min(1.0, max(0.0, prm['w'])))
    return world, K, diag


# ----------------------------------------------------------------------------- clip designs
def clip_idle(D):
    """3.0 s breathing loop: slow rise/fall, tiny wrist and roll drift, all harmonics of 3 s."""
    base = arm_params()
    # V3: the breathing moves the whole forearm+fist+kukri together; the wrist-only terms that rocked
    # the blade about a nearly still fist (read as the knife moving on its own) are cut to a trace.
    terms = [('W', 2, .55, 1, 0.0), ('W', 0, .30, 1, 1.2), ('W', 1, .22, 1, 2.1),
             ('psi', None, .35, 1, .6), ('du', None, .25, 2, 1.0), ('L', 2, .6, 1, 0.3)]
    return dict(length=3.0, loop=True, kind='arm', sample=lambda t: periodic(base, t, 3.0, terms))


def clip_walk(D):
    """0.9 s two-step loop: vertical bob at 2x, lateral sway at 1x, slight forearm roll."""
    base = arm_params(W=(30.0, 20.5, -21.6))
    terms = [('W', 2, .85, 2, -math.pi / 2), ('W', 1, .95, 1, 0.0), ('W', 0, .40, 2, 0.4),
             ('psi', None, .8, 1, .5), ('de', None, .6, 2, -1.2), ('L', 0, 6.0, 1, math.pi)]
    return dict(length=0.9, loop=True, kind='arm', sample=lambda t: periodic(base, t, 0.9, terms))


RUN_POSE = dict(W=(26.0, 26.0, -32.0), E=(10.0, 55.0, -55.0), psi=78.0, du=22.0, de=-12.0, C=(0.0, 0.0, -4.0))


def clip_run(D):
    """2/3 s sprint loop (20 frames at the 30 fps resample grid): kukri lowered to the bottom-right like the reference sprint, arm pump."""
    base = arm_params(**RUN_POSE)
    terms = [('W', 2, 1.8, 2, -math.pi / 2), ('W', 0, 2.4, 1, 0.0), ('W', 1, 1.2, 1, .8),
             ('psi', None, 4.0, 1, .3), ('de', None, 4.0, 1, 1.0), ('L', 0, 14.0, 1, math.pi), ('L', 2, 4.0, 2, 0)]
    return dict(length=80 / FPS, loop=True, kind='arm', sample=lambda t: periodic(base, t, 80 / FPS, terms))


# The draw ("Equip") is authored by author_kukri_equip.py since V2 (2026-10-22, toss and catch: the knife leaves the
# fist, which this generic loop cannot express).  The V1 0.70 s wrist-flip draw is archived under
# trash/kukri-equip-v1-20261022/.


def clip_slash1(D):
    """0.80 s #1 ↘: palm-down backhand diagonal, upper-left down to lower-right; contact 0.27-0.36."""
    # Edge directions from Work/_search_s1_low.py (cut direction (0.15, 0.7, -0.7), elbow kept below
    # the frame): lead 0.85-1.0 with the most anatomical wrist/forearm of each key.
    k = [D.akey(0.00, True),
         D.kkey(0.10, G=(38, 4, -10), b=(-0.1, 0.7, 0.7), e=(0.6, 0.55, -0.55)),
         D.kkey(0.21, True, G=(41, -6, -3), b=(0.0, 0.71, 0.71), e=(0.643, 0.544, -0.544)),
         D.kkey(0.31, G=(44, 8, -13), b=(0.0, 0.87, 0.5), e=(0.342, 0.47, -0.817)),
         D.kkey(0.41, G=(35, 22, -28), b=(0.1, 0.75, 0.65), e=(0.25, 0.6, -0.75)),
         D.kkey(0.50, True, G=(27, 29, -36), b=(0.18, 0.68, 0.71), e=(0.182, 0.687, -0.704)),
         D.akey(0.66, W=(28.0, 24.0, -27.0), psi=96.0, du=14.0, de=2.0),
         D.akey(0.80, True)]
    return dict(length=0.80, loop=False, kind='blade', keys=k, contact=(0.26, 0.37))


def clip_slash2(D):
    """0.80 s #2 ←: palm-up cross-body draw cut from the right across to the left; contact 0.25-0.35."""
    k = [D.akey(0.00, True),
         D.akey(0.10, W=(28.0, 30.0, -17.0), E=(10.0, 55.0, -32.0), psi=70.0, du=6.0, de=-12.0),
         D.akey(0.21, True, W=(26.0, 38.0, -14.0), E=(4.0, 52.0, -30.0), psi=45.0, du=2.0, de=-28.0, C=(0, 4, -6)),
         D.akey(0.30, W=(40.0, 8.0, -20.0), E=(30.0, 32.0, -22.0), psi=40.0, du=0.0, de=-30.0, C=(0, -4, 8)),
         D.akey(0.39, W=(36.0, -12.0, -26.0), E=(28.0, 20.0, -26.0), psi=48.0, du=4.0, de=-24.0, C=(0, -8, 16)),
         D.akey(0.50, True, W=(30.0, -18.0, -34.0), E=(24.0, 14.0, -34.0), psi=56.0, du=8.0, de=-18.0, C=(0, -8, 16)),
         D.akey(0.66, W=(29.0, 12.0, -27.0), psi=92.0, du=12.0, de=-4.0, C=(0, -2, 4)),
         D.akey(0.80, True)]
    return dict(length=0.80, loop=False, kind='blade', keys=k, contact=(0.24, 0.36))


def clip_pommel(D):
    """0.80 s #3 刀把: blade up, the fist and pommel drive forward; contact 0.26-0.34."""
    k = [D.akey(0.00, True),
         D.akey(0.10, W=(28.0, 14.0, -24.0), E=(16.0, 52.0, -40.0), psi=104.0, du=4.0, de=6.0, C=(0, -2, 3)),
         D.akey(0.19, True, W=(24.0, 10.0, -26.0), E=(10.0, 48.0, -42.0), psi=106.0, du=-4.0, de=10.0, C=(0, -4, 5)),
         D.akey(0.27, W=(44.0, 8.0, -16.0), E=(30.0, 42.0, -30.0), psi=102.0, du=-2.0, de=6.0, C=(0, -2, 10)),
         D.akey(0.33, True, W=(48.0, 8.0, -14.5), E=(34.0, 40.0, -28.0), psi=101.0, du=0.0, de=5.0, C=(0, -2, 12)),
         D.akey(0.42, W=(45.0, 9.0, -16.0), E=(30.0, 44.0, -30.0), psi=101.0, du=2.0, de=5.0, C=(0, -2, 9)),
         D.akey(0.62, W=(32.0, 17.0, -21.0), psi=100.0, du=10.0, de=2.0),
         D.akey(0.80, True)]
    return dict(length=0.80, loop=False, kind='blade', keys=k, contact=(0.25, 0.35))


ATTACK_SECONDS = 38 / 30   # reference 1:27.00 -> 1:28.27, on the 30 fps resample grid


def clip_attack(D):
    """Single attack (2026-10-20 V2): reference melee #2 ← big right-to-left sweep, frame-fitted.

    Keys are the anatomical arm parameters fitted per reference frame by fit_reference.py
    (attack_keys.json): drop the blade level and cock right (0-0.10), pull out of frame low-right
    (0.13-0.23), whip back in palm-down with the pommel leading and the blade trailing up-right
    (0.27-0.40, contact), forearm sweeps across close to the lens (0.43-0.70), drops out of frame
    (0.77-0.90), rises from below and flips the blade up into the stance (1.03-1.27)."""
    from fit_reference import Fitter
    F = Fitter(D.R)
    data = json.loads((P / 'attack_keys.json').read_text('utf-8'))
    keys = [dict(t=k['t'], hold=(i == 0), x=np.array(k['x'], float)) for i, k in enumerate(data['keys'])]
    keys.append(dict(t=ATTACK_SECONDS, hold=True, x=np.array(data['keys'][0]['x'], float)))

    def sample(t):
        x = spline(keys, t, ('x',))['x']
        W, phi, psi, du, de, C = F.unpack(x)
        return dict(W=np.array(W, float), E=np.array(F.hint(W, phi, C), float), psi=float(psi), du=float(du),
                    de=float(de), C=np.array(C, float), L=np.array(IDLE['L'], float))
    return dict(length=ATTACK_SECONDS, loop=False, kind='arm', sample=sample, contact=(0.32, 0.45), preview_step=1 / 30)


def clip_attack2(D):
    """Second hit, V11 (2026-10-22): reference melee #1 ↘ (BV1CeYUeSE7b 1:24.33-1:25.60) fitted frame by frame by
    fit_reference.py --attack2 (attack2_keys.json, REF_DIAG).  Starts and ends on the stance (38/30 s): the blade
    dips left and the fist drops (0.03-0.10), backhand cock up-left across the frame close to the lens (0.13-0.33),
    one diagonal cut through the centre to the lower-right corner with the blade trailing up-left (contact
    0.34-0.47 s), below the frame (0.50-0.95), re-raise and blade flip into the stance (1.03-1.27)."""
    from fit_reference import Fitter
    F = Fitter(D.R)
    data = json.loads((P / 'attack2_keys.json').read_text('utf-8'))
    stance = data.get('start') == 'stance'
    keys = [dict(t=k['t'], hold=(stance and i == 0), x=np.array(k['x'], float)) for i, k in enumerate(data['keys'])]
    keys.append(dict(t=data['length'], hold=True, x=np.array(json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x'], float)))

    def sample(t):
        x = spline(keys, t, ('x',))['x']
        W, phi, psi, du, de, C = F.unpack(x)
        return dict(W=np.array(W, float), E=np.array(F.hint(W, phi, C), float), psi=float(psi), du=float(du),
                    de=float(de), C=np.array(C, float), L=np.array(IDLE['L'], float))
    return dict(length=data['length'], loop=False, kind='arm', sample=sample,
                contact=(0.34, 0.47) if stance else (0.19, 0.31), preview_step=1 / 30)


# V12c stab drive (author seconds): the frozen cock at 0.333 -> the crosshair at 0.367, eased in (u ** EASE: speed
# peaks on arrival), then the fist runs STAB_OVERSHOOT cm past the extension along the stab and rebounds within
# STAB_REBOUND (peak at STAB_PEAK of it).  KukriRhythm::Swings[2].StrikeAt is the arrival.
STAB_DRIVE = (0.333, 0.367)
STAB_DRIVE_EASE = 2.2
STAB_OVERSHOOT = 2.0
STAB_REBOUND = 0.033
STAB_PEAK = 0.35


def clip_attack3(D):
    """Third hit, fitted by fit_reference.py --attack3 (attack3_keys.json).
    V12 (2026-10-22): one-handed crouch stab, reference melee #5 戳 (BV1CeYUeSE7b 1:34.77-1:35.97), from the stance
    (36/30 s): blade flips upright and the fist drops (0.03-0.10), slides to the lower left with the blade turned to
    point forward (0.13-0.17), cocked low at the left hip (0.17-0.33), one-frame drive to the crosshair with the blade
    into the screen (contact 0.34-0.47), held (0.43-0.57), withdrawn down-left and out through the bottom (0.60-0.77),
    re-raise into the stance.  The left hand stays lowered (left_press false).
    V8-V11 (archived, trash/kukri-20261022-v12/): two-handed thrust, left palm on the pommel 0.07-0.58 s."""
    from fit_reference import Fitter
    F = Fitter(D.R)
    data = json.loads((P / 'attack3_keys.json').read_text('utf-8'))
    stance = data.get('start') == 'stance'
    two_handed = data.get('left_press', True)
    # V12c: keys fitted with target 'hold' (the frozen cock, the arrival on the crosshair) get zero spline tangents.
    keys = [dict(t=k['t'], hold=(stance and i == 0) or bool(k.get('target', {}).get('hold')), x=np.array(k['x'], float))
            for i, k in enumerate(data['keys'])]
    keys.append(dict(t=data['length'], hold=True, x=np.array(json.loads((P / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x'], float)))
    drive = STAB_DRIVE if data.get('variant', '').startswith('V12c') else None
    if drive:
        k0 = next(k for k in keys if abs(k['t'] - drive[0]) < 1e-3)
        k1 = next(k for k in keys if abs(k['t'] - drive[1]) < 1e-3)
        W0, W1 = k0['x'][:3], k1['x'][:3]
        push = (W1 - W0) / np.linalg.norm(W1 - W0)   # camera-space stab direction of the wrist

    def arm_x(t):
        """V12c drive: cock -> crosshair eased in (speed peaks on arrival, no settling into the target), then the fist
        overshoots STAB_OVERSHOOT cm along the stab and rebounds onto the held extension (the impact stop)."""
        if drive and drive[0] <= t < drive[1]:
            u = (t - drive[0]) / (drive[1] - drive[0])
            return k0['x'] + (k1['x'] - k0['x']) * u ** STAB_DRIVE_EASE
        x = np.array(spline(keys, t, ('x',))['x'], float)
        if drive and drive[1] <= t < drive[1] + STAB_REBOUND:
            s = (t - drive[1]) / STAB_REBOUND
            peak = STAB_PEAK
            bump = math.sin(0.5 * math.pi * s / peak) if s < peak else 0.5 * (1 + math.cos(math.pi * (s - peak) / (1 - peak)))
            x[:3] = x[:3] + push * STAB_OVERSHOOT * bump
        return x

    def press(t):
        if not two_handed or t <= 0.07 or t >= 0.58:
            return 0.0
        if t < 0.17:
            return (t - 0.07) / 0.10
        if t <= 0.45:
            return 1.0
        return 1.0 - (t - 0.45) / 0.13

    def sample(t):
        x = arm_x(t)
        W, phi, psi, du, de, C = F.unpack(x)
        return dict(W=np.array(W, float), E=np.array(F.hint(W, phi, C), float), psi=float(psi), du=float(du),
                    de=float(de), C=np.array(C, float), L=np.array(IDLE['L'], float), Lp=press(t))
    return dict(length=data['length'], loop=False, kind='arm', sample=sample,
                contact=(0.26, 0.38) if two_handed else (0.34, 0.47), preview_step=1 / 30)


CLIPS = {'Idle': clip_idle, 'Walk': clip_walk, 'Run': clip_run,
         'Slash1': clip_slash1, 'Slash2': clip_slash2, 'Pommel': clip_pommel, 'Attack': clip_attack,
         'Attack2': clip_attack2, 'Attack3': clip_attack3}


def author(names=None, preview=False, step=.05):
    R = KukriRig()
    D = Designer(R)
    summary, previews = {}, {}
    for name, make in CLIPS.items():
        if names and name not in names:
            continue
        spec = make(D)
        R.reset_twist_memory()
        n = int(round(spec['length'] * FPS))
        frames, diags, prev_q, prev_mid = [], [], None, None
        for i in range(n + 1):
            t = i / FPS
            if spec['loop'] and i == n:
                t = 0.0  # exact seam
            if spec['kind'] == 'arm':
                world, K, d = solve_arm_sample(R, spec['sample'](t))
            else:
                world, K, d = solve_blade_sample(R, spline(spec['keys'], t, BLADE))
            keys = R.local_keys(world, prev_q)
            prev_q = {b: v[1] for b, v in keys.items()}
            frames.append({b: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for b, v in keys.items()})
            mid = mesh_to_cam(K.point(MID))
            lead = None
            if prev_mid is not None:
                v = (mid - prev_mid) * FPS
                if np.linalg.norm(v) > 60:
                    lead = float(np.dot(mesh_to_cam(K.axis(0)), v / np.linalg.norm(v)))
            prev_mid = mid
            r = d['right']
            diags.append(dict(t=round(t, 4), reach=round(r['reach'], 3), rho=round(r['rho'], 1), twist=round(math.degrees(r['theta']), 1), roll_u=round(r['roll_u'], 1), ext=round(r['ext'], 1),
                              uln=round(r['uln'], 1), tip=[round(v, 3) for v in d['tip_ndc']],
                              grip=[round(v, 3) for v in d['grip_ndc']], elbow=[round(v, 2) for v in d['elbow_ndc']],
                              mid_cam=[round(float(v), 2) for v in mid], edge_lead=None if lead is None else round(lead, 2),
                              speed=0 if i == 0 else round(float(np.linalg.norm(v)) if prev_mid is not None else 0, 1)))
            if preview and (i % max(1, int(round(FPS * spec.get('preview_step', step)))) == 0 or i == n):
                previews['%s_%03d' % (name, int(round(t * 1000)))] = (world, K)
        data = dict(name=name, fps=FPS, length=spec['length'], loop=spec['loop'], contact=spec.get('contact'),
                    bones=R.rig.names, frames=frames, diagnostics=diags)
        (OUT / (name + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
        worst = dict(max_reach=max(x['reach'] for x in diags), rho=[min(x['rho'] for x in diags), max(x['rho'] for x in diags)],
                     twist=[min(x['twist'] for x in diags), max(x['twist'] for x in diags)],
                     twist_rate=max(abs(diags[i + 1]['twist'] - diags[i]['twist']) * FPS for i in range(len(diags) - 1)),
                     ext=[min(x['ext'] for x in diags), max(x['ext'] for x in diags)],
                     uln=[min(x['uln'] for x in diags), max(x['uln'] for x in diags)])
        if spec.get('contact'):
            c0, c1 = spec['contact']
            leads = [x['edge_lead'] for x in diags if c0 <= x['t'] <= c1 and x['edge_lead'] is not None]
            worst['contact_edge_lead'] = [min(leads), max(leads)] if leads else None
        summary[name] = dict(length=spec['length'], loop=spec['loop'], frames=n + 1, contact=spec.get('contact'), ranges=worst)
        print(name, json.dumps(worst), flush=True)
    return summary, previews


if __name__ == '__main__':
    names = [a for a in sys.argv[1:] if not a.startswith('--')]
    summary, previews = author(names or None, '--preview' in sys.argv)
    old = json.loads((P / 'clips.json').read_text('utf-8')).get('clips', {}) if (P / 'clips.json').exists() else {}
    old.update(summary)
    (P / 'clips.json').write_text(json.dumps(dict(fps=FPS, clips=old, skeleton='/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny_Skeleton',
                                                 mesh='/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms',
                                                 reference='https://www.bilibili.com/video/BV1CeYUeSE7b/', runtime_tested=False),
                                            ensure_ascii=False, indent=2), encoding='utf-8')
    if previews:
        from preview_tools import write_poses, render, sheet
        (P / 'Work').mkdir(exist_ok=True)
        write_poses(previews, P / 'Work' / 'clip_previews.json')
        render(P / 'Work' / 'clip_previews.json', P / 'Work' / 'clip_previews', 480)
        groups = {}
        for k in previews:
            groups.setdefault(k.split('_')[0], []).append(k)
        for g, ks in groups.items():
            sheet(P / 'Work' / 'clip_previews', ks, P / 'Work' / ('sheet_' + g + '.jpg'), cols=6)



