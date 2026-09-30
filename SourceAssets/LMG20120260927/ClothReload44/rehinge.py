"""Anatomical left arm skin frames for PKM V7 / 201 reloads.

The rest skeleton bends the elbow about the upper-arm helpers' local Z.  The coherent
segment convention (PKM LeftArm48) instead carries the palm roll up into the upper arm, so
in the reloads the upper arm is rolled off its bend axis (PKM ~160 deg, 201 up to ~110 deg):
the elbow flexes against the skin's anatomy and the upper arm reads thin and twisted.

Here, per frame and with shoulder/elbow/wrist positions, hand and fingers kept:
  upper-arm helpers  : aligned so local Z is the actual bend axis (humerus-rigid)
  lowerarm           : that frame carried across the elbow bend (pure hinge)
  forearm helpers    : pronation ramp at their real stations (0, 1/3, 2/3), hand = 1
blended in by elbow bend (w = 0 below 25 deg, 1 above 50 deg) so near-straight idle poses
are exactly unchanged.  Optionally the elbow is re-placed on the shoulder-wrist circle to
reduce the forearm pronation (swivel), with bone lengths and the hand world matrix fixed.
"""
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from scipy.ndimage import gaussian_filter1d
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'Diagnostics'))
import diag_lib as D

BI, REST = D.BI, D.REST
UPPER = ('upperarm_twist_01_l', 'upperarm_twist_02_l')
FORE = (('lowerarm_l', 0.0), ('lowerarm_twist_02_l', 1 / 3), ('lowerarm_twist_01_l', 2 / 3))


def rot(m):
    return m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)


def unit(v):
    return v / max(np.linalg.norm(v), 1e-12)


def axis_angle(ax, a):
    return Rot.from_rotvec(unit(ax) * a).as_matrix()


def twist_about(Rm, ax):
    q = Rot.from_matrix(Rm).as_quat()
    s = q[:3] @ unit(ax)
    return 2 * np.arctan2(s, q[3])


def smooth(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


P = lambda n: REST[BI[n]][:3, 3]
U0, F0 = P('lowerarm_l') - P('upperarm_l'), P('hand_l') - P('lowerarm_l')
H0 = unit(np.cross(U0, F0))


def frame(x, z):
    x = unit(x)
    z = unit(z - x * (z @ x))
    return np.column_stack((x, np.cross(z, x), z))


FU0, FL0 = frame(U0, H0), frame(F0, H0)
R_REST = {n: rot(REST[BI[n]]) for n in UPPER + tuple(n for n, _ in FORE) + ('hand_l',)}


def anatomical(W):
    """Anatomical skin rotations (deltas vs rest) of upper arm and elbow-end forearm, and
    the forearm pronation needed to reach the hand, for one frame."""
    a, e, t = (W[BI[n]][:3, 3] for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
    u, f = e - a, t - e
    h = np.cross(u, f)
    bend = np.degrees(np.arctan2(np.linalg.norm(h), u @ f))
    return u, f, unit(h), bend


def solve_clip(Wall, hinge_lo=25.0, hinge_hi=50.0, sigma_frames=4):
    """Return new world matrices for the left-arm skin bones for every frame."""
    n = len(Wall)
    data, prev_h = [], None
    for k in range(n):
        u, f, h, bend = anatomical(Wall[k])
        # continuity of the bend axis through near-straight frames
        if prev_h is not None and bend < 8:
            h = unit(prev_h - unit(u) * (prev_h @ unit(u)))
        prev_h = h
        Du = frame(u, h) @ FU0.T               # anatomical upper-arm skin delta
        Dl = frame(f, h) @ FL0.T               # anatomical lowerarm (elbow end)
        Dh = rot(Wall[k][BI['hand_l']]) @ R_REST['hand_l'].T
        tau = twist_about(Dl.T @ Dh, F0)       # pronation (rest forearm axis) from elbow end to hand
        cur = rot(Wall[k][BI['upperarm_twist_02_l']]) @ R_REST['upperarm_twist_02_l'].T
        phi = twist_about(Du.T @ cur, U0)      # current helper roll off the bend axis
        data.append((u, f, h, bend, Du, Dl, tau, phi))
    tau = np.unwrap([d[6] for d in data])
    phi = np.unwrap([d[7] for d in data])
    w = smooth((np.array([d[3] for d in data]) - hinge_lo) / (hinge_hi - hinge_lo))
    w = gaussian_filter1d(w, sigma_frames, mode='nearest')
    out = []
    for k, (u, f, h, bend, Du, Dl, _, _) in enumerate(data):
        W = Wall[k]
        a, e = W[BI['upperarm_l']][:3, 3], W[BI['lowerarm_l']][:3, 3]
        new = {}
        for nme in UPPER:
            cur = rot(W[BI[nme]])
            tgt = Du @ R_REST[nme]
            # blend about the humerus axis only (both frames share the bone axis)
            ang = twist_about(tgt @ cur.T, u)
            R_new = axis_angle(u, w[k] * ang) @ cur
            m = W[BI[nme]].copy()
            m[:3, :3] = R_new * np.linalg.norm(W[BI[nme]][:3, :3], axis=0)
            m[:3, 3] = a + axis_angle(u, w[k] * ang) @ (W[BI[nme]][:3, 3] - a)
            new[nme] = m
        for nme, st in FORE:
            cur = rot(W[BI[nme]])
            tgt = axis_angle(f, tau[k] * st) @ Dl @ R_REST[nme]
            ang = twist_about(tgt @ cur.T, f)
            R_new = axis_angle(f, w[k] * ang) @ cur
            m = W[BI[nme]].copy()
            m[:3, :3] = R_new * np.linalg.norm(W[BI[nme]][:3, :3], axis=0)
            m[:3, 3] = e + axis_angle(f, w[k] * ang) @ (W[BI[nme]][:3, 3] - e)
            new[nme] = m
        out.append(new)
    info = dict(tau_deg=np.degrees(tau), phi_deg=np.degrees(phi), w=w, bend=np.array([d[3] for d in data]))
    return out, info
