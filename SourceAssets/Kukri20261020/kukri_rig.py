"""One-hand kukri rig solver on the shared sword arms skeleton (SK_AzureRunesword_Manny_Skeleton).

Anchor: the accepted sword Idle frame 0 (right fist around the hilt, V9 bare-arm skin and twist
convention). The right hand keeps that exact fist and its transform relative to a grip frame on the
hilt axis; the kukri mesh is authored in the same grip frame (see author_kukri_model.py), so the
hand-to-handle contact is the accepted sword contact. Every frame:

  * WPN_root = kukri grip frame (scale 100 like the rig), hand_r = grip relation * WPN_root;
  * the elbow is the point of the shoulder/wrist reach circle closest to the hand's natural forearm
    line, so the wrist stays near the accepted sword wrist; bone lengths are preserved exactly;
  * upper/lower arm keep their hinge frame (arm plane), the hand's axial rotation relative to the
    forearm goes to lowerarm_twist_01 (100 %) and lowerarm_twist_02 (50 %) per the V9 convention;
  * the left arm is solved the same way to a lowered wrist target outside the frame.
"""
import json
import math
from pathlib import Path

import numpy as np

from kmath import (T, Rig, load_dump, frame_local, qmul, qconj, qrot, qaxis, qnorm, qbetween,
                   qfrommat, qfromzx, qslerp, mesh_to_cam, cam_to_mesh)

P = Path(__file__).resolve().parent
VFOV = 75.0
ASPECT = 16 / 9
TAN = math.tan(math.radians(VFOV) / 2)

# Kukri mesh contract (cm, grip frame): see model.json.
MODEL = json.loads((P / 'model.json').read_text('utf-8')) if (P / 'model.json').exists() else {}
TIP = np.array(MODEL.get('tip_cm', [6.18, 0.0, 26.29]))
POMMEL = np.array([0.4, 0.0, -12.5])
PRESS_TURN = 70.0   # left palm normal: blade direction turned this far towards camera-right (two-handed thrust)
BLADE_BASE = np.array([0.0, 0.0, 7.5])
# Points along the cutting edge used for the hit sweep (grip frame, cm).
EDGE_SAMPLES = [np.array(v) for v in ([0.6, 0, 8.0], [1.4, 0, 12.0], [2.6, 0, 16.0], [4.0, 0, 20.0], [5.6, 0, 24.0], [6.18, 0, 26.29])]


def ndc(cam):
    x, y, z = cam
    if x <= 1e-3:
        return (float('nan'), float('nan'))
    return (y / (x * TAN * ASPECT), -z / (x * TAN))


def frame_mat(direction, normal):
    d = direction / np.linalg.norm(direction)
    n = normal - d * np.dot(normal, d)
    n = n / np.linalg.norm(n)
    return np.column_stack([d, n, np.cross(d, n)])


def twist_angle(q, axis):
    """Twist (radians) of rotation q about unit axis (swing-twist decomposition)."""
    v = np.array(q[1:])
    p = axis * np.dot(v, axis)
    t = np.array([q[0], *p])
    nrm = np.linalg.norm(t)
    if nrm < 1e-9:
        return 0.0
    t = t / nrm
    ang = 2 * math.atan2(np.dot(t[1:], axis), t[0])
    return (ang + math.pi) % (2 * math.pi) - math.pi


class KukriRig:
    def __init__(self, idle_frame=0):
        self.dump = load_dump()
        self.rig = Rig(self.dump)
        self.idle = self.dump['clips']['Idle']
        self.base_local = frame_local(self.rig, self.idle, idle_frame)
        self.base = self.rig.world(self.base_local)
        b = self.base
        wpn = b['WPN_root']
        # Grip frame on the sword hilt: hilt axis = WPN +Z, fist centre 7 cm below WPN_root,
        # edge = WPN +X (the user-confirmed TangDao edge side after its 180 degree flip).
        grip_local = T((0.0, 0.0, -0.070), (1, 0, 0, 0))
        self.grip_world = T(wpn.point(grip_local.p), wpn.q, (1, 1, 1))
        self.hand_rel = b['hand_r'].relative_to(self.grip_world)   # carries scale 100
        self.lengths = {}
        for s in 'lr':
            self.lengths[s] = (float(np.linalg.norm(b['lowerarm_' + s].p - b['upperarm_' + s].p)),
                               float(np.linalg.norm(b['hand_' + s].p - b['lowerarm_' + s].p)))
        # Natural forearm direction (elbow -> wrist) in each hand's local frame.
        self.forearm_local = {}
        for s in 'lr':
            h = b['hand_' + s]
            v = b['hand_' + s].p - b['lowerarm_' + s].p
            self.forearm_local[s] = qrot(qconj(h.q), v / np.linalg.norm(v))
        self.right_chain = self.rig.descendants('clavicle_r')
        self.left_chain = self.rig.descendants('clavicle_l')
        self.upper_desc = {s: self.rig.descendants('upperarm_' + s) for s in 'lr'}
        self.wpn_desc = self.rig.descendants('WPN_root')
        # Bind pose: the skin's zero for the forearm twist split (V9: twist_01 100 %, twist_02 50 %).
        self.ref_world = {n: T(np.array(v[0:3]), np.array(v[3:7]), np.array(v[7:10])) for n, v in self.dump['ref_world'].items()}
        self.ref_local = {n: T(np.array(v[0:3]), np.array(v[3:7]), np.array(v[7:10])) for n, v in self.dump['ref_local'].items()}
        self.twist_memory = {}

    def reset_twist_memory(self):
        self.twist_memory = {}

    # ------------------------------------------------------------------ helpers
    def kukri_frame(self, grip_cam, blade_cam, edge_cam):
        """Grip frame from camera-space grip centre, blade direction and edge hint."""
        z = cam_to_mesh(blade_cam)
        x = cam_to_mesh(edge_cam)
        return T(cam_to_mesh(grip_cam), qfromzx(z, x), (1, 1, 1))

    def rotate_chain(self, world, root, rot, pivot):
        """Rigidly rotate a bone subtree about a pivot (component space)."""
        for n in self.rig.descendants(root):
            w = world[n]
            world[n] = T(qrot(rot, w.p - pivot) + pivot, qmul(rot, w.q), w.s)

    def solve_arm(self, world, side, hand_world, pole_bias=None, pole_weight=0.0):
        """Two-bone solve keeping lengths; returns diagnostics. world is modified in place."""
        b = self.base
        up, lo, ha = 'upperarm_' + side, 'lowerarm_' + side, 'hand_' + side
        S = world[up].p.copy()
        W = hand_world.p.copy()
        Lu, Ll = self.lengths[side]
        D = float(np.linalg.norm(W - S))
        reach = D / (Lu + Ll)
        Dc = min(D, (Lu + Ll) * 0.999)
        n = (W - S) / D
        a = (Lu * Lu - Ll * Ll + Dc * Dc) / (2 * Dc)
        r = math.sqrt(max(Lu * Lu - a * a, 1e-6))
        C = S + n * a
        d_nat = qrot(hand_world.q, self.forearm_local[side])
        E_star = W - d_nat * Ll
        if pole_bias is not None and pole_weight > 0:
            E_star = E_star * (1 - pole_weight) + np.asarray(pole_bias) * pole_weight
        u = E_star - C
        u = u - n * np.dot(u, n)
        if np.linalg.norm(u) < 1e-6:
            u = np.cross(n, [0, 0, 1])
        u = u / np.linalg.norm(u)
        E = C + u * r
        if D > Dc:  # out of reach: the wrist lands short along the line
            W = S + n * Dc
        # Hinge frames.
        S0, E0, W0 = b[up].p, b[lo].p, b[ha].p
        n0 = np.cross(E0 - S0, W0 - E0)
        n1 = np.cross(E - S, W - E)
        Ru = frame_mat(E - S, n1) @ frame_mat(E0 - S0, n0).T
        Rl = frame_mat(W - E, n1) @ frame_mat(W0 - E0, n0).T
        qu = qmul(qfrommat(Ru), b[up].q)
        ql = qmul(qfrommat(Rl), b[lo].q)
        world[up] = T(S, qu, b[up].s)
        world[lo] = T(E, ql, b[lo].s)
        world[ha] = T(W, hand_world.q, b[ha].s)
        # Twist: hand rotation about the forearm relative to the BIND relation (the skin's zero),
        # unwrapped against the previous frame so a crossing of +-180 never flips the forearm.
        rel = qmul(qconj(ql), hand_world.q)
        rel_ref = qmul(qconj(self.ref_world[lo].q), self.ref_world[ha].q)
        delta = qmul(rel, qconj(rel_ref))                   # lowerarm-local delta from bind
        axis = qrot(qconj(ql), (W - E) / np.linalg.norm(W - E))
        theta = twist_angle(delta, axis)
        prev = self.twist_memory.get(side)
        if prev is not None:
            while theta - prev > math.pi:
                theta -= 2 * math.pi
            while theta - prev < -math.pi:
                theta += 2 * math.pi
        self.twist_memory[side] = theta
        # Humeral roll against bind (diagnostic: shoulder skin twist).
        cl = 'clavicle_' + side
        relu = qmul(qconj(world[cl].q), qu)
        relu_ref = qmul(qconj(self.ref_world[cl].q), self.ref_world[up].q)
        roll_u = twist_angle(qmul(relu, qconj(relu_ref)), qrot(qconj(world[cl].q), (E - S) / np.linalg.norm(E - S)))
        wrist = math.degrees(math.acos(max(-1, min(1, np.dot((W - E) / np.linalg.norm(W - E), d_nat)))))
        # Anatomical split in the hand frame: -X fingers, +Y palm, +Z thumb (right hand).
        f = qrot(qconj(hand_world.q), (W - E) / np.linalg.norm(W - E))
        ext = math.degrees(math.atan2(f[1], -f[0]))     # + extension (dorsiflexion)
        uln = math.degrees(math.atan2(f[2], -f[0]))     # + ulnar deviation
        # Anatomical forearm rotation: 0 = thumb up with palm medial (palm normal along the arm-plane
        # normal), + supination (palm towards the shoulder side), - pronation.  Camera coordinates.
        uc, fc = mesh_to_cam(E - S), mesh_to_cam(W - E)
        uc, fc = uc / np.linalg.norm(uc), fc / np.linalg.norm(fc)
        med = np.cross(uc, fc); med = med / max(np.linalg.norm(med), 1e-9)
        if side == 'l':
            med = -med
        up_side = -uc - fc * np.dot(-uc, fc); up_side = up_side / max(np.linalg.norm(up_side), 1e-9)
        palm = mesh_to_cam(qrot(hand_world.q, [0, 1, 0]))
        palm = palm - fc * np.dot(palm, fc)
        rho = math.degrees(math.atan2(np.dot(palm, up_side), np.dot(palm, med)))
        return dict(reach=reach, wrist_deg=wrist, twist_deg=math.degrees(theta), elbow=E, axis=axis, theta=theta,
                    ext=ext, uln=uln, rho=rho, roll_u=math.degrees(roll_u))

    def finish_children(self, world, local_base, side, diag):
        """Rebuild descendants of the arm from anchor locals, then apply forearm twist split."""
        lo = 'lowerarm_' + side
        rig = self.rig
        fixed = {'upperarm_' + side, lo, 'hand_' + side}
        for n, par in zip(rig.names, rig.parents):
            if n in fixed or par is None:
                continue
            if n in self.upper_desc[side] and n not in fixed:
                world[n] = local_base[n] * world[par]
        axis, theta = diag['axis'], diag['theta']
        for twist, frac in (('lowerarm_twist_01_' + side, 1.0), ('lowerarm_twist_02_' + side, 0.5)):
            ref = self.ref_local[twist]
            loc = T(local_base[twist].p, qmul(qaxis(axis, theta * frac), ref.q), local_base[twist].s)
            world[twist] = loc * world[lo]

    def clavicle_rotation(self, ang):
        return qnorm(qmul(qaxis(cam_to_mesh((0, 0, 1)), math.radians(ang[2])),
                     qmul(qaxis(cam_to_mesh((0, 1, 0)), math.radians(ang[1])),
                          qaxis(cam_to_mesh((1, 0, 0)), math.radians(ang[0])))))

    def arm_to_kukri(self, wrist_cam, elbow_hint_cam, psi=0.0, d_ext=0.0, d_uln=0.0, clav_r=(0, 0, 0)):
        """Arm-centric design: wrist position, elbow swivel hint, forearm roll psi (deg, about the
        elbow->wrist axis) and wrist deltas relative to the accepted sword wrist (ext 14.7, uln 15.1).
        Returns (K grip frame, elbow point) with the elbow exactly on the reach circle."""
        b = self.base
        S = b['upperarm_r'].p.copy()
        if any(clav_r):
            piv = b['clavicle_r'].p
            S = qrot(self.clavicle_rotation(clav_r), S - piv) + piv
        W = cam_to_mesh(wrist_cam)
        Lu, Ll = self.lengths['r']
        D = float(np.linalg.norm(W - S))
        Dc = min(D, (Lu + Ll) * 0.995)
        n = (W - S) / D
        if D > Dc:
            W = S + n * Dc
        a = (Lu * Lu - Ll * Ll + Dc * Dc) / (2 * Dc)
        r = math.sqrt(max(Lu * Lu - a * a, 1e-6))
        C = S + n * a
        u = cam_to_mesh(elbow_hint_cam) - C
        u = u - n * np.dot(u, n)
        u = u / np.linalg.norm(u)
        E = C + u * r
        S0, E0, W0 = b['upperarm_r'].p, b['lowerarm_r'].p, b['hand_r'].p
        n0 = np.cross(E0 - S0, W0 - E0)
        n1 = np.cross(E - S, W - E)
        Rl = frame_mat(W - E, n1) @ frame_mat(W0 - E0, n0).T
        ql = qmul(qfrommat(Rl), b['lowerarm_r'].q)
        rel0 = qmul(qconj(b['lowerarm_r'].q), b['hand_r'].q)
        qh = qmul(ql, rel0)
        f = (W - E) / np.linalg.norm(W - E)
        qh = qmul(qaxis(f, math.radians(psi)), qh)
        qh = qmul(qh, qmul(qaxis([0, 0, 1], math.radians(d_ext)), qaxis([0, 1, 0], math.radians(-d_uln))))
        hand = T(W, qh, b['hand_r'].s)
        K = self.hand_rel.inverse() * hand
        K = T(K.p, K.q, (1, 1, 1))
        if getattr(self, '_want_diag', False):
            Ru = frame_mat(E - S, n1) @ frame_mat(E0 - S0, n0).T
            qu = qmul(qfrommat(Ru), b['upperarm_r'].q)
            rel_ref = qmul(qconj(self.ref_world['lowerarm_r'].q), self.ref_world['hand_r'].q)
            theta = twist_angle(qmul(qmul(qconj(ql), qh), qconj(rel_ref)), qrot(qconj(ql), f))
            prev = self._diag_prev_theta
            if prev is not None:
                while theta - prev > math.pi:
                    theta -= 2 * math.pi
                while theta - prev < -math.pi:
                    theta += 2 * math.pi
            fh = qrot(qconj(qh), f)
            qcl = qmul(self.clavicle_rotation(clav_r), b['clavicle_r'].q) if any(clav_r) else b['clavicle_r'].q
            relu = qmul(qconj(qcl), qu)
            relu_ref = qmul(qconj(self.ref_world['clavicle_r'].q), self.ref_world['upperarm_r'].q)
            roll_u = twist_angle(qmul(relu, qconj(relu_ref)), qrot(qconj(qcl), (E - S) / np.linalg.norm(E - S)))
            self.last_diag = dict(theta=theta, ext=math.degrees(math.atan2(fh[1], -fh[0])),
                                  uln=math.degrees(math.atan2(fh[2], -fh[0])), roll_u=math.degrees(roll_u),
                                  reach=D / (Lu + Ll), W=W, S=S)
        return K, E

    def arm_eval(self, wrist_cam, elbow_hint_cam, psi, d_ext, d_uln, clav_r, prev_theta=None):
        """arm_to_kukri plus cheap right-arm diagnostics (no full-rig pose)."""
        self._want_diag = True
        self._diag_prev_theta = prev_theta
        try:
            K, E = self.arm_to_kukri(wrist_cam, elbow_hint_cam, psi, d_ext, d_uln, clav_r)
        finally:
            self._want_diag = False
        return K, E, self.last_diag

    # ------------------------------------------------------------------ pose
    def left_press_hand(self, K):
        """Left hand pressing its palm on the pommel (third hit, two-handed thrust).
        Left hand axes (bind, mirrored from the right): +X fingers, -Y palm, -Z thumb.
        V10 (user: "the left arm is twisted"): a palm pushing straight along the blade needs the left forearm
        pronated 100-134 deg against bind (V8: fingers across to the right) -- the skin wrung at the wrist.
        The palm now meets the pommel end from the back-left: its normal is the blade direction turned 70 deg
        towards camera-right (PRESS_TURN), fingers forward-up around the bottom of the right fist, thumb on top.
        That is close to the left forearm's neutral handshake roll: worst visible twist ~57 deg, wrist <= 16 deg
        (searched over palm turn 0-90 deg and six finger directions, Work/_press_search in the V10 notes)."""
        o = cam_to_mesh((0.0, 0.0, 0.0))
        nb = qrot(K.q, [0, 0, 1])
        right = cam_to_mesh((0.0, 1.0, 0.0)) - o
        right = right - nb * np.dot(right, nb)
        right = right / np.linalg.norm(right)
        turn = math.radians(PRESS_TURN)
        n = nb * math.cos(turn) + right * math.sin(turn)            # palm push direction (mesh)
        n = n / np.linalg.norm(n)
        up = cam_to_mesh((0.7, 0.0, 0.7)) - o
        f = up - n * np.dot(up, n)
        f = f / np.linalg.norm(f)
        y = -n
        z = np.cross(f, y)
        q = qfrommat(np.column_stack([f, y, z]))
        palm_target = K.point(POMMEL) - n * 1.2
        palm_local = np.array([5.0, -2.2, 0.3])                    # palm centre in hand_l space (cm)
        p = palm_target - qrot(q, palm_local)
        return T(p, q, self.base['hand_l'].s)

    def pose(self, K, left_target_cam=(18.0, -24.0, -62.0), clav_r=(0, 0, 0), clav_l=(0, 0, 0),
             pole_r=None, pole_r_weight=0.0, body_local=None, left_press=0.0):
        """K: kukri grip frame in mesh space (T, unit scale). Returns (world, diagnostics).
        left_press 0..1 blends the left hand from its lowered rest onto the pommel (two-handed thrust)."""
        local = {n: t.copy() for n, t in (body_local or self.base_local).items()}
        world = self.rig.world(local)
        # Clavicle adjustments (degrees about camera axes: fwd, right, up) around each clavicle head.
        for side, ang in (('r', clav_r), ('l', clav_l)):
            if any(ang):
                rot = qnorm(qmul(qaxis(cam_to_mesh((0, 0, 1)), math.radians(ang[2])),
                            qmul(qaxis(cam_to_mesh((0, 1, 0)), math.radians(ang[1])),
                                 qaxis(cam_to_mesh((1, 0, 0)), math.radians(ang[0])))))
                self.rotate_chain(world, 'clavicle_' + side, rot, world['clavicle_' + side].p.copy())
        hand_r = self.hand_rel * K
        dr = self.solve_arm(world, 'r', hand_r, pole_r, pole_r_weight)
        self.finish_children(world, local, 'r', dr)
        # Left: lowered, relaxed; hand keeps the anchor wrist relative to its forearm.
        tgt = cam_to_mesh(left_target_cam)
        b = self.base
        S = world['upperarm_l'].p
        Lu, Ll = self.lengths['l']
        # Choose a hand orientation that keeps the anchor forearm/hand relation for a hanging arm:
        # forearm points mostly down/forward; rotate the anchor hand by the lowerarm swing.
        provisional = T(tgt, b['hand_l'].q, b['hand_l'].s)
        E_guess = S + (tgt - S) * 0.5 + cam_to_mesh((-4.0, -6.0, 0.0))
        Rl = qbetween(b['hand_l'].p - b['lowerarm_l'].p, tgt - E_guess)
        provisional = T(tgt, qmul(Rl, b['hand_l'].q), b['hand_l'].s)
        pole_l = E_guess
        pole_w = 0.7
        if left_press > 1e-4:
            w = min(1.0, float(left_press))
            w = w * w * (3 - 2 * w)
            press = self.left_press_hand(K)
            # Only the position travels; the hand takes the press orientation as soon as it starts moving
            # (it is below the frame then).  Slerping from the hanging hand rolled the forearm the long way
            # round (+280 deg) on the way up and back.
            provisional = T(provisional.p * (1 - w) + press.p * w, press.q, b['hand_l'].s)
            # Press elbow: down, out to the left and a little behind the hand.
            pole_press = press.p + cam_to_mesh((-6.0, -20.0, -8.0)) - cam_to_mesh((0.0, 0.0, 0.0))
            pole_l = E_guess * (1 - w) + pole_press * w
            # On the pommel the elbow follows the hand's own forearm line (straight wrist, forearm across the
            # chest under the right fist); the pole only breaks ties.
            pole_w = 0.7 * (1 - w) + 0.15 * w
        # Left twist uses its principal value (no unwrap memory): the pommel press sits near -100 deg and the
        # only +-180 crossing happens while the hand travels below the frame; unwrapping would carry +260 and
        # feed twist_02 the wrong half angle.
        self.twist_memory.pop('l', None)
        dl = self.solve_arm(world, 'l', provisional, pole_bias=pole_l, pole_weight=pole_w)
        self.finish_children(world, local, 'l', dl)
        if left_press > 1e-4:
            # Open the left fingers towards the flat bind hand so the PALM, not a fist, meets the pommel.
            a = 0.8 * w
            hand_desc = self.rig.descendants('hand_l')
            for n, par in zip(self.rig.names, self.rig.parents):
                if n == 'hand_l' or n not in hand_desc or par is None or n.startswith('ik_'):
                    continue
                lb, lr = local[n], self.ref_local[n]
                qr = lr.q if np.dot(lb.q, lr.q) >= 0 else -lr.q
                world[n] = T(lb.p, qslerp(lb.q, qr, a), lb.s) * world[par]
        # Weapon chain: WPN_root is the grip frame (scale 100 like the rest of the rig).
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for n in self.wpn_desc:
            if n == 'WPN_root':
                continue
            par = self.rig.parents[self.rig.index[n]]
            world[n] = local[n] * world[par]
        world['Blade_Base'] = T(K.point(BLADE_BASE), K.q, b['Blade_Base'].s)
        world['Blade_Tip'] = T(K.point(TIP), K.q, b['Blade_Tip'].s)
        # ik_hand helpers follow the hands (kept for any consumer of the IK bones).
        for s in 'lr':
            ik = 'ik_hand_' + s
            if ik in world:
                rel = b[ik].relative_to(b['hand_' + s])
                world[ik] = rel * world['hand_' + s]
        diag = dict(right=dr, left=dl)
        diag['tip_ndc'] = ndc(mesh_to_cam(K.point(TIP)))
        diag['pommel_ndc'] = ndc(mesh_to_cam(K.point(POMMEL)))
        diag['grip_ndc'] = ndc(mesh_to_cam(K.p))
        diag['elbow_ndc'] = ndc(mesh_to_cam(dr['elbow']))
        diag['left_hand_ndc'] = ndc(mesh_to_cam(world['hand_l'].p))
        diag['tip_cam'] = mesh_to_cam(K.point(TIP))
        return world, diag

    def local_keys(self, world, previous=None):
        loc = self.rig.localize(world)
        out = {}
        for n in self.rig.names:
            t = loc[n]
            q = t.q.copy()
            if previous is not None and n in previous and np.dot(q, previous[n]) < 0:
                q = -q
            out[n] = (t.p, q, t.s)
        return out


def fmt(d):
    r, l = d['right'], d['left']
    return ("reach %.2f wrist %5.1f (ext %5.1f uln %5.1f) twist %6.1f | L reach %.2f wrist %4.1f | tip %s pommel %s grip %s elbow %s lhand %s" % (
        r['reach'], r['wrist_deg'], r['ext'], r['uln'], r['twist_deg'], l['reach'], l['wrist_deg'],
        tuple(round(v, 2) for v in d['tip_ndc']), tuple(round(v, 2) for v in d['pommel_ndc']),
        tuple(round(v, 2) for v in d['grip_ndc']), tuple(round(v, 2) for v in d['elbow_ndc']),
        tuple(round(v, 2) for v in d['left_hand_ndc'])))

