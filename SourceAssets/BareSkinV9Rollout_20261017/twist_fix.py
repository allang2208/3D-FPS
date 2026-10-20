"""Twist redistribution (shared by the offline check and the UE writer).

Per frame and side: hand roll about the forearm axis (relative to lowerarm and bind), unwrapped over the
clip; lowerarm_twist_01 then carries SHARE1 of it and lowerarm_twist_02 SHARE2 (the convention of the
accepted M4 / M16 / vertical-grip clips: 1.0 and 0.5). Swing of the twist bones is reset to bind (they
are leaf bones on lowerarm; the hand, fingers and every contact point are untouched).
"""
import numpy as np
from scipy.spatial.transform import Rotation as Rot

SHARE1, SHARE2 = 1.0, 0.5


def twist_angle(q_rel, axis):
    x, y, z, w = q_rel.as_quat()
    if w < 0: x, y, z, w = -x, -y, -z, -w
    return float(np.degrees(2 * np.arctan2(np.dot([x, y, z], axis), w)))


class SideTwist:
    def __init__(self, ref_bones, s):
        self.s = s; L = 'lowerarm_' + s; self.L = L
        rq = {b: Rot.from_quat(ref_bones[b]['q']) for b in (L, 'hand_' + s, 'lowerarm_twist_01_' + s, 'lowerarm_twist_02_' + s)}
        rt = {b: np.array(ref_bones[b]['t']) for b in (L, 'hand_' + s)}
        ax = rt['hand_' + s] - rt[L]; ax /= np.linalg.norm(ax)
        self.axis_l = rq[L].inv().apply(ax)
        self.rel_ref = {b: rq[L].inv() * rq[b] for b in rq if b != L}

    def hand_rolls(self, qL_list, qH_list):
        th = [twist_angle((qL.inv() * qH) * self.rel_ref['hand_' + self.s].inv(), self.axis_l) for qL, qH in zip(qL_list, qH_list)]
        return np.degrees(np.unwrap(np.radians(th)))

    def twist_locals(self, rolls):
        """Local (parent = lowerarm) rotations for twist_01 / twist_02 per frame."""
        out = {}
        for b, share in (('lowerarm_twist_01_' + self.s, SHARE1), ('lowerarm_twist_02_' + self.s, SHARE2)):
            out[b] = [Rot.from_rotvec(self.axis_l * np.radians(share * r)) * self.rel_ref[b] for r in rolls]
        return out
