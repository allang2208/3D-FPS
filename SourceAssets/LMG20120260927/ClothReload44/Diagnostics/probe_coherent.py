"""Compare 201 idle / ClothReload44 frames with PKM coherent segments; left arm."""
import sys, json
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44', r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D

BI, REST = D.BI, D.REST
rot = lambda m: m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
unit = lambda v: v / np.linalg.norm(v)


def basis(a, b):
    a = unit(a); b = unit(b - a * (b @ a)); return np.column_stack((a, b, np.cross(a, b)))


def swing(a, b):
    a = unit(a); b = unit(b); q = np.r_[np.cross(a, b), 1 + np.clip(a @ b, -1, 1)]
    return R.from_quat(unit(q)).as_matrix()


P = lambda n: REST[BI[n]][:3, 3]
S0, E0, H0 = P('upperarm_l'), P('lowerarm_l'), P('hand_l')
U0, F0 = E0 - S0, H0 - E0
width = P('index_metacarpal_l') - P('pinky_metacarpal_l')
bind = basis(F0, width)
fore = ['lowerarm_l', 'lowerarm_twist_02_l', 'lowerarm_twist_01_l']
upper = ['upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l']


def report(W, label):
    s, e, w = (W[BI[n]][:3, 3] for n in ('upperarm_l', 'lowerarm_l', 'hand_l'))
    Dh = rot(W[BI['hand_l']]) @ rot(REST[BI['hand_l']]).T
    fs = basis(w - e, Dh @ width) @ bind.T
    us = swing(fs @ U0, e - s) @ fs
    out = []
    for n in fore:
        Db = rot(W[BI[n]]) @ rot(REST[BI[n]]).T
        out.append(np.degrees(R.from_matrix(Db @ fs.T).magnitude()))
    for n in upper:
        Db = rot(W[BI[n]]) @ rot(REST[BI[n]]).T
        out.append(np.degrees(R.from_matrix(Db @ us.T).magnitude()))
    bend = np.degrees(np.arccos(np.clip(unit(Dh @ F0) @ unit(w - e), -1, 1)))
    print(label, 'deviation from coherent frame (deg) fore[lo,t02,t01]=%s upper[up,t01,t02]=%s wrist bend %.1f' % (
        np.round(out[:3], 1), np.round(out[3:], 1), bend))


idle = json.loads((D.HERE / 'Inputs/201_idle.json').read_text())
W0 = D.worlds({n: np.array([v]) for n, v in zip(D.NAMES, idle['poses'][0])})[0]
report(W0, '201 idle         ')
tr = D.load_tracks(D.HERE / 'Tracks/base_tracks.json.gz')
for t in (0.98, 1.1, 1.3, 1.6, 2.2, 3.0, 3.9, 4.5, 4.78, 5.05, 5.22, 5.5):
    report(D.worlds(tr, [int(t * 120)])[0], 'R44 t=%.2f       ' % t)
