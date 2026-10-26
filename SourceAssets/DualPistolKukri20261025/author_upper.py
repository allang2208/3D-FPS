"""Author the pistol+offhand-kukri uppercut: the main-hand Uppercut clip mirrored to the left hand.

Kukri20261020/Clips/Uppercut.json (BV1CeYUeSE7b #9, 106.20-107.30 s, 120 fps, length 1.2667 s) is the
main-hand 上挑: FK it per frame, conjugate-mirror across the camera Y plane (mesh X) so the clip's right
hand becomes our left swing hand, and the clip's left balance hand becomes the right/gun hand's evade
path — the 右手避让 (the clip's own balance hand sweeps the right edge of the frame and drops out below).

The gun hand cannot follow the clip path absolutely (the clip's own rest sits ~54 cm under our pistol
rest): blend from the hip-framed rest into the mirrored path over 0-0.12 s and back out over 0.45-0.70 s,
with the evasion rotation applied as a camera-space delta damped to ROT_W. The left swing hand blends
out of our stance over 0-0.12 s and back in over 0.97-1.27 s; both end keys are exactly the hip stance.

Grip: the clip holds the sword forward, so the reverse-grip idle digits/KukriInHand can't be reused —
Digits are the clip's right-hand finger locals mirrored onto the V7 _l bones, baked once at t=0.35 s,
and the blade hangs off the mirrored WPN_root grip point (0,0,-0.070). Both apply inside DIGITS window.

Run:  python -I author_upper.py
Output: Work/upper/offhand_upper_keys.json + per-key gun/kukri/arms npz for render_upper.py.
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
sys.path.insert(0, str(P))
sys.path.insert(0, str(ROOT / 'SourceAssets/Kukri20261020'))
import author_idle as A
from kmath import T, Rig, load_dump, qmat, qfrommat, qmul, qconj, qslerp

CLIP = ROOT / 'SourceAssets/Kukri20261020/Clips/Uppercut.json'
OUT = P / 'Work' / 'upper'
OUT.mkdir(parents=True, exist_ok=True)

clip = json.loads(CLIP.read_text(encoding='utf-8'))
rig = Rig(load_dump())
FPS = clip['fps']
LENGTH = float(clip['length'])

S3 = np.diag([-1, 1, 1.])            # mirror across mesh X == camera Y
SM = np.diag([-1, 1, 1, 1.])
C4 = np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.]])  # mesh basis -> camera basis


def mat_of(t):
    m = np.eye(4)
    m[:3, :3] = qmat(t.q) * t.s
    m[:3, 3] = t.p
    return m


def mir(world):
    """Mirrored-scene camera space. Positions only: the clip's world matrices carry the import's x100 scale, so the
    rotation part of this is neither normalised nor in the destination bone's convention -- use mframe()."""
    return C4 @ SM @ mat_of(world) @ SM


C3 = C4[:3, :3]
MX3 = np.diag([-1, 1, 1.])
REFW = {n: mat_of(t) for n, t in rig.world({n: rig.ref_local[n] for n in rig.names}).items()}


def unit3(m):
    m = np.asarray(m, float)[:3, :3]
    return m / np.linalg.norm(m, axis=0)


def mframe(w, src, dst):
    """V3 mirror (same rule as the warhammer swap): camera-space frame of bone `dst` from the clip's `src`, rotation
    normalised and carried into `dst`'s own bind convention by fix = Rref(src)^T MX Rref(dst). The clip rig and the V7
    arms share every arm/finger bind local (diag_grip.py: 0.00 deg) and the clip is symmetric (0.001 cm)."""
    m = mat_of(w[src])
    fix = unit3(REFW[src]).T @ MX3 @ unit3(REFW[dst])
    return A.matrix(C3 @ MX3 @ unit3(m) @ fix, C3 @ MX3 @ m[:3, 3])


def mweapon(w):
    """Mirrored kukri frame: SM_Kukri hangs off WPN_root with identity (KukriWeaponComponent); reflect the frame and its
    flat normal (local Y), keeping the blade (+Z) and the edge (+X)."""
    m = mat_of(w['WPN_root'])
    return A.matrix(C3 @ MX3 @ unit3(m) @ np.diag([1, -1, 1.]), C3 @ MX3 @ m[:3, 3])


def ss(x):
    x = min(max(x, 0.), 1.)
    return x * x * (3 - 2 * x)


HIP = A.controls
REST = A.build(HIP)
idle, view = A.IDLE
H_IDLE = idle['hand_r']
RW_REST = REST['r']['hand_r']
QRW = qfrommat(RW_REST[:3, :3])
LW_REST = REST['l']['hand_l']
QLW = qfrommat(LW_REST[:3, :3])
LS_REST = np.array(HIP['left_shoulder'], float)
LP_REST = np.array(HIP['left_pole'], float)
RS_REST = np.array(HIP['right_shoulder'], float)

ROT_W = 0.6            # damped share of the balance-hand rotation applied to the gun ensemble
DIGITS_AT, DIGITS_END = 0.12, 1.05   # forward-grip digits + KukriInHand active inside this window
# V2 (user: elbow wrong, upper arm pinched thin). The shoulder root now travels onto the mirrored clip shoulder,
# so the clip elbow (pole) is reproduced exactly (was 46-91 deg off in the follow-through, diag_elbow.py).
# The V7 clavicle keeps its bind (pointing back along camera -X), so a raised upper arm pinched the shoulder skin
# to 83-94 % of bind radius; the clavicle now takes CLAV_SHARE of the upper arm's deformation (95-99 %,
# diag_upper_skin.py). Both fade with the swing weight, so the end keys stay exactly the accepted hip stance.
CLAV_SHARE = 0.7

FINGERS = ['index_metacarpal', 'index_01', 'index_02', 'index_03',
           'middle_metacarpal', 'middle_01', 'middle_02', 'middle_03',
           'thumb_01', 'thumb_02', 'thumb_03',
           'pinky_metacarpal', 'pinky_01', 'pinky_02', 'pinky_03',
           'ring_metacarpal', 'ring_01', 'ring_02', 'ring_03']


def world_at(i):
    fr = clip['frames'][i]
    local = {n: T.packed(sum(fr[n], [])) for n in clip['bones']}
    local = {n: local.get(n, rig.ref_local[n]) for n in rig.names}
    return rig.world(local)


# clip rest references (frame 0 == the clip's own rest; it loops back there)
w0 = world_at(0)
SH0 = mir(w0['upperarm_r'])[:3, 3]
QE0 = qfrommat(mframe(w0, 'hand_l', 'hand_r')[:3, :3])

# Forward grip: the mirrored kukri relative to the mirrored left hand, in cm (V1/V2 inverted the x100-scaled hand
# matrix, which shrank this offset to 0.07 cm and hung the blade on the wrist joint).
KIH = None
dev = []
for i in range(int(clip['contact'][0] * FPS), int(clip['contact'][1] * FPS) + 1):
    w = world_at(i)
    k = np.linalg.inv(mframe(w, 'hand_r', 'hand_l')) @ mweapon(w)
    dev.append(k[:3, 3])
    if i == int(0.35 * FPS):
        KIH = k
dev = np.array(dev)
print('KIH grip-point spread over contact: %.3f cm, offset %s cm' % (float(np.ptp(dev, axis=0).max()), np.round(KIH[:3, 3], 2)))

# Forward-grip digits: the mirrored left-hand finger frames' locals (each bone in its own bind convention), baked at
# t=0.35. V1/V2 conjugated the right locals by diag(-1,1,1), which is not the rig's left/right relation.
w_contact = world_at(int(0.35 * FPS))
DIGIT_ROT = {}
for f in FINGERS:
    n = f + '_l'
    par = A.LP[n]
    pf = mframe(w_contact, par[:-2] + '_r', par)
    cf = mframe(w_contact, f + '_r', n)
    DIGIT_ROT[n] = pf[:3, :3].T @ cf[:3, :3]

# Preview arm source: V7 fist source with _l finger locals re-anchored to the mirrored rotations.
SRCU = {n: m.copy() for n, m in A.FIST[0].items()}
for f in FINGERS:
    n = f + '_l'
    par = A.LP[n]
    src_local = np.linalg.inv(SRCU[par]) @ SRCU[n]
    SRCU[n] = SRCU[par] @ A.matrix(DIGIT_ROT[n], src_local[:3, 3])


def write_npz(tag, G, pose, Kc):
    geo = np.load(A.V4 / 'gun_idle.npz')
    xg = 100 * geo['X'] * np.array([1, -1, 1])
    xf = G @ view
    np.savez_compressed(OUT / ('gun_%s.npz' % tag), X=xg @ xf[:3, :3].T + xf[:3, 3],
                        T=geo['T'][:, ::-1], UV=geo['UV'][:, ::-1], slots=geo['slots'])
    km = np.load(P / 'kukri_mesh.npz')
    np.savez_compressed(OUT / ('kukri_%s.npz' % tag), X=km['X'] @ Kc[:3, :3].T + Kc[:3, 3],
                        T=km['T'], UV=km['UV'], slots=km['slots'])
    X, _, _ = A.skin(pose)
    np.savez_compressed(OUT / ('arms_%s.npz' % tag), X=X, T=A.surface['T'], UV=A.surface['UV'])


def main():
    keys = []
    for i in range(0, len(clip['frames']), 2):
        t = min(i / FPS, LENGTH)
        w = world_at(i)
        swing = mframe(w, 'hand_r', 'hand_l')
        evade = mframe(w, 'hand_l', 'hand_r')
        elb = mir(w['lowerarm_r'])[:3, 3]
        sh_clip = mir(w['upperarm_r'])[:3, 3]

        wR = ss(t / 0.12) * (1 - ss((t - 0.45) / 0.25))
        wL = ss(t / 0.12) * (1 - ss((t - 0.97) / 0.30))
        if i == 0 or i == len(clip['frames']) - 1:
            wL = wR = 0.0

        # Right hand: blended absolute path + damped camera-space rotation delta.
        p_ev = (1 - wR) * RW_REST[:3, 3] + wR * evade[:3, 3]
        qd = qmul(qfrommat(evade[:3, :3]), qconj(QE0))
        qe = qslerp(QRW, qmul(qd, QRW), ROT_W * wR)
        rw = A.matrix(qmat(qe), p_ev)
        G = rw @ np.linalg.inv(H_IDLE)
        framing = G.copy()
        framing[:3, 3] = G[:3, 3] - G[:3, :3] @ np.array([-2.0, 3.0, -6.5])

        # Left hand: blended into the mirrored swing at both ends.
        wrist = (1 - wL) * LW_REST[:3, 3] + wL * swing[:3, 3]
        hq = qslerp(QLW, qfrommat(swing[:3, :3]), wL)
        shoulder = (1 - wL) * LS_REST + wL * sh_clip
        pole = (1 - wL) * LP_REST + wL * elb
        clav = CLAV_SHARE * wL

        # Preview pose: solved left arm (forward-grip source inside the digits window, the accepted
        # reverse-grip fist outside it); right arm re-solved on the evaded ensemble.
        fwd = DIGITS_AT <= t <= DIGITS_END
        l, ldiag = A.solve_arm(A.LR, SRCU if fwd else A.FIST[0], A.LP, 'l', shoulder, wrist, pole, qmat(hq))
        A.clavicle_share(l, clav)
        rsrc = {n: G @ m for n, m in idle.items()}
        pole_r = (G @ REST['r']['lowerarm_r'])[:3, 3]
        r, rdiag = A.solve_arm(A.RR, rsrc, A.RP, 'r', RS_REST, rw[:3, 3], pole_r, qmat(qe))
        pose = dict(REST['pose'])
        for n in pose:
            if A.chain(n, 'clavicle_l', A.LP) and n in l:
                pose[n] = l[n]
            elif A.chain(n, 'clavicle_r', A.LP) and n in r:
                pose[n] = r[n]
        Kc = l['hand_l'] @ (KIH if fwd else REST['kukri_in_hand'])

        tag = 't%03d' % round(t * 100)
        write_npz(tag, G, pose, Kc)
        keys.append(dict(t=t,
                         wrist_offset=(wrist - p_ev).round(3).tolist(),
                         left_wrist=wrist.round(3).tolist(),
                         left_hand=A.matrix(qmat(hq), wrist).round(6).tolist(),
                         left_shoulder=shoulder.round(3).tolist(),
                         left_pole=pole.round(3).tolist(),
                         clavicle=round(clav, 4),
                         framing=framing.round(6).tolist()))
        print('t=%.3f %-6s wrist %s evade %s reach L %.2f R %.2f' % (t, tag,
              np.round(wrist, 1), np.round(p_ev, 1), ldiag['reach'], rdiag['reach']))

    digits = {}
    for f in FINGERS:
        q = R.from_matrix(DIGIT_ROT[f + '_l']).as_quat()   # x,y,z,w (UE FQuat order)
        q /= np.linalg.norm(q)
        digits[f + '_l'] = q.round(6).tolist()

    (OUT / 'offhand_upper_keys.json').write_text(json.dumps(dict(
        keys=keys, length=LENGTH, contact=list(clip['contact']), swings=[0.29],
        digits_window=[DIGITS_AT, DIGITS_END],
        kukri_in_hand=KIH.round(6).tolist(), digits=digits), indent=1), encoding='utf-8')
    print('WROTE', OUT / 'offhand_upper_keys.json', len(keys), 'keys')


if __name__ == '__main__':
    main()
