"""V85 frame helpers (from V84): weapon placement, free-hilt contact path, finger shapes, left-hand regrip."""
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector

import v85_keys as C
import v85_hand as Hd
from v85_arm import Arm
from v85_setup import UP, VIEW, WPN

ELBOW_GIVE_R = 0.22
BEND_CAP_SOLVE = 30.0
BEND_CAP_FINAL = 40.0
MIN_TIP_DEPTH = 0.10
DOWNSTROKE_DEG = 0.0  # V82 -22 (forward-spin cock); the CCW windup tilt alone is the counter-move, the pitch made a hitch
OPEN_METACARPAL, OPEN_PHALANX = 0.62, 0.95
DORSAL_M = 0.06  # hilt axis from the palm-side web contact to the back of the web (V84 search settled 6.4-7.2 cm)


def mix_mat(a, b, t):
    la, qa, sa = a.decompose()
    lb, qb, sb = b.decompose()
    if qa.dot(qb) < 0.0:
        qb.negate()
    return Matrix.LocRotScale(la.lerp(lb, t), qa.slerp(qb, t), sa.lerp(sb, t))


class Solver:
    def __init__(self, c):
        self.c = c
        self.arm = Arm(c.rest, c.idle, c.idle_scale)
        self.twist = {s: Hd.Twist(c.rest, s) for s in ('r', 'l')}
        self.humerus = {'r': 0.0}
        self.search_prev = 0.0

    def weapon_at(self, rot, contact_world):
        c = self.c
        return Matrix.LocRotScale(contact_world - rot @ c.contact_bone_local, rot, c.idle_scale[WPN])

    def lift_tip(self, rot, contact_world):
        c = self.c
        tip = (self.weapon_at(rot, contact_world) @ c.rest[WPN].inverted()) @ c.tip_bind
        if tip.y >= MIN_TIP_DEPTH - 1e-5:
            return rot
        axis = (tip - contact_world).cross(VIEW)
        if axis.length < 1e-6:
            return rot
        axis.normalize()
        lo, hi, best = 0.0, math.radians(40.0), rot
        for _ in range(18):
            mid = 0.5 * (lo + hi)
            trial = Quaternion(axis, mid) @ rot
            if ((self.weapon_at(trial, contact_world) @ c.rest[WPN].inverted()) @ c.tip_bind).y >= MIN_TIP_DEPTH:
                best, hi = trial, mid
            else:
                lo = mid
        return best

    def attach_helpers(self, pose, parent_name):
        c = self.c
        side, prefix = parent_name[-1], parent_name[:-2]
        for idx in ('01', '02'):
            n = '%s_twist_%s_%s' % (prefix, idx, side)
            if n in c.rest:
                pose[n] = pose[parent_name] @ c.idle[parent_name].inverted() @ c.idle[n]

    def free_weapon(self, pose, rot, t):
        """Hilt tangent to the keyed skin contact: across the palm (index root + middle pad), the thumb web,
        or the back of the web (dorsal: web + hand thickness along the back of the hand)."""
        c = self.c
        P, _ = c.contact_skin.posed(pose)
        w = {k: max(0.0, C.CONTACT[k](t)) for k in ('palm', 'web', 'dorsal')}
        total = sum(w.values()) or 1.0
        weights = {'web': (w['web'] + w['dorsal']) / total, 'index': 0.5 * w['palm'] / total,
                   'hook': 0.5 * w['palm'] / total}
        back = pose['hand_r'].to_quaternion() @ Vector((0.0, 1.0, 0.0))
        shift = C.STATION(t)
        origin = Vector()
        for k, key in enumerate(('web', 'index', 'hook')):
            ct = c.contacts[key]
            skin = Vector(P[k])
            axis_pt = skin + (pose[ct['bone']].to_quaternion() @ ct['dir']) * ct['d']
            origin += weights[key] * (axis_pt - rot @ Vector((0.0, 0.0, ct['z'] + shift)))
        origin += back * (DORSAL_M * w['dorsal'] / total + C.SIDE(t))
        return Matrix.LocRotScale(origin, rot, c.idle_scale[WPN]), w

    def right_fingers(self, pose, t):
        c = self.c
        local = Hd.finger_locals(C.finger_shape(t), c.local_rest, c.finger_idle_r)
        for n in c.finger_r:
            pose[n] = pose[c.parent[n]] @ local[n]

    def left_fingers(self, pose, seconds, left_open):
        c = self.c
        for n in c.finger_l:
            finger, joint = n.split('_')[0], n.split('_')[1]
            amount = left_open
            if seconds >= C.LEFT_APPROACH_START:
                a, b = C.LEFT_CLOSE_WINDOWS[finger]
                delay = {'metacarpal': -0.008, '01': -0.006, '02': 0.0, '03': 0.006}.get(joint, 0.0)
                # Clamped: the quintic can round to 1 + 2e-16, which slerp rejects.
                amount = min(1.0, max(0.0, 1.0 - C.smoothstep((seconds - a - delay) / (b - a))))
            w = amount * (OPEN_METACARPAL if joint == 'metacarpal' else OPEN_PHALANX)
            w *= {'metacarpal': 0.45, '01': 0.90, '02': 0.82, '03': 0.70}.get(joint, 1.0)
            if finger == 'thumb':
                w *= 0.74
            loc_i, q_i, s_i = c.idle_local[n]
            q_r = Quaternion()
            if q_i.dot(q_r) < 0.0:
                q_r.negate()
            pose[n] = pose[c.parent[n]] @ c.local_rest[n] @ Matrix.LocRotScale(loc_i, q_i.slerp(q_r, w), s_i)
