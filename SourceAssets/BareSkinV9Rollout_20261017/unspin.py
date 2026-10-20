"""Forearm unspin (numpy only, shared by the offline evaluation and the UE commandlet).

Per key: p = hand roll about the forearm (relative to lowerarm and bind), e = the forearm's own axial roll inside
the elbow (lowerarm relative to upperarm, against bind). Rotating the forearm bone about the line elbow->wrist by
beta keeps every joint position and the hand's world rotation; it moves roll between the two: p' = p - beta,
e' = e + beta. beta minimises  max(0, |p'| - P_LIM)^2 + max(0, |e'| - E_LIM)^2  (0 for every normal key), so only
keys beyond the anatomical roll range change, and a spurious elbow spin that the hand counter-rotates is removed.
p and e are unwrapped over the clip; beta is smoothed in time so the change stays continuous."""
import math
import numpy as np
from scipy.spatial.transform import Rotation as Rot

P_LIM, E_LIM = 165.0, 90.0


def twist(q, axis):
    q = np.asarray(q, float)
    if q[3] < 0: q = -q
    return math.degrees(2 * math.atan2(q[:3] @ np.asarray(axis), q[3]))


def unwrap(v):
    out, p = [], None
    for x in v:
        if p is not None:
            while x - p > 180: x -= 360
            while x - p < -180: x += 360
        out.append(x); p = x
    return out


def centre(v):
    k = round(sum(v) / len(v) / 360); return [x - 360 * k for x in v]


def best_beta(p, e):
    """Only keys whose hand roll is beyond P_LIM change: beta brings p back to the limit, as far as the elbow's
    axial roll stays within max(its authored value, E_LIM) - a spurious elbow spin that the hand counter-rotates
    is removed completely, a roll that is already in the same direction at the elbow is not pushed into it."""
    if abs(p) <= P_LIM: return 0.0
    want = p - math.copysign(P_LIM, p)
    cap = max(abs(e), E_LIM)
    if abs(e + want) <= cap: return want
    lo, hi = sorted((-cap - e, cap - e))                   # beta range keeping |e + beta| <= cap
    b = min(max(want, lo), hi)
    return b if b * want > 0 else 0.0


def smooth(beta, rate, sigma_s=0.04):
    """Gaussian smoothing in time (sigma 40 ms) that never lowers a key's |beta| below what it needs."""
    b = np.asarray(beta, float)
    if not b.any(): return b
    r = max(1, int(round(sigma_s * rate * 3))); k = np.exp(-.5 * (np.arange(-r, r + 1) / (sigma_s * rate)) ** 2); k /= k.sum()
    pad = np.pad(b, r, mode='edge'); sm = np.convolve(pad, k, mode='valid')
    return np.where(np.abs(b) > np.abs(sm), b, sm)


def elbow_twist(U, L, U0, L0, axis_l):
    return twist(((U0.inv() * L0).inv() * (U.inv() * L)).as_quat(), axis_l)


PHI_MAX, ELBOW_MOVE_MAX = 75.0, 15.0


def swivel_for(p_now, S, E, W, L, H, rel_hand, axis_l):
    """Whole-arm swivel about the shoulder->wrist line (shoulder, wrist and the hand's world rotation stay; the elbow
    moves on its circle) that brings the hand roll back to P_LIM, within PHI_MAX and ELBOW_MOVE_MAX cm of elbow
    travel. Returns phi in degrees (0 if the key is within range)."""
    if abs(p_now) <= P_LIM: return 0.0
    a = (W - S) / np.linalg.norm(W - S); r = np.linalg.norm((E - S) - ((E - S) @ a) * a)
    lim = PHI_MAX if r < 1e-6 else min(PHI_MAX, math.degrees(2 * math.asin(min(1.0, ELBOW_MOVE_MAX / (2 * r)))))

    def p_at(phi):
        Ls = Rot.from_rotvec(a * math.radians(phi)) * L
        x = twist((Ls.inv() * H * Rot.from_quat(rel_hand).inv()).as_quat(), axis_l)
        while x - p_now > 180: x -= 360
        while x - p_now < -180: x += 360
        return x
    target = math.copysign(P_LIM, p_now); best = 0.0; best_err = abs(p_now - target)
    for phi in np.linspace(-lim, lim, 61):
        err = abs(p_at(phi) - target) if abs(p_at(phi)) > P_LIM else 0.0
        if err < best_err - 1e-6 or (abs(err - best_err) < 1e-6 and abs(phi) < abs(best)): best, best_err = float(phi), err
    return best
