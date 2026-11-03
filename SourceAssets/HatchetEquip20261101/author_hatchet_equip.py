"""Tactical hatchet draw "HatchetEquip" V2: the reference toss and catch (2026-11-02).

User 2026-11-02: refine the draw after BV1pqkyYyEDY 39-40 s (Apex Bloodhound heirloom, 切刀动作 #2 抛), as close to
100 % as possible.  V1 (2026-11-01, straight vertical toss, Work/v1/) is replaced.  Read-out of the reference (file
time, t = 0 at 38.700 s / frame 1161; Reference/grid_ref.py sheets, camera from Reference/camera_ref.py):
  0.033-0.10  the right forearm swings in from the right edge, palm down, the fist just under the head; the head points
              forward-left with the edge down, the handle runs back towards the camera behind the fist
              (V2.1 replaces this by a lift from under the bottom edge on our clock 0-0.15 s, see LIFT_SECONDS)
  0.10-0.145  the wrist flips the head up (the handle swings down through the loosening fist) and lets go at the
              middle of the handle, head up-left (35 deg)
Times below are the reference's; on our clock everything from the flip on runs LIFT_SECONDS - 0.10 later (rt()).
  0.145-0.333 the axe floats up without spinning, straightening to vertical, drifting right and closer; the open hand
              moves out to the right, then comes back down to the lower handle
  0.333       the fist closes on the handle (caught)
  0.333-0.433 pulled down and pushed out to the screen centre, the head tipping right (31 deg)
  0.433-0.667 held out at arm's length: the head rocks from right to left (-30 deg) while the edge turns away from the
              camera (edge-on 0.53-0.67)
  0.667-      back to the stance.  The reference settles into its own upright hold; this clip goes on into the
              kukri-family stance the hatchet shares (attack_keys.json key 0 = Idle frame 0): the left lean continues
              and the head comes in close.
Our hatchet has a shorter handle than the Apex axe: the head is matched in position, size and lean, the handle only in
direction, so the fist sits higher than the reference's when it holds the lower handle.  The accepted hammer grip puts
the edge on the knuckle side; the flat-to-camera views of the reference need the head tilted away (the solver trades
flatness against the wrist, see KEY weights).

Every pose is the hatchet's grip frame from a screen read-out (hatchet_pose.axe_frame): head point EYE at an NDC position
and depth, on-screen lean, tilt along the view ray and facing about the handle.  Held keys put the fist at offset s on the
handle and are solved for the wrist (solve_key); the parameter tracks are Catmull-Rom splines through the keys.

Run:  python author_hatchet_equip.py [--preview] [--compare] [--header] [--poses]
Output: Clips/HatchetEquip.json, clips.json; --header writes Source/FPSGAME/Weapons/Kukri/HatchetDrawRhythm.h;
--preview renders Previews/ (videos, sheets); --compare puts the reference above our frames (Previews/compare_*.jpg).
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

P = Path(__file__).resolve().parent
KUKRI = P.parent / 'Kukri20261020'
sys.path.insert(0, str(KUKRI))
sys.path.insert(0, str(P))
from kukri_rig import KukriRig, ndc, TIP, BLADE_BASE  # noqa: E402
from kmath import T, mesh_to_cam, cam_to_mesh, qslerp, qmul, qconj, qaxis  # noqa: E402
from fit_reference import Fitter  # noqa: E402
from hatchet_pose import (EYE_Z, SPIKE, BEARD, POMMEL, ndc_cam, unit, axe_frame, hand_on_axe, arm_diag,  # noqa: E402
                          strain)

FPS = 120
CLIP = 'HatchetEquip'
OUT = P / 'Clips'
WORK = P / 'Work'
PREVIEWS = P / 'Previews'
HEADER = P.parents[1] / 'Source' / 'FPSGAME' / 'Weapons' / 'Kukri' / 'HatchetDrawRhythm.h'
REF_DIR = Path(r"D:\FPS3D\FPSGAME\Saved\Reference\HatchetBV1pqkyYyEDY20261102")
REF_T0 = 1161                       # reference frame at t = 0 (38.700 s)
IDLE_L = (16.0, -24.0, -64.0)       # left hand lowered out of frame (as in the kukri draw)
HEAD_PTS = [np.array(v) for v in ([4.0, 0.0, 30.9], [16.35, 0.0, 27.0], [16.0, 0.0, 19.0], [-4.5, 0.0, 30.0],
                                  [-4.5, 0.0, 22.0], [6.0, 0.0, 16.5])]

# ---------------------------------------------------------------- reference read-out
# Matched head point: where the reference handle enters the head's top piece, ~22 % of the head height below its top;
# on our 15 cm head that is z = 27.5 (the fist at the grip centre is then as far below it as the reference's catching
# fist is below its socket).
MATCH_Z = 27.5
HEAD_CM = 15.0                       # our head height (z 16 -> 31)
S_CHOKE = 13.0                       # the lift holds the handle just under the head (grip offset, cm)
ASPECT_SCREEN = 16.0 / 9.0           # NDC x -> screen-proportional units
# V2.1 (user 2026-11-02: keep the rest, bring the hatchet up from below the frame into the flip).  The reference swings
# the forearm in from the right in 0.10 s (1161-1164); here the fist lifts the hatchet straight up from under the bottom
# edge, head first, and cocks the head back to the reference's 1164 pose for the flip.  The lift takes LIFT_SECONDS:
# reference time up to 1164 is stretched onto it (the reference camera too), everything after is shifted by the extra.
LIFT_SECONDS = 0.15
LIFT_DROP = (-20.0, 0.0, -20.0)      # t = 0: the first lift pose moved by this (camera cm: nearer and down) -> under
                                     # the frame and within reach (the fist comes up from beside the body)


def rt(frame):
    """Our clip time of a reference frame."""
    s = (frame - REF_T0) / 30.0
    return s * LIFT_SECONDS / 0.10 if s <= 0.10 else s + (LIFT_SECONDS - 0.10)


def kt(key):
    return key.get('t', rt(key['f']))


# Per reference frame: eye = handle top at the head (NDC x right, y down), h = head height on screen (NDC), lean =
# on-screen handle angle (deg, + head right), face = how the head shows (0 flat to the camera with the edge left,
# 90 edge-on with the edge away), fist = the fist (NDC) where the reference shows it, s = grip offset while held
# (None = in the air).  'hide' = everything below / right of the frame.
REF = [
    # lift (V2.1, designed): the fist holds the upper handle turned in the hand (turned: beta free), the head shows its
    # flat and comes up through the bottom edge leaning a little left, the forearm rising behind it from below the frame
    # (elbow_below); it cocks back to 45 deg as it arrives (1164) so the wrist can flip it up.  t = 0 is the first pose
    # dropped LIFT_DROP cm under the frame.
    # tilt / twist targets make one progression: the head comes up upright (tilt 0), cocks back towards the face as the
    # forearm rises from below (a back-cocked head is what keeps that wrist natural), and the flip throws it forward
    # again (tilt 6 at the release, then -31 at the catch: ~35 deg out of the screen plane in the air) while the
    # forearm pronates into the flick (twist -22 -> -50).
    dict(f=1162, t=0.070, eye=(0.10, 0.80), h=0.60, lean=-22, face=0, fist=None, s=S_CHOKE, turned=True,
         wface=3.0, tilt=0.0, wtilt=4.0, elbow_below=True, forearm_deg=60.0, reach=0.82, twist=-32.0),
    dict(f=1163, t=0.112, eye=(0.11, 0.44), h=0.62, lean=-36, face=0, fist=None, s=S_CHOKE, turned=True,
         wface=3.0, tilt=12.0, wtilt=4.0, elbow_below=True, forearm_deg=60.0, reach=0.82, twist=-26.0),
    dict(f=1164, eye=(0.12, 0.15), h=0.62, lean=-45, face=0, fist=None, s=S_CHOKE, turned=True, wface=3.0,
         tilt=24.0, wtilt=4.0, elbow_below=True, forearm_deg=62.0, reach=0.82, twist=-22.0),                           # cocked: head back towards the face
    dict(f=1165, eye=(0.20, -0.05), h=0.61, lean=-38, face=0, fist=None, s=S_CHOKE, turned=True, wface=3.0,
         tilt=6.0, wtilt=4.0, elbow_below=True, forearm_deg=70.0, reach=0.82, twist=-50.0),                            # flipped up, letting go
    # in the air: hand = the open hand (NDC), fing / palm = its finger and palm directions in the reference (camera:
    # x away, y right, z up): palm down and fingers left as it lets go, then fingers up with the palm to the handle
    dict(f=1166, eye=(0.20, -0.33), h=0.66, lean=-26, face=0, hand=(0.62, 0.00), s=None, fing=(0.2, -1.0, 0.1),
         palm=(0.0, 0.0, -1.0)),
    dict(f=1167, eye=(0.29, -0.47), h=0.66, lean=-5, face=0, hand=(0.74, -0.11), s=None, fing=(0.2, -0.7, 0.7),
         palm=(0.0, -0.6, -0.8)),
    dict(f=1168, eye=(0.35, -0.50), h=0.66, lean=-3, face=0, hand=(0.80, 0.00), s=None, fing=(0.2, -0.3, 1.0),
         palm=(0.0, -1.0, -0.2)),
    dict(f=1169, eye=(0.36, -0.48), h=0.66, lean=0, face=0, hand=(0.76, 0.15), s=None, fing=(0.2, -0.3, 1.0),
         palm=(0.0, -1.0, 0.0)),
    dict(f=1170, eye=(0.48, -0.53), h=0.63, lean=2, face=0, hand=(0.60, 0.45), s=None),     # reaching for the grip
    # caught; twist = forearm roll targets that keep the catch from rolling the forearm in and straight back out
    dict(f=1171, eye=(0.50, -0.51), h=0.60, lean=2, face=10, fist=(0.45, 0.62), s=0.0, twist=-58.0),
    dict(f=1172, eye=(0.55, -0.12), h=0.48, lean=13, face=45, fist=(0.42, 0.85), s=0.0, twist=-50.0),
    # held out from below: in the reference only the handle shows, the arm stays under the frame
    dict(f=1173, eye=(0.54, 0.06), h=0.36, lean=31, face=20, fist=(0.27, 0.88), s=0.0, arm_hide=True, twist=-45.0),
    dict(f=1174, eye=(0.25, 0.13), h=0.32, lean=17, face=0, fist=(0.12, 0.92), s=0.0, arm_hide=True),
    dict(f=1176, eye=(0.04, 0.07), h=0.38, lean=0, face=45, fist=None, s=0.0, arm_hide=True),
    dict(f=1178, eye=(0.01, 0.10), h=0.40, lean=-18, face=85, fist=None, s=0.0, arm_hide=True),
    dict(f=1180, eye=(0.00, 0.10), h=0.40, lean=-30, face=85, fist=None, s=0.0, arm_hide=True),
    dict(f=1181, eye=(0.16, 0.02), h=0.44, lean=-25, face=75, fist=None, s=0.0, arm_hide=True),
]
TR = rt(1165)                        # release: the handle leaves the opening fist
TC = rt(1171)                        # catch: the fist closes on the lower handle
T_STANCE = rt(1181) + 0.133          # into the shared stance (the reference settles about as long after 1181)
LENGTH = T_STANCE + 0.05

# Fingers (towards the flat bind hand; 0 = the accepted fist): loosen for the flip, spread wide in the air (the reference
# hand opens fully), cup to grab, close index first.
FINGER_KEYS = [(0.0, 0.0), (rt(1164), 0.0), (TR, 0.35), (rt(1166), 0.75), (rt(1169), 0.70), (rt(1170), 0.55),
               (TC - 0.004, 0.45)]
FINGER_CLOSE = {'index': (-0.004, 0.070), 'middle': (-0.001, 0.070), 'ring': (0.003, 0.070),
                'pinky': (0.006, 0.070), 'thumb': (0.012, 0.065)}

# Runtime grip lock (KukriArmsMeshComponent KukriGrip::HoldBand / ReleaseBand / DegreeToCm).
LOCK_HOLD, LOCK_FREE, LOCK_DEG_CM = 0.6, 2.5, 0.25

# Sounds (author seconds; existing assets, not auditioned): the flick as the head comes up and the axe leaves the
# hand, and the grip slap of the catch.
TOSS_SOUND = dict(volume=0.36, pitch=0.95)
CATCH_SOUND = dict(volume=0.32, pitch=1.05)

# ---------------------------------------------------------------- key poses
def head_box(K):
    """Our head on screen: NDC bounding box height and the visible margin of the whole hatchet."""
    pts = [mesh_to_cam(K.point(v)) for v in HEAD_PTS]
    ys = [ndc(c)[1] for c in pts if c[0] > 2]
    allp = pts + [mesh_to_cam(K.point(v)) for v in (POMMEL, [0.0, 0.0, 0.0], [0.0, 0.0, 10.0])]
    margin = min((max(ndc(c)[1], abs(ndc(c)[0])) for c in allp if c[0] > 2), default=9.0)
    return (max(ys) - min(ys)) if ys else 0.0, margin, min(float(c[0]) for c in pts)


def depth_for(eye, h, lean, R, tilt=0.0, facing=0.0):
    """Depth at which our head shows the read-out height h."""
    best = None
    for depth in np.linspace(14.0, 80.0, 133):
        K = axe_frame(R, eye, depth, lean, tilt, facing, MATCH_Z)
        hh = head_box(K)[0]
        err = abs(hh - h)
        if best is None or err < best[0]:
            best = (err, depth)
    return best[1]


def key_hand(K_axe, s, beta):
    """The fist on the handle at offset s, turned beta deg about the handle against the hatchet (the swing-in holds the
    upper handle turned in the hand; from the catch on beta = 0, the accepted grip)."""
    Kh = hand_on_axe(K_axe, s)
    if abs(beta) < 1e-6:
        return Kh
    return T(Kh.p, qmul(Kh.q, qaxis([0.0, 0.0, 1.0], math.radians(-beta))), (1, 1, 1))


def key_cost(z, key, R, prev=None, verbose=False):
    depth, lean, tilt, facing, dx, dy, beta = z
    if not key.get('turned'):
        beta = 0.0
    eye = (key['eye'][0] + dx, key['eye'][1] + dy)
    K = axe_frame(R, eye, depth, lean, tilt, facing, MATCH_Z)
    Kh = key_hand(K, key['s'], beta)
    a, _ = arm_diag(R, Kh)
    hh, margin, near = head_box(K)
    c = 60.0 * (dx * dx + dy * dy)
    c += ((lean - key['lean']) / 10.0) ** 2
    c += 6.0 * ((hh - key['h']) / key['h']) ** 2
    c += key.get('wface', 0.6) * ((facing - key['face']) / 45.0) ** 2
    c += 0.15 * ((tilt - key.get('tilt', 0.0)) / 60.0) ** 2 * key.get('wtilt', 1.0)
    c += strain(a)
    if 'twist' in key:                                       # the reference forearm roll (palm down in the swing-in)
        c += ((a['twist'] - key['twist']) / 25.0) ** 2
    if key.get('fist') is not None and not key.get('hide'):
        e = np.subtract(a['grip'], key['fist'])
        c += 8.0 * float(np.dot(e, e)) if np.all(np.isfinite(e)) else 5.0
    if key.get('hide'):
        c += 40.0 * max(0.0, 1.06 - margin) ** 2 + 40.0 * max(0.0, 1.06 - a['arm_margin']) ** 2
        g = a['grip']
        c += 40.0 * max(0.0, 1.1 - max(abs(g[0]), g[1])) ** 2 if np.all(np.isfinite(g)) else 0.0
    c += 0.5 * max(0.0, 9.0 - near) ** 2                      # never through the lens
    if key.get('arm_hide'):                                  # held out from below: only the fist end of the forearm shows
        c += 30.0 * max(0.0, 1.05 - a['forearm_margin']) ** 2
    if key.get('elbow_below'):                               # the forearm rises from under the bottom edge
        ey = a['elbow'][1]
        c += 20.0 * max(0.0, 1.2 - ey) ** 2 if np.isfinite(ey) else 0.0
        if a['elbow_cam'][0] < 6.0:                          # ... in front of the shoulder, not folded back past it
            c += 0.2 * (6.0 - a['elbow_cam'][0]) ** 2
        # ... and points down the screen from the fist (not out to the right edge): on-screen angle from vertical
        g, e = np.asarray(a['grip'], float), np.asarray(a['elbow'], float)
        if np.all(np.isfinite(g)) and np.all(np.isfinite(e)) and a['elbow_cam'][0] > 2.0:
            ang = math.degrees(math.atan2((e[0] - g[0]) * ASPECT_SCREEN, e[1] - g[1]))
            c += key.get('wforearm', 2.0) * (max(0.0, abs(ang) - key.get('forearm_deg', 30.0)) / 20.0) ** 2
    if key.get('elbow_off'):                                 # the forearm comes in from the right edge, elbow outside
        ex, ey = a['elbow']
        c += 20.0 * max(0.0, 1.15 - max(abs(ex), ey)) ** 2 if np.all(np.isfinite(a['elbow'])) else 0.0
    c += 100.0 * max(0.0, a['reach'] - key.get('reach', 0.92)) ** 2
    if prev is not None:                                     # continuity of the solved tilt / facing / hand turn
        c += 0.05 * (((tilt - prev[2]) / 30.0) ** 2 + ((facing - prev[3]) / 30.0) ** 2)
        if key.get('turned'):
            c += 0.05 * ((beta - prev[6]) / 30.0) ** 2
    if verbose:
        print('    eye %s depth %.1f lean %.1f tilt %.1f facing %.1f beta %.1f | head h %.2f (ref %.2f) | wrist %.1f ext %.1f '
              'uln %.1f twist %.1f reach %.2f grip %s elbow %s arm %.2f' % (
                  np.round(eye, 3), depth, lean, tilt, facing, beta, hh, key['h'], a['wrist'], a['ext'], a['uln'],
                  a['twist'], a['reach'], np.round(a['grip'], 2), np.round(a['elbow'], 2), a['arm_margin']))
    return c


def solve_key(key, R, prev=None):
    best = None
    tilts = (key['tilt'],) if 'tilt' in key else (-50.0, -25.0, 0.0, 25.0)
    for tilt in tilts:
        d0 = depth_for(key['eye'], key['h'], key['lean'], R, tilt, key['face'])
        facings = (key['face'],) if key.get('turned') else (key['face'], key['face'] + 40.0, key['face'] + 80.0)
        betas = (-120.0, -60.0, 0.0, 60.0, 120.0, 180.0) if key.get('turned') else (0.0,)
        for facing in facings:
            for beta in betas:
                z0 = np.array([d0, key['lean'], tilt, facing, 0.0, 0.0, beta])
                r = minimize(key_cost, z0, args=(key, R, prev), method='Nelder-Mead',
                             options=dict(maxiter=2500, xatol=1e-2, fatol=1e-4))
                if best is None or r.fun < best.fun:
                    best = r
    z = best.x.copy()
    if not key.get('turned'):
        z[6] = 0.0
    return z, best.fun


def air_hand(z, hand_ndc, q0):
    depth, rx, ry, rz = z
    q = from_rot(Rotation.from_rotvec([rx, ry, rz]) * to_rot(q0))
    return T(cam_to_mesh(ndc_cam(hand_ndc, depth)), q, (1, 1, 1))


def hand_axes(R, K):
    """Finger and palm directions (camera space) of the fist for grip frame K (hand: -X fingers, +Y palm)."""
    q = (R.hand_rel * K).q
    from kmath import qrot
    return mesh_to_cam(qrot(q, [-1.0, 0.0, 0.0])), mesh_to_cam(qrot(q, [0.0, 1.0, 0.0]))


def air_cost(z, R, hand_ndc, depth0, q0, prev, fing=None, palm=None):
    K = air_hand(z, hand_ndc, q0)
    a, _ = arm_diag(R, K)
    c = strain(a) + 0.4 * float(np.dot(z[1:], z[1:])) / 0.36 + ((z[0] - depth0) / 12.0) ** 2
    if fing is not None or palm is not None:
        f, p = hand_axes(R, K)
        if fing is not None:
            c += 2.0 * (1.0 - float(np.dot(f, unit(fing))))
        if palm is not None:
            c += 1.2 * (1.0 - float(np.dot(p, unit(palm))))
    ex, ey = a['elbow']
    e_cam = a['elbow_cam']
    if e_cam[0] < 8.0:                                  # the elbow stays in front of the shoulder plane
        c += 0.2 * (8.0 - e_cam[0]) ** 2
    if np.all(np.isfinite(a['elbow'])) and e_cam[0] > 8.0:
        c += 10.0 * max(0.0, 1.1 - max(abs(ex), ey)) ** 2
    if prev is not None:                                # one 1/30 s step: keep the turn moderate
        c += 1.5 * (angle_deg(prev.q, K.q) / 45.0) ** 2
    return c


def solve_air_hand(R, hand_ndc, depth0, q0, prev=None, fing=None, palm=None):
    """The open hand in the air at a read-out screen position: depth and a turn of the carried orientation chosen for a
    natural wrist, an elbow out of the frame and the reference's finger / palm directions."""
    best = None
    starts = [np.array([d, 0.0, 0.0, 0.0]) for d in (depth0, depth0 + 8.0, depth0 + 16.0)]
    if fing is not None:
        starts += [np.array([depth0 + 4.0, *v]) for v in ([0.8, 0, 0], [-0.8, 0, 0], [0, 0.8, 0], [0, -0.8, 0],
                                                           [0, 0, 0.8], [0, 0, -0.8])]
    for z0 in starts:
        r = minimize(air_cost, z0, args=(R, hand_ndc, depth0, q0, prev, fing, palm), method='Nelder-Mead',
                     options=dict(maxiter=3000, xatol=1e-3, fatol=1e-5))
        if best is None or r.fun < best.fun:
            best = r
    K = air_hand(best.x, hand_ndc, q0)
    a, _ = arm_diag(R, K)
    f, p = hand_axes(R, K)
    print('  air hand %s depth %.1f turn %.0f deg | fingers %s palm %s | wrist %.1f ext %.1f uln %.1f twist %.1f reach %.2f '
          'elbow %s' % (hand_ndc, best.x[0], math.degrees(np.linalg.norm(best.x[1:])), np.round(f, 2), np.round(p, 2),
                        a['wrist'], a['ext'], a['uln'], a['twist'], a['reach'], np.round(a['elbow'], 2)), flush=True)
    return K


def solve_keys(R, cache=WORK / 'v2_keys.json', refit=False):
    if cache.exists() and not refit:
        data = json.loads(cache.read_text('utf-8'))
        if data.get('ref') == REF:
            return {int(k): np.array(v) for k, v in data['z'].items()}
    out, prev = {}, None
    for key in REF:
        if key['s'] is None:
            continue
        z, c = solve_key(key, R, prev)
        print('key %d t=%.3f cost %.3f' % (key['f'], kt(key), c), flush=True)
        key_cost(z, key, R, prev, verbose=True)
        out[key['f']] = z
        prev = z
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(dict(ref=REF, z={k: list(map(float, v)) for k, v in out.items()}), indent=1), encoding='utf-8')
    return out

# ---------------------------------------------------------------- curves
from scipy.interpolate import CubicSpline  # noqa: E402
from scipy.spatial.transform import Rotation, RotationSpline  # noqa: E402


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (x * 6 - 15) + 10)


def to_rot(q):
    return Rotation.from_quat([q[1], q[2], q[3], q[0]])


def from_rot(r):
    x, y, z, w = r.as_quat()
    return np.array([w, x, y, z])


class Track:
    """Rigid frame track: cubic spline on a point (camera cm) and a rotation spline on the frame (mesh space).  The point
    is the frame's local `anchor` (so the hatchet's matched head point follows the read-out exactly)."""

    def __init__(self, times, frames, anchor=(0.0, 0.0, 0.0), start='clamped'):
        self.anchor = np.asarray(anchor, float)
        self.t0, self.t1 = times[0], times[-1]
        pts = np.array([mesh_to_cam(K.point(self.anchor)) for K in frames])
        # 'natural' start: the clip opens on a motion already under way (no acceleration from rest in the first frame)
        bc = ((2, np.zeros(3)), (1, np.zeros(3))) if start == 'natural' else 'clamped'
        self.pos = CubicSpline(times, pts, bc_type=bc)
        qs = [frames[0].q]
        for K in frames[1:]:
            qs.append(K.q if np.dot(K.q, qs[-1]) >= 0 else -K.q)
        self.rot = RotationSpline(times, Rotation.from_quat([[q[1], q[2], q[3], q[0]] for q in qs]))

    def __call__(self, t):
        t = min(max(t, self.t0), self.t1)
        q = from_rot(self.rot([t])[0])
        p = cam_to_mesh(self.pos(t))
        return T(p - T((0, 0, 0), q).vector(self.anchor), q, (1, 1, 1))


def blend_t(a, b, w):
    qb = b.q if np.dot(a.q, b.q) >= 0 else -b.q
    return T(a.p + (b.p - a.p) * w, qslerp(a.q, qb, w), (1, 1, 1))


def finger_open(t, finger='middle'):
    start, seconds = FINGER_CLOSE[finger]
    start += TC

    def opening(x):
        for (t0, a0), (t1, a1) in zip(FINGER_KEYS, FINGER_KEYS[1:]):
            if x <= t1:
                return a0 + (a1 - a0) * smooth((x - t0) / (t1 - t0))
        return FINGER_KEYS[-1][1]
    if t < start:
        return opening(t)
    return opening(start) * (1.0 - smooth((t - start) / seconds))


def finger_of(bone):
    head = bone.split('_')[0]
    return head if head in FINGER_CLOSE else 'middle'


def lock_free(dev):
    x = min(max((dev - LOCK_HOLD) / (LOCK_FREE - LOCK_HOLD), 0.0), 1.0)
    return x * x * (3 - 2 * x)


def lock_compensation(dev):
    """s >= 1 with s * lock_free(s * dev) = 1: the runtime lock then shows the intended offset (author_kukri_equip)."""
    if dev >= LOCK_FREE or dev <= 1e-6:
        return 1.0
    lo, hi = LOCK_HOLD, LOCK_FREE
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if mid * lock_free(mid) < dev else (lo, mid)
    return 0.5 * (lo + hi) / dev


def angle_deg(q0, q1):
    d = qmul(q1, qconj(q0))
    return math.degrees(2.0 * math.atan2(float(np.linalg.norm(d[1:])), abs(float(d[0]))))


def deviation(K_axe, K_hand):
    return float(np.linalg.norm(K_axe.p - K_hand.p)) + angle_deg(K_hand.q, K_axe.q) * LOCK_DEG_CM


def runtime_shown(K_axe, K_hand):
    free = lock_free(deviation(K_axe, K_hand))
    return T(K_hand.p + (K_axe.p - K_hand.p) * free, qslerp(K_hand.q, K_axe.q, free), (1, 1, 1))

# ---------------------------------------------------------------- clip
POLE = (rt(1181) + 0.033, T_STANCE)  # elbow: natural forearm line -> the stance elbow
HAND_BLEND = 0.025                   # s each side of the release / catch: the held and the air hand tracks cross-fade


class HatchetEquipClip:
    def __init__(self, R=None, refit=False):
        self.R = R or KukriRig()
        R = self.R
        F = Fitter(R)
        stance = json.loads((KUKRI / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x']
        W, phi, psi, du, de, C = F.unpack(np.array(stance, float))
        self.K_stance, self.E_stance = R.arm_to_kukri(W, F.hint(W, phi, C), psi, de, du, C)
        self.clav = tuple(C)
        self.z = solve_keys(R, refit=refit)
        held = {k['f']: k for k in REF if k['s'] is not None}
        # hatchet frames per key: held keys as solved; in the air the read-out with tilt / facing carried from the release
        # to the catch
        zr, zc = self.z[1165], self.z[1171]
        self.axe_keys = []
        tk = {k['f']: kt(k) for k in REF}
        for k in REF:
            t = kt(k)
            if k['s'] is not None:
                z = self.z[k['f']]
                eye = (k['eye'][0] + z[4], k['eye'][1] + z[5])
                K = axe_frame(R, eye, z[0], z[1], z[2], z[3], MATCH_Z)
            else:
                u = (t - TR) / (TC - TR)
                tilt, facing = zr[2] + (zc[2] - zr[2]) * u, zr[3] + (zc[3] - zr[3]) * u
                depth = depth_for(k['eye'], k['h'], k['lean'], R, tilt, facing)
                K = axe_frame(R, k['eye'], depth, k['lean'], tilt, facing, MATCH_Z)
            self.axe_keys.append((t, K))
        self.axe_keys += [(T_STANCE, self.K_stance), (LENGTH, self.K_stance)]
        # t = 0: the first lift pose dropped straight down under the frame (fist and hatchet as they are, the forearm lifts
        # them without turning)
        z0 = self.z[1162]
        K1 = self.axe_keys[0][1]
        K0 = T(K1.p + cam_to_mesh(np.array(LIFT_DROP)), K1.q, (1, 1, 1))
        hh, margin, _ = head_box(K0)
        a0, _ = arm_diag(R, key_hand(K0, S_CHOKE, z0[6]))
        print('  lift start: hatchet margin %.2f, arm margin %.2f, fist %s, wrist %.1f, reach %.2f' % (
            margin, a0['arm_margin'], np.round(a0['grip'], 2), a0['wrist'], a0['reach']))
        self.axe_keys.insert(0, (0.0, K0))
        self.beta0 = float(z0[6])
        self.axe = Track([t for t, _ in self.axe_keys], [K for _, K in self.axe_keys], (0.0, 0.0, MATCH_Z), start='natural')
        # the hand on the upper handle until the release: turned beta about the handle (linear between the lift keys)
        self.beta_keys = [(0.0, self.beta0)] + [(kt(k), float(self.z[k['f']][6])) for k in REF if k.get('turned')]
        # the hand in the air: from the releasing fist out to the right and down to the lower handle; its track runs
        # through held poses on both sides so it joins the held motion smoothly at the release and the catch
        hk = []
        for f in (1163, 1164, 1165):
            hk.append((tk[f], self.held_hand(tk[f])))
        q_r, q_c = hk[-1][1].q, self.held_hand(TC).q
        d_r, d_c = float(mesh_to_cam(hk[-1][1].p)[0]), float(mesh_to_cam(self.held_hand(TC).p)[0])
        prev = hk[-1][1]                 # each air pose turns on from the one before (the releasing fist first)
        for k in REF:
            if k.get('hand') is None:
                continue
            t = kt(k)
            u = smooth((t - TR) / (TC - TR))
            q_c2 = q_c if np.dot(q_c, q_r) >= 0 else -q_c
            K = solve_air_hand(R, k['hand'], d_r + (d_c - d_r) * u, qslerp(q_r, q_c2, u), prev, k.get('fing'), k.get('palm'))
            hk.append((t, K))
            prev = K
        for f in (1171, 1172, 1173):
            hk.append((tk[f], self.held_hand(tk[f])))
        self.hand_air = Track([t for t, _ in hk], [K for _, K in hk])
        self.fingers = [n for n in R.rig.descendants('hand_r') if n != 'hand_r' and not n.startswith('ik_')]
        self.order = [n for n in R.rig.names if n in self.fingers]

    def beta(self, t):
        ks = self.beta_keys
        if t <= ks[0][0]:
            return ks[0][1]
        for (t0, b0), (t1, b1) in zip(ks, ks[1:]):
            if t <= t1:
                return b0 + (b1 - b0) * (t - t0) / (t1 - t0)
        return ks[-1][1]

    def held_hand(self, t):
        """The fist that holds the hatchet at time t (upper handle, turned, until the release; the grip from the catch)."""
        K = self.axe(t)
        return key_hand(K, S_CHOKE, self.beta(t)) if t <= TR else key_hand(K, 0.0, 0.0)

    def hand(self, t):
        """The fist: held on the upper handle, in the air, then gripping.  Both hand tracks pass through the same pose
        at the release and the catch; HAND_BLEND hands over between them so the fist's velocity has no kink there."""
        B = HAND_BLEND
        choke = key_hand(self.axe(t), S_CHOKE, self.beta(t))
        grip = key_hand(self.axe(t), 0.0, 0.0)
        if t <= TR - B:
            return choke, 'held'
        if t < TR + B:
            return blend_t(choke, self.hand_air(t), smooth((t - (TR - B)) / (2 * B))), ('held' if t <= TR else 'air')
        if t <= TC - B:
            return self.hand_air(t), 'air'
        if t < TC + B:
            return blend_t(self.hand_air(t), grip, smooth((t - (TC - B)) / (2 * B))), ('air' if t < TC else 'grip')
        return grip, 'grip'

    def pole(self, t):
        return smooth((t - POLE[0]) / (POLE[1] - POLE[0]))

    def axe_authored(self, t, K_hand, mode):
        """WPN_root as authored: the hatchet's own frame, with offsets below the runtime lock's release band pre-scaled
        so the shown hatchet follows the track (the lock compares WPN_root with the accepted grip on the fist)."""
        K = self.axe(t)
        if mode == 'grip':
            return K_hand
        rel = K.relative_to(K_hand)
        dev = float(np.linalg.norm(rel.p)) + angle_deg(np.array([1.0, 0, 0, 0]), rel.q) * LOCK_DEG_CM
        s = lock_compensation(dev)
        if s == 1.0:
            return K
        rv = to_rot(rel.q).as_rotvec() * s
        return T(rel.p * s, from_rot(Rotation.from_rotvec(rv)), (1, 1, 1)) * K_hand

    def sample(self, t):
        R = self.R
        K_hand, mode = self.hand(t)
        world, diag = R.pose(K_hand, left_target_cam=IDLE_L, clav_r=self.clav, pole_r=self.E_stance,
                             pole_r_weight=self.pole(t))
        rig = R.rig
        for n in self.order:
            an = finger_open(t, finger_of(n))
            if an <= 1e-4:
                continue
            par = rig.parents[rig.index[n]]
            lb, lr = R.base_local[n], R.ref_local[n]
            qr = lr.q if np.dot(lb.q, lr.q) >= 0 else -lr.q
            world[n] = T(lb.p, qslerp(lb.q, qr, an), lb.s) * world[par]
        K = self.axe_authored(t, K_hand, mode)
        b = R.base
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for n in R.wpn_desc:
            if n == 'WPN_root':
                continue
            par = rig.parents[rig.index[n]]
            world[n] = R.base_local[n] * world[par]
        world['Blade_Base'] = T(K.point(BLADE_BASE), K.q, b['Blade_Base'].s)
        world['Blade_Tip'] = T(K.point(TIP), K.q, b['Blade_Tip'].s)
        Kf = R.hand_rel.inverse() * world['hand_r']
        Kf = T(Kf.p, Kf.q, (1, 1, 1))
        shown = runtime_shown(K, Kf)
        r = diag['right']
        head = [mesh_to_cam(shown.point(v)) for v in HEAD_PTS]
        d = dict(t=round(t, 4), mode=mode, open=round(finger_open(t, 'index'), 3), reach=round(r['reach'], 3),
                 twist=round(r['twist_deg'], 1), ext=round(r['ext'], 1), uln=round(r['uln'], 1), wrist=round(r['wrist_deg'], 1),
                 grip=[round(float(v), 3) for v in ndc(mesh_to_cam(Kf.p))], elbow=[round(float(v), 2) for v in diag['elbow_ndc']],
                 eye=[round(float(v), 3) for v in ndc(mesh_to_cam(shown.point([0.0, 0.0, MATCH_Z])))],
                 head_depth=round(min(float(c[0]) for c in head), 1), hand_err=round(float(np.linalg.norm(Kf.p - K_hand.p)), 3),
                 dev=round(deviation(self.axe(t), Kf), 2),
                 eye_cam=[float(v) for v in mesh_to_cam(shown.point([0.0, 0.0, MATCH_Z]))],
                 fist_cam=[float(v) for v in mesh_to_cam(Kf.p)], axe_q=[float(v) for v in shown.q])
        return world, shown, d


def smoothness(diags, top=6):
    """Frame-to-frame read-out of what the eye sees moving (120 Hz): the head point and the fist (cm/s and the change
    of velocity per frame), the hatchet's turn rate and the forearm twist rate.  Spikes in the velocity change are the
    hitches."""
    rows = []
    for a, b, c in zip(diags, diags[1:], diags[2:]):
        dt = b['t'] - a['t']
        ve0, ve1 = (np.subtract(b['eye_cam'], a['eye_cam'])) / dt, (np.subtract(c['eye_cam'], b['eye_cam'])) / dt
        vf0, vf1 = (np.subtract(b['fist_cam'], a['fist_cam'])) / dt, (np.subtract(c['fist_cam'], b['fist_cam'])) / dt
        rows.append(dict(t=b['t'], eye_v=float(np.linalg.norm(ve1)), eye_dv=float(np.linalg.norm(ve1 - ve0)),
                         fist_v=float(np.linalg.norm(vf1)), fist_dv=float(np.linalg.norm(vf1 - vf0)),
                         spin=angle_deg(np.array(b['axe_q']), np.array(c['axe_q'])) / dt,
                         twist_rate=abs(c['twist'] - b['twist']) / dt))
    for key, unit_ in (('eye_dv', 'cm/s per frame'), ('fist_dv', 'cm/s per frame'), ('spin', 'deg/s'), ('twist_rate', 'deg/s')):
        worst = sorted(rows, key=lambda r: -r[key])[:top]
        print('  %-10s %s' % (key, ', '.join('%.3f:%.0f' % (r['t'], r[key]) for r in sorted(worst, key=lambda r: r['t']))),
              '(%s)' % unit_)
    return rows

# ---------------------------------------------------------------- camera (degrees; pitch + up, yaw + right, roll + cw)
CAMERA_FADE = (rt(1181), LENGTH)     # the reference settles into its own hold; ours eases back to the stance view
FOV_SHARE = 0.5                      # the registration's scale is noisy (+-0.5 deg frame to frame): half, smoothed


def camera_samples():
    """Reference camera (Reference/camera_ref.py) on our clock: 3-tap smoothed, zero at the start, faded out after the
    reference reaches its own hold."""
    data = json.loads((REF_DIR / 'camera.json').read_text('utf-8'))
    rows = {r['frame']: r for r in data['frames'] if r.get('ok')}
    ts, vals = [], []
    for f in range(REF_T0, REF_T0 + int(round(LENGTH * 30)) + 2):
        win = [rows[g] for g in (f - 1, f, f + 1) if g in rows]
        ts.append(rt(f))
        vals.append([float(np.mean([w[k] for w in win])) for k in ('pitch', 'yaw', 'roll', 'fov')])
    vals = np.array(vals)
    vals -= vals[0]
    vals[:, 3] *= FOV_SHARE
    return np.array(ts), vals


_CAM = None


def camera(t):
    global _CAM
    if _CAM is None:
        _CAM = camera_samples()
    ts, vals = _CAM
    v = np.array([np.interp(t, ts, vals[:, k]) for k in range(4)])
    v *= 1.0 - smooth((t - CAMERA_FADE[0]) / (CAMERA_FADE[1] - CAMERA_FADE[0]))
    if t <= 0.0 or t >= LENGTH:
        v *= 0.0
    return tuple(float(x) for x in v)


# ---------------------------------------------------------------- outputs
def author(preview_every=0, refit=False):
    clip = HatchetEquipClip(refit=refit)
    R = clip.R
    R.reset_twist_memory()
    n = int(round(LENGTH * FPS))
    frames, diags, previews, prev_q = [], [], {}, None
    for i in range(n + 1):
        t = i / FPS
        world, shown, d = clip.sample(t)
        keys = R.local_keys(world, prev_q)
        prev_q = {b: v[1] for b, v in keys.items()}
        frames.append({b: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for b, v in keys.items()})
        diags.append(d)
        if preview_every and i % preview_every == 0:
            previews['%s_%04d' % (CLIP, i)] = (world, shown, camera(t))
    OUT.mkdir(parents=True, exist_ok=True)
    data = dict(name=CLIP, fps=FPS, length=n / FPS, loop=False, contact=None, release=round(TR, 5), catch=round(TC, 5),
                bones=R.rig.names, frames=frames, diagnostics=diags)
    (OUT / (CLIP + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    vis = [x for x in diags if x['mode'] != 'air']
    summary = dict(version='V2 reference toss', length=round(n / FPS, 4), frames=n + 1, release=round(TR, 4),
                   catch=round(TC, 4), stance=T_STANCE, max_reach=max(x['reach'] for x in diags),
                   twist=[min(x['twist'] for x in diags), max(x['twist'] for x in diags)],
                   ext=[min(x['ext'] for x in diags), max(x['ext'] for x in diags)],
                   uln=[min(x['uln'] for x in diags), max(x['uln'] for x in diags)],
                   wrist_max_held=max(x['wrist'] for x in vis), wrist_max=max(x['wrist'] for x in diags),
                   head_depth_min=min(x['head_depth'] for x in diags), hand_err_max=max(x['hand_err'] for x in diags))
    print(CLIP, json.dumps(summary), flush=True)
    meta_path = P / 'clips.json'
    meta = json.loads(meta_path.read_text('utf-8')) if meta_path.exists() else {}
    meta.setdefault('clips', {})[CLIP] = dict(summary, source='author_hatchet_equip.py')
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return clip, diags, previews


def table(diags, every=4):
    print('   t     mode  open reach twist   ext   uln wrist  grip            eye             elbow        depth  dev')
    for d in diags[::every]:
        print('  %.3f %-5s %.2f  %.2f %6.1f %5.1f %5.1f %5.1f  %-15s %-15s %-12s %5.1f %5.1f' % (
            d['t'], d['mode'], d['open'], d['reach'], d['twist'], d['ext'], d['uln'], d['wrist'], d['grip'], d['eye'],
            d['elbow'], d['head_depth'], d['dev']))

def write_header():
    n = int(round(LENGTH * 60)) + 1
    rows = [camera(i / 60.0) for i in range(n)]
    arr = lambda k: ','.join('%.2ff' % (r[k] + 0.0) for r in rows)
    seconds = int(round(LENGTH * FPS)) / FPS
    text = f'''#pragma once

#include "CoreMinimal.h"

/**
 * 碳钢战斧拔斧 V2.1（参考 BV1pqkyYyEDY 38.70-39.55 s「切刀动作 #2 抛」，2026-11-02）作者时钟。
 * 作者源：SourceAssets/HatchetEquip20261101/author_hatchet_equip.py（clip "HatchetEquip"，{seconds:.3f} s；本文件由该脚本 --header 生成）。
 *  0-{LIFT_SECONDS:.2f} 拳握斧柄上段，把斧子从画面下方提起、斧头先露出，到位时手腕把斧头向后扣；随即翻起，{TR:.3f} s 松手；
 *  斧子在空中不旋转地上浮、摆正并向右靠近，张开的右手先让到右侧再下探斧柄下段，{TC:.3f} s 握住；
 *  随后下拉并前送到画面中央，斧头先右倾再左倾、刃口转向前方，{T_STANCE:.2f} s 收进与弯刀共用的持斧架势。
 * 斧子离手和握在柄上段期间 WPN_root 播放作者轨迹，UKukriArmsMeshComponent 的握持锁随作者偏离量淡出（≤0.6 cm 锁死、≥2.5 cm 放开）。
 * 镜头为参考背景配准（Reference/camera_ref.py），换算到本作 75° 垂直视场，60 Hz：抛起时随斧抬头约 2.4°、右转约 2°，
 * 前送时下沉回摆，{CAMERA_FADE[0]:.2f} s 后淡出回正。
 */
namespace HatchetDrawRhythm
{{
    inline const TCHAR* Clip=TEXT("/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_Equip.A_TacticalHatchet_Equip");
    inline constexpr float Seconds={seconds:.4f}f;
    inline constexpr float Release={TR:.4f}f;
    inline constexpr float Catch={TC:.4f}f;

    /** 翻斧脱手的风声与接柄握声（作者秒，沿用弯刀拔刀的两条资产）；音量与音高未试听，按需调整。 */
    inline constexpr float TossAt=Release, TossVolume={TOSS_SOUND['volume']:.2f}f, TossPitch={TOSS_SOUND['pitch']:.2f}f;
    inline constexpr float CatchAt=Catch, CatchVolume={CATCH_SOUND['volume']:.2f}f, CatchPitch={CATCH_SOUND['pitch']:.2f}f;

    /** 整体镜头幅度（1 = 参考原幅）。 */
    inline constexpr float CameraScale=1.f;
    inline constexpr int32 DrawSamples={n};
    inline constexpr float DrawPitch[DrawSamples]={{{arr(0)}}};
    inline constexpr float DrawYaw[DrawSamples]={{{arr(1)}}};
    inline constexpr float DrawRoll[DrawSamples]={{{arr(2)}}};
    inline constexpr float DrawFov[DrawSamples]={{{arr(3)}}};

    inline float SampleDraw(const float (&Curve)[DrawSamples],float Time)
    {{
        const float X=FMath::Clamp(Time*60.f,0.f,float(DrawSamples-1));
        const int32 I=FMath::Min(int32(X),DrawSamples-2);
        return FMath::Lerp(Curve[I],Curve[I+1],X-I);
    }}

    /** Draw camera (degrees: pitch/yaw/roll + vertical FOV delta) at author time T; Yaw + right, Pitch + up, Roll + clockwise. */
    inline void Camera(float T,FRotator& Rotation,float& Fov)
    {{
        Rotation=FRotator(SampleDraw(DrawPitch,T),SampleDraw(DrawYaw,T),SampleDraw(DrawRoll,T))*CameraScale;
        Fov=SampleDraw(DrawFov,T)*CameraScale;
    }}
}}
'''
    HEADER.write_bytes(text.replace('-0.00f', '0.00f').encode('utf-8'))
    print('header ->', HEADER)


BLENDER = r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"


def write_poses(previews):
    poses = {'poses': {name: {'bones': {b: t.pack() for b, t in world.items()}, 'kukri': K.pack(), 'camera': list(cam)}
                       for name, (world, K, cam) in previews.items()}}
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'previews.json').write_text(json.dumps(poses), encoding='utf-8')


def grid(im, color=(90, 90, 90)):
    import cv2
    h, w = im.shape[:2]
    for k in range(1, 8):
        c = (0, 220, 220) if k == 4 else color
        cv2.line(im, (k * w // 8, 0), (k * w // 8, h), c, 1)
        cv2.line(im, (0, k * h // 8), (w, k * h // 8), c, 1)
    return im


def render_previews(previews, width=960, compare=True):
    """Render the poses (hatchet as the game shows it, camera curve applied); videos, sheets and the reference
    comparison (reference above, ours below, every 1/30 s)."""
    import cv2
    frames_dir = WORK / 'frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob('*.png'):
        old.unlink()
    write_poses(previews)
    cmd = [BLENDER, '-b', '--factory-startup', '--python', str(P / 'render_hatchet_preview.py'), '--',
           str(WORK / 'previews.json'), str(frames_dir), str(width)]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0 or 'Traceback' in res.stdout:
        print(res.stdout[-3000:], res.stderr[-3000:])
        raise RuntimeError('preview render failed')
    names = sorted(previews)
    imgs = []
    for name in names:
        im = cv2.imread(str(frames_dir / (name + '.png')))
        t = int(name.rsplit('_', 1)[1]) / FPS
        cv2.putText(im, 't=%.3f s' % t, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        imgs.append((t, im))
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    for old in PREVIEWS.glob('*'):
        old.unlink()
    h, w = imgs[0][1].shape[:2]
    step = max(1, FPS // 120)
    for path, fps, stride in ((PREVIEWS / 'hatchet_equip_realtime.mp4', 60, 2 * step),
                              (PREVIEWS / 'hatchet_equip_slow4x.mp4', 30, step)):
        raw = WORK / ('raw_' + path.name)
        vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        for _ in range(fps // 3):
            vw.write(imgs[0][1])
        for _, im in imgs[::stride]:
            vw.write(im)
        for _ in range(fps // 2):
            vw.write(imgs[-1][1])
        vw.release()
        try:
            import imageio_ffmpeg
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(raw), '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', '-crf', '18', str(path)], check=True)
            raw.unlink()
        except Exception as exc:
            print('H.264 transcode skipped (%s); mp4v kept' % exc)
            raw.replace(path)
    if not compare:
        return
    # reference above ours, one column per 1/30 s
    cells = []
    for k in range(0, int(round(LENGTH * 30)) + 1):
        f = REF_T0 + k
        ref = cv2.imread(str(REF_DIR / 'frames' / ('f%05d.png' % f)))
        ours = next((im for t, im in imgs if abs(t - rt(f)) < 1e-6), None)       # on our clock (the lift is longer)
        if ref is None or ours is None:
            continue
        ref = grid(cv2.resize(ref, (480, 270), interpolation=cv2.INTER_AREA))
        ours = grid(cv2.resize(ours, (480, 270), interpolation=cv2.INTER_AREA))
        cv2.putText(ref, 'ref %d (%.3f)' % (f, (f - REF_T0) / 30), (6, 262), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cells.append(np.vstack([ref, ours]))
    for s in range(0, len(cells), 8):
        chunk = cells[s:s + 8]
        while len(chunk) % 4:
            chunk.append(np.zeros_like(chunk[0]))
        cv2.imwrite(str(PREVIEWS / ('compare_%d.jpg' % (s // 8))),
                    np.vstack([np.hstack(chunk[r:r + 4]) for r in range(0, len(chunk), 4)]), [cv2.IMWRITE_JPEG_QUALITY, 82])
    print('previews ->', PREVIEWS)


if __name__ == '__main__':
    every = 1 if ('--preview' in sys.argv or '--poses' in sys.argv) else 0
    clip, diags, previews = author(preview_every=every, refit='--refit' in sys.argv)
    table(diags, every=4 if '--all' not in sys.argv else 1)
    smoothness(diags)
    if '--header' in sys.argv:
        write_header()
    if '--poses' in sys.argv:
        write_poses(previews)
    elif previews:
        render_previews(previews)
