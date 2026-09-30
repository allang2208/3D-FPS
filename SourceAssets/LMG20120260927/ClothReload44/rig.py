"""Rig math for ClothReload44 (UE component space, centimetres).

World matrices carry the root's 100x scale in their rotation columns, exactly as
UE evaluates the saved LMG201 skeleton.  Every arm frame is rebuilt from world
targets and then converted to parent-local tracks, so bone lengths never change.
"""
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp

UNIT = 100.0  # world rotation column norm under SK_M4_Infima


def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-12)


def rot(W):
    return W[:3, :3] / np.linalg.norm(W[:3, :3], axis=0)


def compose(R, p, s=UNIT):
    m = np.eye(4)
    m[:3, :3] = R * s
    m[:3, 3] = p
    return m


def mat(v):
    m = np.eye(4)
    m[:3, :3] = Rot.from_quat(v[3:7]).as_matrix() @ np.diag(v[7:10])
    m[:3, 3] = v[:3]
    return m


def pack(m):
    s = np.linalg.norm(m[:3, :3], axis=0)
    return np.r_[m[:3, 3], Rot.from_matrix(m[:3, :3] / s).as_quat(), s]


def swing(a, b):
    """Minimal rotation matrix taking unit a to unit b."""
    a, b = unit(a), unit(b)
    v = np.cross(a, b)
    s, c = np.linalg.norm(v), float(np.dot(a, b))
    if s < 1e-10:
        if c > 0:
            return np.eye(3)
        k = unit(np.cross(a, [1, 0, 0] if abs(a[0]) < .9 else [0, 1, 0]))
        return Rot.from_rotvec(k * np.pi).as_matrix()
    return Rot.from_rotvec(v / s * np.arctan2(s, c)).as_matrix()


def axis_angle(axis, ang):
    return Rot.from_rotvec(unit(axis) * ang).as_matrix()


def twist_about(R, axis):
    """Signed twist (rad) of rotation matrix R about axis, in (-pi, pi]."""
    q = Rot.from_matrix(R).as_quat()
    if q[3] < 0:
        q = -q
    a = 2 * np.arctan2(np.dot(q[:3], unit(axis)), q[3])
    return (a + np.pi) % (2 * np.pi) - np.pi


def slerp_R(A, B, u):
    if u <= 0:
        return A.copy()
    if u >= 1:
        return B.copy()
    return Slerp([0, 1], Rot.from_matrix([A, B]))([u]).as_matrix()[0]


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (u * 6 - 15) + 10)


def ease_in(u):
    u = min(1.0, max(0.0, u))
    return u * u * u


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def hermite(p0, p1, m0, m1, u, dt):
    u2, u3 = u * u, u * u * u
    return ((2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * dt * m0
            + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * dt * m1)


def basis(a, b):
    a = unit(a)
    b = unit(np.asarray(b, float) - a * np.dot(b, a))
    return np.column_stack((a, b, np.cross(a, b)))


def palm_frame(finger_dir, palmar):
    """Orthonormal frame [f, p, f x p] from finger direction and palmar normal."""
    f = unit(finger_dir)
    p = unit(np.asarray(palmar, float) - f * np.dot(palmar, f))
    return np.column_stack([f, p, np.cross(f, p)])


class Arm:
    """Two-bone arm with fixed clavicle, frame-carried upper-arm roll and the
    accepted V43 / Skin07 forearm roll stations (cap 0, helpers, wrist 1)."""

    STATIONS = {'lowerarm_twist_02': 0.273869, 'lowerarm_twist_01': 0.847869}

    def __init__(self, side, names, parent, rest, idle_world):
        self.s = side
        b = lambda n: names.index(n + '_' + side)
        self.i = {k: b(k) for k in ('clavicle', 'upperarm', 'lowerarm', 'hand',
                                    'lowerarm_twist_01', 'lowerarm_twist_02')}
        self.rest = rest
        W = idle_world
        self.W0 = {k: W[i].copy() for k, i in self.i.items()}
        A, E, T = (W[self.i[k]][:3, 3] for k in ('upperarm', 'lowerarm', 'hand'))
        self.l1 = np.linalg.norm(rest[self.i['lowerarm']][:3, 3] - rest[self.i['upperarm']][:3, 3])
        self.l2 = np.linalg.norm(rest[self.i['hand']][:3, 3] - rest[self.i['lowerarm']][:3, 3])
        self.pole0 = self._pole_of(A, E, T)
        self.F0 = self._frame(A, E, T, self.pole0)
        self.rest_fore = unit(rest[self.i['hand']][:3, 3] - rest[self.i['lowerarm']][:3, 3])
        self.Rrest = {k: rot(rest[i]) for k, i in self.i.items()}
        # idle roll offsets relative to the transported frame
        nr, ax = self._no_roll(rot(W[self.i['upperarm']]), E, T)
        self.cap0 = twist_about(rot(W[self.i['lowerarm']]) @ self.Rrest['lowerarm'].T @ nr.T, ax)
        self.help0 = {k: twist_about(rot(W[self.i[k]]) @ self.Rrest[k].T @ nr.T, ax) for k in self.STATIONS}
        self.phi0 = twist_about(rot(W[self.i['hand']]) @ self.Rrest['hand'].T @ nr.T, ax)
        self.phi_prev = self.phi0
        # helper local translations relative to lowerarm (constant)
        self.help_t = {k: (np.linalg.inv(W[self.i['lowerarm']]) @ W[self.i[k]])[:3, 3] for k in self.STATIONS}
        self.up_t = (np.linalg.inv(W[self.i['clavicle']]) @ W[self.i['upperarm']])[:3, 3]
        self.lo_t = (np.linalg.inv(W[self.i['upperarm']]) @ W[self.i['lowerarm']])[:3, 3]
        self.ha_t = (np.linalg.inv(W[self.i['lowerarm']]) @ W[self.i['hand']])[:3, 3]
        self._coherent_init(names, rest)

    def _pole_of(self, A, E, T):
        ax = unit(T - A)
        v = (E - A) - ax * np.dot(E - A, ax)
        return unit(v)

    def _frame(self, A, E, T, pole):
        u = unit(E - A)
        n = unit(np.cross(unit(T - A), pole))
        return np.column_stack([u, n, np.cross(u, n)])

    def _no_roll(self, Rup, E, T):
        ax = unit(T - E)
        up_d = Rup @ self.Rrest['upperarm'].T
        return swing(up_d @ self.rest_fore, ax) @ up_d, ax

    def reach(self, T, clavicle=None):
        C = self.W0['clavicle'] if clavicle is None else clavicle
        A = (C @ np.r_[self.up_t, 1])[:3]
        return np.linalg.norm(T - A) / (self.l1 + self.l2)

    def positions(self, T, pole_hint, clavicle=None):
        """Two-bone positions and the V43 transport frame (independent of hand rotation)."""
        C = self.W0['clavicle'] if clavicle is None else clavicle
        A = (C @ np.r_[self.up_t, 1])[:3]
        d = T - A
        dist = np.linalg.norm(d)
        lim = (self.l1 + self.l2) * .9995
        if dist > lim:
            T = A + d / dist * lim
            dist = lim
        ax = d / dist
        along = (self.l1 ** 2 - self.l2 ** 2 + dist ** 2) / (2 * dist)
        h = np.sqrt(max(0.0, self.l1 ** 2 - along ** 2))
        pole = np.asarray(pole_hint, float) - ax * np.dot(pole_hint, ax)
        pole = unit(pole) if np.linalg.norm(pole) > 1e-6 else self.pole0
        E = A + ax * along + pole * h
        Rup = self._frame(A, E, T, pole) @ self.F0.T @ rot(self.W0['upperarm'])
        nr, fax = self._no_roll(Rup, E, T)
        return dict(C=C, A=A, E=E, T=T, Rup=Rup, nr=nr, fax=fax, reach=dist / (self.l1 + self.l2))

    def hand_relative(self, pos, Rhand, center=np.radians(40)):
        """Hand rotation as (swing, twist) relative to the transport frame; the
        twist branch is taken nearest to `center` (absolute wrist roll)."""
        Q = Rhand @ self.Rrest['hand'].T @ pos['nr'].T
        phi = twist_about(Q, pos['fax'])
        while phi - center > np.pi:
            phi -= 2 * np.pi
        while phi - center <= -np.pi:
            phi += 2 * np.pi
        S = Q @ axis_angle(pos['fax'], -phi)
        return S, phi

    def hand_from_relative(self, pos, S, phi):
        return S @ axis_angle(pos['fax'], phi) @ pos['nr'] @ self.Rrest['hand']

    def finish(self, pos, Rhand, phi):
        dphi = phi - self.phi0
        out = {'clavicle': pos['C'].copy(), 'upperarm': compose(pos['Rup'], pos['A'])}
        fax, nr = pos['fax'], pos['nr']
        out['lowerarm'] = compose(axis_angle(fax, self.cap0) @ nr @ self.Rrest['lowerarm'], pos['E'])
        for k, st in self.STATIONS.items():
            Rh = axis_angle(fax, self.help0[k] + st * dphi) @ nr @ self.Rrest[k]
            out[k] = compose(Rh, (out['lowerarm'] @ np.r_[self.help_t[k], 1])[:3])
        out['hand'] = compose(Rhand, pos['T'])
        S = Rhand @ self.Rrest['hand'].T @ nr.T @ axis_angle(fax, -phi)
        self.last = dict(reach=pos['reach'], dphi=np.degrees(dphi), phi=np.degrees(phi),
                         wrist=np.degrees(Rot.from_matrix(S).magnitude()),
                         elbow=np.degrees(np.arccos(np.clip(np.dot(unit(pos['A'] - pos['E']), unit(pos['T'] - pos['E'])), -1, 1))))
        return out

    # ---- coherent segments (PKM LeftArm48 / ArmJoint49 / RightReload51 skin) ----
    def _coherent_init(self, names, rest):
        s = self.s
        P = lambda n: rest[names.index(n + '_' + s)][:3, 3]
        self.S0, self.E0, self.H0 = P('upperarm'), P('lowerarm'), P('hand')
        self.cU0, self.cF0 = self.E0 - self.S0, self.H0 - self.E0
        self.width0 = P('index_metacarpal') - P('pinky_metacarpal')
        self.bind = basis(self.cF0, self.width0)
        self.seg = {}
        for seg, bones, origin, axis in (('upper', ('upperarm', 'upperarm_twist_01', 'upperarm_twist_02'), self.S0, self.cU0),
                                         ('fore', ('lowerarm', 'lowerarm_twist_02', 'lowerarm_twist_01'), self.E0, self.cF0)):
            for b in bones:
                i = names.index(b + '_' + s)
                st = float((rest[i][:3, 3] - origin) @ axis / (axis @ axis))
                off = rest[i][:3, 3] - origin - st * axis
                self.seg[b] = (seg, i, st, off, rot(rest[i]))
        self.tau_prev = 0.0

    def tau_of(self, pos, Rhand):
        """Forearm pronation (rad) between the elbow-transported frame and the
        palm-width frame; 0 for the accepted idle."""
        fax, nr = pos['fax'], pos['nr']
        fe = axis_angle(fax, self.cap0) @ nr                       # lowerarm skin, elbow end
        Dh = Rhand @ self.Rrest['hand'].T
        fs = basis(pos['T'] - pos['E'], Dh @ self.width0) @ self.bind.T  # palm-width skin, wrist end
        return twist_about(fs @ fe.T, fax), fe, fs

    def finish_coherent(self, pos, Rhand):
        """PKM LeftArm48 convention (matches every accepted 201 grip idle exactly):
        forearm bones share the palm-width frame, upper-arm helpers carry it across
        the elbow bend, the main upper-arm bone keeps its IK rotation."""
        A, E, T = pos['A'], pos['E'], pos['T']
        tau, fe, fs = self.tau_of(pos, Rhand)
        while tau - self.tau_prev > np.pi:
            tau -= 2 * np.pi
        while tau - self.tau_prev < -np.pi:
            tau += 2 * np.pi
        self.tau_prev = tau
        us = swing(fs @ self.cU0, E - A) @ fs
        out = {'clavicle': pos['C'].copy(), 'upperarm': compose(pos['Rup'], A)}
        for b, (seg, i, st, off, Rr) in self.seg.items():
            if b == 'upperarm':
                continue
            if seg == 'upper':
                out[b] = compose(us @ Rr, A + st * (E - A) + us @ off)
            else:
                out[b] = compose(fs @ Rr, E + st * (T - E) + fs @ off)
        out['hand'] = compose(Rhand, T)
        Dh = Rhand @ self.Rrest['hand'].T
        bend = np.degrees(np.arccos(np.clip(unit(Dh @ self.cF0) @ unit(T - E), -1, 1)))
        self.last = dict(reach=pos['reach'], tau=np.degrees(tau), bend=bend, dphi=np.degrees(tau), phi=np.degrees(tau), wrist=bend,
                         elbow=np.degrees(np.arccos(np.clip(np.dot(unit(A - E), unit(T - E)), -1, 1))))
        return out

    def finish_ramp(self, pos, Rhand, tau=None):
        t, fe, fs = self.tau_of(pos, Rhand)
        if tau is None:
            while t - self.tau_prev > np.pi:
                t -= 2 * np.pi
            while t - self.tau_prev < -np.pi:
                t += 2 * np.pi
            tau = t
        self.tau_prev = tau
        fax, A, E, T = pos['fax'], pos['A'], pos['E'], pos['T']
        us = pos['Rup'] @ self.Rrest['upperarm'].T
        out = {'clavicle': pos['C'].copy()}
        for b, (seg, i, st, off, Rr) in self.seg.items():
            if seg == 'upper':
                skin = us
                p = A + st * (E - A) + us @ off
            else:
                skin = axis_angle(fax, tau * st) @ fe
                p = E + st * (T - E) + skin @ off
            out[b] = compose(skin @ Rr, p)
        out['hand'] = compose(Rhand, T)
        Dh = Rhand @ self.Rrest['hand'].T
        bend = np.degrees(np.arccos(np.clip(unit(Dh @ self.cF0) @ unit(T - E), -1, 1)))
        self.last = dict(reach=pos['reach'], tau=np.degrees(tau), bend=bend, dphi=np.degrees(tau), phi=np.degrees(tau), wrist=bend,
                         elbow=np.degrees(np.arccos(np.clip(np.dot(unit(A - E), unit(T - E)), -1, 1))))
        return out

    def solve(self, T, Rhand, pole_hint, clavicle=None):
        """Return world matrices {clavicle, upperarm, lowerarm, hand, helpers}."""
        C = self.W0['clavicle'] if clavicle is None else clavicle
        A = (C @ np.r_[self.up_t, 1])[:3]
        d = T - A
        dist = np.linalg.norm(d)
        lim = (self.l1 + self.l2) * .9995
        if dist > lim:
            T = A + d / dist * lim
            dist = lim
        ax = d / dist
        along = (self.l1 ** 2 - self.l2 ** 2 + dist ** 2) / (2 * dist)
        h = np.sqrt(max(0.0, self.l1 ** 2 - along ** 2))
        pole = np.asarray(pole_hint, float) - ax * np.dot(pole_hint, ax)
        pole = unit(pole) if np.linalg.norm(pole) > 1e-6 else self.pole0
        E = A + ax * along + pole * h
        F = self._frame(A, E, T, pole)
        Rup = F @ self.F0.T @ rot(self.W0['upperarm'])
        nr, fax = self._no_roll(Rup, E, T)
        phi = twist_about(Rhand @ self.Rrest['hand'].T @ nr.T, fax)
        while phi - self.phi_prev > np.pi:
            phi -= 2 * np.pi
        while phi - self.phi_prev < -np.pi:
            phi += 2 * np.pi
        self.phi_prev = phi
        dphi = phi - self.phi0
        out = {'clavicle': C.copy(), 'upperarm': compose(Rup, A)}
        Rlo = axis_angle(fax, self.cap0) @ nr @ self.Rrest['lowerarm']
        out['lowerarm'] = compose(Rlo, E)
        for k, st in self.STATIONS.items():
            Rh = axis_angle(fax, self.help0[k] + st * dphi) @ nr @ self.Rrest[k]
            p = (out['lowerarm'] @ np.r_[self.help_t[k], 1])[:3]
            out[k] = compose(Rh, p)
        out['hand'] = compose(Rhand, T)
        self.last = dict(A=A, E=E, T=T, reach=dist / (self.l1 + self.l2), dphi=np.degrees(dphi),
                         elbow=np.degrees(np.arccos(np.clip(np.dot(unit(A - E), unit(T - E)), -1, 1))))
        return out
