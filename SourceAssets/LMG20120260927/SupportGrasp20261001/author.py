"""Author a fitted 201 underside grasp from its native SVD/AKM-style support pose.

Only authored source data are evaluated. This script does not render or run game tests.
"""
import gzip
import json
import sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
from scipy.optimize import least_squares

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path.insert(0, str(PROJECT / 'SourceAssets/LMG20120260927/ClothReload44/Diagnostics'))
import diag_lib as D

INPUT = json.loads((HERE / 'inputs.json').read_text())
IDLE = '/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_idle'
DIGITS = [n for n in D.NAMES if n.endswith('_l') and n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_'))]

def pose(key):
    with gzip.open(INPUT['201'][key]['file'], 'rt', encoding='utf8') as f:
        data = json.load(f)
    got = {n: D.mat(t) for n, t in zip(data['bones'], data['world'][0])}
    W = D.REST.copy()
    for i, n in enumerate(D.NAMES):
        W[i] = got[n] if n in got else W[D.PARENT[i]] @ (D.REST_INV[D.PARENT[i]] @ D.REST[i]) if D.PARENT[i] >= 0 else D.REST[i]
    return W

def rotation(M):
    return M[:3, :3] / np.linalg.norm(M[:3, :3], axis=0)

def source_local(W, name):
    i = D.BI[name]
    return np.linalg.inv(W[D.PARENT[i]]) @ W[i]

def hand_skin(body):
    arm = np.isin(body.tri_mat, body.ARM_MATS)
    ids = np.unique(body.tris[arm])
    names = np.array(D.NAMES)[body.bi[ids, 0]]
    keep = np.char.endswith(names, '_l') & (np.char.startswith(names, 'hand_') | np.any([np.char.startswith(names, f + '_') for f in ('thumb', 'index', 'middle', 'ring', 'pinky')], 0))
    ids, names = ids[keep], names[keep]
    return D.Skin(body.pos[ids], (body.bi[ids], body.bw[ids])), names

def donor_hand(W0, donor):
    src = INPUT['donors'][donor]
    gw, hw = D.mat(src['world']['WPN_root']), D.mat(src['world']['hand_l'])
    H = np.linalg.inv(gw) @ hw
    G = W0[D.BI['WPN_root']]
    target = np.linalg.inv(G) @ W0[D.BI['hand_l']]
    target[:3, :3] = H[:3, :3]
    # Keep the existing 201 axial support location; donor lateral wrist offset
    # puts the fingers around the side instead of closing into an empty fist.
    target[0, 3] = H[0, 3]
    W = W0.copy()
    W[D.BI['hand_l']] = G @ target
    for n in DIGITS:
        i = D.BI[n]
        L = source_local(W0, n)
        L[:3, :3] = rotation(D.mat(src['local'][n])) * np.linalg.norm(L[:3, :3], axis=0)
        W[i] = W[D.PARENT[i]] @ L
    return W

def curl_axis(name):
    i = D.BI[name]
    next_name = name.replace('_01_', '_02_') if '_01_' in name else name.replace('_02_', '_03_')
    if '_03_' in name:
        previous = D.BI[name.replace('_03_', '_02_')]
        direction = D.REST[i, :3, 3] - D.REST[previous, :3, 3]
    else:
        direction = D.REST[D.BI[next_name], :3, 3] - D.REST[i, :3, 3]
    origin = D.REST[D.BI['hand_l'], :3, 3]
    normal = np.cross(D.REST[D.BI['index_01_l'], :3, 3] - origin,
                      D.REST[D.BI['pinky_01_l'], :3, 3] - origin)
    Rb = rotation(D.REST[i])
    axis = np.cross(Rb.T @ direction, Rb.T @ normal)
    return axis / np.linalg.norm(axis)

def box_distance(points):
    # Closed 201 handguard, in WPN_root centimetres. Its bottom and side walls
    # determine the palm support and finger wrap, rather than the PKM open shell.
    centre = np.array([0.0, 35.5, 4.05])
    half = np.array([3.1, 13.0, 2.65])
    q = np.abs(points - centre) - half
    return np.linalg.norm(np.maximum(q, 0.0), axis=1) + np.minimum(q.max(axis=1), 0.0)

def fit(W0, body):
    Wref = donor_hand(W0, 'SVD')
    skin, tags = hand_skin(body)
    # A fixed subset is used as an authoring constraint; full topology/skin stays intact.
    selected = np.arange(0, len(tags), 5)
    sample_skin = D.Skin(skin.p[selected], (skin.idx[selected], skin.w[selected]))
    sample_tags = tags[selected]
    joints = [f'{f}_{s}_l' for f in ('thumb', 'index', 'middle', 'ring', 'pinky') for s in ('01', '02', '03')]
    locals0 = {n: source_local(Wref, n) for n in DIGITS}
    axes = {n: curl_axis(n) for n in joints}
    reference_curl = np.array([np.degrees(Rot.from_matrix(rotation(source_local(D.REST, n)).T @ rotation(locals0[n])).as_rotvec() @ axes[n]) for n in joints])
    G = W0[D.BI['WPN_root']]
    GI = np.linalg.inv(G)
    Href = GI @ Wref[D.BI['hand_l']]
    reference_points = sample_skin.pose(Wref)
    reference_points = ((GI[:3, :3] @ reference_points.T).T + GI[:3, 3]) * 100.0
    palm_region = np.char.startswith(sample_tags, 'hand_') | (np.char.find(sample_tags, 'metacarpal') >= 0)
    underneath = palm_region & (np.abs(reference_points[:, 0]) < 2.8) & (reference_points[:, 1] > 29.0) & (reference_points[:, 1] < 36.0)
    palm_ids = np.where(underneath)[0]
    palm_ids = palm_ids[np.argsort(reference_points[palm_ids, 2])[-12:]]

    def make(x):
        H = Href.copy()
        H[:3, 3] += np.array([x[0], 0.0, x[1]]) / 100.0
        H[:3, :3] = Rot.from_rotvec(np.radians(x[2:5])).as_matrix() @ H[:3, :3]
        W = Wref.copy()
        W[D.BI['hand_l']] = G @ H
        for n in DIGITS:
            L = locals0[n].copy()
            if n in axes:
                L[:3, :3] = L[:3, :3] @ Rot.from_rotvec(axes[n] * np.radians(x[5 + joints.index(n)])).as_matrix()
            i = D.BI[n]
            W[i] = W[D.PARENT[i]] @ L
        return W

    def residual(x):
        W = make(x)
        pts = sample_skin.pose(W)
        p = ((GI[:3, :3] @ pts.T).T + GI[:3, 3]) * 100.0
        dist = box_distance(p)
        errors = [np.minimum(dist - .10, 0.0) * 12.0]
        for f in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            # Both middle/distal sections participate; an isolated fingertip is
            # insufficient to define the support grasp.
            for segment in ('02', '03'):
                ds = dist[np.char.startswith(sample_tags, f'{f}_{segment}_')]
                if len(ds):
                    errors.append(np.array([np.quantile(ds, .12) - .15]) * 4.0)
        # Keep the supporting palm against the underside. Finger contact alone
        # can otherwise move the hand down and leave an empty fist below it.
        errors.append((p[palm_ids, 2] - (1.4 - .18)) * 10.0)
        errors.append(x[:2] * .25)
        errors.append(x[2:5] * .025)
        errors.append(x[5:] * .016)
        # Keep the middle/distal curl in the natural M4 grasp range. In
        # particular, contact fitting must not solve a missed side wall by
        # folding a DIP joint past a right angle.
        for j in range(1, 5):
            errors.append(np.array([reference_curl[3*j + 1] + x[5 + 3*j + 1] - 60.0,
                                    reference_curl[3*j + 2] + x[5 + 3*j + 2] - 43.0]) * .022)
        # Neighbouring joint corrections follow a natural coupled curl.
        for j in range(5):
            a = x[5 + 3*j:8 + 3*j]
            errors.append(np.array([a[0] - a[1], .65*a[1] - a[2]]) * .008)
        return np.concatenate(errors)

    bound = np.r_[1.8, 1.5, 8.0, 12.0, 8.0, np.tile([25.0, 35.0, 55.0], 5)]
    lower, upper = -bound, bound.copy()
    for j in range(1, 5):
        for s, (lo, hi) in enumerate(((15.0, 85.0), (25.0, 90.0), (18.0, 62.0))):
            i = 5 + 3*j + s
            lower[i] = max(lower[i], lo - reference_curl[3*j+s])
            upper[i] = min(upper[i], hi - reference_curl[3*j+s])
    start = np.clip(np.zeros(len(bound)), lower + .01, upper - .01)
    solution = least_squares(residual, start, bounds=(lower, upper), max_nfev=150, diff_step=.003)
    W = make(solution.x)
    H = GI @ W[D.BI['hand_l']]
    target = {'reference': INPUT['donors']['SVD']['asset'], 'hand_gun': H.tolist(),
              'hand_gun_before': (GI @ W0[D.BI['hand_l']]).tolist(),
              'locals': {n: source_local(W, n).tolist() for n in DIGITS},
              'fit_parameters': solution.x.tolist(), 'preserve_axial_support': True,
              'runtime_tested': False}
    (HERE / 'target.json').write_text(json.dumps(target, indent=1))
    print('SUPPORTGRASP_AUTHORED', solution.x.round(3).tolist(), flush=True)
    return target

if __name__ == '__main__':
    W = pose(IDLE)
    if '--fit' in sys.argv:
        fit(W, D.Body())
        sys.exit(0)
    G = W[D.BI['WPN_root']]
    H = np.linalg.inv(G) @ W[D.BI['hand_l']]
    body = D.Body()
    skin, tags = hand_skin(body)
    local = np.linalg.inv(G)
    pts = skin.pose(W)
    pg = ((local[:3, :3] @ pts.T).T + local[:3, 3]) * 100.0
    print('SOURCE_HAND', H[:3, 3] * 100.0)
    for f in ('hand', 'thumb', 'index', 'middle', 'ring', 'pinky'):
        p = pg[np.char.startswith(tags, f + '_')]
        print('SOURCE_REGION', f, p.min(0).round(2), p.max(0).round(2))
    for donor, src in INPUT['donors'].items():
        gw, hw = D.mat(src['world']['WPN_root']), D.mat(src['world']['hand_l'])
        hd = np.linalg.inv(gw) @ hw
        angle = np.degrees(np.linalg.norm(Rot.from_matrix(rotation(H).T @ rotation(hd)).as_rotvec()))
        print('DONOR_ORIENTATION', donor, round(angle, 2))
        Wd = donor_hand(W, donor)
        pts = skin.pose(Wd)
        pg = ((local[:3, :3] @ pts.T).T + local[:3, 3]) * 100.0
        for f in ('hand', 'thumb', 'index', 'middle', 'ring', 'pinky'):
            p = pg[np.char.startswith(tags, f + '_')]
            print('AUTHOR_DONOR_REGION', donor, f, p.min(0).round(2), p.max(0).round(2))
