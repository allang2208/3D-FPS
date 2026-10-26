"""Author the pistol+offhand-kukri quick melee (F): ONE left-hand thrust after BV1hQnh6hEio's knife cycles.

V2 (user 2026-10-25): the three-slash flourish only twisted the left hand in place -> one thrust.
V3 (user: direction right; path and trajectory still off, especially how the left upper arm is raised; more impact).
Re-read on all three knife cycles at 1080p (frames 1178-1196, 1210-1230, 1243-1261; cycle C is the clearest):
  - the crossed hold swings out to the RIGHT, the pistol's muzzle turning to point left (1245-1246 / 1212-1213)
  - 1-2 empty frames: the left fist travels under the view to the LEFT side and loads there, elbow up
  - the fist sweeps in HORIZONTALLY from the left edge (forearm level, entering at ~0.3-0.5 of the frame height,
    so the upper arm is raised out to the side), passes just right of centre (1216 / 1249: ref NDC 0.2, 0.4) and
    hooks up and forward into the centre (1217-1219 / 1250-1252: 0.1, 0.07 -> 0.05, 0.05), arm near full length
  - the fist withdraws to the right and down (1220-1221 / 1253-1254) while the pistol rises from the bottom right,
    muzzle up-left (1255-1256), and settles back over the fist into the crossed hold (1257-1260)
The viewmodel shoulder root sits 31 cm under the eye, too low for that elbow height: it rises ~9 cm and comes ~4 cm
forward over the punch (shrug + protraction, always off screen), and the clavicle follows a share of the upper arm
(same fix as the uppercut) so the raised upper arm keeps its volume.

Each key is a controls dict fed through author_idle.build() (V4 arm solver, contact-fitted reversed grip). Fist
positions are reference-FOV (~44 deg) directions at a reachable depth, as in the accepted idle; gun keys are camera
cm. fit_thrust.py then fits blade/knuckle/elbow/shoulder under the wrist limits (Work/strike/thrust_fit.json).
"""
import json, math, sys
from pathlib import Path
import numpy as np

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_idle as A

OUT = P / 'Work' / 'strike'
OUT.mkdir(parents=True, exist_ok=True)

REF_T = math.tan(math.radians(44.0 / 2))          # reference viewmodel vertical FOV ~44
REF_TH = REF_T * 16 / 9
def at(ndc, depth):
    nx, ny = ndc
    return (np.array([1.0, nx * REF_TH, -ny * REF_T]) * depth).tolist()

HIP = A.controls
REST = A.build(HIP)
REST_BLADE = HIP['kukri']['blade_direction']
REST_KNUCKLE = HIP['kukri']['knuckle_direction']
AIM = HIP['gun']['aim_point']
LSH = HIP['left_shoulder']
LP = HIP['left_pole']

GUN_OUT = ((14, 33, -18), (150, -950, -150), 70)          # thrown out past the right edge, muzzle pointing left
GUN_LOW = ((16, 24, -28), (450, -350, 820), 40)           # below the bottom-right edge, muzzle up-left
THRUST_BLADE = (0.99, -0.03, 0.12)
THRUST_KNUCKLE = (-0.10, 0.50, 0.86)


def K(t, fist, depth=None, blade=None, knuckle=None, pole=None, dsh=(0, 0, 0), gun=None, clav=0.0):
    return dict(t=t, fist=fist, depth=depth, blade=blade, knuckle=knuckle, pole=pole, dsh=dsh, gun=gun, clav=clav)


KEYS = [
    K(0.000, 'rest'),
    # the crossed hold swings out to the right, the pistol's muzzle turning left
    K(0.033, (1.15, 0.90), 27, (0.80, 0.45, -0.40), (0.05, 0.40, 0.92), (12, -34, -44), (1, 0, 0), ((27, 12, -4), (800, -450, 350), 32), .1),
    K(0.067, (1.60, 1.40), 25, (0.40, 0.80, -0.45), (0.15, 0.35, 0.92), (12, -34, -46), (1, 0, 0), ((24, 25, -9), (250, -950, 120), 60), .2),
    # under the view to the left side, loading with the elbow up
    K(0.100, (0.90, 3.20), 19, (0.70, 0.20, -0.68), (0.30, 0.55, 0.78), (6, -40, -50), (0, -1, 0), GUN_OUT, .3),
    K(0.133, (-0.30, 3.40), 18, (0.75, -0.05, -0.66), (0.25, 0.55, 0.80), (10, -46, -30), (1, -1, 3), GUN_OUT, .5),
    # loaded just past our wider left edge (the reference's 44 deg frame shows only from our NDC x -0.53 inward)
    K(0.167, (-2.10, 1.60), 20, (0.95, -0.10, 0.30), (-0.10, 0.50, 0.86), (10, -50, -12), (2, -2, 7), GUN_OUT, .7),
    # horizontal drive-in from the left edge (1216/1249) -> hook up and forward into the centre -> full length (1218/1251)
    # accelerating into the hit: 11 cm in 33 ms, then 7 cm in 17 ms to an overshoot; it stops dead on the contact
    # (hit-stop) and recoils 5 cm -- the punch's snap
    K(0.200, (0.24, 0.36), 36, (0.97, 0.00, 0.22), (-0.10, 0.48, 0.87), (24, -46, 2), (3, -2, 10), GUN_OUT, .7),
    K(0.233, (0.10, 0.08), 47, THRUST_BLADE, THRUST_KNUCKLE, (28, -44, 4), (3, -2, 11), GUN_OUT, .7),
    K(0.250, (0.05, 0.05), 54, THRUST_BLADE, THRUST_KNUCKLE, (30, -42, 4), (4, -2, 11), GUN_OUT, .7),
    K(0.267, (0.05, 0.06), 52, THRUST_BLADE, THRUST_KNUCKLE, (30, -42, 3), (4, -2, 11), GUN_OUT, .7),
    K(0.300, (0.07, 0.09), 48.5, THRUST_BLADE, THRUST_KNUCKLE, (28, -42, 0), (3, -2, 10), GUN_LOW, .7),
    # withdraw to the right, clear of the pistol rising from the bottom right with its muzzle up-left (1253-1256)
    K(0.333, (0.40, 0.28), 41, (0.95, 0.15, 0.27), (-0.05, 0.45, 0.89), (24, -40, -6), (3, -1, 8), GUN_LOW, .6),
    K(0.367, (1.35, 0.70), 32, (0.97, 0.12, 0.20), (0.00, 0.50, 0.87), (16, -38, -20), (2, 0, 4), ((20, 6, -25), (380, -330, 860), 34), .45),
    K(0.400, (1.70, 1.90), 26, (0.99, 0.05, 0.12), (0.00, 0.55, 0.84), (12, -38, -40), (1, 0, 1), ((23, 5, -16), (480, -280, 820), 30), .3),
    K(0.433, (1.20, 2.10), 25, (0.99, 0.05, 0.12), (0.00, 0.55, 0.84), (12, -36, -44), (0, 0, 0), ((25, 5, -10), (600, -230, 720), 27), .2),
    # the pistol settles first, the fist rises back under it into the crossed hold
    K(0.500, (1.00, 1.15), 28, REST_BLADE, REST_KNUCKLE, None, (0, 0, 0), ((27, 6, -5), (900, -100, 250), 24), .1),
    K(0.567, (0.98, 0.85), 28.5, REST_BLADE, REST_KNUCKLE, None, (0, 0, 0), ((28.8, 4.4, -1.8), AIM, 21.5), 0.),
    K(0.633, 'rest'),
]
SWINGS = [0.175]
CONTACTS = [0.250]
LENGTH = 0.633
FIT_PATH = OUT / 'thrust_fit.json'


def fitted(k):
    """Apply fit_thrust.py's wrist-limited blade/knuckle/elbow/shoulder for this key, when present."""
    if k['fist'] == 'rest' or not FIT_PATH.exists():
        return k
    f = json.loads(FIT_PATH.read_text(encoding='utf-8')).get('%.3f' % k['t'])
    if not f:
        return k
    return dict(k, blade=tuple(f['blade']), knuckle=tuple(f['knuckle']), pole=tuple(f['pole']),
                dsh=tuple(np.array(k['dsh'], float) + np.array(f['shoulder_delta'])))


def controls_for(k, fit=True):
    if fit:
        k = fitted(k)
    if k['fist'] == 'rest':
        return dict(HIP), REST
    gun = k['gun']
    c = {
        'vertical_fov': 75,
        'gun': ({'rear_sight': list(gun[0]), 'aim_point': list(gun[1]), 'cant_degrees': gun[2]} if gun else dict(HIP['gun'])),
        'right_shoulder': HIP['right_shoulder'], 'right_pole': HIP['right_pole'],
        'left_shoulder': (np.array(LSH) + np.array(k['dsh'])).tolist(),
        'left_pole': list(k['pole'] or LP),
        'kukri': {'fist_centre': at(k['fist'], k['depth']), 'blade_direction': k['blade'] or REST_BLADE,
                  'knuckle_direction': k['knuckle'] or REST_KNUCKLE},
    }
    return c, None


CLAV_VERTS = np.array([w.get('clavicle_l', 0.) for w in A.surface['W']]) > .3
TV = math.tan(math.radians(37.5)); TH = TV * 16 / 9


def visible(X):
    return (X[:, 0] > 8) & (np.abs(X[:, 1]) < X[:, 0] * TH) & (np.abs(X[:, 2]) < X[:, 0] * TV)


def write_npz(b, tag):
    V4 = P.parents[1] / 'SourceAssets/PistolBookPoseV4_20261020'
    geo = np.load(V4 / 'gun_idle.npz')
    xg = 100 * geo['X'] * np.array([1, -1, 1])
    xf = b['G'] @ b['view']
    np.savez_compressed(OUT / ('gun_%s.npz' % tag), X=xg @ xf[:3, :3].T + xf[:3, 3],
                        T=geo['T'][:, ::-1], UV=geo['UV'][:, ::-1], slots=geo['slots'])
    km = np.load(P / 'kukri_mesh.npz')
    Kc = b['Kc']
    np.savez_compressed(OUT / ('kukri_%s.npz' % tag), X=km['X'] @ Kc[:3, :3].T + Kc[:3, 3],
                        T=km['T'], UV=km['UV'], slots=km['slots'])
    X, correctives, _ = A.skin(b['pose'])
    np.savez_compressed(OUT / ('arms_%s.npz' % tag), X=X, T=A.surface['T'], UV=A.surface['UV'])
    return X


def main():
    for old in OUT.glob('*_t*.npz'):
        old.unlink()
    keys = []
    for k in KEYS:
        t = k['t']
        c, built = controls_for(k)
        b = built or A.build(c)
        if built is None and k['clav'] > 0:
            b = dict(b, l={n: m.copy() for n, m in b['l'].items()}, pose=dict(b['pose']))
            A.clavicle_share(b['l'], k['clav'])
            b['pose']['clavicle_l'] = b['l']['clavicle_l']
        tag = 't%03d' % round(t * 1000)
        X = write_npz(b, tag)
        lw, rw = np.array(b['l']['hand_l']), np.array(b['r']['hand_r'])
        G = b['G']
        framing = G.copy(); framing[:3, 3] = G[:3, 3] - G[:3, :3] @ np.array([-2.0, 3.0, -6.5])
        keys.append(dict(t=t,
                         wrist_offset=(lw[:3, 3] - rw[:3, 3]).round(3).tolist(),
                         left_wrist=lw[:3, 3].round(3).tolist(),
                         left_hand=lw.round(6).tolist(),
                         left_shoulder=np.array(b['l']['upperarm_l'])[:3, 3].round(3).tolist(),
                         left_pole=np.array(c['left_pole'], float).round(3).tolist(),
                         clavicle=k['clav'],
                         framing=framing.round(6).tolist(),
                         reach={'left': round(b['ldiag']['reach'], 3), 'right': round(b['rdiag']['reach'], 3)}))
        wl = b['wrists']['l']
        el = A.ndc(b['l']['lowerarm_l'][:3, 3], 75) if b['l']['lowerarm_l'][0, 3] > 1 else ['behind']
        print('t=%.3f fist %s elbow %s reach L %.2f R %.2f | elbow %.0f flex %.0f dev %.0f roll %.0f | clav verts on screen %d' % (
            t, A.ndc(b['K'][:3, 3], 75), el, b['ldiag']['reach'], b['rdiag']['reach'],
            *[float(v) for v in wl], int((visible(X) & CLAV_VERTS).sum())))
    (OUT / 'strike_keys.json').write_text(json.dumps(dict(keys=keys,
        contacts=CONTACTS, swings=SWINGS, length=LENGTH), indent=1), encoding='utf-8')
    print('WROTE', OUT / 'strike_keys.json')
    if '--tween' in sys.argv:
        tween(keys)


def tween(keys, times=(0.150, 0.175, 0.183, 0.192, 0.217, 0.317, 0.350, 0.383)):
    """Preview frames between keys, sampled the way OffhandKukriAuthoredStrike.h::SamplePose + the runtime solve do:
    linear wrist offset (from the live pistol hand), slerped hand, linear shoulder/pole/clavicle share, slerped framing."""
    from scipy.spatial.transform import Rotation as R, Slerp
    idle, view = A.IDLE
    off = np.array([-2.0, 3.0, -6.5])
    for t in times:
        i = max(j for j in range(len(keys) - 1) if keys[j]['t'] <= t)
        a, b = keys[i], keys[i + 1]
        f = (t - a['t']) / (b['t'] - a['t'])
        fa, fb = np.array(a['framing']), np.array(b['framing'])
        rot = Slerp([0, 1], R.from_matrix([fa[:3, :3], fb[:3, :3]]))(f).as_matrix()
        framing = A.matrix(rot, (1 - f) * fa[:3, 3] + f * fb[:3, 3])
        G = A.matrix(rot, framing[:3, 3] + rot @ off)
        gun = {n: G @ m for n, m in idle.items()}
        r, _ = A.solve_arm(A.RR, gun, A.RP, 'r', HIP['right_shoulder'], gun['hand_r'][:3, 3], HIP['right_pole'], gun['hand_r'][:3, :3])
        wrist = r['hand_r'][:3, 3] + (1 - f) * np.array(a['wrist_offset']) + f * np.array(b['wrist_offset'])
        ha, hb = np.array(a['left_hand'])[:3, :3], np.array(b['left_hand'])[:3, :3]
        hand = Slerp([0, 1], R.from_matrix([ha, hb]))(f).as_matrix()
        shoulder = (1 - f) * np.array(a['left_shoulder']) + f * np.array(b['left_shoulder'])
        pole = (1 - f) * np.array(a['left_pole']) + f * np.array(b['left_pole'])
        l, d = A.solve_arm(A.LR, A.FIST[0], A.LP, 'l', shoulder, wrist, pole, hand)
        A.clavicle_share(l, (1 - f) * a['clavicle'] + f * b['clavicle'])
        _, pose = A.wrist_signature(l, r)
        built = dict(G=G, view=view, pose=pose, Kc=l['hand_l'] @ A.GRIP_IN_HAND)
        tag = 't%03d' % round(t * 1000)
        write_npz(built, tag)
        el = l['lowerarm_l'][:3, 3]
        print('tween t=%.3f elbow %s reach %.2f' % (t, A.ndc(el, 75) if el[0] > 1 else 'behind', d['reach']))
    data = json.loads((OUT / 'strike_keys.json').read_text(encoding='utf-8'))
    data['preview_tweens'] = list(times)
    (OUT / 'strike_keys.json').write_text(json.dumps(data, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
