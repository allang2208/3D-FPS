"""GripLayer56 study: "base clip + runtime grip layer" against the authored grip-family clips.

The layer is the reference for the C++ runtime (same steps, per frame, no history except the
grip poses read once from the idles):
  grip poses   base / family idle frame 0: hand_l in WPN_root space, left finger locals;
  weight       base hand near the base grip (gun space) -> 1, away (reload, inspect) -> 0;
  hand         base hand (gun space) * interp(I, inv(G_base) * G_family, weight);
  fingers      local slerp(base, family, weight), base local offsets (lengths exact);
  arm          ArmHinge55 construction re-evaluated around the base arm: elbow by two-bone
               IK with the base elbow as pole, both segments carried by the rotation that maps
               the base arm plane to the new one, crease term re-weighted for the new bend,
               residual palm twist added to the base forearm pronation (cap 110 deg, excess
               to the upper-arm roll), upper-arm helpers from the forearm frame (ArmHinge55).
At weight 0 the construction returns the (ArmHinge55-solved) base arm unchanged.

python -X utf8 evaluate.py
"""
import json, gzip, sys
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as Rot

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'ArmHinge55'))
import author as AH  # noqa: E402

FAMS = ('angled', 'vertical', 'canted', 'prism')
W_POS = (1.0, 5.0)    # cm, base hand to base grip: full layer / no layer
W_ANG = (6.0, 20.0)   # deg
ARM = AH.BONES
C, UP, T1, T2, LO, F2, F1, HA = range(8)
IDLE = {'PKM': ('/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_idle',
                '/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations/{f}/A_PKM_{f}_idle'),
        '201': ('/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle',
                '/Game/Weapons/LMG201/Accessories22/Animations/{f}/A_LMG201_{f}_idle')}


def unit(v):
    return v / max(np.linalg.norm(v), 1e-12)


def ang(Rm):
    return np.degrees(np.linalg.norm(Rot.from_matrix(Rm).as_rotvec()))


def ss(e, x):
    t = np.clip((x - e[0]) / (e[1] - e[0]), 0, 1)
    return t * t * (3 - 2 * t)


def wrap(x):
    return (x + np.pi) % (2 * np.pi) - np.pi


def load(c):
    with gzip.open(c['file'], 'rt', encoding='utf8') as f:
        d = json.load(f)
    v = np.array(d['world'])
    n, b, _ = v.shape
    R = Rot.from_quat(v[..., 3:7].reshape(-1, 4)).as_matrix().reshape(n, b, 3, 3)
    return {name: (R[:, i], v[:, i, :3]) for i, name in enumerate(d['bones'])}, n


def base_key(key, fam):
    head, name = key.rsplit('/A_', 1)
    act = name.split('_', 2)[2]
    if '/Accessories14/' in key:
        return '/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_' + act, act
    if '/Accessories22/' in key:
        return '/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_' + act, act
    folder = key.split('/Weapons/LMG201/')[1].split('/')[0]
    return key.replace(f'/Animations/{fam}/A_LMG201_{fam}_', '/Animations/base/A_LMG201_base_'), folder + ':' + act


class Grip:
    """hand_l in WPN_root space and the left finger locals, at an idle's first key."""

    def __init__(self, clip, fingers, parent):
        Rw, Pw = clip['WPN_root'][0][0], clip['WPN_root'][1][0]
        Rh, Ph = clip['hand_l'][0][0], clip['hand_l'][1][0]
        self.R, self.p = Rw.T @ Rh, Rw.T @ (Ph - Pw)
        self.fl = {b: clip[parent[b]][0][0].T @ clip[b][0][0] for b in fingers}


def two_bone(A, E0, T, L1, L2):
    d = T - A
    dist = np.clip(np.linalg.norm(d), abs(L1 - L2) + 1e-3, L1 + L2 - 1e-3)
    x = unit(d)
    y = unit((E0 - A) - x * ((E0 - A) @ x))
    a = (L1 * L1 - L2 * L2 + dist * dist) / (2 * dist)
    return A + x * a + y * np.sqrt(max(L1 * L1 - a * a, 0.0)), A + x * dist


def layer_arm(R, P, Rh_t, Ph_t, bind):
    """R, P: base rigid rotations / positions of ARM bones. Returns new R, P, info."""
    A, E0, H0 = P[UP], P[LO], P[HA]
    L1, L2 = np.linalg.norm(E0 - A), np.linalg.norm(H0 - E0)
    E1, H1 = two_bone(A, E0, Ph_t, L1, L2)
    u0, f0, u1, f1 = E0 - A, H0 - E0, E1 - A, H1 - E1
    n0, n1 = np.cross(u0, f0), np.cross(u1, f1)
    Q = AH.frame(u1, n1) @ AH.frame(u0, n0).T
    Bq = AH.swing(Q @ f0, f1) @ Q
    b0 = np.degrees(np.arctan2(np.linalg.norm(n0), u0 @ f0))
    b1 = np.degrees(np.arctan2(np.linalg.norm(n1), u1 @ f1))
    crease = AH.axis_angle(f1, AH.CREASE_ROLL * (AH.crease_weight(b1) - AH.crease_weight(b0)))
    fe_base = R[LO] @ bind.R[LO].T
    tf_base = 1.5 * wrap(AH.twist_about(R[F1] @ bind.R[F1].T @ fe_base.T, f0))
    fe = crease @ Bq @ fe_base
    tau = AH.twist_about(Rh_t @ (crease @ Bq @ R[HA]).T, f1)
    tf = tf_base + wrap(tau)
    tfc = np.clip(tf, -AH.CAP, AH.CAP)
    fe = AH.axis_angle(f1, tf - tfc) @ fe
    upper = AH.swing(fe @ bind.U0, u1) @ fe
    Rn, Pn = R.copy(), P.copy()
    Rn[UP] = AH.swing(u0, u1) @ R[UP]
    for i in (T1, T2):
        Rn[i] = upper @ bind.R[i]
        Pn[i] = A + bind.st[i] * u1 + upper @ bind.off[i]
    Rn[LO], Pn[LO] = fe @ bind.R[LO], E1
    for i in (F2, F1):
        D = AH.axis_angle(f1, tfc * AH.PRONATION_SHARE[i]) @ fe
        Rn[i] = D @ bind.R[i]
        Pn[i] = E1 + bind.st[i] * f1 + D @ bind.off[i]
    Rn[HA], Pn[HA] = Rh_t, H1
    return Rn, Pn, dict(eps=np.degrees(abs(tf - tfc)), tf=np.degrees(abs(tfc)), short=np.linalg.norm(H1 - Ph_t),
                        upper=np.degrees(abs(wrap(AH.twist_about((upper @ bind.R[T2]) @ R[T2].T, u1)))))


def study(gun, index, bind_names, bind_parents):
    bind = AH.Bind(gun)
    names = index['bones']
    parent = {n: bind_names[bind_parents[bind_names.index(n)]] for n in names if n != 'WPN_root'}
    fingers = [n for n in names if n not in ARM and n != 'WPN_root']
    cache = {}

    def clip(k):
        if k not in cache:
            cache[k] = load(index['clips'][k])
        return cache[k]
    gb = Grip(clip(IDLE[gun][0])[0], fingers, parent)
    rows = []
    for fam in FAMS:
        gf = Grip(clip(IDLE[gun][1].format(f=fam))[0], fingers, parent)
        RO, pO = gb.R.T @ gf.R, gb.R.T @ (gf.p - gb.p)
        rvO = Rot.from_matrix(RO).as_rotvec()
        for key in index['clips']:
            if f'/{fam}/' not in key:
                continue
            bk, act = base_key(key, fam)
            (Bc, n), (Fc, nf) = clip(bk), clip(key)
            assert n == nf, (key, n, nf)
            m = {k: [] for k in ('w', 'gun_cm', 'gun_deg', 'hand_cm', 'hand_deg', 'hand_path_cm', 'finger_deg',
                                 'elbow_cm', 'eps', 'tf', 'short', 'recon_deg', 'recon_cm', 'fam_hand_cm')}
            for k in range(n):
                Rw, Pw = Bc['WPN_root'][0][k], Bc['WPN_root'][1][k]
                R = np.array([Bc[b][0][k] for b in ARM])
                P = np.array([Bc[b][1][k] for b in ARM])
                Rg, pg = Rw.T @ R[HA], Rw.T @ (P[HA] - Pw)
                w = (1 - ss(W_POS, np.linalg.norm(pg - gb.p))) * (1 - ss(W_ANG, ang(gb.R.T @ Rg)))
                Rt = Rg @ Rot.from_rotvec(w * rvO).as_matrix()
                pt = pg + Rg @ (w * pO)
                Rn, Pn, info = layer_arm(R, P, Rw @ Rt, Pw + Rw @ pt, bind)
                if w == 0:
                    m['recon_deg'].append(max(ang(Rn[i] @ R[i].T) for i in range(8)))
                    m['recon_cm'].append(float(np.abs(Pn - P).max()))
                FRw, FPw = Fc['WPN_root'][0][k], Fc['WPN_root'][1][k]
                FRh, FPh = Fc['hand_l'][0][k], Fc['hand_l'][1][k]
                FRg, Fpg = FRw.T @ FRh, FRw.T @ (FPh - FPw)
                fr = 0.0
                for b in fingers:
                    lb = Bc[parent[b]][0][k].T @ Bc[b][0][k]
                    lw = Rot.from_matrix(lb) * Rot.from_rotvec(w * (Rot.from_matrix(lb).inv() * Rot.from_matrix(gf.fl[b])).as_rotvec())
                    lf = Fc[parent[b]][0][k].T @ Fc[b][0][k]
                    fr = max(fr, ang(lw.as_matrix().T @ lf))
                m['w'].append(w)
                m['gun_cm'].append(np.linalg.norm(Pw - FPw))
                m['gun_deg'].append(ang(Rw.T @ FRw))
                m['hand_cm'].append(np.linalg.norm(pt - Fpg))
                m['hand_deg'].append(ang(Rt.T @ FRg))
                m['hand_path_cm'].append(np.linalg.norm(Pn[HA] - FPh))
                m['finger_deg'].append(fr)
                m['elbow_cm'].append(np.linalg.norm(Pn[LO] - Fc['lowerarm_l'][1][k]))
                m['fam_hand_cm'].append(np.linalg.norm(Fpg - gf.p))
                for q in ('eps', 'tf', 'short'):
                    m[q].append(info[q])
            m = {k: np.array(v) for k, v in m.items()}
            g = m['w'] > 0.99
            mx = lambda a, s=None: float(a[s].max()) if (s is None or s.any()) and len(a) else 0.0
            rows.append(dict(gun=gun, fam=fam, act=act, keys=n, grip_share=float(g.mean()),
                             gun_cm=mx(m['gun_cm']), gun_deg=mx(m['gun_deg']),
                             hand_cm_grip=mx(m['hand_cm'], g), hand_deg_grip=mx(m['hand_deg'], g),
                             hand_cm_all=mx(m['hand_cm']), hand_path_cm_all=mx(m['hand_path_cm']),
                             finger_deg_grip=mx(m['finger_deg'], g), finger_deg_all=mx(m['finger_deg']),
                             elbow_cm_grip=mx(m['elbow_cm'], g), elbow_cm_all=mx(m['elbow_cm']),
                             eps_deg=mx(m['eps']), tf_deg=mx(m['tf']), short_cm=mx(m['short']),
                             recon_deg=mx(m['recon_deg']), recon_cm=mx(m['recon_cm']),
                             base_off_grip_cm=None))
            r = rows[-1]
            print('%-4s %-8s %-22s grip %3.0f%% gun %4.1fcm %4.1f° | hand grip %4.2fcm %4.1f° all %5.1fcm | finger %4.1f°/%4.1f° | elbow %4.1f/%4.1fcm | eps %4.1f° tf %5.1f° short %.2f | recon %.1e°'
                  % (gun, fam, act, 100 * r['grip_share'], r['gun_cm'], r['gun_deg'], r['hand_cm_grip'], r['hand_deg_grip'],
                     r['hand_cm_all'], r['finger_deg_grip'], r['finger_deg_all'], r['elbow_cm_grip'], r['elbow_cm_all'],
                     r['eps_deg'], r['tf_deg'], r['short_cm'], r['recon_deg']), flush=True)
    return rows


def main():
    index = json.loads((HERE / 'inputs.json').read_text())
    out = []
    for gun in sys.argv[1:] or ['PKM', '201']:
        b = json.loads((HERE.parent / 'ArmHinge55' / 'Inputs' / (gun + '_bind.json')).read_text())
        out += study(gun, index[gun], b['names'], b['parents'])
    (HERE / 'study.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
