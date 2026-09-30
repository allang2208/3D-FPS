"""Search a right arm-root offset that keeps the right sleeve out of the action-framed view."""
import sys, json, numpy as np
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44', r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D
import rig as K
tr = D.load_tracks(D.HERE / 'Tracks/base_tracks.json.gz')
fr = [72, 360]
Wall = D.worlds(tr, fr)
idle = json.loads((D.L201 / 'ClothFeed33/Inputs/201_idle.json').read_text())
W0 = D.worlds({n: np.array([v]) for n, v in zip(D.NAMES, idle['poses'][0])})[0]
armR = K.Arm('r', D.NAMES, D.PARENT, D.REST, W0)
local0 = {i: K.mat(v) for i, v in enumerate(idle['poses'][0])}
garments = {'chainmail': D.SA / 'ChainmailReloadFit20260929/LMG201_saved.json',
            'sweater': D.SA / 'FieldSweaterKnit20260929/Authored/LMG201.json',
            'skin': D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json'}
G = {k: D.load_json_mesh(p) for k, p in garments.items()}
right = {k: np.char.endswith(np.array([D.NAMES[b] for b in g.dom]), '_r') for k, g in G.items()}
eye, f, r, u = D.camera(1.0)
sub = [i for i in range(len(D.NAMES)) if D.NAMES[i].endswith('_r') and any(D.NAMES[i].startswith(x) for x in ('clavicle', 'upperarm', 'lowerarm', 'hand', 'index', 'middle', 'ring', 'pinky', 'thumb'))]


def pose_with(W, delta):
    W = W.copy()
    C = W[D.BI['clavicle_r']].copy()
    C[:3, 3] += delta
    H = W[D.BI['hand_r']]
    pos = armR.positions(H[:3, 3], armR.pole0, clavicle=C)
    _, ph = armR.hand_relative(pos, K.rot(H), armR.phi0)
    sol = armR.finish(pos, K.rot(H), ph)
    for k, m in sol.items():
        W[armR.i[k]] = m
    for n in ('upperarm_twist_01_r', 'upperarm_twist_02_r'):
        W[D.BI[n]] = W[D.BI['upperarm_r']] @ local0[D.BI[n]]
    for i in sub:
        if i not in armR.i.values() and D.NAMES[i] not in ('upperarm_twist_01_r', 'upperarm_twist_02_r'):
            W[i] = W[D.PARENT[i]] @ (np.linalg.inv(Wall_ref[D.PARENT[i]]) @ Wall_ref[i])
    return W, pos['reach']


def score(W):
    out = {}
    for k, g in G.items():
        p = g.pose(W)[right[k]]
        v = p - eye
        z = v @ f
        x = v @ r
        y = v @ u
        th = np.tan(np.radians(37.5))
        ins = (z > .5) & (np.abs(x) < z * th * 16 / 9) & (np.abs(y) < z * th)
        near = ins & (z < 14)
        out[k] = (int(near.sum()), float(z[ins].min()) if ins.any() else 99.)
    return out


for k, fi in enumerate(fr):
    Wall_ref = Wall[k]
    print('frame', fi, 'as authored', score(Wall[k]))
    best = []
    for dx in (0, 3, 6):
        for dy in (0, 3, 6):
            for dz in (0, -3, -6, -9):
                W, reach = pose_with(Wall[k], np.array([dx, dy, dz], float))
                s = score(W)
                best.append((s['chainmail'][0] + s['sweater'][0], -s['chainmail'][1], (dx, dy, dz), round(reach, 3), s))
    best.sort()
    for b in best[:6]:
        print('  ', b[2], 'reach', b[3], b[4])
