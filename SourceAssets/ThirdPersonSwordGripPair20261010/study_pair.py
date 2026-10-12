"""Scoped diagnosis of the reported pair, with the actual production gauntlets."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
helper=ROOT/'SourceAssets/ThirdPersonSwordGrip20261007/refine_kwang_grip.py'
ns={'__file__':str(helper)}
exec(compile(helper.read_text().split('clips={}')[0],str(helper),'exec'),ns)
names,parents=ns['names'],ns['parents'];ix=ns['ix']
geo=json.loads((OUT/'production-steel.json').read_text())
points=np.asarray(geo['positions']);tri=np.asarray(geo['triangles'],dtype=int)
bind=np.array([np.block([[np.array(b['axes']).T,np.array(b['position'])[:,None]],[np.zeros((1,3)),np.ones((1,1))]]) for b in geo['bones']])
ib=np.linalg.inv(bind)
groups={}
for i,weights in enumerate(geo['weights']):
    for bone,weight in weights:groups.setdefault(bone,[]).append((i,weight))
groups={b:(np.array(a)[:,0].astype(int),np.array(a)[:,1,None]) for b,a in groups.items()}
hand_ids={}
for side in ('r','l'):
    bones={ix['hand_'+side]}
    for i,p in enumerate(parents):
        if p in bones:bones.add(i)
    hand_ids[side]=np.array([i for i,ws in enumerate(geo['weights']) if sum(w for b,w in ws if b in bones)>.95])

def fk(frame):
    a=np.asarray(frame);m=np.zeros((len(names),4,4));m[:,3,3]=1
    m[:,:3,:3]=R.from_quat(a[:,3:7]).as_matrix()*a[:,None,7:];m[:,:3,3]=a[:,:3]
    for i,p in enumerate(parents):
        if p>=0:m[i]=m[p]@m[i]
    return m

def skin(frame):
    w=fk(frame);x=w@ib;p=np.zeros_like(points)
    for b,(ids,weight) in groups.items():p[ids]+=(points[ids]@x[b,:3,:3].T+x[b,:3,3])*weight
    return w,p

def weapon(w,roll):
    hand=np.r_[w[ix['hand_r'],:3,3],R.from_matrix(w[ix['hand_r'],:3,:3]).as_quat()]
    return ns['compose'](ns['compose'](hand,ns['hand_to_weapon']),np.r_[0.,0.,0.,ns['axis']([0,0,1],-np.radians(roll))])

def in_weapon(p,wp):return R.from_quat(wp[3:7]).inv().apply(p-wp[:3])

if __name__=='__main__':
    data=json.loads((OUT/'native-before.json').read_text())
    fig,axs=plt.subplots(1,3,figsize=(12,7),facecolor='#20252c')
    summary=[]
    for i,row in enumerate(data['dash_samples']):
        f=np.array([row['actual_local'][n] for n in names]);w,p=skin(f);wp=weapon(w,row['grip_roll']);v=in_weapon(p,wp)
        z={s:v[ids,2] for s,ids in hand_ids.items()}
        summary.append({'progress':row['progress'],'gap_cm':float(z['r'].min()-z['l'].max()),
            'right_z':np.array([z['r'].min(),z['r'].max()]).tolist(),'left_z':np.array([z['l'].min(),z['l'].max()]).tolist()})
        if i not in (0,3,7):continue
        ax=axs[(0,3,7).index(i)];view=R.from_euler('z',-35,degrees=True).as_matrix();vv=v@view.T
        for s,color in [('r',np.array([.25,.65,1.])),('l',np.array([1.,.6,.28]))]:
            keep=np.zeros(len(points),bool);keep[hand_ids[s]]=True;faces=tri[np.all(keep[tri],axis=1)]
            pface=vv[faces];norm=np.cross(pface[:,1]-pface[:,0],pface[:,2]-pface[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1)[:,None],1e-8)
            shade=.5+.5*np.abs(norm@np.array([.2,-.8,.55]));order=np.argsort(-pface[:,:,1].mean(1))
            ax.add_collection(PolyCollection(pface[order][:,:,[0,2]],facecolors=(shade[:,None]*color)[order],edgecolors='none'))
        ax.plot([0,0],[-25,2],color='white',alpha=.35);ax.set_xlim(-13,13);ax.set_ylim(-26,2);ax.set_aspect('equal');ax.set_facecolor('#20252c')
        ax.set_title(f"Actual native pose {row['progress']:.0%}\nRight blue / left orange",color='white');ax.tick_params(colors='white')
    fig.tight_layout();fig.savefig(OUT/'pair-before.png',dpi=150)
    (OUT/'pair-before.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
