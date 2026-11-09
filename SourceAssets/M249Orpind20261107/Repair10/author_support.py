"""Sparse shared corrections at held-grip contact, including action handoffs."""
from pathlib import Path
import json,pickle,gzip,numpy as np
from motion import *
from support_pose import apply_support
r=Path(__file__).resolve().parent;g=pickle.load(open(r/'geometry.pkl','rb'));m=pickle.load(open(r/'m249_inputs.pkl','rb'))
names=m['names'];parents={n:(names[p] if p>=0 else None) for n,p in zip(names,m['parents'])};B={n:matrix(v) for n,v in zip(names,m['bind'])};L={n:matrix(v) for n,v in zip(names,m['frames'][0])};H=compose(names,parents,L)
params=json.loads((r/'hold_fit.json').read_text())['parameters'];reference=np.linalg.inv(H['WPN_root'])@H['hand_l']
selected=[n for n in names if n.endswith('_l') and (n.startswith(('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')) or n=='ik_hand_l')]
clips=[];summary={}
for path,d in pickle.load(open(r/'support_inputs.pkl','rb')).items():
    tracks={n:[] for n in selected};weights=[];times=np.minimum(np.arange(len(d['frames']))/d['fps'],d['duration'])
    for rows in d['frames']:
        local={n:matrix(v) for n,v in zip(names,rows)};world=compose(names,parents,local);rel=np.linalg.inv(world['WPN_root'])@world['hand_l']
        # Root scale is 100 in this native rig: compare in component centimeters.
        distance=np.linalg.norm((rel[:3,3]-reference[:3,3])*np.linalg.norm(H['WPN_root'][:3,:3],axis=0))
        angle=np.degrees(R.from_matrix(rot(reference).T@rot(rel)).magnitude())
        weight=float((1-ease((distance-.8)/4.2))*(1-ease((angle-12.)/33.)))
        out=apply_support(world,local,names,parents,B,H,params,weight);weights.append(weight)
        for n in selected:
            a=np.linalg.inv(out[parents[n]])@out[n];old=local[n];q=R.from_matrix(rot(a)@rot(old).T).as_quat()
            if q[3]<0:q=-q
            tracks[n].append([*(a[:3,3]-old[:3,3]),*q,0.,0.,0.])
    encoded=[]
    for n,values in tracks.items():
        a=np.array(values);delta=np.max(np.abs(a-np.array([0,0,0,0,0,0,1,0,0,0])),axis=1);active=delta>1.e-6
        if not active.any():continue
        keep=active|np.r_[False,active[:-1]]|np.r_[active[1:],False];keep[0]=True;keep[-1]=True
        if np.max(np.abs(a-a[0]))<1.e-6:ids=np.array([0])
        else:ids=np.nonzero(keep)[0]
        encoded.append(dict(bone=n,times=times[ids].tolist(),values=a[ids].ravel().tolist()))
    clips.append(dict(base=path,duration=d['duration'],tracks=encoded));summary[path]=dict(tracks=len(encoded),active_samples=int((np.array(weights)>1.e-6).sum()),samples=len(weights))
    print('SUPPORT_PROFILE',path,summary[path],flush=True)
with gzip.open(r/'support.json.gz','wt') as f:json.dump(dict(family='base',clips=clips),f,separators=(',',':'))
(r/'support_authoring.json').write_text(json.dumps(dict(parameters=params,clips=summary),indent=2))
