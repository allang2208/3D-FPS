"""Close views of the posed left bare arm around the elbow (offline LBS, no garments), from
the runtime eye direction.  python -X utf8 elbow_views.py <tracks.json.gz> <out.npz> t1 t2 ..."""
import sys
import numpy as np
from pathlib import Path
sys.path.insert(0, r'D:\FPS3D\FPSGAME\SourceAssets\LMG20120260927\ClothReload44\Diagnostics')
import diag_lib as D

tracks, out = Path(sys.argv[1]), Path(sys.argv[2])
times = [float(x) for x in sys.argv[3:]]
skin = D.load_json_mesh(D.SA / 'ChainmailReloadFit20260929/LMG201_skin.json', 'skin')
left = {D.BI[n] for n in D.NAMES if n.endswith('_l')}
keep = np.isin(skin.idx[:, 0], list(left))
vid = np.where(keep)[0]
remap = -np.ones(len(skin.p), int)
remap[vid] = np.arange(len(vid))
tri = skin.tris[np.all(keep[skin.tris], 1)]
tr = D.load_tracks(tracks)
fr = [int(round(t * 120)) for t in times]
W = D.worlds(tr, fr)
pos, cams, look = [], [], []
for k, t in enumerate(times):
    p = skin.pose(W[k])[vid]
    eye = D.camera(D.framing_alpha(t))[0]
    el = W[k][D.BI['lowerarm_l']][:3, 3]
    d = (eye - el) / np.linalg.norm(eye - el)
    pos.append(p)
    cams.append(el + d * 16.0)
    look.append(el)
np.savez(out, pos=np.array(pos, np.float32), tri=remap[tri], times=np.array(times), cam=np.array(cams), look=np.array(look))
print('ELBOW_VIEWS', out, len(times), len(vid))
