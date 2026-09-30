"""LMG201 cloth-pouch reload, ClothReload44.

Rebuilt from the user's Delta Force reference (22.36.59.03.mp4) instead of the
mirrored PKM chain used by ClothFeed33.  Everything is authored as world/prop
targets and solved per frame:

* gun: small camera-space hold pose plus decaying contact impulses, pivoting on
  the right-hand grip; the right hand keeps its idle grip (two-bone solve).
* left hand: contact keys attached to the part being handled (gun, cover, old
  pouch, new pouch).  Arm solved with a fixed clavicle, an explicit elbow pole
  and the accepted Skin07 forearm stations, so bone lengths are exact and the
  elbow cap keeps the idle roll.
* props: cover about its own hinge bone, pouches as rigid bodies, the short
  visible belt as a 6-segment chain from the pouch mouth.

python -X utf8 author_motion.py [family ...]
"""
import sys, json, gzip
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE / 'Diagnostics')]
import diag_lib as D
import rig as K
from rig import unit, rot, compose, ease, ease_in, ease_out, axis_angle, slerp_R, palm_frame

C33 = D.L201 / 'ClothFeed33'
NAMES, PARENT, REST = D.NAMES, D.PARENT, D.REST
BI = D.BI
FPS, DURATION = 120, 6.2
RIGHT_ROOT_BACK = np.array([0.0, 3.0, 0.0])
POLE_SMOOTH = 0.07  # s, Gaussian sigma for the left elbow swivel
BEND_MAX = 66.0  # deg, PKM ArmJoint49 accepted left wrist axis bend
PINCH_CELL = (0.8, 0.6, 0.4)  # cm along fingers / palmar / across: held belt cell vs the pinch point
CONTACT_BEND = 22.0  # deg, wrist axis bend on contact keys (reference: forearm level, palm flat)
TRANSIT_BEND = 45.0  # deg, between contacts
CENTER = np.radians(-25.0)  # middle of the usable absolute forearm roll; idle underhand support is ~15
COUNT = round(DURATION * FPS) + 1
inputs = json.loads((C33 / 'inputs.json').read_text())

# ------------------------------------------------------------------ timeline
T = dict(release=.52, lift=.74, reach=.98, hook=1.10, cover_open=1.12, lift_end=1.33, let_go=1.46,
         tray=1.60, tray_pull=1.74, box_grab=2.00, box_out=2.10, old_hidden=2.45, new_visible=2.80,
         box_seat=3.35, box_release=3.62, belt_grab=3.82, belt_top=4.38, belt_seat=4.78,
         belt_release=4.88, cover_reach=4.98, cover_pull=5.13, cover_close=5.22, press_end=5.34,
         return_start=5.45, grip=5.80, duration=DURATION, belt_fade=4.55)
# Empty reload: no spent belt in the tray, so the hand goes from the lid straight to the
# pouch (no tray/tray_pull) and the remaining actions spread over the same 6.2 s.
EMPTY_KNOTS = ((1.46, 1.46), (2.00, 1.80), (5.45, 5.46), (DURATION, DURATION))


def empty_time(t):
    if t <= EMPTY_KNOTS[0][0]:
        return t
    for (a, ea), (b, eb) in zip(EMPTY_KNOTS, EMPTY_KNOTS[1:]):
        if t <= b:
            return ea + (t - a) * (eb - ea) / (b - a)
    return t


T_NORMAL = dict(T)
T_EMPTY = {k: empty_time(v) for k, v in T.items()}


INPUTS44 = json.loads((HERE / 'inputs.json').read_text()) if (HERE / 'inputs.json').exists() else None
if INPUTS44:
    # current idles are re-read from UE before authoring; the skeleton must be unchanged
    ref = inputs['meshes']['201']
    assert INPUTS44['mesh']['names'] == ref['names'] and INPUTS44['mesh']['parents'] == ref['parents'], 'skeleton changed'
    assert np.abs(np.array(INPUTS44['mesh']['rest'])[:, :3] - np.array(ref['rest'])[:, :3]).max() < 1e-3, 'rest changed'


def load_pose(key):
    if INPUTS44 and key in INPUTS44['clips']:
        return json.loads(Path(INPUTS44['clips'][key]['file']).read_text())
    return json.loads(Path(inputs['clips'][key]['file']).read_text())


def world_of(local_rows):
    W = np.zeros((len(NAMES), 4, 4))
    for i, v in enumerate(local_rows):
        m = K.mat(v)
        W[i] = W[PARENT[i]] @ m if PARENT[i] >= 0 else m
    return W


def subtree(root):
    out = [BI[root]]
    for i in range(len(NAMES)):
        if PARENT[i] in out and i not in out:
            out.append(i)
    return out


FINGERS_L = [i for i in subtree('hand_l') if NAMES[i] != 'hand_l']
FINGERS_R = [i for i in subtree('hand_r') if NAMES[i] != 'hand_r']
WPN = subtree('WPN_root')

# ------------------------------------------------------------------ hand shapes
pk = inputs['meshes']['pkm']
pk_names = pk['names']
pk_parent = pk['parents']
pk_rest = np.array([K.mat(v) for v in pk['rest']])
pkm = load_pose('pkm_reload_empty')['poses']


def pkm_world(frame):
    rows = pkm[frame]
    W = np.zeros((len(pk_names), 4, 4))
    for i, v in enumerate(rows):
        m = K.mat(v)
        W[i] = W[pk_parent[i]] @ m if pk_parent[i] >= 0 else m
    return W


MIRROR = np.diag([-1.0, 1, 1, 1])


def shape_from_pkm(t, side):
    """Finger locals for the 201 left hand from a PKM frame (direct or mirrored)."""
    Wp = pkm_world(int(round(t * 120)))
    out = {}
    if side == 'l':
        for i in FINGERS_L:
            n = NAMES[i]
            j, pj = pk_names.index(n), pk_names.index(NAMES[PARENT[i]])
            out[i] = np.linalg.inv(Wp[pj]) @ Wp[j]
    else:
        Wm = {}
        for i in [BI['hand_l']] + FINGERS_L:
            n = NAMES[i]
            j = pk_names.index(n[:-2] + '_r')
            Wm[i] = MIRROR @ Wp[j] @ np.linalg.inv(pk_rest[j]) @ MIRROR @ REST[i]
        for i in FINGERS_L:
            out[i] = np.linalg.inv(Wm[PARENT[i]]) @ Wm[i]
    return out


def slerp_vec(a, b, u):
    """Spherical interpolation of elbow pole directions (no collapse through zero)."""
    a, b = unit(np.asarray(a, float)), unit(np.asarray(b, float))
    w = np.arccos(np.clip(a @ b, -1, 1))
    if w < 1e-6:
        return a
    return unit((np.sin((1 - u) * w) * a + np.sin(u * w) * b) / np.sin(w))


def pkm_rot(t, side):
    """Left-hand world rotation of the PKM reload_empty hand at t (gun motion removed;
    right hand mirrored). PKM and 201 share arm rest and idle gun axes."""
    Wp, Wp0 = pkm_world(int(round(t * 120))), pkm_world(0)
    iw, j = pk_names.index('WPN_root'), pk_names.index('hand_' + side)
    H = Wp0[iw] @ np.linalg.inv(Wp[iw]) @ Wp[j]
    if side == 'r':
        H = MIRROR @ H @ np.linalg.inv(pk_rest[j]) @ MIRROR @ REST[BI['hand_l']]
    return K.rot(H)


SHAPES = {'hook': shape_from_pkm(.60, 'l'), 'open': shape_from_pkm(1.20, 'l'),
          'box': shape_from_pkm(1.90, 'r'), 'spread': shape_from_pkm(2.60, 'r'),
          'pinch': shape_from_pkm(4.00, 'r'), 'flat': shape_from_pkm(4.60, 'r')}


def shape_mix(a, b, u):
    if u <= 0:
        return a
    if u >= 1:
        return b
    out = {}
    for i in a:
        va, vb = K.pack(a[i]), K.pack(b[i])
        R = slerp_R(K.rot(a[i]), K.rot(b[i]), u)
        out[i] = compose(R, va[:3] * (1 - u) + vb[:3] * u, s=1.0)
    return out


def hand_fk(shape, fingers=FINGERS_L, hand='hand_l'):
    """Finger bone positions in hand-local cm (hand at identity, unit scale)."""
    H = np.eye(4)
    H[:3, :3] *= K.UNIT
    Wl = {BI[hand]: H}
    for i in fingers:
        Wl[i] = Wl[PARENT[i]] @ shape[i]
    return {NAMES[i]: Wl[i][:3, 3] for i in Wl}


def hand_point(M, lm):
    """World point of a hand-local cm landmark; M carries the bone scale, so use R|t only."""
    return K.rot(M) @ lm + M[:3, 3]


def landmark(shape, name):
    p = hand_fk(shape)
    tip = lambda f: p[f + '_03_l'] + .75 * (p[f + '_03_l'] - p[f + '_02_l'])
    if name == 'palm':
        return .44 * p['hand_l'] + .56 * p['middle_01_l']
    if name == 'pinch':
        return .5 * (tip('thumb') + tip('index'))
    if name == 'pinchcell':
        return .5 * (tip('thumb') + tip('index')) + PINCH_CELL[0] * F_LOC + PINCH_CELL[1] * P_LOC + PINCH_CELL[2] * ACROSS
    if name == 'hook':
        return .5 * (p['middle_02_l'] + p['ring_02_l'])
    if name == 'pads':
        return (tip('index') + tip('middle') + tip('ring')) / 3
    raise KeyError(name)


# hand-local palm reference frame (constant across shapes: metacarpal/knuckle rest)
_rh = np.linalg.inv(REST[BI['hand_l']])
_pl = lambda n: (_rh @ REST[BI[n]])[:3, 3]
F_LOC = unit(_pl('middle_01_l'))
ACROSS = unit(_pl('index_01_l') - _pl('pinky_01_l'))
P_LOC = unit(np.cross(ACROSS, F_LOC))
B_LOC = palm_frame(F_LOC, P_LOC)


def hand_rot(finger_dir, palmar):
    return palm_frame(finger_dir, palmar) @ B_LOC.T


# ------------------------------------------------------------------ gun motion
def gun_offset(t):
    """(translation cm, rotvec rad) in component space about the right grip."""
    hold = ease(t / .70) * (1 - ease((t - T['return_start']) / (T['grip'] + .10 - T['return_start'])))
    tr = np.array([-1.0, 2.0, -0.8]) * hold
    rv = np.array([np.radians(2.0), np.radians(6.5), np.radians(-1.5)]) * hold
    def kick(t0, dz, pitch, tau=.16, f=9.0):
        if t < t0:
            return 0.0, 0.0
        x = t - t0
        k = np.exp(-x / tau) * np.sin(2 * np.pi * f * x + np.pi / 2) * min(1, x / .02)
        return dz * k, pitch * k
    for t0, dz, pitch in ((T['cover_open'], .30, .7), (T['box_out'], -.35, -.4), (T['box_seat'], .45, .8),
                          (T['belt_seat'], -.18, -.3), (T['cover_close'], -.55, -1.1)):
        a, b = kick(t0, dz, pitch)
        tr = tr + np.array([0, 0, a])
        rv = rv + np.array([np.radians(b), 0, 0])
    return tr, rv


def gun_rel(t, pivot):
    tr, rv = gun_offset(t)
    G = np.eye(4)
    G[:3, :3] = K.Rot.from_rotvec(rv).as_matrix()
    G[:3, 3] = pivot + tr - G[:3, :3] @ pivot
    return G


# ------------------------------------------------------------------ cover
COVER_MAX = 86.0


def cover_angle(t):
    if t < T['hook']:
        return 0.0
    if t < T['lift_end']:
        return 60 * ease((t - T['hook']) / (T['lift_end'] - T['hook']))
    if t < T['lift_end'] + .10:
        return 60 + 31 * ease_out((t - T['lift_end']) / .10)
    if t < T['lift_end'] + .24:
        return 91 - (91 - COVER_MAX) * ease((t - T['lift_end'] - .10) / .14)
    if t < T['cover_reach']:
        return COVER_MAX
    if t < T['cover_pull']:
        return COVER_MAX - (COVER_MAX - 40) * ease((t - T['cover_reach']) / (T['cover_pull'] - T['cover_reach']))
    if t < T['cover_close']:
        return 40 * (1 - ease_in((t - T['cover_pull']) / (T['cover_close'] - T['cover_pull'])))
    return 0.0


# ------------------------------------------------------------------ pouches
def box_path(t, which):
    """Rigid offset (gun-idle frame) of the old/new pouch: translation, rotvec."""
    down = np.array([0, 0, -2.5])
    away = np.array([-9.0, 7.0, -15.0])
    tilt = np.array([0, np.radians(-20), 0])
    def at(u1, u2):
        return down * u1 + away * u2, tilt * u2
    if which == 'old':
        if t < T['box_grab']:
            return at(0, 0)
        u1 = ease((t - T['box_grab']) / (T['box_out'] + .05 - T['box_grab']))
        u2 = ease((t - T['box_out'] - .04) / (T['old_hidden'] - T['box_out'] - .04))
        return at(u1, u2)
    if t < T['new_visible']:
        return at(1, 1)
    u2 = 1 - ease((t - T['new_visible']) / (T['box_seat'] - .13 - T['new_visible']))
    u1 = 1 - ease((t - (T['box_seat'] - .13)) / .13)
    return at(u1, u2)


# ------------------------------------------------------------------ belt chain
BODY = D.Body()


BELT49 = np.load(HERE / 'Inputs' / 'belt49_cells.npz')


class Belt:
    """Six belt cells, 0 at the tray .. 5 at the pouch mouth.  Cell points are the
    points the runtime belt physics uses (LMG201BeltDynamics: Belt49 cell centroids
    in each bone's rest frame, NewCenters for the new belt), and the chain keeps
    their idle chord lengths, which is what FPKMSoftChain holds fixed."""

    def __init__(self, W_idle, prefix):
        self.ids = [BI[prefix + 'LMG201_Belt_%02d' % k] for k in range(6)]
        self.c = []
        for k, i in enumerate(self.ids):
            cr = BELT49['pos'][BELT49['cell'] == 'LMG201_Belt_%02d' % k].mean(0)
            self.c.append((W_idle[i] @ D.REST_INV[i] @ np.r_[cr, 1])[:3])
        self.c = np.array(self.c)
        self.gap = np.linalg.norm(np.diff(self.c, axis=0), axis=1)
        self.L = self.gap.sum()
        self.tan0 = [unit(self.c[max(k - 1, 0)] - self.c[min(k + 1, 5)]) for k in range(6)]
        self.W_idle = {i: W_idle[i].copy() for i in self.ids}
        self.s_prev = None

    def relax(self, pts, iters=40):
        """Restore idle chord lengths with both ends fixed (same sweep as the runtime)."""
        pts = np.array(pts, float)
        for it in range(iters):
            for j in range(5):
                k = 4 - j if it % 2 else j
                wa, wb = (0. if k == 0 else 1.), (0. if k + 1 == 5 else 1.)
                dl = pts[k + 1] - pts[k]
                dist = np.linalg.norm(dl)
                if wa + wb == 0 or dist < 1e-9:
                    continue
                c = dl * ((dist - self.gap[k]) / (dist * (wa + wb)))
                pts[k] += c * wa
                pts[k + 1] -= c * wb
        return pts

    def chain(self, anchor, end, sag_dir):
        """Cells from the mouth anchor (5) to the held end (0) on a sagging curve,
        spaced by the idle chord lengths; the sag side is kept continuous in time."""
        d = end - anchor
        dist = np.linalg.norm(d)
        if dist >= self.L * .998:
            end = anchor + d / dist * self.L * .998
            d, dist = end - anchor, self.L * .998
        dn = d / dist
        raw = np.asarray(sag_dir, float) - dn * np.dot(sag_dir, dn)
        if self.s_prev is None:
            s = unit(raw) if np.linalg.norm(raw) > 1e-6 else unit(np.cross(dn, [0, 1, 0]))
        else:
            sp = self.s_prev - dn * np.dot(self.s_prev, dn)
            sp = unit(sp) if np.linalg.norm(sp) > 1e-6 else unit(raw)
            tgt = unit(raw) if np.linalg.norm(raw) > .05 else sp
            ang = np.arccos(np.clip(np.dot(sp, tgt), -1, 1))
            step = min(ang, np.radians(3.0))  # per 1/120 s: the bulge side turns, never flips
            ax = np.cross(sp, tgt)
            s = K.axis_angle(unit(ax), step) @ sp if np.linalg.norm(ax) > 1e-9 and step > 0 else sp
            s = unit(s - dn * np.dot(s, dn))
        self.s_prev = s
        u = np.linspace(0, 1, 401)

        def walk(sig):
            Kp = .5 * (anchor + end) + s * sig
            q = (1 - u)[:, None] ** 2 * anchor + 2 * (u * (1 - u))[:, None] * Kp + (u ** 2)[:, None] * end
            pts, j = [anchor], 0
            for g in self.gap[::-1]:
                while j < 400 and np.linalg.norm(q[j + 1] - pts[-1]) < g:
                    j += 1
                if j >= 400:
                    return pts + [q[-1]] * (6 - len(pts)), 1.0 + (g - np.linalg.norm(q[-1] - pts[-1]))
                a0, a1 = q[j], q[j + 1]
                lo, hi = 0.0, 1.0
                for _ in range(30):
                    m = .5 * (lo + hi)
                    if np.linalg.norm(a0 + (a1 - a0) * m - pts[-1]) < g:
                        lo = m
                    else:
                        hi = m
                pts.append(a0 + (a1 - a0) * lo)
                j = j
            return pts, (j + lo) / 400

        lo, hi = 0.0, 3 * self.L
        for _ in range(40):
            mid = .5 * (lo + hi)
            _, ustar = walk(mid)
            if ustar < 1.0:
                hi = mid          # curve too long: less sag
            else:
                lo = mid
        pts, _ = walk(lo)
        pts = np.array(pts[::-1])
        pts[0], pts[5] = end, anchor
        return self.relax(pts)

    def worlds(self, pts, G, mouth_rot=None):
        out = {}
        for k, i in enumerate(self.ids):
            tan = unit(pts[max(k - 1, 0)] - pts[min(k + 1, 5)])
            R = K.swing(self.tan0[k], tan)
            if k == 5 and mouth_rot is not None:
                # Belt49 makes the mouth cell rigid, including the part inside the pouch;
                # it rides with the pouch so that part never swings out through the wall.
                R = mouth_rot
            X = np.eye(4)
            X[:3, :3] = R
            X[:3, 3] = pts[k] - R @ self.c[k]
            out[i] = G @ X @ self.W_idle[i]
        return out


# ------------------------------------------------------------------ keys
class Key:
    def __init__(self, t, frame, H, shape, stop=True, pole=None, lead=.6, follow=False, spec=None):
        self.t, self.frame, self.H, self.shape = t, frame, H, shape
        self.stop, self.pole, self.lead, self.follow, self.spec = stop, pole, lead, follow, spec


SWING_MAX = np.radians(48.0)
PHI_RANGE = (np.radians(-100.0), np.radians(45.0))
EYE = D.camera(1.0)[0]


def clamp_rel(S, phi):
    rv = K.Rot.from_matrix(S).as_rotvec()
    a = np.linalg.norm(rv)
    if a > SWING_MAX:
        S = K.Rot.from_rotvec(rv / a * SWING_MAX).as_matrix()
    return S, float(np.clip(phi, *PHI_RANGE)), a, phi


def author(family, empty=False):
    global T
    T = T_EMPTY if empty else T_NORMAL
    idle_key = '201_idle' if family == 'base' else '201_%s_idle' % family
    idle = load_pose(idle_key)
    W0 = world_of(idle['poses'][0])
    local0 = {i: K.mat(v) for i, v in enumerate(idle['poses'][0])}
    iw = BI['WPN_root']
    pivot = W0[BI['hand_r']][:3, 3]
    grip_shape = {i: local0[i] for i in FINGERS_L}
    SH = dict(SHAPES, grip=grip_shape)
    armL = K.Arm('l', NAMES, PARENT, REST, W0)
    armR = K.Arm('r', NAMES, PARENT, REST, W0)
    beltN, beltO = Belt(W0, 'New_'), Belt(W0, '')
    cover_i = BI['LMG201_Cover']
    cover_local0 = np.linalg.inv(W0[iw]) @ W0[cover_i]
    hinge_axis_cover = rot(cover_local0).T @ np.array([-1.0, 0, 0])   # WPN -X, opens rear edge up
    boxes = {'old': [BI['LMG201_Box'], BI['LMG201_BoxLid']], 'new': [BI['New_LMG201_Box'], BI['New_LMG201_BoxLid']]}
    sel = BODY.parts['LMG201_Box']
    bc = D.Skin(BODY.pos[sel], (BODY.bi[sel], BODY.bw[sel])).pose(W0).mean(0)

    def frames_at(t):
        G = gun_rel(t, pivot)
        Wg = G @ W0[iw]
        C = Wg @ cover_local0 @ compose(axis_angle(hinge_axis_cover, np.radians(cover_angle(t))), np.zeros(3), 1)
        F = {'gun': Wg, 'cover': C, 'G': G}
        for w in ('old', 'new'):
            tr, rv = box_path(t, w)
            X = np.eye(4)
            X[:3, :3] = K.Rot.from_rotvec(rv).as_matrix()
            X[:3, 3] = bc + tr - X[:3, :3] @ bc
            F[w + '_box'] = G @ X
            F[w + '_X'] = X
        return F

    F_idle = frames_at(0.0)

    # geometry helpers in the gun-idle world (component at idle)
    def hand_pose(contact, lm, shape, fdir, palmar, clear=np.zeros(3)):
        R = hand_rot(fdir, palmar)
        p = np.asarray(contact, float) + clear - R @ landmark(SH[shape], lm)
        return compose(R, p)

    Hidle = W0[BI['hand_l']].copy()
    cover_rear_top = np.array([6.6, -25.3, -5.7])
    belt0 = beltN.c[0]
    pinch_off = np.array([-0.9, 0.0, 0.1])
    stow_end = lambda: beltN.c[5] + np.array([-3.0, 0.0, -5.2])
    dangle_end = beltO.c[5] + np.array([-3.4, 0.3, -4.6])

    # Hand orientations per phase come from the installed PKM reload_empty: its left hand
    # opens the cover; its right hand handles pouch, belt and cover closing (mirrored).
    R_hook, R_lift, R_lidrel = pkm_rot(.60, 'l'), pkm_rot(.95, 'l'), pkm_rot(1.20, 'l')
    R_box, R_seat = pkm_rot(1.90, 'r'), pkm_rot(3.45, 'r')
    R_pinch, R_lay = pkm_rot(3.90, 'r'), pkm_rot(4.15, 'r')
    R_push, R_shut = pkm_rot(4.60, 'r'), pkm_rot(4.82, 'r')

    def hand_at(contact, lm, shape, R):
        return compose(R, np.asarray(contact, float) - R @ landmark(SH[shape], lm))

    box_bottom = np.array([bc[0] - 1.5, bc[1] + .3, -26.5])  # pouch underside (idle)
    R_under = hand_rot([0.33, -0.94, 0.0], [0, 0, 1])     # fingers forward along the pouch, palm up (probe_box_grip: twist ~0, bend ~16)
    lm = lambda n: {'lm': n}
    # empty clip: from the lid down the outside of the receiver/pouch, then in under the pouch
    via_empty = .5 * (hand_at(cover_rear_top + [-2.5, 2.2, 4.2], 'palm', 'open', R_lidrel)[:3, 3]
                      + hand_at(box_bottom + [0, 0, -1.7], 'palm', 'box', R_under)[:3, 3]) + np.array([-10.0, 3.0, 2.0])
    keys = [
        Key(0.0, 'gun', Hidle, 'grip', pole=None),
        Key(T['release'], 'gun', Hidle, 'grip', pole=None),
        Key(T['lift'], 'gun', compose(rot(Hidle), Hidle[:3, 3] + [-2.0, 3.5, -1.5]), 'open', stop=False, pole=[-.2, .1, -1]),
        Key(T['reach'], 'gun', hand_at(cover_rear_top + [-1.0, 1.4, 3.8], 'palm', 'open', R_hook), 'open',
            stop=False, pole=[-.55, .15, -.8], spec=lm('palm')),
        Key(T['hook'], 'cover', hand_at(cover_rear_top + [-.9, -.1, 1.9], 'palm', 'hook', R_hook), 'hook',
            pole=[-.55, .15, -.8], lead=.5, follow=True, spec={'lm': 'palm', 'bend': 30.0}),
        Key(T['lift_end'], 'cover', None, 'hook', pole=[-.45, .2, -.85]),
        Key(T['let_go'], 'gun', hand_at(cover_rear_top + [-2.5, 2.2, 4.2], 'palm', 'open', R_lidrel), 'open',
            stop=False, pole=[-.6, .2, -.75], spec=lm('palm')),
        *([Key(.5 * (T['let_go'] + T['box_grab']), 'gun', compose(np.eye(3), via_empty), 'open', stop=False,
               pole=[-.8, .25, -.55], spec={'lm': 'palm', 'mid': True})] if empty else [
        Key(T['tray'], 'gun', hand_at(beltO.c[0] + pinch_off, 'pinchcell', 'pinch', R_pinch), 'pinch',
            pole=[-.75, .25, -.6], lead=.45, spec=lm('pinchcell')),
        Key(T['tray_pull'], 'gun', hand_at(beltO.c[0] + [-2.4, 0.3, -1.6] + pinch_off, 'pinchcell', 'pinch', R_pinch), 'pinch',
            stop=False, pole=[-.8, .25, -.55], spec=lm('pinchcell'))]),
        # The 201 pouch hangs under the receiver centre: carry it from underneath, palm up,
        # the same forearm roll family as the accepted underhand idle (PKM's side grip needs ~150 deg twist here)
        Key(T['box_grab'], 'old_box', hand_at(box_bottom + [0, 0, -1.7], 'palm', 'box', R_under), 'box',
            pole=[.1, .55, -.8], lead=.5, follow=True, spec=lm('palm')),
        Key(T['old_hidden'], 'old_box', None, 'box', pole=[.1, .55, -.8]),
        Key(T['new_visible'], 'new_box', 'same', 'box', pole=[.1, .55, -.8], follow=True),
        Key(T['box_seat'] + .08, 'new_box', None, 'box', pole=[.1, .55, -.8]),
        Key(T['box_release'], 'gun', hand_at(box_bottom + [-3.0, 1.0, -2.6], 'palm', 'spread', R_under), 'spread',
            stop=False, pole=[-.3, .45, -.8], spec=lm('palm')),
        Key(T['belt_grab'], 'new_box', hand_at(stow_end() + pinch_off, 'pinchcell', 'pinch', R_pinch), 'pinch',
            pole=[-.85, .3, -.45], lead=.45, spec=lm('pinchcell')),
        Key(T['belt_top'], 'gun', hand_at(belt0 + [-2.3, 0.0, -0.4] + pinch_off, 'pinchcell', 'pinch', R_lay), 'pinch',
            stop=False, pole=[-.75, .25, -.6], spec=lm('pinchcell')),
        Key(T['belt_seat'], 'gun', hand_at(belt0 + pinch_off, 'pinchcell', 'pinch', R_lay), 'pinch',
            pole=[-.75, .25, -.6], spec=lm('pinchcell')),
        Key(T['belt_release'], 'gun', hand_at(belt0 + [-3.0, 1.5, 2.5] + pinch_off, 'pinchcell', 'open', slerp_R(R_lay, R_push, .5)),
            'open', stop=False, pole=[-.7, .25, -.65], spec=lm('pinchcell')),
    ]
    # closing as PKM: flat palm on the inner face of the raised cover pushes it back, then shuts it
    Fo = frames_at(T['cover_reach'])
    Rel_o = Fo['cover'] @ np.linalg.inv(F_idle['cover'])
    top_edge_open = (Rel_o @ np.r_[cover_rear_top, 1])[:3]
    inner = rot(Rel_o) @ np.array([0, 0, -1.0])            # cover underside normal, now facing the muzzle
    down_face = rot(Rel_o) @ np.array([0, -1.0, 0])        # from the rear edge toward the hinge
    keys += [
        Key(T['cover_reach'], 'cover', np.linalg.inv(Rel_o) @ hand_at(top_edge_open + inner * 2.0 + down_face * 2.5, 'palm', 'flat', R_push),
            'flat', pole=[-.55, .2, -.8], lead=.5, follow=True, spec=lm('palm')),
        Key(T['cover_pull'], 'cover', None, 'flat', stop=False, pole=[-.55, .2, -.8]),
        Key(T['cover_close'], 'gun', hand_at(cover_rear_top + [-1.2, -2.5, 2.3], 'palm', 'flat', R_shut), 'flat',
            pole=[-.55, .2, -.8], lead=.5, spec=lm('palm')),
        Key(T['press_end'], 'gun', hand_at(cover_rear_top + [-1.2, -2.5, 2.1], 'palm', 'flat', R_shut), 'flat',
            pole=[-.55, .2, -.8], spec=lm('palm')),
        Key(T['return_start'] + .05, 'gun', compose(np.eye(3), .5 * (cover_rear_top + [-4.5, 1.0, 1.0]) + .5 * Hidle[:3, 3] + [-3, 2, 1]),
            'open', stop=False, pole=[-.4, .1, -.9], spec={'lm': 'palm', 'mid': True}),
        Key(T['grip'] - .12, 'gun', compose(rot(Hidle), Hidle[:3, 3] + [-1.2, 2.0, -1.2]), 'grip', stop=False, pole=None, lead=.8),
        Key(T['grip'], 'gun', Hidle, 'grip', pole=None),
        Key(DURATION, 'gun', Hidle, 'grip', pole=None),
    ]
    # pouch frames are relative offsets: identity == seated on the idle gun
    frame_idle = {'gun': F_idle['gun'], 'cover': F_idle['cover'], 'old_box': np.eye(4), 'new_box': np.eye(4)}
    CENTER_L = armL.phi0

    def limit_bend(pos, R, cap=None):
        """Pull a wrist bend above cap back toward the forearm. The reference keeps the
        wrist nearly straight on every contact (forearm level, palm flat)."""
        cap = BEND_MAX if cap is None else cap
        Dh = R @ armL.Rrest['hand'].T
        hd = unit(Dh @ armL.cF0)
        fax = unit(pos['T'] - pos['E'])
        bend = np.degrees(np.arccos(np.clip(hd @ fax, -1, 1)))
        if bend <= cap:
            return R, bend
        ax = unit(np.cross(hd, fax))
        return axis_angle(ax, np.radians(bend - cap)) @ R, bend

    def resolve(k):
        """Contact key: search the elbow on the shoulder-wrist circle for the least
        shoulder twist (coherent-segment mismatch) and wrist bend, away from the eye."""
        F = frames_at(k.t)
        Rel = F[k.frame] @ np.linalg.inv(frame_idle[k.frame])
        if k.spec.get('mid'):
            j = keys.index(k)
            Tp = (Rel @ k.H)[:3, 3]
            pos = armL.positions(Tp, rot(F['G']) @ unit(k.pole))
            na, nb = keys[j - 1], keys[j + 1]
            Ra = rot(F[na.frame] @ np.linalg.inv(frame_idle[na.frame]) @ na.H)
            Rb = rot(F[nb.frame] @ np.linalg.inv(frame_idle[nb.frame]) @ nb.H)
            Sa, pa = armL.hand_relative(pos, Ra, CENTER_L)
            Sb, pb = armL.hand_relative(pos, Rb, CENTER_L)
            R = armL.hand_from_relative(pos, slerp_R(Sa, Sb, .5), .5 * (pa + pb))
            k.H = np.linalg.inv(Rel) @ compose(R, Tp)
            print('RESOLVE t=%.2f %-7s via midpoint' % (k.t, k.frame), flush=True)
            return
        W_des = Rel @ k.H
        Rdes = rot(W_des)
        lmk = landmark(SH[k.shape], k.spec['lm'])
        contact = W_des[:3, 3] + Rdes @ lmk
        hint = rot(F['G']) @ unit(k.pole)
        prev = PREV_POLE[0]
        best = None
        for psi in np.radians(np.arange(-176, 177, 8)):
            R = Rdes
            for _ in range(3):
                Tp = contact - R @ lmk
                ax = unit(Tp - armL.positions(Tp, hint)['A'])
                pole = axis_angle(ax, psi) @ hint
                pos = armL.positions(Tp, pole)
                R, bend = limit_bend(pos, Rdes, k.spec.get('bend', CONTACT_BEND))
            tau = np.degrees(armL.tau_of(pos, R)[0])
            seg = [pos['A'] + (pos['E'] - pos['A']) * s for s in np.linspace(.35, 1, 8)] + \
                  [pos['E'] + (pos['T'] - pos['E']) * s for s in np.linspace(0, 1, 8)]
            eye = float(np.min(np.linalg.norm(np.array(seg) - EYE, axis=1)))
            dev = np.degrees(K.Rot.from_matrix(R @ Rdes.T).magnitude())
            elbow_dir = unit(pos['E'] - .5 * (pos['A'] + pos['T']))
            turn = 0.0 if prev is None else np.degrees(np.arccos(np.clip(np.dot(elbow_dir, prev), -1, 1)))
            up = float(elbow_dir @ rot(F['G'])[:, 2])  # only a clearly raised elbow reads as a wing
            cost = ((tau / 70) ** 2 * .6 + (dev / 20) ** 2 + max(0, 18 - eye) ** 2 * .03 + max(0, up - .35) ** 2 * 12
                    + max(0, pos['reach'] - .92) ** 2 * 400 + (turn / 45) ** 2 * .5 + (psi / np.pi) ** 2 * .1)
            if best is None or cost < best[0]:
                best = (cost, R, contact - R @ lmk, pole, np.degrees(psi), bend, tau, eye, pos['reach'], dev)
        cost, R, Tp, pole, psi, bend, tau, eye, reach, dev = best
        pos = armL.positions(Tp, pole)
        PREV_POLE[0] = unit(pos['E'] - .5 * (pos['A'] + pos['T']))
        k.H = np.linalg.inv(Rel) @ compose(R, Tp)
        k.pole = rot(F['G']).T @ pole
        print('RESOLVE t=%.2f %-7s psi %5.0f wrist-bend %5.1f (PKM pose %5.1f) shoulder-twist %6.1f eye %5.1f reach %.3f rot-dev %5.1f elbow %s' % (
            k.t, k.frame, psi, min(bend, k.spec.get('bend', CONTACT_BEND)), bend, tau, eye, reach, dev, np.round(pos['E'], 1)), flush=True)

    _p0 = armL.positions(Hidle[:3, 3], armL.pole0)
    PREV_POLE = [unit(_p0['E'] - .5 * (_p0['A'] + _p0['T']))]
    for k in keys:
        if k.spec is not None:
            resolve(k)
    for k in keys:
        if k.H is None or isinstance(k.H, str):
            continue
        k.L = np.linalg.inv(frame_idle[k.frame]) @ k.H
    # follow segments: the next key inherits the same local in its own frame
    for a, b in zip(keys, keys[1:]):
        if a.follow and b.H is None:
            b.L = a.L
            b.pole = a.pole  # keep the resolved elbow swivel through the followed contact
        if isinstance(b.H, str) and b.H == 'same':
            # hand world stays: new pouch at new_visible sits where the old one was hidden
            Wa = frames_at(a.t)[a.frame] @ a.L
            b.L = np.linalg.inv(frames_at(b.t)[b.frame]) @ Wa
    for k in keys:
        if k.pole is None:
            k.pole = armL.pole0

    def key_world(k, t, F):
        return F[k.frame] @ k.L

    def left_target(t, F):
        """Wrist position, the two key rotations with blend weight (or a followed
        rotation), finger shape and elbow pole for time t."""
        i = max(j for j in range(len(keys)) if keys[j].t <= t + 1e-9)
        a = keys[i]
        if i == len(keys) - 1:
            M = key_world(a, t, F)
            return M, SH[a.shape], a.pole, (rot(M), rot(M), 0.0)
        b = keys[i + 1]
        u = (t - a.t) / (b.t - a.t)
        Ma, Mb = key_world(a, t, F), key_world(b, t, F)
        if a.follow and b.L is a.L:
            M, rots = Ma, (rot(Ma), rot(Ma), 0.0)
        else:
            def vel(j):
                k = keys[j]
                if k.stop or j == 0 or j == len(keys) - 1:
                    return np.zeros(3)
                p0 = key_world(keys[j - 1], t, F)[:3, 3]
                p1 = key_world(keys[j + 1], t, F)[:3, 3]
                return (p1 - p0) / (keys[j + 1].t - keys[j - 1].t)
            p = K.hermite(Ma[:3, 3], Mb[:3, 3], vel(i), vel(i + 1), u, b.t - a.t)
            rots = (rot(Ma), rot(Mb), ease(u))
            M = compose(slerp_R(rot(Ma), rot(Mb), ease(u)), p)
        us = ease((u - (1 - b.lead)) / b.lead) if a.shape != b.shape else 0
        shape = shape_mix(SH[a.shape], SH[b.shape], us)
        pole = slerp_vec(a.pole, b.pole, ease(u))
        return M, shape, pole, rots

    def solve_left(t, F, pole_override=None):
        M, shape, pole, (Ra, Rb, e) = left_target(t, F)
        if pole_override is not None:
            pole = pole_override
        pos = armL.positions(M[:3, 3], rot(F['G']) @ pole)
        Sa, pa = armL.hand_relative(pos, Ra, CENTER_L)
        Sb, pb = armL.hand_relative(pos, Rb, CENTER_L)
        Rh = armL.hand_from_relative(pos, slerp_R(Sa, Sb, e), pa + (pb - pa) * e)
        Rh, _ = limit_bend(pos, Rh, TRANSIT_BEND)
        return armL.finish_coherent(pos, Rh), shape, M

    print('LEFT idle phi0 %.1f cap0 %.1f pole0 %s' % (np.degrees(armL.phi0), np.degrees(armL.cap0), np.round(armL.pole0, 2)))
    for k in keys:
        F = frames_at(k.t)
        solve_left(k.t, F)
        x = armL.last
        print('KEY t=%.2f %-8s %-6s reach %.3f elbow %5.1f shoulder-twist %6.1f wrist-bend %5.1f' % (
            k.t, k.frame, k.shape, x['reach'], x['elbow'], x['tau'], x['bend']))
    armL.tau_prev = 0.0
    # elbow swivel continuity: low-pass the pole direction (hand targets unchanged)
    raw = np.array([left_target(fi / FPS, frames_at(fi / FPS))[2] for fi in range(COUNT)])
    sig = POLE_SMOOTH * FPS
    kern = np.exp(-.5 * (np.arange(-int(3 * sig), int(3 * sig) + 1) / sig) ** 2)
    padded = np.concatenate([np.repeat(raw[:1], len(kern) // 2, 0), raw, np.repeat(raw[-1:], len(kern) // 2, 0)])
    smooth = np.stack([np.convolve(padded[:, c], kern / kern.sum(), mode='valid') for c in range(3)], 1)
    smooth /= np.linalg.norm(smooth, axis=1, keepdims=True)
    frames, info = [], []
    old_release = [None]
    for fi in range(COUNT):
        t = fi / FPS
        F = frames_at(t)
        G = F['G']
        W = W0.copy()
        # gun and its sub-bones
        for i in WPN:
            W[i] = G @ W0[i]
        W[cover_i] = F['cover']
        for w in ('old', 'new'):
            for i in boxes[w]:
                W[i] = G @ F[w + '_X'] @ W0[i]
        # right arm follows the grip
        Hr = G @ W0[BI['hand_r']]
        # Action framing brings the eye 9 cm toward the right shoulder; slide the arm
        # root back behind the camera plane with the runtime framing weight (SVD arm-root
        # method), so the thick right sleeve never reaches the near plane.
        Cr = W0[BI['clavicle_r']].copy()
        Cr[:3, 3] += RIGHT_ROOT_BACK * D.framing_alpha(t, DURATION, T['return_start'])
        pos = armR.positions(Hr[:3, 3], rot(G) @ armR.pole0, clavicle=Cr)
        _, pr = armR.hand_relative(pos, rot(Hr), armR.phi0)
        sol = armR.finish(pos, rot(Hr), pr)
        for k2, m in sol.items():
            W[armR.i[k2]] = m
        for n in ('upperarm_twist_01_r', 'upperarm_twist_02_r'):
            W[BI[n]] = W[BI['upperarm_r']] @ local0[BI[n]]
        for i in FINGERS_R:
            W[i] = W[PARENT[i]] @ local0[i]
        # left arm
        sol, shape, _ = solve_left(t, F, smooth[fi])
        for k2, m in sol.items():
            W[armL.seg[k2][1] if k2 in armL.seg else armL.i[k2]] = m
        for i in FINGERS_L:
            W[i] = W[PARENT[i]] @ shape[i]
        # belts: after the arm, from the solved fingertips (runtime pins cells 0 and 5
        # to these animated points; free cells 1-4 get the damped secondary motion)
        pin = (np.linalg.inv(G) @ np.r_[hand_point(W[BI['hand_l']], landmark(shape, 'pinchcell')), 1])[:3] - pinch_off
        for belt, w in ((beltO, 'old'), (beltN, 'new')):
            X = F[w + '_X']
            anchor = (X @ np.r_[belt.c[5], 1])[:3]
            if w == 'old':
                sag = X[:3, :3] @ unit(np.array([-.8, 0, -.6]))
            else:
                g = ease((t - (T['belt_grab'] + .08)) / .30)
                sag = X[:3, :3] @ unit(np.array([-.3, 0, -1.0]) * (1 - g) + np.array([-1.0, 0, -.3]) * g)
            if w == 'old':
                t0 = T['tray'] - .04
                if empty or t < t0:
                    pts = belt.c.copy()
                    belt.s_prev = None
                else:
                    if t < T['tray_pull'] + .02:
                        end = belt.c[0] + (pin - belt.c[0]) * ease((t - t0) / .08)
                        old_release[0] = end
                    else:
                        dang = (X @ np.r_[dangle_end, 1])[:3]
                        end = old_release[0] + (dang - old_release[0]) * ease((t - T['tray_pull'] - .02) / .22)
                    wb = ease((t - t0) / .10)   # idle tray shape -> free chain
                    pts = belt.relax(belt.c * (1 - wb) + belt.chain(anchor, end, sag) * wb)
            else:
                if t >= T['belt_seat']:
                    pts = belt.c.copy()
                else:
                    end = (X @ np.r_[stow_end(), 1])[:3] if t < T['belt_grab'] else pin
                    ch = belt.chain(anchor, end, sag)
                    ws = ease((t - T['belt_fade']) / (T['belt_seat'] - T['belt_fade']))   # same fade as the runtime damping
                    pts = belt.relax(ch * (1 - ws) + belt.c * ws) if ws > 0 else ch
            for i, m in belt.worlds(pts, G, X[:3, :3]).items():
                W[i] = m
        # every bone not driven above keeps its idle local under its (possibly moved) parent
        driven = set(WPN) | set(FINGERS_L) | set(FINGERS_R) | {BI['upperarm_twist_01_l'], BI['upperarm_twist_02_l'],
                  BI['upperarm_twist_01_r'], BI['upperarm_twist_02_r']} | set(armL.i.values()) | set(armR.i.values())
        for i in range(len(NAMES)):
            if i not in driven and PARENT[i] >= 0:
                W[i] = W[PARENT[i]] @ local0[i]
        info.append(dict(t=t, reach=armL.last['reach'], elbow=armL.last['elbow'], tau=armL.last['tau'], bend=armL.last['bend'],
                         dphi=armL.last['tau'], reach_r=armR.last['reach'], cover=cover_angle(t)))
        # locals
        L = np.zeros((len(NAMES), 10))
        for i in range(len(NAMES)):
            m = np.linalg.inv(W[PARENT[i]]) @ W[i] if PARENT[i] >= 0 else W[i]
            L[i] = K.pack(m)
        frames.append(L)
    # exact idle ends, continuity of quaternion signs
    arr = np.stack(frames)  # (F,B,10)
    for fi in (0, COUNT - 1):
        arr[fi] = np.array(idle['poses'][0])
    for fi in range(1, COUNT):
        flip = (arr[fi, :, 3:7] * arr[fi - 1, :, 3:7]).sum(-1) < 0
        arr[fi, flip, 3:7] *= -1
    return arr, info, idle


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    empty_only = '--empty-only' in sys.argv
    fams = args or ['base', 'vertical', 'canted', 'prism', 'angled']
    report = json.loads((HERE / 'motion.json').read_text()) if (HERE / 'motion.json').exists() else {}
    report.update(revision='ClothReload44.4', reference_video=r'C:\Users\allan\Videos\NVIDIA\Delta Force\Delta Force 2026.09.28 - 22.36.59.03.mp4',
                  method='prop-attached left-hand keys with PKM reload hand orientations (left: cover open; right mirrored: pouch, belt, '
                         'cover close); fixed clavicle two-bone solve, elbow on the shoulder-wrist circle for least shoulder twist and '
                         'wrist bend (<=66 deg); PKM LeftArm48 coherent segments (palm-width forearm frame shared by all forearm bones, '
                         'upper-arm helpers transported across the elbow); right grip follows gun; rigid pouches; 6-segment belt chain; '
                         'empty clip skips the spent-belt tray work (EMPTY_KNOTS)', phases=T_NORMAL, phases_empty=T_EMPTY,
                  empty_knots=EMPTY_KNOTS, runtime_tested=False)
    report.setdefault('clips', {})
    report['install_only'] = []
    for fam in fams:
        for empty in ((True,) if empty_only else (False, True)):
            arr, info, idle = author(fam, empty)
            tracks = {n: arr[:, i].round(7).tolist() for i, n in enumerate(NAMES)}
            out = HERE / 'Tracks' / (fam + ('_empty' if empty else '') + '_tracks.json.gz')
            out.parent.mkdir(exist_ok=True)
            with gzip.open(out, 'wt', encoding='utf8') as f:
                json.dump(tracks, f, separators=(',', ':'))
            (HERE / 'Tracks' / (fam + ('_empty' if empty else '') + '_solve.json')).write_text(json.dumps(info))
            r = np.array([x['reach'] for x in info])
            e = np.array([x['elbow'] for x in info])
            ph = np.array([x['dphi'] for x in info])
            bd = np.array([x['bend'] for x in info])
            print('AUTHORED', fam, 'empty' if empty else 'normal', 'reach max %.3f' % r[20:-20].max(), 'elbow %.0f..%.0f' % (e.min(), e.max()),
                  'shoulder twist %.0f..%.0f' % (ph.min(), ph.max()), 'wrist bend max %.1f' % bd.max(), flush=True)
            key = fam + ('_reload_empty' if empty else '_reload')
            report['clips'][key] = dict(destination='/Game/Weapons/LMG201/ClothReload44/Animations/%s/A_LMG201_%s' % (fam, key),
                                        idle_source=idle['asset'], idle_sha256=idle['sha256'], keys=str(out), fps=FPS,
                                        frames=COUNT, seconds=DURATION, empty=empty)
            report['install_only'].append(key)
    (HERE / 'motion.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
