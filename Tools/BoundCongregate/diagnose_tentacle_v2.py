"""Requested anatomical diagnosis: original surface, chain and influence regions."""
from pathlib import Path
import json
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
OUT=ROOT/'TentacleRepairV2';OUT.mkdir(exist_ok=True)
d=np.load(ROOT/'Assessment/output.npz');s=np.load(ROOT/'RigRepairV3/skin_weights.npz')
v,inv=np.unique(np.round(d['vertices'],5),axis=0,return_inverse=True);tri=inv[d['triangles']]
names=s['names'].tolist();weights=np.zeros((len(inv),len(names)))
weights[np.arange(len(inv))[:,None],s['indices']]=s['weights']
w=np.zeros((len(v),len(names)));np.add.at(w,inv,weights);w/=np.bincount(inv)[:,None]
chain_ids=[i for i,n in enumerate(names) if n.startswith(('curl_','feeler_'))]
influence=w[:,chain_ids].sum(1)
recipe=json.loads((ROOT/'Authoring/rig_recipe.json').read_text())
bones=[b for b in recipe['bones'] if b['name'].startswith(('curl_','feeler_'))]
guide=np.array([b['head'] for b in bones]+[bones[-1]['tail']])
edges=np.unique(np.sort(np.concatenate([tri[:,:2],tri[:,1:],tri[:,[0,2]]]),axis=1),axis=0)
g=coo_matrix((np.ones(len(edges)*2),(np.r_[edges[:,0],edges[:,1]],np.r_[edges[:,1],edges[:,0]])),shape=(len(v),len(v))).tocsr()
n,labels=connected_components(g)
report={'welded_vertices':len(v),'connected_sizes':sorted(np.bincount(labels).tolist(),reverse=True)[:20],
        'influence_counts':{str(t):int((influence>t).sum()) for t in [.001,.05,.25,.5,.95]}}
(OUT/'source_diagnosis.json').write_text(json.dumps(report,indent=2))
fig,axes=plt.subplots(1,3,figsize=(18,9))
for ax,(a,b),title in zip(axes,[(0,2),(1,2),(0,1)],['Front XZ','Side YZ','Top XY']):
    ax.scatter(v[:,a],v[:,b],c=influence,s=.35,cmap='turbo',vmin=0,vmax=1)
    ax.plot(guide[:,a],guide[:,b],'k.-',lw=.8,ms=3)
    for i,p in enumerate(guide):ax.text(p[a],p[b],str(i),fontsize=8,color='black')
    ax.set_aspect('equal');ax.set_title(title);ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(OUT/'influence_before.png',dpi=160);plt.close(fig)
np.savez_compressed(OUT/'diagnostic_surface.npz',vertices=v,triangles=tri,inverse=inv,weights=w,guide=guide)
print(json.dumps(report),flush=True)
levels=[.46,.40,.35,.30,.24,.18,.12,.06,0,-.06,-.12,-.18,-.24,-.30,-.36,-.42,-.46,-.49,-.515]
fig,axes=plt.subplots(5,4,figsize=(16,18))
for ax,z in zip(axes.flat,levels):
    mask=(abs(v[:,2]-z)<.004)&(v[:,0]>-.26)&(v[:,0]<.5)&(v[:,1]<.25)
    ax.scatter(v[mask,0],v[mask,1],s=3,c=influence[mask],cmap='turbo',vmin=0,vmax=1)
    ax.set_title(f'Z={z}');ax.set_aspect('equal');ax.grid(alpha=.4)
fig.tight_layout();fig.savefig(OUT/'surface_sections.png',dpi=160)
