"""Like elbow_views.py, but re-solves the left arm with the current author.py on the fly.
python -X utf8 elbow_views_solved.py <tracks.json.gz> <out.npz> <gun> t1 t2 ..."""
import sys
import numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HERE), r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics']
import diag_lib as D
import author as A

tracks, out, gun = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
times = [float(x) for x in sys.argv[4:]]
skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json', 'skin')
keep = np.isin(skin.idx[:, 0], [D.BI[n] for n in D.NAMES if n.endswith('_l')])
vid = np.where(keep)[0]
remap = -np.ones(len(skin.p), int)
remap[vid] = np.arange(len(vid))
tri = skin.tris[np.all(keep[skin.tris], 1)]
tr = D.load_tracks(tracks)
Wf = D.worlds(tr)
ids = [D.BI[b] for b in A.BONES]
out_w, info = A.solve(Wf[:, ids], A.Bind(gun))
pos, cams, look = [], [], []
for t in times:
    k = int(round(t * 120))
    W = Wf[k].copy()
    for j, i in enumerate(ids):
        W[i] = out_w[k][j]
    p = skin.pose(W)[vid]
    eye = D.camera(D.framing_alpha(t))[0]
    el = W[D.BI['lowerarm_l']][:3, 3]
    d = (eye - el) / np.linalg.norm(eye - el)
    pos.append(p)
    cams.append(el + d * 16.0)
    look.append(el)
np.savez(out, pos=np.array(pos, np.float32), tri=remap[tri], times=np.array(times), cam=np.array(cams), look=np.array(look))
print('ELBOW_VIEWS_SOLVED', out)
