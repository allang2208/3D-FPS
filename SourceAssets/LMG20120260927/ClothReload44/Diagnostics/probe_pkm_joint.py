"""PKM reload_empty joint ranges (right + left) with the coherent-segment measures."""
import sys, json
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44', r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D

BI, REST = D.BI, D.REST
rot = lambda m: m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
unit = lambda v: v / np.linalg.norm(v)
P = lambda n: REST[BI[n]][:3, 3]


def basis(a, b):
    a = unit(a); b = unit(b - a * (b @ a)); return np.column_stack((a, b, np.cross(a, b)))


def swing(a, b):
    a = unit(a); b = unit(b); q = np.r_[np.cross(a, b), 1 + np.clip(a @ b, -1, 1)]
    return R.from_quat(unit(q)).as_matrix()


def joint(W, s_):
    s, e, w = (W[BI[n + s_]][:3, 3] for n in ('upperarm', 'lowerarm', 'hand'))
    U0 = P('lowerarm' + s_) - P('upperarm' + s_)
    F0 = P('hand' + s_) - P('lowerarm' + s_)
    width = P('index_metacarpal' + s_) - P('pinky_metacarpal' + s_)
    Dh = rot(W[BI['hand' + s_]]) @ rot(REST[BI['hand' + s_]]).T
    fs = basis(w - e, Dh @ width) @ basis(F0, width).T
    us = swing(fs @ U0, e - s) @ fs
    dev = max(np.degrees(R.from_matrix(rot(W[BI[n + s_]]) @ rot(REST[BI[n + s_]]).T @ fs.T).magnitude())
              for n in ('lowerarm', 'lowerarm_twist_02', 'lowerarm_twist_01'))
    bend = np.degrees(np.arccos(np.clip(unit(Dh @ F0) @ unit(w - e), -1, 1)))
    elbow = np.degrees(np.arccos(np.clip(unit(s - e) @ unit(w - e), -1, 1)))
    Dc = rot(W[BI['clavicle' + s_]]) @ rot(REST[BI['clavicle' + s_]]).T
    rel = Dc.T @ us  # upper-arm skin relative to shoulder girdle
    ax = unit(Dc.T @ unit(e - s))
    q = R.from_matrix(rel).as_quat()
    q = q if q[3] >= 0 else -q
    roll = np.degrees(2 * np.arctan2(q[:3] @ ax, q[3]))
    return dev, bend, elbow, roll


for label, f in (('PKM reload_empty', 'pkm_reload_empty_asbase.json.gz'), ('PKM reload', 'pkm_reload_asbase.json.gz')):
    tr = D.load_tracks(D.HERE / 'Diagnostics' / f)
    n = len(tr['hand_r'])
    W = D.worlds(tr, np.arange(0, n, 3))
    for s_ in ('_r', '_l'):
        vals = np.array([joint(W[k], s_) for k in range(len(W))])
        print(label, s_, 'coherent dev max %.1f  wrist bend %.0f..%.0f  elbow %.0f..%.0f  upper roll vs girdle %.0f..%.0f' % (
            vals[:, 0].max(), vals[:, 1].min(), vals[:, 1].max(), vals[:, 2].min(), vals[:, 2].max(), vals[:, 3].min(), vals[:, 3].max()))
tr = D.load_tracks(D.HERE / 'Tracks/base_tracks.json.gz')
W = D.worlds(tr, np.arange(0, 745, 3))
vals = np.array([joint(W[k], '_l') for k in range(len(W))])
print('R44 base _l', 'coherent dev max %.1f  wrist bend %.0f..%.0f  elbow %.0f..%.0f  upper roll vs girdle %.0f..%.0f' % (
    vals[:, 0].max(), vals[:, 1].min(), vals[:, 1].max(), vals[:, 2].min(), vals[:, 2].max(), vals[:, 3].min(), vals[:, 3].max()))
idle = json.loads((D.HERE / 'Inputs/201_idle.json').read_text())
W0 = D.worlds({n: np.array([v]) for n, v in zip(D.NAMES, idle['poses'][0])})[0]
print('201 idle _l', np.round(joint(W0, '_l'), 1))
