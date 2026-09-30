"""ArmHinge55 author: anatomical left-arm skin frames for every collected PKM / 201 clip.

The PKM V7 bare arm (also used by the 201) is bound with the elbow hinge on the upper-arm
helpers' local Z (rest bend 39 deg about it); the upper-arm skin is carried only by
upperarm_twist_01/02.  The LeftArm48 'coherent segment' convention carries the palm roll up
into those helpers, so in the support/reload poses the upper arm is rolled off its bend axis
(PKM ~160 deg, 201 up to ~115 deg) and the elbow folds against the skin's anatomy.

Per frame (shoulder, wrist and the hand world matrix fixed; bone lengths exact):
  1. elbow may move up to 6 cm on the shoulder-wrist circle (decided per pose, then
     smoothed) to reduce the roll that cannot go into the forearm;
  2. forearm pronation from the anatomical elbow frame to the hand, capped at +-110 deg and
     ramped over the real forearm stations (lowerarm 0, twist_02 1/3, twist_01 2/3, hand 1);
  3. whatever exceeds the cap stays as a (small) upper-arm roll, applied coherently to the
     upper-arm helpers and the elbow end so the elbow itself remains a pure hinge.

python -X utf8 author.py [PKM|201 ...]
"""
import json, gzip, sys
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as Rot
from scipy.ndimage import gaussian_filter1d

HERE = Path(__file__).resolve().parent
IN, OUT = HERE / 'Inputs', HERE / 'Tracks'
OUT.mkdir(exist_ok=True)
CAP = np.radians(110.0)
# share of the forearm pronation at each forearm skin bone (hand = 1).  Kept low next to the
# elbow: a real forearm turns mostly in its distal half, and a twisted band right beside the
# flexed elbow folds into a crescent crease on the forearm.
PRONATION_SHARE = {4: 0.0, 5: 1 / 3, 6: 2 / 3}
# The skin's modelled elbow crease sits ~20 deg off the bind bend axis (ArmHinge55b, elbow
# close views): the elbow pair is referenced to that, faded in with the elbow bend.
CREASE_ROLL = np.radians(20.0)


def crease_weight(bend_deg):
    w = np.clip((bend_deg - 30.0) / 40.0, 0.0, 1.0)
    return w * w * (3 - 2 * w)
ELBOW_CM = 6.0  # the elbow may move this far on the shoulder-wrist circle
PSI = np.radians(np.arange(-90, 91, 3.0))
BONES = ['clavicle_l', 'upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l',
         'lowerarm_twist_02_l', 'lowerarm_twist_01_l', 'hand_l']
C, UP, T1, T2, LO, F2, F1, HA = range(8)
WRITE = ['upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'lowerarm_l', 'lowerarm_twist_02_l',
         'lowerarm_twist_01_l', 'hand_l']
PARENT = {'upperarm_l': 'clavicle_l', 'upperarm_twist_01_l': 'upperarm_l', 'upperarm_twist_02_l': 'upperarm_l',
          'lowerarm_l': 'upperarm_l', 'lowerarm_twist_02_l': 'lowerarm_l', 'lowerarm_twist_01_l': 'lowerarm_l', 'hand_l': 'lowerarm_l'}


def mat(v):
    m = np.eye(4)
    m[:3, :3] = Rot.from_quat(v[3:7]).as_matrix() * np.array(v[7:10])
    m[:3, 3] = v[:3]
    return m


def rot(m):
    return m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)


def unit(v):
    return v / max(np.linalg.norm(v), 1e-12)


def axis_angle(ax, a):
    return Rot.from_rotvec(unit(ax) * a).as_matrix()


def twist_about(Rm, ax):
    q = Rot.from_matrix(Rm).as_quat()
    return 2 * np.arctan2(q[:3] @ unit(ax), q[3])


def swing(a, b):
    a, b = unit(a), unit(b)
    q = np.r_[np.cross(a, b), 1 + np.clip(a @ b, -1, 1)]
    return Rot.from_quat(unit(q)).as_matrix()


def frame(x, z):
    x = unit(x)
    z = unit(z - x * (z @ x))
    return np.column_stack((x, np.cross(z, x), z))


def pack(m, prev):
    s = np.linalg.norm(m[:3, :3], axis=0)
    q = Rot.from_matrix(m[:3, :3] / s).as_quat()
    if prev is not None and q @ prev < 0:
        q = -q
    return [*m[:3, 3], *q, *s], q


class Bind:
    def __init__(self, gun):
        b = json.loads((IN / (gun + '_bind.json')).read_text())
        rest = {n: mat(v) for n, v in zip(b['names'], b['rest'])}
        par = {n: (b['names'][p] if p >= 0 else None) for n, p in zip(b['names'], b['parents'])}
        for n, p in PARENT.items():
            assert par[n] == p, (gun, n, par[n])
        self.R = [rot(rest[n]) for n in BONES]
        P = [rest[n][:3, 3] for n in BONES]
        self.U0, self.F0 = P[LO] - P[UP], P[HA] - P[LO]
        self.H0 = unit(np.cross(self.U0, self.F0))
        self.FU0, self.FL0 = frame(self.U0, self.H0), frame(self.F0, self.H0)
        self.st, self.off = {}, {}
        for i, (o, ax) in ((T1, (P[UP], self.U0)), (T2, (P[UP], self.U0)), (F2, (P[LO], self.F0)), (F1, (P[LO], self.F0))):
            s = (P[i] - o) @ ax / (ax @ ax)
            self.st[i], self.off[i] = s, P[i] - o - s * ax


def pinned_smooth(x, sigma):
    """Gaussian smoothing whose first/last values equal the raw per-pose values (the
    correction fades out over 3 sigma), so clip boundaries match their idle poses."""
    x = np.asarray(x, float)
    y = gaussian_filter1d(x, sigma, mode='nearest')
    n = len(x)
    if n < 2:
        return x.copy()
    i = np.arange(n)
    fade = lambda d: np.clip(1 - d / (3 * sigma), 0, 1) ** 2
    return y + (x[0] - y[0]) * fade(i) + (x[-1] - y[-1]) * fade(n - 1 - i)


def solve(Wall, bind):
    n = len(Wall)
    Rh0 = bind.R[HA]
    a = Wall[:, UP, :3, 3]
    e = Wall[:, LO, :3, 3]
    t = Wall[:, HA, :3, 3]

    def elbow(k, psi):
        axis = unit(t[k] - a[k])
        c = a[k] + axis * ((e[k] - a[k]) @ axis)
        return c + axis_angle(axis, psi) @ (e[k] - c)

    def pron(k, E, h_prev, ref):
        u, f = E - a[k], t[k] - E
        h = np.cross(u, f)
        bend = np.degrees(np.arctan2(np.linalg.norm(h), u @ f))
        if h_prev is not None:
            carried = h_prev - unit(u) * (unit(u) @ h_prev)
            w = np.clip((bend - 10.0) / 30.0, 0.0, 1.0)
            w = w * w * (3 - 2 * w)
            h = w * unit(h) + (1 - w) * unit(carried) if np.linalg.norm(h) > 1e-9 else carried
        h = unit(h - unit(u) * (unit(u) @ h))
        Dl = axis_angle(f, CREASE_ROLL * crease_weight(bend)) @ frame(f, h) @ bind.FL0.T
        Dh = rot(Wall[k, HA]) @ Rh0.T
        tau = twist_about(Dl.T @ Dh, bind.F0)
        tau += 2 * np.pi * np.round((ref - tau) / (2 * np.pi))
        return u, f, h, Dl, tau

    wrap = lambda x: (x + np.pi) % (2 * np.pi) - np.pi
    # 1. elbow adjust, decided per pose (no history): least upper-arm remainder beyond the
    #    forearm cap, elbow moved at most ELBOW_CM on the shoulder-wrist circle.
    psi_raw, h_prev = [], None
    for k in range(n):
        best = None
        for p in PSI:
            E = elbow(k, p)
            d = np.linalg.norm(E - e[k])
            if d > ELBOW_CM:
                continue
            u, f, h, Dl, tau = pron(k, E, h_prev, 0.0)
            tau = wrap(tau)
            rem = abs(tau) - CAP if abs(tau) > CAP else 0.0
            cost = rem ** 2 + .02 * (d / 5.0) ** 2
            if best is None or cost < best[0] - 1e-9:
                best = (cost, p, h)
        _, p, h_prev = best
        psi_raw.append(p)
    psi = pinned_smooth(np.unwrap(psi_raw), 6)
    # 2. pronation split with the smoothed elbow
    rows, h_prev = [], None
    for k in range(n):
        E = elbow(k, psi[k])
        u, f, h, Dl, tau = pron(k, E, h_prev, 0.0)
        h_prev = h
        rows.append((E, u, f, h, Dl, wrap(tau)))
    tau = np.array([r[5] for r in rows])
    tf = np.clip(pinned_smooth(np.clip(tau, -CAP, CAP), 4), -CAP, CAP)
    tu = wrap(tau - tf)
    # before: current helper roll off the bend axis (report)
    before = []
    for k, (E, u, f, h, Dl, _) in enumerate(rows):
        Du = frame(Wall[k, LO, :3, 3] - a[k], unit(np.cross(Wall[k, LO, :3, 3] - a[k], t[k] - Wall[k, LO, :3, 3]))) @ bind.FU0.T
        cur = rot(Wall[k, T2]) @ bind.R[T2].T
        before.append(twist_about(Du.T @ cur, bind.U0))
    out = []
    for k, (E, u, f, h, Dl, _) in enumerate(rows):
        Wn = {}
        sc = [np.linalg.norm(Wall[k, i, :3, :3], axis=0) for i in range(8)]
        fe = axis_angle(f, tu[k]) @ Dl
        upper = swing(fe @ bind.U0, u) @ fe
        m = Wall[k, UP].copy()
        m[:3, :3] = (swing(Wall[k, LO, :3, 3] - a[k], u) @ rot(Wall[k, UP])) * sc[UP]
        Wn[UP] = m
        for i in (T1, T2):
            m = np.eye(4)
            m[:3, :3] = (upper @ bind.R[i]) * sc[i]
            m[:3, 3] = a[k] + bind.st[i] * u + upper @ bind.off[i]
            Wn[i] = m
        for i, s in ((LO, 0.0), (F2, bind.st[F2]), (F1, bind.st[F1])):
            D = axis_angle(f, tf[k] * PRONATION_SHARE[i]) @ fe
            m = np.eye(4)
            m[:3, :3] = (D @ bind.R[i]) * sc[i]
            m[:3, 3] = E + (0 if i == LO else bind.st[i]) * f + (0 if i == LO else 1) * (D @ bind.off.get(i, np.zeros(3)))
            Wn[i] = m
        Wn[HA] = Wall[k, HA].copy()
        Wn[C] = Wall[k, C]
        out.append(Wn)
    info = dict(psi=np.degrees(psi), tau=np.degrees(tau), forearm=np.degrees(tf), upper=np.degrees(tu),
                before=np.degrees(np.unwrap(before)))
    return out, info


def main():
    guns = sys.argv[1:] or ['PKM', '201']
    index = json.loads((HERE / 'inputs.json').read_text())
    report = json.loads((HERE / 'authoring.json').read_text()) if (HERE / 'authoring.json').exists() else {}
    for gun in guns:
        bind = Bind(gun)
        for key, c in index[gun]['clips'].items():
            with gzip.open(c['file'], 'rt', encoding='utf8') as f:
                d = json.load(f)
            assert d['bones'] == BONES
            Wall = np.array([[mat(v) for v in fr] for fr in d['world']])
            out, info = solve(Wall, bind)
            tracks, prev = {n: [] for n in WRITE}, {n: None for n in WRITE}
            herr = lerr = 0.0
            for k, Wn in enumerate(out):
                for n in WRITE:
                    i, p = BONES.index(n), BONES.index(PARENT[n])
                    row, prev[n] = pack(np.linalg.inv(Wn[p]) @ Wn[i], prev[n])
                    tracks[n].append(row)
                herr = max(herr, float(np.abs(Wn[HA] - Wall[k, HA]).max()))
                lerr = max(lerr, abs(np.linalg.norm(Wn[LO][:3, 3] - Wn[UP][:3, 3]) - np.linalg.norm(Wall[k, LO, :3, 3] - Wall[k, UP, :3, 3])),
                           abs(np.linalg.norm(Wn[HA][:3, 3] - Wn[LO][:3, 3]) - np.linalg.norm(Wall[k, HA, :3, 3] - Wall[k, LO, :3, 3])))
            fn = OUT / Path(c['file']).name
            with gzip.open(fn, 'wt', encoding='utf8') as f:
                json.dump({'asset': key, 'source_sha256': c['sha256'], 'keys': len(out), 'tracks': tracks}, f, separators=(',', ':'))
            wrap = lambda x: (x + 180) % 360 - 180
            r = dict(tracks=str(fn), keys=len(out),
                     before_roll_off_deg=[float(wrap(info['before']).min()), float(wrap(info['before']).max())],
                     forearm_pronation_deg=[float(info['forearm'].min()), float(info['forearm'].max())],
                     upper_roll_deg=[float(info['upper'].min()), float(info['upper'].max())],
                     swivel_deg=[float(info['psi'].min()), float(info['psi'].max())], hand_world_error=herr, bone_length_error_cm=lerr)
            report[key] = r
            print('ARMHINGE55', gun, key.split('/')[-1], 'before %4.0f..%4.0f -> upper %4.0f..%4.0f forearm %4.0f..%4.0f swivel %3.0f..%3.0f hand-err %.1e len-err %.1e' % (
                *r['before_roll_off_deg'], *r['upper_roll_deg'], *r['forearm_pronation_deg'], *r['swivel_deg'], herr, lerr), flush=True)
    (HERE / 'authoring.json').write_text(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
