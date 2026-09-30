"""Pure elbow flexion from the bind pose about the anatomical hinge (no pronation, no roll),
left and right arm, current skin weights.  Output npz for render_elbow.py (one frame each,
camera facing the inner elbow)."""
import sys, json
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics')
import diag_lib as D

out = Path(sys.argv[1])
flex = float(sys.argv[2]) if len(sys.argv) > 2 else 70.0
weights = sys.argv[3] if len(sys.argv) > 3 else None
skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json', 'skin')
if weights:  # alternative weight source with the same vertex order
    alt = D.load_json_mesh(weights, 'alt')
    assert len(alt.p) == len(skin.p) and np.abs(alt.p - skin.p).max() < 1e-3
    skin.idx, skin.w = alt.idx, alt.w
REST = D.REST


def desc(root):
    out, stack = [], [D.BI[root]]
    while stack:
        i = stack.pop()
        out.append(i)
        stack += [j for j, p in enumerate(D.PARENT) if p == i]
    return out


pos, cams, looks, tags = [], [], [], []
for s in ('l', 'r'):
    S0, E0, H0 = (REST[D.BI[n + '_' + s]][:3, 3] for n in ('upperarm', 'lowerarm', 'hand'))
    h = np.cross(E0 - S0, H0 - E0)
    h /= np.linalg.norm(h)
    Rm = R.from_rotvec(h * np.radians(flex)).as_matrix()
    W = REST.copy()
    for i in desc('lowerarm_' + s):
        m = REST[i].copy()
        m[:3, :3] = Rm @ m[:3, :3]
        m[:3, 3] = E0 + Rm @ (m[:3, 3] - E0)
        W[i] = m
    sel = np.isin(skin.idx[:, 0], [D.BI[n] for n in D.NAMES if n.endswith('_' + s)])
    p = skin.pose(W)
    # camera on the inner side of the bend: toward the bisector of the two segments
    u = (S0 - E0) / np.linalg.norm(S0 - E0)
    f = (W[D.BI['hand_' + s]][:3, 3] - E0)
    f /= np.linalg.norm(f)
    inner = (u + f) / np.linalg.norm(u + f)
    pos.append(np.where(sel[:, None], p, np.nan))
    cams.append(E0 + inner * 18.0 + h * 6.0 * (1 if s == 'l' else -1))
    looks.append(E0 + inner * 2.0)
    tags.append(s)
keep = ~np.isnan(pos[0]).any(1) | ~np.isnan(pos[1]).any(1)
vid = np.where(keep)[0]
remap = -np.ones(len(skin.p), int)
remap[vid] = np.arange(len(vid))
tri = skin.tris[np.all(keep[skin.tris], 1)]
P = np.array([np.nan_to_num(p[vid], nan=0.0) for p in pos], np.float32)
np.savez(out, pos=P, tri=remap[tri], times=np.array([0.0, 1.0]), cam=np.array(cams), look=np.array(looks))
print('HINGE_TEST', out, 'flex +%.0f' % flex)
