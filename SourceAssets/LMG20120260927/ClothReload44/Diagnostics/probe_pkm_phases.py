"""PKM reload_empty: gun-relative hand frames per phase (right mirrored to left)."""
import sys, json
import numpy as np
sys.path[:0] = [r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44', r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D

BI, REST = D.BI, D.REST
M = np.diag([-1.0, 1, 1, 1])
rot = lambda m: m[:3, :3] / np.linalg.norm(m[:3, :3], axis=0)
unit = lambda v: v / np.linalg.norm(v)
tr = D.load_tracks(D.HERE / 'Diagnostics/pkm_reload_empty_asbase.json.gz')
W = D.worlds(tr)
wr = BI['WPN_root']
G0 = W[0, wr]


def lhand_frame(H, side):
    """finger dir / palmar normal of a left hand world matrix (mirrored if right)."""
    names = ('middle_01', 'index_01', 'pinky_01')
    if side == 'r':
        H = M @ H @ np.linalg.inv(REST[BI['hand_r']]) @ M @ REST[BI['hand_l']]
    R = rot(H)
    loc = lambda n: (np.linalg.inv(REST[BI['hand_l']]) @ REST[BI[n + '_l']])[:3, 3]
    f = unit(R @ loc('middle_01'))
    a = unit(R @ (loc('index_01') - loc('pinky_01')))
    return f, unit(np.cross(a, f)), H


for label, t, side in (('cover hook (L)', .60, 'l'), ('cover lift (L)', .95, 'l'), ('lid released (L)', 1.20, 'l'),
                       ('box grip (R)', 1.90, 'r'), ('box off (R)', 2.20, 'r'), ('new box (R)', 3.20, 'r'),
                       ('box seated (R)', 3.45, 'r'), ('belt pinch (R)', 3.90, 'r'), ('belt lay (R)', 4.15, 'r'),
                       ('cover push (R)', 4.60, 'r'), ('cover shut (R)', 4.82, 'r')):
    k = int(round(t * 120))
    G = W[k, wr]
    H = G0 @ np.linalg.inv(G) @ W[k, BI['hand_' + side]]  # remove PKM gun motion
    f, p, Hm = lhand_frame(H, side)
    pos = Hm[:3, 3] if side == 'l' else (M @ H)[:3, 3]
    print('%-18s t=%.2f finger %s palmar %s wrist(pkm-gun idle, left-mirrored) %s' % (label, t, np.round(f, 2), np.round(p, 2), np.round(pos, 1)))
print('PKM WPN idle axes', np.round(rot(G0), 2).tolist(), 'pos', np.round(G0[:3, 3], 1))
print('PKM cover bone idle', np.round(W[0, BI['WPN_root']][:3, 3], 1))
