"""Offline weighted Jason skin from actual native-graph poses, not a gameplay capture."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
data=json.loads((OUT/'native-graph.json').read_text(encoding='utf-8-sig'))
v=next(v for v in data['variants'] if v['variant']=='jason')
geo=json.loads((ROOT/'SourceAssets/JasonPlayer20261003/Jason.json').read_text())
names=v['names'];index={n:i for i,n in enumerate(names)}
def matrices(rows):
    a=np.asarray(rows);m=np.zeros((len(a),4,4));m[:,3,3]=1
    m[:,:3,:3]=R.from_quat(a[:,3:7]).as_matrix()*a[:,None,7:10]
    m[:,:3,3]=a[:,:3]
    return m
inverse_bind=np.linalg.inv(matrices(v['reference_cs']))
points=np.asarray(geo['positions']);tris=np.asarray(geo['triangles'],dtype=int)
weights={}
for i,influences in enumerate(geo['weights']):
    for bone,weight in influences:
        target=index[geo['bones'][bone]['name']]
        weights.setdefault(target,[]).append((i,weight))
weights={b:(np.asarray(rows)[:,0].astype(int),np.asarray(rows)[:,1,None]) for b,rows in weights.items()}
def skin(sample):
    transforms=matrices(sample['pose_cs'])@inverse_bind
    p=np.zeros_like(points)
    for bone,(ids,w) in weights.items():
        p[ids]+=(points[ids]@transforms[bone,:3,:3].T+transforms[bone,:3,3])*w
    return p
rows=[s for s in v['cases'][0]['samples'] if 'pose_cs' in s]
times=[0,.10,.20,.267,.333,1.10]
chosen=[min(rows,key=lambda r:abs(r['time']-t)) for t in times]
fig,axes=plt.subplots(2,6,figsize=(15,7),facecolor='#171d27')
for col,s in enumerate(chosen):
    p=skin(s)
    for row,angle in enumerate((0,90)):
        view=R.from_euler('z',angle,degrees=True).as_matrix();q=p@view.T
        f=q[tris];normal=np.cross(f[:,1]-f[:,0],f[:,2]-f[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-9)
        light=np.array([-.3,-.8,.5]);light/=np.linalg.norm(light)
        shade=.35+.6*np.abs(normal@light)
        lower=points[tris][:,:,2].mean(axis=1)<85
        colors=shade[:,None]*np.where(lower[:,None],np.array([.40,.75,.95]),np.array([.78,.80,.82]))
        order=np.argsort(-f[:,:,1].mean(axis=1))
        ax=axes[row,col];ax.set_facecolor('#171d27')
        ax.add_collection(PolyCollection(f[order][:,:,[0,2]],facecolors=colors[order],edgecolors='none',rasterized=True))
        ax.axhline(0,color='#6a778c',lw=.7);ax.set_xlim(-85,85);ax.set_ylim(-5,195);ax.set_aspect('equal');ax.axis('off')
        ax.set_title(f"{s['time']:.3f}s | travel {s['travel']:.0f}cm",color='white',fontsize=10)
        if row==1:ax.text(0,-17,s['phase'].replace('Warhammer',''),color='#a9bbcf',ha='center',fontsize=9)
fig.suptitle('Hammer sprint | current native animation graph | grounded 1x\nFront / side; body-centred poses; capsule travel shown above; offline skin preview',color='white',fontsize=13)
fig.subplots_adjust(left=.02,right=.98,top=.87,bottom=.06,wspace=.06,hspace=.2)
fig.savefig(OUT/'lower-body-review.png',dpi=110,facecolor=fig.get_facecolor())
print(OUT/'lower-body-review.png')
