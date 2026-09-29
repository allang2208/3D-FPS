"""Smooth the compressed ASH12 elbow transition over its cloth surface."""
import json,numpy as np
from pathlib import Path
from scipy.spatial import cKDTree
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ChainmailReloadFit20260929');d=json.loads((R/'ASH12_fitted.json').read_text());p=np.array(d['positions'])
names=sorted({n for w in d['weights'] for n in w});ids={n:i for i,n in enumerate(names)};w=np.zeros((len(p),len(names)))
for i,weights in enumerate(d['weights']):
 for n,v in weights.items():w[i,ids[n]]=v
tree=cKDTree(p);neighbours=tree.query_ball_point(p,2.5)
elbows=np.array([d['rest']['lowerarm_'+s]['p'] for s in ['l','r']]);distance_to_elbow=np.min(np.linalg.norm(p[:,None,:]-elbows[None,:,:],axis=2),axis=1)
factor=np.clip((10-distance_to_elbow)/4,0,1)
for iteration in range(4):
 nw=w.copy()
 for i,near in enumerate(neighbours):
  distance=np.linalg.norm(p[near]-p[i],axis=1);blend=np.exp(-(distance/1.2)**2);nw[i]=w[i]*(1-factor[i])+np.sum(w[near]*blend[:,None],axis=0)/sum(blend)*factor[i]
 w=nw
edits=[]
for i,ww in enumerate(w):
 keep=np.argsort(ww)[-8:];weights={names[k]:float(ww[k]) for k in keep if ww[k]>1e-6};total=sum(weights.values());weights={n:v/total for n,v in weights.items()};d['weights'][i]=weights;edits.append(dict(vertex_id=i,position=p[i].tolist(),weights=weights))
(R/'ASH12_fitted.json').write_text(json.dumps(d,separators=(',',':')));(R/'ASH12_edits.json').write_text(json.dumps(edits,separators=(',',':')))
