"""Tactical hatchet combo stage 3 "HatchetAttack3": an overhead chop (2026-11-02).

User 2026-11-02: the hatchet gets its own last hit of the three-hit combo -- a chop from above -- with the hit feel, impact
and screen shake of the current one.  The hatchet keeps the kukri moveset otherwise (melee_animation_family = kukri); this
clip replaces Attack3 (the kukri's low stab) for the hatchet only.

It is authored on the stab's own clock so every gameplay table of stage 2 stays valid unchanged: 38/30 s, the stage tempo
(KukriRhythm::StabTempo), the contact window 0.34-0.47, the impact moment 0.367, the click buffer 0.47, the server's
receipt timing (KukriAttackReceipt / ColdSteelKukriAuthority).  The stab's phases map onto a chop:
  0.00-0.30  slow visible raise (stab: the turn to the hip) -- the fist lifts the hatchet up the right edge and cocks it
             over the shoulder, head behind, edge up
  0.30-0.333 the hold at the top (stab: the freeze before the drive, tempo x0.5)
  0.333-0.367 the chop (stab: the drive, tempo x0.9): the head whips over the top and down through the crosshair, edge
             leading; 0.367 = the impact (KukriRhythm::Strikes[2].At)
  0.367-0.40 the bite: a short overshoot and rebound (stab: the overshoot)
  0.40-0.533 held in the target (stab: the hold on the crosshair)
  0.54-0.59  yanked out (stab: the pull-back)
  0.61-1.267 down out of the lower right, turned over below the frame and back up into the stance (stab: the same path)
Presentation that differs from the stab lives in HatchetChopRhythm.h (generated here): camera curve (pitch dips with the
chop instead of the stab's forward push), impact accents (nod down, press down), viewmodel kick (pushed back up), hit-stop
x2.2 / impact x1.35, and the rift ribbon swept by the edge.

Run:  python author_hatchet_chop.py [--preview] [--header]
"""
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

P = Path(__file__).resolve().parent
EQUIP = P.parent / 'HatchetEquip20261101'
KUKRI = P.parent / 'Kukri20261020'
sys.path.insert(0, str(KUKRI))
sys.path.insert(0, str(EQUIP))
from kukri_rig import KukriRig, ndc, TIP, BLADE_BASE  # noqa: E402
from kmath import T, mesh_to_cam, cam_to_mesh, qrot  # noqa: E402
from fit_reference import Fitter  # noqa: E402
from hatchet_pose import unit, arm_diag, strain  # noqa: E402
from author_hatchet_equip import Track, smoothness, angle_deg, smooth  # noqa: E402

FPS = 120
CLIP = 'HatchetAttack3'
LENGTH = 38.0 / 30.0
OUT = P / 'Clips'
WORK = P / 'Work'
PREVIEWS = P / 'Previews'
HEADER = P.parents[1] / 'Source' / 'FPSGAME' / 'Weapons' / 'Kukri' / 'HatchetChopRhythm.h'
IDLE_L = (16.0, -24.0, -64.0)
STAGE_AT = 0.367                     # KukriRhythm::Strikes[2].At
HEAD_PTS = [np.array(v) for v in ([4.0, 0.0, 30.9], [16.35, 0.0, 27.0], [16.0, 0.0, 19.0], [-4.5, 0.0, 30.0],
                                  [-4.5, 0.0, 22.0], [6.0, 0.0, 16.5])]
EDGE_LOW, EDGE_HIGH = np.array([16.0, 0.0, 19.0]), np.array([16.35, 0.0, 27.0])

# Keys (author s): fist = grip centre (camera cm: x away, y right, z up), d = handle direction towards the head, e = the
# edge direction wanted (both camera; the solver turns the edge about the handle and tips the handle a little for a
# natural wrist).  None = the stance (attack_keys key 0 = Idle frame 0).
KEYS = [
    (0.000, None),
    (0.080, dict(fist=(31.0, 22.0, -6.0), d=(-0.50, -0.25, 0.83), e=(0.80, 0.10, 0.50))),     # lifting up the right edge
    (0.160, dict(fist=(24.0, 26.0, 7.0), d=(-0.88, -0.18, 0.45), e=(0.45, 0.10, 0.88))),       # over the shoulder
    (0.250, dict(fist=(20.0, 27.5, 14.0), d=(-0.97, -0.10, 0.20), e=(0.20, 0.00, 0.98))),      # at the top
    # The blow starts from rest at the very top (hold, 0.30: the stab's freeze runs at x0.5 there) and accelerates over
    # the top so the head is readable on the way down; it still crosses the crosshair at the stage's impact moment.
    # twist: forearm roll targets (deg vs bind) -- the hammer-grip chop lands pronated (~-110 with the edge leading down,
    # like the accepted kukri sprint chop's -112); the top stays near -20, so the roll is spread over the swing.
    (0.300, dict(fist=(19.5, 28.0, 15.0), d=(-0.98, -0.08, 0.15), e=(0.15, 0.00, 0.99), hold=True)),  # cocked a touch more
    (0.335, dict(fist=(24.0, 24.0, 13.0), d=(-0.60, -0.12, 0.79), e=(0.79, 0.00, 0.60), twist=-45.0)),  # coming over
    # The blow comes down a little diagonally: from over the right shoulder to the crosshair, the hatchet ending pointed
    # up-left from the fist at the lower right.  A chop straight along the view shows only the back of the head; the
    # hammer grip cannot land it with the head below the fist (Work/probe_impact.py: that needs the forearm rolled 150-180
    # deg).  Probe pick: head 44 cm out on the crosshair, handle 40 deg up-left (its flat turned ~70 deg from the view
    # instead of edge-on), edge forward-down, wrist 4 deg, twist -97, elbow out past the right edge.
    # 2026-11-03 (user: "再劈深一些，最后位置再靠近摄像机镜头下方一下"): the impact and the held-in pose go deeper and sit
    # closer to the lens -- the head drops further below the crosshair (NDC y ~0.36 instead of 0.06) at ~42 cm depth
    # instead of 44 (Work/probe_deep.py), and the bite, rebound, hold and yank follow the same pose.
    (0.352, dict(fist=(27.0, 18.0, 2.0), d=(-0.05, -0.35, 0.94), e=(0.95, -0.10, 0.10), twist=-75.0)),   # over the top
    (0.367, dict(fist=(27.0, 12.5, -24.0), d=(0.58, -0.50, 0.64), e=(0.72, -0.04, -0.69), twist=-97.0)),  # impact
    (0.383, dict(fist=(28.0, 12.0, -26.2), d=(0.63, -0.48, 0.60), e=(0.70, -0.05, -0.71), twist=-99.0)),   # bites on
    (0.400, dict(fist=(27.6, 12.2, -25.4), d=(0.61, -0.49, 0.62), e=(0.71, -0.05, -0.70), twist=-98.0)),   # rebound
    (0.533, dict(fist=(27.6, 12.2, -25.8), d=(0.61, -0.49, 0.62), e=(0.71, -0.05, -0.70), twist=-98.0,
                 hold=True)),                                                                     # held in
    (0.575, dict(fist=(25.5, 14.5, -21.5), d=(0.52, -0.48, 0.71), e=(0.75, -0.05, -0.66), twist=-92.0)),   # yanked out
    (0.700, dict(fist=(28.0, 22.0, -50.0), d=(0.70, 0.05, 0.71), e=(0.70, 0.00, -0.70), twist=-50.0)),     # down out of the
                                                                                                      # lower right
    (0.850, dict(fist=(26.0, 20.0, -52.0), d=(0.10, -0.30, 0.95), e=(0.90, -0.10, 0.10))),     # turned over below the frame
    (1.000, dict(fist=(32.0, 17.0, -32.0), d=(-0.45, -0.60, 0.66), e=(0.80, -0.20, 0.55))),    # coming up
    (1.150, 'blend'),                                                                         # nearly in the stance
    (LENGTH, None),
]
POLE = (1.00, 1.20)                  # elbow: natural forearm line -> the stance elbow for the last rise

# ---------------------------------------------------------------- key poses
def frame_from(fist, d, e):
    """Grip frame (mesh T) at camera point fist, handle along d, edge e made perpendicular to d."""
    d = unit(d)
    e = np.asarray(e, float)
    e = unit(e - d * np.dot(e, d))
    return T(cam_to_mesh(np.asarray(fist, float)), _qzx(cam_to_mesh(d), cam_to_mesh(e)), (1, 1, 1))


def _qzx(z, x):
    from kmath import qfromzx
    return qfromzx(z, x)


def rotate(v, axis, deg):
    axis = unit(axis)
    a = math.radians(deg)
    v = np.asarray(v, float)
    return v * math.cos(a) + np.cross(axis, v) * math.sin(a) + axis * np.dot(axis, v) * (1 - math.cos(a))


def key_frame(z, key):
    """z = (edge turn about the handle, handle tip about camera y, about camera x) in degrees."""
    psi, ty, tx = z
    d = rotate(rotate(key['d'], (0.0, 1.0, 0.0), ty), (1.0, 0.0, 0.0), tx)
    e = rotate(key['e'], d, psi)
    return frame_from(key['fist'], d, e)


def key_cost(z, key, R, prev_twist=None):
    K = key_frame(z, key)
    a, _ = arm_diag(R, K)
    # strain() walls the twist at -70; a hammer-grip chop pronates past that (the accepted kukri sprint chop reaches
    # -112 / the sword's -145), so the chop keys carry their own forearm-roll target instead
    c = (a['wrist'] / 15.0) ** 2 + 200.0 * max(0.0, a['reach'] - 0.92) ** 2
    c += (z[0] / key.get('psi_soft', 35.0)) ** 2 + (z[1] / 12.0) ** 2 + (z[2] / 12.0) ** 2
    if 'twist' in key:
        c += ((a['twist'] - key['twist']) / 20.0) ** 2
    elif prev_twist is not None:
        c += ((a['twist'] - prev_twist) / 45.0) ** 2
    c += max(0.0, a['twist'] - 60.0) ** 2 / 400.0 + max(0.0, -125.0 - a['twist']) ** 2 / 400.0
    return c


def solve_keys(R):
    out, prev = {}, None
    for t, key in KEYS:
        if not isinstance(key, dict):
            continue
        best = None
        for psi in (-60.0, -30.0, 0.0, 30.0, 60.0):
            r = minimize(key_cost, np.array([psi, 0.0, 0.0]), args=(key, R, prev), method='Nelder-Mead',
                         options=dict(maxiter=2000, xatol=1e-2, fatol=1e-5))
            if best is None or r.fun < best.fun:
                best = r
        K = key_frame(best.x, key)
        a, _ = arm_diag(R, K)
        prev = a['twist']
        out[t] = K
        head = [ndc(mesh_to_cam(K.point(v))) for v in HEAD_PTS]
        print('  key %.3f cost %.3f psi %.0f tip %.0f/%.0f | wrist %.1f ext %.1f uln %.1f twist %.1f reach %.2f fist %s elbow %s '
              'head %s' % (t, best.fun, best.x[0], best.x[1], best.x[2], a['wrist'], a['ext'], a['uln'], a['twist'],
                           a['reach'], np.round(a['grip'], 2), np.round(a['elbow'], 2),
                           np.round(np.nanmean(np.array(head), axis=0), 2)), flush=True)
    return out


# ---------------------------------------------------------------- holds-aware frame track
def _log(q):
    """Rotation vector of unit quaternion q (w, x, y, z)."""
    q = np.asarray(q, float)
    q = q if q[0] >= 0 else -q
    s = float(np.linalg.norm(q[1:]))
    return np.zeros(3) if s < 1e-12 else q[1:] / s * 2.0 * math.atan2(s, q[0])


def _exp(r):
    a = float(np.linalg.norm(r))
    if a < 1e-12:
        return np.array([1.0, 0.0, 0.0, 0.0])
    return np.array([math.cos(a / 2), *(np.asarray(r) / a * math.sin(a / 2))])


class HoldTrack:
    """Piecewise cubic Hermite through key frames (camera point + rotation): Catmull-Rom tangents, zero velocity at
    hold keys and the ends -- so a held pose really stops and the move out of it starts from rest (the chop's freeze at
    the top, the hatchet held in the target).  Rotation per segment: q_i * exp(h(u)) with h a Hermite on the rotation
    vector from q_i (exact at both keys)."""

    def __init__(self, times, frames, holds):
        from kmath import qmul, qconj
        self.qmul, self.qconj = qmul, qconj
        self.t = np.asarray(times, float)
        self.p = np.array([mesh_to_cam(K.p) for K in frames])
        qs = [frames[0].q]
        for K in frames[1:]:
            qs.append(K.q if np.dot(K.q, qs[-1]) >= 0 else -K.q)
        self.q = qs
        n = len(times)
        self.d = [_log(qmul(qconj(qs[i]), qs[i + 1])) for i in range(n - 1)]       # segment rotations (local)
        self.vp, self.w = [], []
        for i in range(n):
            if i == 0 or i == n - 1 or holds[i]:
                self.vp.append(np.zeros(3)); self.w.append(np.zeros(3)); continue
            h0, h1 = self.t[i] - self.t[i - 1], self.t[i + 1] - self.t[i]
            self.vp.append((self.p[i + 1] - self.p[i - 1]) / (h0 + h1))
            self.w.append((self.d[i - 1] / h0 * h1 + self.d[i] / h1 * h0) / (h0 + h1))   # local angular velocity

    def __call__(self, t):
        t = min(max(t, self.t[0]), self.t[-1])
        i = min(int(np.searchsorted(self.t, t, side='right')) - 1, len(self.t) - 2)
        h = self.t[i + 1] - self.t[i]
        u = (t - self.t[i]) / h
        h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
        p = h00 * self.p[i] + h10 * h * self.vp[i] + h01 * self.p[i + 1] + h11 * h * self.vp[i + 1]
        # angular velocity at the far key re-expressed in this segment's frame (approximately: rotated back by d)
        w1 = qrot(_exp(self.d[i]), self.w[i + 1])
        r = h10 * h * self.w[i] + h01 * self.d[i] + h11 * h * w1
        q = self.qmul(self.q[i], _exp(r))
        return T(cam_to_mesh(p), q / np.linalg.norm(q), (1, 1, 1))


# ---------------------------------------------------------------- clip
class ChopClip:
    def __init__(self, R=None):
        self.R = R or KukriRig()
        R = self.R
        F = Fitter(R)
        stance = json.loads((KUKRI / 'attack_keys.json').read_text('utf-8'))['keys'][0]['x']
        W, phi, psi, du, de, C = F.unpack(np.array(stance, float))
        self.K_stance, self.E_stance = R.arm_to_kukri(W, F.hint(W, phi, C), psi, de, du, C)
        self.clav = tuple(C)
        solved = solve_keys(R)
        times, frames, holds = [], [], []
        for t, key in KEYS:
            if key is None:
                K = self.K_stance
            elif key == 'blend':
                # nearly in the stance: the stance raised a touch less high, so the rise eases in
                K = T(self.K_stance.p + cam_to_mesh(np.array([0.0, 0.0, -2.5])), self.K_stance.q, (1, 1, 1))
            else:
                K = solved[t]
            times.append(t)
            frames.append(K)
            holds.append(isinstance(key, dict) and key.get('hold', False))
        self.key_times, self.key_frames, self.key_holds = times, frames, holds      # reused by the dual chop
        self.track = HoldTrack(times, frames, holds)

    def pole(self, t):
        return smooth((t - POLE[0]) / (POLE[1] - POLE[0]))

    def sample(self, t):
        R = self.R
        K = self.track(t)
        world, diag = R.pose(K, left_target_cam=IDLE_L, clav_r=self.clav, pole_r=self.E_stance, pole_r_weight=self.pole(t))
        b = R.base
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for n in R.wpn_desc:
            if n == 'WPN_root':
                continue
            par = R.rig.parents[R.rig.index[n]]
            world[n] = R.base_local[n] * world[par]
        world['Blade_Base'] = T(K.point(BLADE_BASE), K.q, b['Blade_Base'].s)
        world['Blade_Tip'] = T(K.point(TIP), K.q, b['Blade_Tip'].s)
        r = diag['right']
        eye = mesh_to_cam(K.point([0.0, 0.0, 23.5]))
        d = dict(t=round(t, 4), mode='grip', open=0.0, reach=round(r['reach'], 3), twist=round(r['twist_deg'], 1),
                 ext=round(r['ext'], 1), uln=round(r['uln'], 1), wrist=round(r['wrist_deg'], 1),
                 grip=[round(float(v), 3) for v in diag['grip_ndc']], elbow=[round(float(v), 2) for v in diag['elbow_ndc']],
                 eye=[round(float(v), 3) for v in ndc(eye)], head_depth=round(float(eye[0]), 1), dev=0.0,
                 eye_cam=[float(v) for v in eye], fist_cam=[float(v) for v in mesh_to_cam(K.p)],
                 axe_q=[float(v) for v in K.q])
        return world, K, d


# ---------------------------------------------------------------- presentation tables (HatchetChopRhythm.h)
# Camera (author s; pitch + up, yaw + right, roll + clockwise, vertical FOV delta, push along the view cm).  Same scale as
# the stage's other curves: the stab widens the view ~11 deg and pushes 9 cm; the heavy chop dips ~6.4 deg.  The chop
# looks up a little and leans with the raise, then the view is dragged down with the blow (pitch -6), snaps clockwise,
# widens and lurches forward into the bite, and eases back while the hatchet is held in and yanked out.
CAMERA_KEYS = [(0.000, 0.0, 0.0, 0.0, 0.0, 0.0),
               (0.150, 0.9, 0.35, -0.7, -0.5, -0.6),
               (0.250, 1.6, 0.65, -1.4, -0.9, -1.4),
               (0.300, 1.8, 0.75, -1.6, -1.1, -1.6),
               (0.335, 1.1, 0.50, -0.6, -0.4, -0.6),
               (0.352, -0.6, 0.15, 1.6, 1.8, 1.6),
               (0.367, -3.2, -0.20, 3.8, 4.4, 3.8),
               (0.400, -6.0, -0.60, 4.6, 6.5, 6.0),
               (0.450, -5.2, -0.50, 2.8, 5.0, 5.0),
               (0.533, -3.2, -0.30, 1.4, 3.0, 3.4),
               (0.590, -2.0, -0.10, 0.6, 1.6, 1.8),
               (0.700, -1.2, 0.10, 0.2, 0.6, 0.6),
               (0.850, -0.4, 0.05, 0.0, 0.1, 0.1),
               (1.000, 0.0, 0.0, 0.0, 0.0, 0.0),
               (LENGTH, 0.0, 0.0, 0.0, 0.0, 0.0)]
# FSwing (KukriRhythm.h order): Length, SwingSound, ContactStart, ContactEnd, BufferOpen, SwingPitch, CameraPitchScale,
# CameraMode, CameraGain, HitStopScale, ImpactScale, KickYaw, KickPitch, HitRoll.  Timing = Swings[2]; the swing sound a
# little lower (a heavier head), camera mode 5 = this curve, the flesh stop x2.2 and the jolt x1.35 (stab x2.0 / x1.25),
# the viewmodel thrown back up (+pitch) against the blow, a lighter roll rattle than the stab.
SWING = ('TEXT("HatchetAttack3")', '38.f/30.f', '.328f', '.34f', '.47f', '.47f', '.92f', '1.f', '5', '1.f', '2.2f', '1.35f',
         '0.f', '1.f', '1.6f')
# FStrike: At, MissStop, AccentFov, AccentPushCM, AccentPitch, AccentYaw, PressX, PressY, PressZ, bWhoosh.  At = the stab's;
# a miss stops a beat longer (the head lands), the accent nods down and widens; a hit presses the hatchet on down.
STRIKE = ('.367f', '.045f', '1.8f', '2.0f', '-1.6f', '0.f', '.5f', '0.f', '-1.4f', 'true')
RIFT = (0.345, 0.400, 0.110, 0.20, 70.0)          # Start, End, Strength, Dissolve, DriftCM: from the head entering the top
RIBBON = (np.array([12.0, 0.0, 14.0]), np.array([19.0, 0.0, 32.0]))   # across the head, past the edge
STATIONS = 40
LENS_CM = 12.0


def camera(t):
    ts = [k[0] for k in CAMERA_KEYS]
    vs = [np.array(k[1:], float) for k in CAMERA_KEYS]
    t = min(max(t, 0.0), LENGTH)
    i = max(0, min(len(ts) - 2, int(np.searchsorted(ts, t, side='right')) - 1))

    def tan(j):
        if j == 0 or j == len(ts) - 1:
            return vs[j] * 0.0
        return (vs[j + 1] - vs[j - 1]) / (ts[j + 1] - ts[j - 1])
    h = ts[i + 1] - ts[i]
    u = (t - ts[i]) / h
    v = ((2 * u ** 3 - 3 * u ** 2 + 1) * vs[i] + (u ** 3 - 2 * u ** 2 + u) * h * tan(i) + (-2 * u ** 3 + 3 * u ** 2) * vs[i + 1]
         + (u ** 3 - u ** 2) * h * tan(i + 1))
    return tuple(float(x) for x in v)


def clamp_lens(p):
    c = mesh_to_cam(p)
    if c[0] >= LENS_CM:
        return p
    return cam_to_mesh(c * (LENS_CM / max(c[0], 1e-3))) if c[0] > 1 else cam_to_mesh(np.array([LENS_CM, c[1], c[2]]))


def ribbon(clip):
    rows = []
    for i in range(STATIONS):
        t = RIFT[0] + (RIFT[1] - RIFT[0]) * i / (STATIONS - 1)
        K = clip.track(t)
        rows.append([clamp_lens(K.point(RIBBON[0])), clamp_lens(K.point(RIBBON[1]))])
    depth = [float(mesh_to_cam(p)[0]) for row in rows for p in row]
    print('  rift: depth %.1f-%.1f cm, outer travels %.1f cm' % (min(depth), max(depth),
                                                                 float(np.linalg.norm(rows[-1][1] - rows[0][1]))))
    return rows


def write_header(clip):
    n = 39                                             # KukriRhythm::CameraSamples (30 Hz over 38/30 s)
    rows = [camera(i / 30.0) for i in range(n)]
    arr = lambda k: ','.join('%.2ff' % (r[k] + 0.0) for r in rows).replace('-0.00f', '0.00f')
    rib = ',\n        '.join('{%s}' % ','.join('{%.2ff,%.2ff,%.2ff}' % tuple(float(v) for v in p) for p in row)
                             for row in ribbon(clip))
    text = f'''#pragma once

#include "CoreMinimal.h"
#include "KukriRhythm.h"

// GENERATED by SourceAssets/HatchetChop20261102/author_hatchet_chop.py -- do not edit by hand.
/**
 * 碳钢战斧三连击第三段：从上往下劈砍（clip "HatchetAttack3"，38/30 s，2026-11-02）。只替换斧子的第三段，弯刀仍是戳刺。
 * 时间轴与弯刀第三段完全一致（StabTempo 节奏、命中窗 0.34-0.47、打击时刻 0.367、缓冲 0.47），所以服务端回执、命中校验
 * 和连击规则都沿用 KukriRhythm::Swings[2]；这里只换表现：
 *  0-0.30 慢速举斧过右肩、刃口朝上；0.30-0.333 顶点定格；0.333-0.367 斧头越过头顶劈下，0.367 刃口到准星（打击时刻）；
 *  0.367-0.40 咬入过冲回弹；0.40-0.533 停在目标里；0.54-0.59 拔出；之后从右下出画、画外回转、由下抬回架势。
 * 镜头：举斧时略抬头、逆时针倾；劈下时被带着低头约 6°、顺时针一甩约 4.6°、视场放宽 6.5°、前冲 6 cm，停住时回落。
 * 打击时刻：挥空硬停 0.045 s，镜头下点头 1.6°、视场 +1.8°；命中顿帧 ×2.2、冲击 ×1.35，顿帧期间视模向下压 1.4 cm，
 * 视模冲击把斧子往上顶。剑气沿斧头扫过的弧线（0.345-0.40）。
 */
namespace HatchetChopRhythm
{{
    inline const TCHAR* Clip=TEXT("/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_Attack3.A_TacticalHatchet_Attack3");
    inline constexpr int32 Stage=2;
    inline constexpr KukriRhythm::FSwing Swing={{{','.join(SWING)}}};
    inline constexpr KukriRhythm::FStrike Strike={{{','.join(STRIKE)}}};
    inline constexpr KukriRhythm::FRift Rift={{{RIFT[0]:.3f}f,{RIFT[1]:.3f}f,{RIFT[2]:.3f}f,{RIFT[3]:.2f}f,{RIFT[4]:.1f}f}};
    static_assert(Swing.Length==KukriRhythm::Swings[Stage].Length&&Swing.ContactStart==KukriRhythm::Swings[Stage].ContactStart&&
        Swing.ContactEnd==KukriRhythm::Swings[Stage].ContactEnd&&Swing.BufferOpen==KukriRhythm::Swings[Stage].BufferOpen&&
        Strike.At==KukriRhythm::Strikes[Stage].At,"the chop keeps stage 2's gameplay clock (server receipts and windows)");

    inline constexpr int32 CameraSamples=KukriRhythm::CameraSamples;
    inline constexpr float ChopPitch[CameraSamples]={{{arr(0)}}};
    inline constexpr float ChopYaw[CameraSamples]={{{arr(1)}}};
    inline constexpr float ChopRoll[CameraSamples]={{{arr(2)}}};
    inline constexpr float ChopFov[CameraSamples]={{{arr(3)}}};
    inline constexpr float ChopPush[CameraSamples]={{{arr(4)}}};

    /** Chop camera at author time T (same conventions and tail fade as KukriRhythm::SwingCamera). */
    inline void Camera(float T,FRotator& Rotation,float& Fov,FVector* Location=nullptr)
    {{
        using namespace KukriRhythm;
        const float Gain=CameraScale*Swing.CameraGain*FMath::Clamp((Swing.Length-T)/CameraTailSeconds,0.f,1.f);
        Rotation=FRotator(SampleCurve(ChopPitch,T)*Swing.CameraPitchScale,SampleCurve(ChopYaw,T),SampleCurve(ChopRoll,T))*Gain;
        Fov=SampleCurve(ChopFov,T)*Gain;
        if(Location)*Location=FVector(SampleCurve(ChopPush,T)*Gain,0.f,0.f);
    }}

    /** Rift ribbon swept by the head over Rift.Start-Rift.End (viewmodel mesh space cm, [station][inner, outer][xyz]). */
    inline constexpr int32 Stations={STATIONS};
    inline constexpr float Ribbon[Stations][2][3]={{
        {rib}}};
}}
'''
    HEADER.write_bytes(text.encode('utf-8'))
    print('header ->', HEADER)


# ---------------------------------------------------------------- runtime clock (for the previews)
# KukriRhythm::StabTempo (copied; the chop runs on it) and the base play rate 38/30 s / attack_seconds 0.8.
STAB_TEMPO = [(0.0, .60), (.150, .60), (.185, 1.0), (.225, 1.0), (.245, .55), (.295, .55), (.302, .50), (.331, .50),
              (.336, .90), (.400, .90), (.410, .75), (.525, .75), (.540, .55), (.590, .55), (.610, .85), (.760, .85),
              (.785, 1.50), (.890, 1.50), (.930, .65), (1.060, .65), (1.110, 1.0)]
PLAY_RATE = LENGTH / 0.8


def tempo(t):
    k = STAB_TEMPO
    if t <= k[0][0]:
        return k[0][1]
    for (t0, r0), (t1, r1) in zip(k, k[1:]):
        if t < t1:
            x = (t - t0) / (t1 - t0)
            return r0 + (r1 - r0) * x * x * (3 - 2 * x)
    return k[-1][1]


def real_clock(fps=60, miss_stop=0.045):
    """Author times of real-time frames at the base attack speed, with the miss stop frozen on the impact moment."""
    out, t, real, stopped = [], 0.0, 0.0, 0.0
    while t < LENGTH:
        out.append(t)
        step = 1.0 / fps
        if t >= STAGE_AT and stopped < miss_stop:
            stopped += step
            continue
        sub = step / 8
        for _ in range(8):
            t = min(LENGTH, t + sub * PLAY_RATE * tempo(t))
    out.append(LENGTH)
    return out


# ---------------------------------------------------------------- outputs
def author(preview=False):
    clip = ChopClip()
    R = clip.R
    R.reset_twist_memory()
    n = int(round(LENGTH * FPS))
    frames, diags, prev_q = [], [], None
    for i in range(n + 1):
        t = i / FPS
        world, K, d = clip.sample(t)
        keys = R.local_keys(world, prev_q)
        prev_q = {b: v[1] for b, v in keys.items()}
        frames.append({b: [list(map(float, v[0])), list(map(float, v[1])), list(map(float, v[2]))] for b, v in keys.items()})
        diags.append(d)
    OUT.mkdir(parents=True, exist_ok=True)
    data = dict(name=CLIP, fps=FPS, length=n / FPS, loop=False, contact=[0.34, 0.47], strike=STAGE_AT, bones=R.rig.names,
                frames=frames, diagnostics=diags)
    (OUT / (CLIP + '.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
    summary = dict(length=round(n / FPS, 4), frames=n + 1, max_reach=max(x['reach'] for x in diags),
                   twist=[min(x['twist'] for x in diags), max(x['twist'] for x in diags)],
                   ext=[min(x['ext'] for x in diags), max(x['ext'] for x in diags)],
                   uln=[min(x['uln'] for x in diags), max(x['uln'] for x in diags)], wrist_max=max(x['wrist'] for x in diags),
                   impact_head=next(x['eye'] for x in diags if abs(x['t'] - STAGE_AT) < 0.005))
    print(CLIP, json.dumps(summary), flush=True)
    (P / 'clips.json').write_text(json.dumps({'clips': {CLIP: dict(summary, source='author_hatchet_chop.py')}},
                                             ensure_ascii=False, indent=2), encoding='utf-8')
    for d in diags[::6]:
        print('  %.3f twist %6.1f ext %5.1f uln %5.1f wrist %5.1f reach %.2f fist %-16s elbow %-14s head %s depth %.1f' % (
            d['t'], d['twist'], d['ext'], d['uln'], d['wrist'], d['reach'], d['grip'], d['elbow'], d['eye'], d['head_depth']))
    smoothness(diags)
    previews = {}
    if preview:
        for k, t in enumerate(real_clock()):
            world, K, _ = clip.sample(t)
            previews['%s_%04d' % (CLIP, k)] = (world, K, camera(t))
    return clip, previews


BLENDER = r"E:\Program Files\Blender Foundation\Blender 5.1\blender.exe"


def render_previews(previews, width=960):
    import cv2
    frames_dir = WORK / 'frames'
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob('*.png'):
        old.unlink()
    poses = {'poses': {name: {'bones': {b: t.pack() for b, t in world.items()}, 'kukri': K.pack(), 'camera': list(cam[:4])}
                       for name, (world, K, cam) in previews.items()}}
    (WORK / 'previews.json').write_text(json.dumps(poses), encoding='utf-8')
    res = subprocess.run([BLENDER, '-b', '--factory-startup', '--python', str(EQUIP / 'render_hatchet_preview.py'), '--',
                          str(WORK / 'previews.json'), str(frames_dir), str(width)],
                         capture_output=True, text=True, encoding='utf-8', errors='replace')
    if res.returncode != 0 or 'Traceback' in res.stdout:
        print(res.stdout[-3000:], res.stderr[-3000:])
        raise RuntimeError('preview render failed')
    names = sorted(previews)
    imgs = []
    for k, name in enumerate(names):
        im = cv2.imread(str(frames_dir / (name + '.png')))
        cv2.putText(im, '%.3f s' % (k / 60.0), (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        imgs.append(im)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    h, w = imgs[0].shape[:2]
    for path, fps in ((PREVIEWS / 'hatchet_chop_realtime.mp4', 60), (PREVIEWS / 'hatchet_chop_slow4x.mp4', 15)):
        raw = WORK / ('raw_' + path.name)
        vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        for im in [imgs[0]] * (fps // 3) + imgs + [imgs[-1]] * (fps // 2):
            vw.write(im)
        vw.release()
        try:
            import imageio_ffmpeg
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error', '-i', str(raw), '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', '-crf', '18', str(path)], check=True)
            raw.unlink()
        except Exception as exc:
            print('H.264 transcode skipped (%s); mp4v kept' % exc)
            raw.replace(path)
    cells = [cv2.resize(im, (480, 270), interpolation=cv2.INTER_AREA) for im in imgs[::2]]
    while len(cells) % 4:
        cells.append(np.zeros_like(cells[0]))
    rows = [np.hstack(cells[k:k + 4]) for k in range(0, len(cells), 4)]
    for s in range(0, len(rows), 4):
        cv2.imwrite(str(PREVIEWS / ('sheet_%d.jpg' % (s // 4))), np.vstack(rows[s:s + 4]), [cv2.IMWRITE_JPEG_QUALITY, 82])
    print('previews ->', PREVIEWS)


if __name__ == '__main__':
    clip, previews = author(preview='--preview' in sys.argv)
    if '--header' in sys.argv:
        write_header(clip)
    if previews:
        render_previews(previews)
