import json,gzip,sys,collections
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).parent;S=json.loads((O/'source.json').read_text())
def mat(v):
 a=np.eye(4);a[:3,:3]=R.from_quat(v[3:7]).as_matrix()@np.diag(v[7:]);a[:3,3]=v[:3];return a
rest={b['index']:mat(b['rest']) for b in S['bones']};names={b['index']:b['name'] for b in S['bones']}
idle={n:mat(v) for n,v in S['idle'].items()}
with gzip.open(O/'feed.json.gz','rt') as f:F=json.load(f)
ids=list(map(int,F['vertices']));imap={v:i for i,v in enumerate(ids)}
p=np.array([F['vertices'][str(i)]['p'] for i in ids]);dom=np.array([max(F['vertices'][str(i)]['w'],key=lambda w:w[1])[0] for i in ids])
tri=np.array([[imap[i] for i in row[:3]] for row in F['triangles']]);mi=np.array([row[3] for row in F['triangles']])
ir=np.linalg.inv(idle['WPN_root']);pr=np.zeros_like(p)
for b in np.unique(dom):
 m=ir@idle[names[b]]@np.linalg.inv(rest[b]);sel=dom==b;pr[sel]=p[sel]@m[:3,:3].T+m[:3,3]
for m in np.unique(mi):
 vs=np.unique(tri[mi==m]);print(S['slots'][m]['name'],len(vs),'root bounds',pr[vs].min(0),pr[vs].max(0))
L=json.loads((O.parent/'BeltRebuild52/layout.json').read_text())
for t,rows in S['clips']['base_reload']['samples'].items():
 W={n:mat(v) for n,v in rows.items()};G=np.linalg.inv(W['WPN_root']);C=[]
 for i in range(6):C.append((G@W['LMG201_Belt_%02d'%i]@np.r_[L['centers_bone_local'][0][i],1])[:3])
 # idle mouth is measured via actual frame geometry, not inherited pivots
 mouth=(G@W['LMG201_Box']@np.linalg.inv(idle['LMG201_Box'])@idle['WPN_root']@np.r_[L['centers_root_m'][5],1])[:3]
 print('TIME',t,'gaps mm',np.round(np.linalg.norm(np.diff(C,axis=0),axis=1)*1000,2),'tail anchor mm',np.linalg.norm(C[-1]-mouth)*1000)
np.savez_compressed(O/'feed.npz',p=p,root=pr,dom=dom,tri=tri,mi=mi,ids=ids)
