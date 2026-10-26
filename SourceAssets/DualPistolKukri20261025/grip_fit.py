"""Fit the reversed kukri inside the accepted VRE left fist: no skin inside the handle, every finger on it.

Works in the VRE source pose (component space) on the V9 BareArmsV7 surface with its JC_ correctives.
Variables: kukri offset/rotation in the fist (kukri-local cm / degrees) and one flexion scale per digit
(scales each joint's rotation away from the native rest-local, metacarpals unchanged). The kukri SDF is
a voxel field of the watertight mesh (0.08 cm). Writes grip.json (`--accept`): kukri_in_hand relative to
hand_l and the adjusted left digit component transforms, consumed by author_idle.py.
"""
import json, sys
from pathlib import Path
import numpy as np
import trimesh
from scipy import ndimage
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
import author_idle as A

DIGITS = ('thumb', 'index', 'middle', 'ring', 'pinky')
PITCH = 0.08
START_ON_HANDLE = -8.5   # previous fist position on the handle (kukri z, cm)
BOUNDS = np.array([[-2.5, 2.5], [-2.0, 2.0], [4.0, 8.0], [-15, 15], [-15, 15], [-45, 45],
                   [.35, 1.5], [.5, 1.5], [.5, 1.5], [.5, 1.5], [.5, 1.5],
                   [-45, 45], [-45, 45], [-45, 45]], float)
# R2 (user): hold the kukri further forward, at the middle of the handle (flare starts near -10, blade at +7.5).
SLIM_CENTRE = -2.0   # the handle is a uniform 3.5 x 1.7 cm between -6 and +6; the pommel flares below -9


def kukri_sdf():
    km = np.load(P / 'kukri_mesh.npz')
    mesh = trimesh.Trimesh(km['X'], km['T'], process=False)
    lo = np.array([-4.0, -3.0, -17.5]); hi = np.array([6.0, 3.0, 10.0])
    vox = mesh.voxelized(PITCH).fill()
    occ = vox.matrix; origin = vox.transform[:3, 3]
    shape = np.ceil((hi - lo) / PITCH).astype(int) + 1
    grid = np.zeros(shape, bool)
    off = np.round((origin - lo) / PITCH).astype(int)
    src = [slice(max(0, -o), min(s, g - o)) for o, s, g in zip(off, occ.shape, shape)]
    dst = [slice(max(0, o), max(0, o) + (sl.stop - sl.start)) for o, sl in zip(off, src)]
    grid[tuple(dst)] = occ[tuple(src)]
    sdf = (ndimage.distance_transform_edt(~grid) - ndimage.distance_transform_edt(grid)) * PITCH
    return sdf, lo


SDF, LO = kukri_sdf()


def sample(points):
    idx = ((points - LO) / PITCH).T
    return ndimage.map_coordinates(SDF, idx, order=1, mode='nearest')


surface = A.surface
LR, LP = A.LR, A.LP
source, fist = A.vertical_fist()   # raw VRE fist; A.FIST already carries grip.json digits
labels = []
for w in surface['W']:
    top = max(w, key=w.get) if w else ''
    labels.append(next((d for d in DIGITS if top.startswith(d) and top.endswith('_l')), 'palm' if top == 'hand_l' else ''))
labels = np.array(labels)
HAND = np.where(labels != '')[0]
HLAB = labels[HAND]
BONES = sorted({b for i in HAND for b in surface['W'][i]})
WM = np.zeros((len(HAND), len(BONES)))
for r, i in enumerate(HAND):
    for b, v in surface['W'][i].items(): WM[r, BONES.index(b)] = v
WM /= WM.sum(axis=1, keepdims=True)
REST_INV = {b: np.linalg.inv(LR[b]) for b in BONES}
X0 = surface['X'][HAND]
SHAPES = {n: s[HAND] for n, s in surface['shapes'].items()}
# Palmar side of each digit: vertices facing the handle axis in the start pose.
K_FIST = A.kukri_frame(fist['centre'], fist['axis'], fist['edge'], 0.0)


def digit_chain(d):
    return [f'{d}_0{k}_l' for k in (1, 2, 3)]


def flexed(scales, thumb_euler=(0, 0, 0)):
    """Scale each digit joint's rotation away from its rest-local; returns new component transforms."""
    pose = {n: m.copy() for n, m in source.items()}
    for d, s in zip(DIGITS, scales):
        for n in digit_chain(d):
            par = A.LP[n]
            local = np.linalg.inv(source[par]) @ source[n]
            rest_local = np.linalg.inv(LR[par]) @ LR[n]
            delta = R.from_matrix(rest_local[:3, :3].T @ local[:3, :3]).as_rotvec()
            local[:3, :3] = rest_local[:3, :3] @ R.from_rotvec(delta * s).as_matrix()
            # The thumb CMC joint can also abduct/curl on top of the flex scale,
            # so the thumb tip can lie along the handle instead of into the pommel flare.
            if n == 'thumb_01_l' and np.any(thumb_euler):
                local[:3, :3] = local[:3, :3] @ R.from_euler('xyz', thumb_euler, degrees=True).as_matrix()
            pose[n] = pose[par] @ local
    return pose


def kukri_in_fist(x):
    dx, dy, dz, rx, ry, rz = x[:6]
    m = np.eye(4); m[:3, :3] = R.from_euler('xyz', [rx, ry, rz], degrees=True).as_matrix()
    m[:3, 3] = [dx, dy, -(START_ON_HANDLE + dz)]   # fist centre lands at kukri z = START + dz
    # Edge 'in' turns the kukri half a turn about its handle in the fist frame.
    return np.diag([-1, -1, 1, 1]) @ m


def skin_hand(pose):
    sig = {n: (m[:3, 3], R.from_matrix(m[:3, :3]).as_quat()) for n, m in pose.items()}
    x = X0.copy()
    for name, a in A.DRIVER.weights(sig).items():
        if a > .001 and name in SHAPES and (name.endswith('_L') or '_L_' in name):
            x = x + a * SHAPES[name]
    out = np.zeros_like(x)
    for j, b in enumerate(BONES):
        w = WM[:, j]
        if not w.any(): continue
        xf = pose[b] @ REST_INV[b]
        out += (x @ xf[:3, :3].T + xf[:3, 3]) * w[:, None]
    return out


def evaluate(x):
    pose = flexed(x[6:11], x[11:14])
    K = K_FIST @ kukri_in_fist(x)
    inv = np.linalg.inv(K)
    local = skin_hand(pose) @ inv[:3, :3].T + inv[:3, 3]
    return sample(local), pose, K


def cost(x, verbose=False):
    d, _, _ = evaluate(x)
    terms = {}
    inside = np.minimum(d, 0)
    terms['penetration'] = float(np.sum(inside ** 2) * 60 + inside.min() ** 2 * 400)
    for g in DIGITS + ('palm',):
        m = d[HLAB == g].min()
        tol = .08 if g in ('index', 'middle', 'ring', 'pinky') else .15
        terms['contact_' + g] = max(0, m - tol) ** 2 * (30 if g != 'palm' else 15)
    terms['flex'] = float(np.sum((x[6:11] - 1) ** 2)) * 4 + float(np.sum((x[11:14] / 15) ** 2))
    # Keep the thumb side off the flared pommel: prefer the fist on the uniform part of the handle.
    terms['slim'] = ((START_ON_HANDLE + x[2] - SLIM_CENTRE) / 0.6) ** 2
    terms['offset'] = float(np.sum(x[:2] ** 2)) * .3 + float(np.sum((x[3:6] / 10) ** 2)) * .3
    if verbose:
        print({k: round(v, 4) for k, v in terms.items()})
        print({g: round(float(d[HLAB == g].min()), 3) for g in DIGITS + ('palm',)}, 'deepest', round(float(d.min()), 3))
    return sum(terms.values())


def main():
    x0 = np.array([0, 0, 6.5, 0, 0, 0, 1, 1, 1, 1, 1, 0, 0, 0], float)
    print('start (previous grip at %.1f cm)' % START_ON_HANDLE); cost(np.r_[0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1.], True)
    best = None
    for k, dz in enumerate((5.5, 6.5, 7.5)):
        xs = x0.copy(); xs[2] = dz
        res = minimize(cost, xs, method='Powell', bounds=BOUNDS, options={'maxiter': 8000, 'xtol': 1e-3, 'ftol': 1e-6})
        print('start', k, 'cost', round(res.fun, 4), flush=True)
        if best is None or res.fun < best.fun: best = res
    print('best', np.round(best.x, 3)); cost(best.x, True)
    if '--accept' in sys.argv:
        _, pose, K = evaluate(best.x)
        hand = source['hand_l']
        digits = {n: pose[n].tolist() for n in pose if any(n.startswith(d) for d in DIGITS) and n.endswith('_l')}
        (P / 'grip.json').write_text(json.dumps({
            'kukri_in_hand': (np.linalg.inv(hand) @ K).tolist(), 'source_hand_l': hand.tolist(), 'digits': digits,
            'parameters': {'offset_cm': best.x[:3].round(3).tolist(), 'rotation_deg': best.x[3:6].round(2).tolist(),
                           'digit_flex_scale': dict(zip(DIGITS, best.x[6:11].round(3).tolist())),
                           'thumb_cmc_deg': best.x[11:14].round(2).tolist(),
                           'fist_centre_on_handle_cm': round(float(START_ON_HANDLE + best.x[2]), 2), 'edge': 'in'},
            'cost': round(float(best.fun), 5)}, indent=1), encoding='utf-8')
        print('ACCEPTED')


if __name__ == '__main__':
    main()
