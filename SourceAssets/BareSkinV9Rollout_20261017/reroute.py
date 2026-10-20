"""Hand roll re-route for clips whose hand turns past the anatomical range about the forearm (user approved
10-18: in those frames the hand may turn the way a human arm can; rhythm and length stay).

Per side, every key (component space, scipy Rotations; positions numpy):
  p   hand roll about the forearm, relative to lowerarm and bind, unwrapped from key 0 (key 0 as authored).
  A correction c (deg) is removed from p so |p - c| <= P_MAX everywhere:
  - an excursion that comes back on the same side is softly clamped at the limit;
  - one that ends on the other side of +-180 (net crossing) is re-routed: inside the window the hand travels the
    other way round (360 - original travel) with the original timing profile; after it the correction is a
    whole turn, i.e. the pose is exactly as authored again.
  c is split by where the original spin happened inside the window: the part the forearm bone spun (the hand
  steady in the world) is taken back from the forearm (and from the upper arm if it spun with it); the part the
  hand itself spun is re-routed on the hand (fingers follow; contact can shift in those frames). Right hands
  never get the hand part (weapons hang off them) - that part stays and is reported.
Joint positions never move: the upper arm turns about shoulder->elbow, the forearm about elbow->wrist, the
hand about the same forearm line."""
import math
import numpy as np
from scipy.spatial.transform import Rotation as Rot

P_MAX, P_FLAG, P_EXT, CLAMP_MAX = 170.0, 180.0, 110.0, 45.0


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
    return np.array(out)


def smooth(x, rate, sigma_s=0.03):
    x = np.asarray(x, float); r = max(1, int(round(3 * sigma_s * rate)))
    k = np.exp(-.5 * (np.arange(-r, r + 1) / max(sigma_s * rate, 1e-6)) ** 2); k /= k.sum()
    return np.convolve(np.pad(x, r, mode='edge'), k, mode='valid')


def unit(v): return v / max(np.linalg.norm(v), 1e-12)


def correction(p, rate):
    """-> c (deg per key), parts [(k0, k1, kind, contribution array)].

    R3c: every key whose own (wrapped) roll is within the range keeps exactly its authored orientation; only the
    keys near +-180 change. A run that comes back on the same side is held at the limit; a run that passes
    through 180 (or a jump over it between two keys) becomes a short window from the last key within P_EXT before
    it to the first one after it, in which the hand travels between those two orientations through 0, with the
    original's timing. (R3's version re-planned the whole rest of the clip when the authored path stayed on the
    other branch, which froze the hand's roll for seconds, e.g. M4 prism drum reload, ASH12 / M16 equips.)"""
    n = len(p); w = (p + 180.0) % 360.0 - 180.0
    bad = np.abs(w) > P_MAX
    jump = np.zeros(n, bool); jump[1:] = np.abs(np.diff(w)) > 180.0           # crossed 180 between two keys
    runs, k = [], 0
    while k < n:
        if not (bad[k] or jump[k]): k += 1; continue
        a = k
        while k + 1 < n and (bad[k + 1] or jump[k + 1]): k += 1
        runs.append((a, k)); k += 1
    target = w.copy(); parts = []; prev_end = -1; skip_to = -1
    for i, (a, b) in enumerate(runs):
        if a < skip_to: continue
        nxt = runs[i + 1][0] if i + 1 < len(runs) else n
        pre = w[a - 1] if a > 0 else None; post = w[b + 1] if b + 1 < n else None
        crossing = pre is not None and post is not None and pre * post < 0
        if crossing:
            # a shallow pass beyond 180 (the far side never comes back below 180 - CLAMP_MAX before the path
            # returns or the clip ends) is held at the limit instead: the hand turns a little less (sword uppercut)
            j, deep = b + 1, False
            while j < n:
                if w[j] * pre > 0 and not bad[j] and not jump[j]: break
                if w[j] * post > 0 and abs(w[j]) < 180.0 - CLAMP_MAX: deep = True; break
                j += 1
            if not deep:
                target[a:j] = math.copysign(P_MAX, pre); parts.append((a, j - 1, 'clamp')); prev_end = j - 1; skip_to = j
                continue
        if not crossing:
            s0 = math.copysign(1, pre if pre is not None else (post if post is not None else w[a]))
            target[a:b + 1] = s0 * P_MAX                                     # held at the limit on its side
            parts.append((a, b, 'clamp')); prev_end = b; continue
        k0 = a - 1
        while k0 - 1 > prev_end and abs(w[k0]) > P_EXT: k0 -= 1
        k1 = b + 1
        while k1 + 1 < nxt and abs(w[k1]) > P_EXT: k1 += 1
        D = p[k1] - p[k0]
        t = np.clip((p[k0:k1 + 1] - p[k0]) / D, 0, 1) if abs(D) > 1e-6 else np.linspace(0, 1, k1 - k0 + 1)
        target[k0:k1 + 1] = w[k0] + t * (w[k1] - w[k0])                        # through 0, original timing
        parts.append((k0, k1, 'reroute')); prev_end = k1
    c = p - target                                          # whole turns outside the windows
    # soft corners on the clamps (never less than needed)
    for a, b, kind in parts:
        if kind != 'clamp': continue
        lo, hi = max(0, a - int(rate * .05)), min(n, b + 1 + int(rate * .05))
        cw = c[lo:hi] - np.round(c[lo:hi] / 360.0) * 360.0
        sm = smooth(cw, rate); cw = np.where(np.abs(sm) > np.abs(cw), sm, cw)
        c[lo:hi] = np.round(c[lo:hi] / 360.0) * 360.0 + cw
    # per window contribution: the change inside it plus the whole turn it leaves behind
    out, off = [], 0.0
    for a, b, kind in parts:
        arr = np.zeros(n); base = np.round(c[a - 1] / 360.0) * 360.0 if a > 0 else 0.0
        end_off = np.round(c[b + 1] / 360.0) * 360.0 if b + 1 < n else np.round(c[b] / 360.0) * 360.0
        arr[a:b + 1] = c[a:b + 1] - base; arr[b + 1:] = end_off - base
        out.append((a, b, kind, arr))
    # anything left between windows is a whole turn from the start (anchor); keep it in the first part's tail
    lead = np.round(c[0] / 360.0) * 360.0
    if out and abs(lead) > 0: out[0][3][:] += lead
    return c, out


def plan_side(keys, rel_hand, axis_l, rate, side):
    """keys: list of dict(S, E, W, U, L, H) per key (component). -> dict with alpha, beta, gamma (deg per key),
    p, p2, windows, residual (hand part not applied on right hands)."""
    rel = Rot.from_quat(rel_hand); ax = np.asarray(axis_l, float)
    p = unwrap([twist((k['L'].inv() * k['H'] * rel.inv()).as_quat(), ax) for k in keys])
    if np.abs(p).max() <= P_FLAG: return None
    c, parts = correction(p, rate); windows = [(k0, k1, kind) for k0, k1, kind, _ in parts]
    n = len(keys)
    # world axial spin increments about the current forearm / upper-arm axes
    dh = np.zeros(n); dl = np.zeros(n); du = np.zeros(n)
    for i in range(1, n):
        F = unit(keys[i]['W'] - keys[i]['E']); A = unit(keys[i]['E'] - keys[i]['S'])
        dh[i] = twist((keys[i]['H'] * keys[i - 1]['H'].inv()).as_quat(), F)
        dl[i] = twist((keys[i]['L'] * keys[i - 1]['L'].inv()).as_quat(), F)
        du[i] = twist((keys[i]['U'] * keys[i - 1]['U'].inv()).as_quat(), A)
    beta = np.zeros(n); gamma = np.zeros(n); alpha = np.zeros(n)
    for k0, k1, kind, arr in parts:
        a, b = max(0, k0 - 1), min(n - 1, k1 + 1)
        Hs, Ls, Us = dh[a + 1:b + 1].sum(), dl[a + 1:b + 1].sum(), du[a + 1:b + 1].sum()
        # p grows with the hand's spin and against the forearm's: dp ~ dH - dL
        sb = float(np.clip(-Ls / (Hs - Ls), 0, 1)) if abs(Hs - Ls) > 1e-6 else 1.0
        r_ = float(np.clip(Us / Ls, 0, 1)) if abs(Ls) > 1e-6 else 0.0
        if side == 'r': sb = 1.0                                   # weapons hang off the right hand: never turn it
        if kind == 'reroute':
            # after the window the correction is a whole turn: each bone must end on a whole turn too
            sb = 1.0 if sb >= .5 else 0.0; r_ = 1.0 if r_ >= .5 else 0.0
        beta += arr * sb; gamma += arr * (1 - sb); alpha += arr * sb * r_
    residual = np.zeros(n)
    p2 = p - beta - gamma
    return dict(p=p, p2=p2, alpha=alpha, beta=beta, gamma=gamma, residual=residual, windows=windows)


def apply_key(k, alpha, beta, gamma):
    """New component rotations U*, L*, H* (positions unchanged)."""
    A = unit(k['E'] - k['S']); F = unit(k['W'] - k['E'])
    U2 = Rot.from_rotvec(A * math.radians(alpha)) * k['U']
    L2 = Rot.from_rotvec(F * math.radians(beta)) * k['L']
    H2 = Rot.from_rotvec(F * math.radians(-gamma)) * k['H']
    return U2, L2, H2
