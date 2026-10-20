"""Elbow hinge normalisation (numpy only; offline simulation and UE commandlet share it).

Per key and side (component space): p = hand roll about the forearm (vs lowerarm and bind), e = the forearm bone's
axial roll inside the elbow (lowerarm vs upperarm, against bind; a pure hinge is 0). Both wrapped to +-180.
The total t = p + e is what the arm has to carry between the upper arm and the hand. Anatomically the elbow is a
hinge and the forearm (radius) carries the roll, so: e' = 0, p' = t; beyond P_LIM the excess stays in the elbow.
The forearm bone is rotated about the line elbow->wrist by beta = e' - e: every joint position and the hand's
world rotation are unchanged (the hand's local rotation is recomputed). Per key, no unwrapping: the same pose
always gives the same result, so clips that blend into each other stay consistent."""
import math
import numpy as np
from scipy.spatial.transform import Rotation as Rot

P_LIM, E_OK = 165.0, 45.0


def wrap(d): return (d + 180.0) % 360.0 - 180.0


def twist(q, axis):
    q = np.asarray(q, float)
    if q[3] < 0: q = -q
    return math.degrees(2 * math.atan2(q[:3] @ np.asarray(axis), q[3]))


class Side:
    def __init__(self, ref, s, rel_hand, axis_l, rel_t1=None, rel_t2=None, shares=(1.0, 0.5)):
        self.s = s; self.U0 = Rot.from_quat(ref['upperarm_' + s]['q']); self.L0 = Rot.from_quat(ref['lowerarm_' + s]['q'])
        self.B = self.U0.inv() * self.L0; self.rel_hand = Rot.from_quat(rel_hand); self.axis = np.asarray(axis_l, float)
        self.rel_t1 = Rot.from_quat(rel_t1) if rel_t1 is not None else None; self.rel_t2 = Rot.from_quat(rel_t2) if rel_t2 is not None else None
        self.shares = shares

    def solve(self, U, L, H):
        """-> beta (deg, about the forearm axis), p, e, p', e'."""
        p = wrap(twist((L.inv() * H * self.rel_hand.inv()).as_quat(), self.axis))
        e = wrap(twist(((U * self.B).inv() * L).as_quat(), self.axis))
        if abs(e) <= E_OK: return 0.0, p, e, p, e                     # normal keys stay exactly as authored
        t = wrap(p + e)
        e2 = math.copysign(E_OK, e); p2 = wrap(t - e2)                 # least change that brings the elbow back to E_OK
        if abs(p2) > P_LIM:                                            # forearm full: the rest stays in the elbow
            p2 = math.copysign(P_LIM, p2); e2 = wrap(t - p2)
            if abs(e2) >= abs(e): return 0.0, p, e, p, e
        return wrap(e2 - e), p, e, p2, e2

    def blend_beta(self, U, L, H, e_lo=60.0, e_hi=120.0):
        """Per key, deterministic: keys whose elbow axial roll is beyond e_lo move toward the anatomical split
        (elbow a pure hinge, forearm carries the roll up to P_LIM), fully at e_hi. -> beta, p, e."""
        p = wrap(twist((L.inv() * H * self.rel_hand.inv()).as_quat(), self.axis))
        e = wrap(twist(((U * self.B).inv() * L).as_quat(), self.axis))
        x = min(1.0, max(0.0, (abs(e) - e_lo) / (e_hi - e_lo))); w = x * x * (3 - 2 * x)
        if w <= 0: return 0.0, p, e
        t = wrap(p + e)
        # near a total roll of +-180 the split would flip sides between keys: fade out there (no new discontinuity)
        y = min(1.0, max(0.0, (abs(t) - 130.0) / 40.0)); w *= 1 - y * y * (3 - 2 * y)
        if w <= 0: return 0.0, p, e
        p2 = max(-P_LIM, min(P_LIM, t)); e2 = t - p2
        d = wrap(e2 - e)
        # the target is ambiguous when the elbow is turned ~180 from it: a partial blend there would jump between the
        # two ways round from one key to the next; go all the way instead (both ways are then the same rotation)
        z = min(1.0, max(0.0, (abs(d) - 140.0) / 35.0)); w = w + (1 - w) * z * z * (3 - 2 * z)
        return w * d, p, e

    def apply(self, L, H, beta, p2):
        """New lowerarm and twist rotations (component); the hand keeps H."""
        Ls = L * Rot.from_rotvec(self.axis * math.radians(beta))        # about the forearm's own axis (local)
        out = {'lowerarm': Ls}
        if self.rel_t1 is not None:
            out['twist_01'] = Ls * Rot.from_rotvec(self.axis * math.radians(self.shares[0] * p2)) * self.rel_t1
            out['twist_02'] = Ls * Rot.from_rotvec(self.axis * math.radians(self.shares[1] * p2)) * self.rel_t2
        return out
