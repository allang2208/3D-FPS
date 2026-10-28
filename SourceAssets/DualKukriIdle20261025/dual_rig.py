"""Dual kukri (one in each hand) on the shared sword arms skeleton.

Right arm: the accepted single-kukri solver (Kukri20261020/kukri_rig.py, arm_to_kukri) with the accepted
sword hammer fist on the hilt.
Left arm: the same solver in mirrored space.  The skeleton is left/right symmetric (bind check: every
*_l bone = Rot_X(180) * mirror(*_r), positions within 0.6 cm), so a "virtual right arm" is solved for the
mirrored left targets and its world rotations are mirrored onto the left chain.  The left fist is the exact
mirror image of the accepted right fist, and the left kukri is the mirror of the right kukri about its blade
plane (flip of the grip-frame Y axis; the mesh is symmetric to 0.13 cm), so the hand/handle contact is the
accepted one on both sides.  Left bone translations stay the skeleton's own; since every left rotation is
mirrored, the whole left arm is the ideal mirror shifted by the constant clavicle-root offset of the base
pose (LEFT_SHIFT, < 1 cm).

Camera space: +X forward, +Y right, +Z up (cm).  Arm parameters per side:
  W (wrist, camera cm), phi (elbow swivel about shoulder->wrist, deg; 0 = elbow straight down, + = outward),
  psi (forearm roll, deg), de / du (wrist ext / ulnar deltas vs the accepted sword wrist), C (clavicle deg).
Left parameters are given in the mirrored (virtual right) space.
"""
import math
import sys
from pathlib import Path

import numpy as np

P = Path(__file__).resolve().parent
KUKRI = P.parent / 'Kukri20261020'
sys.path.insert(0, str(KUKRI))

from kukri_rig import KukriRig, ndc, TIP, POMMEL, BLADE_BASE  # noqa: E402,F401
from kmath import T, qmat, qrot, qmul, qaxis, qfrommat, mesh_to_cam  # noqa: E402

F = np.diag([-1.0, 1.0, 1.0])          # mesh mirror (camera right = mesh +X)
ROT_X180 = np.diag([1.0, -1.0, -1.0])  # left bone frame = ROT_X180 @ right bone frame (checked on bind)
FY = np.diag([1.0, -1.0, 1.0])         # kukri mirror about its blade plane


def elbow_hint(S_cam, W_cam, phi):
    """A point on the elbow side of the shoulder->wrist line for arm_to_kukri (camera cm)."""
    S, W = np.asarray(S_cam, float), np.asarray(W_cam, float)
    n = (W - S) / np.linalg.norm(W - S)
    d0 = np.array([0.0, 0.0, -1.0]) + n * n[2]
    d0 = d0 / np.linalg.norm(d0)
    d1 = np.cross(n, d0)
    if d1[1] < 0:   # + phi swings the elbow outward (camera right for a right arm)
        d1 = -d1
    a = math.radians(phi)
    return (S + W) * 0.5 + 25.0 * (d0 * math.cos(a) + d1 * math.sin(a))


class DualRig:
    def __init__(self):
        self.R = KukriRig()
        rig = self.R.rig
        b = self.R.base
        self.left_chain = [n for n in rig.names if n in self.R.left_chain]
        self.parent = dict(zip(rig.names, rig.parents))
        self.left_shift = b['clavicle_l'].p - F @ b['clavicle_r'].p   # mesh cm

    def shoulder(self, C=(0.0, 0.0, 0.0)):
        b = self.R.base
        S = b['upperarm_r'].p
        if any(C):
            piv = b['clavicle_r'].p
            S = qrot(self.R.clavicle_rotation(C), S - piv) + piv
        return S

    def arm(self, prm, prev_theta=None):
        """Right-arm solve (in that arm's own camera space).  Returns K (grip frame, mesh), elbow (mesh), diag.
        prm['flip'] 'x' / 'y' turns the kukri 180 deg in the fist about its grip-frame axis (reverse grip: the blade
        leaves the little-finger side; 'x' keeps the edge on the knuckle side, 'y' turns it to the palm).  The fist is
        unchanged; diag['K_hand'] is the unflipped frame the hand is solved on."""
        C = tuple(prm.get('C', (0.0, 0.0, 0.0)))
        hint = elbow_hint(mesh_to_cam(self.shoulder(C)), prm['W'], prm['phi'])
        K, E, d = self.R.arm_eval(tuple(prm['W']), tuple(hint), prm['psi'], prm['de'], prm['du'], C, prev_theta)
        d['K_hand'] = K
        flip = prm.get('flip')
        if flip:
            K = T(K.p, qmul(K.q, qaxis((1, 0, 0) if flip == 'x' else (0, 1, 0), math.pi)), (1, 1, 1))
        return K, E, d

    def set_weapon(self, world, K):
        """WPN_root chain and blade markers on kukri frame K (R.pose places them on the hand's unflipped frame)."""
        R = self.R
        b, local = R.base, R.base_local
        world['WPN_root'] = T(K.p, K.q, b['WPN_root'].s)
        for n in R.rig.names:
            if n in R.wpn_desc and n != 'WPN_root':
                world[n] = local[n] * world[self.parent[n]]
        world['Blade_Base'] = T(K.point(BLADE_BASE), K.q, b['Blade_Base'].s)
        world['Blade_Tip'] = T(K.point(TIP), K.q, b['Blade_Tip'].s)

    def to_left(self, p_mesh):
        """Virtual-right point (mesh) -> actual left point (mesh)."""
        return F @ np.asarray(p_mesh, float) + self.left_shift

    def left_kukri(self, Kv):
        return T(self.to_left(Kv.p), qfrommat(F @ qmat(Kv.q) @ FY), (1, 1, 1))

    def pose(self, right, left):
        """right / left: parameter dicts (left in mirrored space).  Returns (world, K_right, K_left, info)."""
        R = self.R
        Kv, Ev, dv = self.arm(left)
        world_v, _ = R.pose(dv['K_hand'], clav_r=tuple(left.get('C', (0, 0, 0))), pole_r=Ev, pole_r_weight=1.0)
        Kr, Er, dr = self.arm(right)
        world, _ = R.pose(dr['K_hand'], clav_r=tuple(right.get('C', (0, 0, 0))), pole_r=Er, pole_r_weight=1.0)
        self.set_weapon(world, Kr)
        local = R.base_local
        for n in self.left_chain:
            src = world_v[n[:-2] + '_r']
            par = self.parent[n]
            world[n] = T(world[par].point(local[n].p), qfrommat(ROT_X180 @ qmat(src.q)), src.s)
        b = R.base
        world['ik_hand_l'] = b['ik_hand_l'].relative_to(b['hand_l']) * world['hand_l']
        K_l = self.left_kukri(Kv)
        err = float(np.linalg.norm(world['hand_l'].p - self.to_left(world_v['hand_r'].p)))
        return world, Kr, K_l, dict(right=dr, left_virtual=dv, left_hand_err_cm=err)
