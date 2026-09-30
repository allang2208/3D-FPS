"""GripLayer56 study v2: "base clip + runtime grip layer" against the authored grip-family clips.

v1 (evaluate_v1.py / study_v1.json) kept the base shoulder and elbow plane: the family idles
move the clavicle (201 ~9 cm, PKM <= 2.5 cm), swing the elbow elsewhere (201 14-24 cm) and turn
the palm 111-155 deg, so v1 reached the family hand only with up to 180 deg of upper-arm roll.

The layer (reference for the C++ runtime; per frame, no history; grip data read once from the
base / family idle first key):
  weight    base hand near the base grip (gun space) -> 1, away (reload, inspect) -> 0;
  clavicle  component-space delta family-idle / base-idle, scaled by weight, arm carried;
  hand      base hand (gun space) * interp(I, inv(G_base) * G_family, weight);
  elbow     base swivel about the shoulder-wrist axis + weight * (family - base idle swivel),
            reference direction fixed in the gun frame; two-bone IK, lengths exact;
  roll      ArmHinge55 anatomical frames of the new arm; the total palm roll is taken
            continuously from the base total, the change of its clamped forearm share (cap
            110 deg) goes to the forearm stations, the rest to the upper-arm roll, so weight 0
            returns the base (ArmHinge55-smoothed) arm unchanged;
  fingers   local slerp(base, family, weight).

python -X utf8 evaluate.py [--pos 1,5] [--ang 6,20] [--out study.json] [PKM|201 ...]
"""
import json, gzip, sys, argparse
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as Rot

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'ArmHinge55'))
import author as AH  # noqa: E402

FAMS = ('angled', 'vertical', 'canted', 'prism')
ARM = AH.BONES
C, UP, T1, T2, LO, F2, F1, HA = range(8)
IDLE = {'PKM': ('/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_idle',
                '/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations/{f}/A_PKM_{f}_idle'),
        '201': ('/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle',
                '/Game/Weapons/LMG201/Accessories22/Animations/{f}/A_LMG201_{f}_idle')}
# the ADS channel (aim, aim_fire) references the aim pair; everything else the idle pair
AIM_ACTS = ('aim', 'aim_fire')


def ref_pair(gun, act):
    b, f = IDLE[gun]
    return (b[:-4] + 'aim', f[:-4] + 'aim') if act in AIM_ACTS else (b, f)


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
    fps = (n - 1) / max(d['seconds'], 1e-6)
    return {name: (R[:, i], v[:, i, :3]) for i, name in enumerate(d['bones'])}, n, fps


def base_key(key, fam):
    name = key.rsplit('/A_', 1)[1]
    act = name.split('_', 2)[2]
    if '/Accessories14/' in key:
        return '/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_' + act, act
    if '/Accessories22/' in key:
        return '/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_' + act, act
    folder = key.split('/Weapons/LMG201/')[1].split('/')[0]
    return key.replace(f'/Animations/{fam}/A_LMG201_{fam}_', '/Animations/base/A_LMG201_base_'), folder + ':' + act


def swivel(E, A, H, r):
    a = unit(H - A)
    v = (E - A) - a * ((E - A) @ a)
    rr = r - a * (r @ a)
    return np.arctan2(a @ np.cross(rr, v), rr @ v)


def elbow_at(A, T, L1, L2, psi, r):
    d = np.clip(np.linalg.norm(T - A), abs(L1 - L2) + 1e-3, L1 + L2 - 1e-3)
    a = unit(T - A)
    along = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
    rr = unit(r - a * (r @ a))
    return A + a * along + AH.axis_angle(a, psi) @ rr * np.sqrt(max(L1 * L1 - along * along, 0.0)), A + a * d


class Grip:
    """First key of an idle: hand_l in WPN_root space, clavicle (component), elbow swivel,
    left finger locals."""

    def __init__(self, clip, fingers, parent, r_gun=None):
        Rw, Pw = clip['WPN_root'][0][0], clip['WPN_root'][1][0]
        g = lambda b: (clip[b][0][0], clip[b][1][0])
        (Rh, Ph), (Rc, Pc), (_, A), (_, E) = g('hand_l'), g('clavicle_l'), g('upperarm_l'), g('lowerarm_l')
        self.R, self.p = Rw.T @ Rh, Rw.T @ (Ph - Pw)
        self.Rw = Rw
        self.Rc, self.Pc = Rc, Pc
        self.r_gun = Rw.T @ unit(E - A) if r_gun is None else r_gun
        self.psi = swivel(E, A, Ph, Rw @ self.r_gun)
        self.fl = {b: clip[parent[b]][0][0].T @ clip[b][0][0] for b in fingers}
        self.arm = (Rh, A, E, Ph)


def anatomical(u, f, bind):
    b = np.degrees(np.arctan2(np.linalg.norm(np.cross(u, f)), u @ f))
    return AH.axis_angle(f, AH.CREASE_ROLL * AH.crease_weight(b)) @ AH.frame(f, np.cross(u, f)) @ bind.FL0.T


def palm_total(R_hand, A, E, H, bind):
    """ArmHinge55 total palm roll (forearm + upper-arm remainder) of an arm pose."""
    return wrap(AH.twist_about(anatomical(E - A, H - E, bind).T @ (R_hand @ bind.R[HA].T), bind.F0))


def layer_arm(R, P, Rh_t, Ph_t, psi, r, bind, total_shift):
    A, E0, H0 = P[UP], P[LO], P[HA]
    L1, L2 = np.linalg.norm(E0 - A), np.linalg.norm(H0 - E0)
    E1, H1 = elbow_at(A, Ph_t, L1, L2, psi, r)
    u0, f0, u1, f1 = E0 - A, H0 - E0, E1 - A, H1 - E1
    Dl0, Dl1 = anatomical(u0, f0, bind), anatomical(u1, f1, bind)
    fe_base = R[LO] @ bind.R[LO].T
    tu_base = wrap(AH.twist_about(fe_base @ Dl0.T, f0))
    tf_base = 1.5 * wrap(AH.twist_about(R[F1] @ bind.R[F1].T @ fe_base.T, f0))
    Rh0 = bind.R[HA]
    total0 = wrap(AH.twist_about(Dl0.T @ (R[HA] @ Rh0.T), bind.F0))
    # branch reference: base total + weight * (family idle - base idle total); never flips
    ref = total0 + total_shift
    total1 = ref + wrap(AH.twist_about(Dl1.T @ (Rh_t @ Rh0.T), bind.F0) - ref)
    cl = lambda x: np.clip(x, -AH.CAP, AH.CAP)
    tf = tf_base + cl(total1) - cl(total0)
    tu = tu_base + (total1 - cl(total1)) - (total0 - cl(total0))
    fe = AH.axis_angle(f1, tu) @ Dl1
    upper = AH.swing(fe @ bind.U0, u1) @ fe
    Rn, Pn = R.copy(), P.copy()
    Rn[UP] = AH.swing(u0, u1) @ R[UP]
    for i in (T1, T2):
        Rn[i] = upper @ bind.R[i]
        Pn[i] = A + bind.st[i] * u1 + upper @ bind.off[i]
    Rn[LO], Pn[LO] = fe @ bind.R[LO], E1
    for i in (F2, F1):
        D = AH.axis_angle(f1, tf * AH.PRONATION_SHARE[i]) @ fe
        Rn[i] = D @ bind.R[i]
        Pn[i] = E1 + bind.st[i] * f1 + D @ bind.off[i]
    Rn[HA], Pn[HA] = Rh_t, H1
    return Rn, Pn, dict(tu=tu, tf=tf, short=np.linalg.norm(H1 - Ph_t))


def study(gun, index, bind_names, bind_parents, wpos, wang, rate):
    bind = AH.Bind(gun)
    names = index['bones']
    parent = {n: bind_names[bind_parents[bind_names.index(n)]] for n in names if n != 'WPN_root'}
    fingers = [n for n in names if n not in ARM and n != 'WPN_root']
    cache = {}

    def clip(k):
        if k not in cache:
            cache[k] = load(index['clips'][k])
        return cache[k]
    refs = {}

    def reference(fam, act):
        """Grip data of the channel's reference pair (runtime: computed once per pair)."""
        pair = ref_pair(gun, act)
        if (fam, pair) not in refs:
            gb = Grip(clip(pair[0])[0], fingers, parent)
            gf = Grip(clip(pair[1].format(f=fam))[0], fingers, parent, gb.r_gun)
            # swivel offset against the base pose carried by the full clavicle delta (the
            # carry itself turns the elbow about the shoulder-wrist axis)
            Mf = gf.Rc @ gb.Rc.T
            carry = lambda p: gf.Pc + Mf @ (p - gb.Pc)
            _, Ab, Eb, Hb = gb.arm
            _, Af, Ef, Hf = gf.arm
            refs[(fam, pair)] = dict(
                gb=gb, gf=gf, rvO=Rot.from_matrix(gb.R.T @ gf.R).as_rotvec(), pO=gb.R.T @ (gf.p - gb.p),
                rvC=Rot.from_matrix(Mf).as_rotvec(), dPc=gf.Pc - gb.Pc,
                # family elbow swivel measured from the carried base elbow (runtime reference)
                dpsi=swivel(Ef, Af, Hf, carry(Eb) - carry(Ab)),
                dtotal=wrap(palm_total(*gf.arm, bind) - palm_total(*gb.arm, bind)))
        return refs[(fam, pair)]
    rows = []
    for fam in FAMS:
        for key in index['clips']:
            if f'/{fam}/' not in key:
                continue
            bk, act = base_key(key, fam)
            ref = reference(fam, act)
            gb, gf, rvO, pO, rvC, dPc, dpsi, dtotal = (ref[x] for x in ('gb', 'gf', 'rvO', 'pO', 'rvC', 'dPc', 'dpsi', 'dtotal'))
            (Bc, n, fps), (Fc, nf, _) = clip(bk), clip(key)
            assert n == nf, (key, n, nf)
            L = {k: [] for k in ('w', 'Rt', 'pt', 'E', 'H', 'tu', 'tf', 'short', 'recon_deg', 'recon_cm', 'RU', 'RF')}
            state = None
            for k in range(n):
                Rw, Pw = Bc['WPN_root'][0][k], Bc['WPN_root'][1][k]
                R = np.array([Bc[b][0][k] for b in ARM])
                P = np.array([Bc[b][1][k] for b in ARM])
                R0, P0 = R.copy(), P.copy()
                Rg, pg = Rw.T @ R[HA], Rw.T @ (P[HA] - Pw)
                target = (1 - ss(wpos, np.linalg.norm(pg - gb.p))) * (1 - ss(wang, ang(gb.R.T @ Rg)))
                # temporal limit (runtime: per channel, reset when its clip changes), eased
                state = target if state is None or rate <= 0 else state + np.clip(target - state, -rate / fps, rate / fps)
                w = state if rate <= 0 else state * state * (3 - 2 * state)
                M = Rot.from_rotvec(w * rvC).as_matrix()
                Pc = P[C].copy()
                for i in range(8):
                    R[i] = M @ R[i]
                    P[i] = Pc + w * dPc + M @ (P[i] - Pc)
                Rt = Rg @ Rot.from_rotvec(w * rvO).as_matrix()
                pt = pg + Rg @ (w * pO)
                # elbow: the carried base elbow turned by weight * swivel offset about the new
                # shoulder-wrist axis (no fixed reference that the arm could line up with)
                Rn, Pn, info = layer_arm(R, P, Rw @ Rt, Pw + Rw @ pt, w * dpsi, P[LO] - P[UP], bind, w * dtotal)
                if w == 0:
                    L['recon_deg'].append(max(ang(Rn[i] @ R0[i].T) for i in range(8)))
                    L['recon_cm'].append(float(np.abs(Pn - P0).max()))
                for q, v in (('w', w), ('Rt', Rt), ('pt', pt), ('E', Pn[LO]), ('H', Pn[HA]), ('tu', info['tu']),
                             ('tf', info['tf']), ('short', info['short']), ('RU', Rn[T2]), ('RF', Rn[F1])):
                    L[q].append(v)
            L = {q: np.array(v) for q, v in L.items()}
            w = L['w']
            FRw, FPw = Fc['WPN_root']
            FRg = np.einsum('nji,njk->nik', FRw, Fc['hand_l'][0])
            Fpg = np.einsum('nji,nj->ni', FRw, Fc['hand_l'][1] - FPw)
            BRw, BPw = Bc['WPN_root']
            # fingers, vectorised: layered local = slerp(base local, family idle local, w)
            fr = np.zeros(n)
            for b in fingers:
                lb = np.einsum('nji,njk->nik', Bc[parent[b]][0], Bc[b][0])
                lf = np.einsum('nji,njk->nik', Fc[parent[b]][0], Fc[b][0])
                Rb = Rot.from_matrix(lb)
                d = (Rb.inv() * Rot.from_matrix(np.broadcast_to(gf.fl[b], lb.shape))).as_rotvec()
                lw = Rb * Rot.from_rotvec(d * w[:, None])
                fr = np.maximum(fr, np.degrees(np.linalg.norm((lw.inv() * Rot.from_matrix(lf)).as_rotvec(), axis=1)))
            hand_deg = np.degrees(np.linalg.norm((Rot.from_matrix(L['Rt']).inv() * Rot.from_matrix(FRg)).as_rotvec(), axis=1))
            spin = lambda Rs: np.degrees(np.linalg.norm((Rot.from_matrix(Rs[:-1]).inv() * Rot.from_matrix(Rs[1:])).as_rotvec(), axis=1)) * fps
            speed = lambda X: np.linalg.norm(np.diff(X, axis=0), axis=1) * fps
            g = w > 0.99
            mx = lambda a, s=None: float(a[s].max()) if len(a) and (s is None or s.any()) else 0.0
            row = dict(gun=gun, fam=fam, act=act, keys=n, fps=fps, grip_share=float(g.mean()),
                       gun_cm=mx(np.linalg.norm(BPw - FPw, axis=1)),
                       gun_deg=mx(np.degrees(np.linalg.norm((Rot.from_matrix(BRw).inv() * Rot.from_matrix(FRw)).as_rotvec(), axis=1))),
                       hand_cm_grip=mx(np.linalg.norm(L['pt'] - Fpg, axis=1), g), hand_deg_grip=mx(hand_deg, g),
                       hand_cm_all=mx(np.linalg.norm(L['H'] - Fc['hand_l'][1], axis=1)), hand_deg_all=mx(hand_deg),
                       finger_deg_grip=mx(fr, g), finger_deg_all=mx(fr),
                       elbow_cm_grip=mx(np.linalg.norm(L['E'] - Fc['lowerarm_l'][1], axis=1), g),
                       elbow_cm_all=mx(np.linalg.norm(L['E'] - Fc['lowerarm_l'][1], axis=1)),
                       spin_layer=mx(spin(L['Rt'])), spin_family=mx(spin(FRg)),
                       elbow_speed_layer=mx(speed(L['E'])), elbow_speed_family=mx(speed(Fc['lowerarm_l'][1])),
                       upper_roll_deg=mx(np.degrees(np.abs(wrap(L['tu'])))), forearm_deg=mx(np.degrees(np.abs(L['tf']))),
                       # angular speed of the upper-arm / forearm skin helpers (flip detector)
                       upper_spin_layer=mx(spin(L['RU'])), upper_spin_family=mx(spin(Fc['upperarm_twist_02_l'][0])),
                       fore_spin_layer=mx(spin(L['RF'])), fore_spin_family=mx(spin(Fc['lowerarm_twist_01_l'][0])),
                       roll_jump_deg=mx(np.degrees(np.abs(np.diff(L['tu'])))) if n > 1 else 0.0,
                       short_cm=mx(L['short']), recon_deg=mx(L['recon_deg']), recon_cm=mx(L['recon_cm']))
            rows.append(row)
            print('%-4s %-8s %-26s grip %3.0f%% gun %4.1fcm %4.1f° | hand grip %4.2fcm %4.1f° all %5.1fcm %5.1f° | finger %4.1f/%4.1f° | elbow %4.1f/%4.1fcm | spin %5.0f/%5.0f°/s elbow v %4.0f/%4.0fcm/s | upper %5.1f° fore %5.1f° jump %4.1f° | short %.2f recon %.1e° %.1e cm'
                  % (gun, fam, act, 100 * row['grip_share'], row['gun_cm'], row['gun_deg'], row['hand_cm_grip'], row['hand_deg_grip'],
                     row['hand_cm_all'], row['hand_deg_all'], row['finger_deg_grip'], row['finger_deg_all'], row['elbow_cm_grip'],
                     row['elbow_cm_all'], row['spin_layer'], row['spin_family'], row['elbow_speed_layer'], row['elbow_speed_family'],
                     row['upper_roll_deg'], row['forearm_deg'], row['roll_jump_deg'], row['short_cm'], row['recon_deg'], row['recon_cm']), flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pos', default='1,5')
    ap.add_argument('--ang', default='6,20')
    ap.add_argument('--rate', type=float, default=0.0, help='max weight change per second (0 = none)')
    ap.add_argument('--out', default='study.json')
    ap.add_argument('--acts', default='', help='comma list of actions to study (default all)')
    ap.add_argument('guns', nargs='*', default=['PKM', '201'])
    a = ap.parse_args()
    wpos, wang = [float(x) for x in a.pos.split(',')], [float(x) for x in a.ang.split(',')]
    index = json.loads((HERE / 'inputs.json').read_text())
    if a.acts:
        keep = set(a.acts.split(','))
        for g in index:
            index[g]['clips'] = {k: c for k, c in index[g]['clips'].items()
                                 if k.endswith('_idle') or any(k.endswith('_' + x) for x in keep)}
    out = []
    for gun in a.guns:
        b = json.loads((HERE.parent / 'ArmHinge55' / 'Inputs' / (gun + '_bind.json')).read_text())
        out += study(gun, index[gun], b['names'], b['parents'], wpos, wang, a.rate)
    (HERE / a.out).write_text(json.dumps(dict(weight_pos_cm=wpos, weight_ang_deg=wang, rate=a.rate, rows=out), indent=1))


if __name__ == '__main__':
    main()
