"""Animation-local elbow surface keys; no changes to bind shape or skin weights."""
from pathlib import Path
import sys,json
O=Path(__file__).resolve().parent
sys.path.insert(0,str(O.parent/'M24LeftElbowReview20261028/PythonDeps'))
sys.path.insert(0,str(O.parent/'BareSkinV9Rollout_20261017'))
import numpy as np
from jc import Rig,Driver,smoothstep
D=json.loads((O/'corrective_source.json').read_text());N=np.load(O/'corrective_source.npz')
P0=N['P'];T0=N['T'];S0=N['S']
_,first,w=np.unique(np.round(P0,4),axis=0,return_index=True,return_inverse=True)
P=P0[first];T=w[T0];S=S0[:,first];W=[D['weights'][i] for i in first]
E=np.array(D['bones']['lowerarm_l']['t']);distance=np.linalg.norm(P-E,axis=1)
region=np.where(distance<12)[0];remap=np.full(len(P),-1);remap[region]=np.arange(len(region))
faces=(distance[T]<12).all(axis=1);T=remap[T[faces]]
P=P[region];S=S[:,region];W=[W[i] for i in region];distance=distance[region]
rig=Rig(P,T,W,np.zeros(len(P)),D['bones'],1);driver=Driver(D['bones'],D['shapes'])
mask=1-smoothstep(5.0,8.5,distance);fm=(distance[T]<6.5).all(axis=1)
frames=D['frames'];base=[];matrices=[]
for fr in frames:
    pose=fr['pose'];weights=driver.weights(pose)
    vals=np.array([weights.get(n,0) if weights.get(n,0)>=.001 else 0 for n in D['shapes']])
    delta=np.einsum('k,kvi->vi',vals,S);Rm,Tv=rig.pose_matrices(pose);X,A=rig.lbs(P+delta,Rm,Tv)
    base.append(X);matrices.append(A)
base=np.array(base);matrices=np.array(matrices)
keys={};log=[]
key_indices=sorted(set(range(4,44,4))|{6,17,18,29,30,31,38})
for i in key_indices:
    X=base[i]
    # Recover the reference surface detail after a smooth deformation and ease
    # the interior crease; avoid uniform arm shrinking or moving any bone.
    corr=((rig.delta_mush(X)-X)*.55+(rig.smooth(X,24)-X)*.45)*mask[:,None]
    for _ in range(5):corr=.5*corr+.5*(rig.Lop@corr)*(mask>0)[:,None]
    corr,guard=rig.fold_guard(X,corr,mask)
    delta=np.linalg.solve(matrices[i],corr[:,:,None])[:,:,0]
    mag=np.linalg.norm(delta,axis=1);delta*=np.minimum(1.,.65/np.maximum(mag,1e-9))[:,None]
    delta[distance>8.5]=0;delta[np.linalg.norm(delta,axis=1)<.001]=0
    name=f'M24_BipodElbow30_{i:02d}'
    full=np.zeros((len(first),3));full[region]=delta;keys[name]=full[w]
    after=X+np.einsum('vij,vj->vi',matrices[i],delta)
    log.append({'time':i/100,'name':name,'folds_before':len(rig.inverted(X,fm)),
                'folds_after':len(rig.inverted(after,fm)),'max_bind_delta_mm':float(np.linalg.norm(delta,axis=1).max()*10)})
    print('BIPOD_ELBOW_KEY',json.dumps(log[-1]),flush=True)
np.savez_compressed(O/'elbow_correctives.npz',**keys)
timeline=[0.]+[i/100 for i in key_indices]+[.44,.48]
curves={name:{'times':timeline,'values':[1. if abs(t-int(name.rsplit('_',1)[1])/100)<.001 else 0. for t in timeline]} for name in keys}
(O/'elbow_curves.json').write_text(json.dumps(curves,indent=2))
(O/'elbow_authoring.json').write_text(json.dumps({'keys':log,'scope':'Animation curves on bipod clips only; no other animation activation'},indent=2))
review=[]
for i,fr in enumerate(frames):
    correction=np.zeros_like(P)
    for name,curve in curves.items():
        weight=np.interp(fr['time'],curve['times'],curve['values'])
        if weight:correction+=keys[name][first][region]*weight
    after=base[i]+np.einsum('vij,vj->vi',matrices[i],correction)
    review.append({'time':fr['time'],'before':len(rig.inverted(base[i],fm)),'after':len(rig.inverted(after,fm))})
(O/'Review/elbow_surface_result.json').write_text(json.dumps(review,indent=2))
print('SURFACE_SUMMARY',max(v['before'] for v in review),max(v['after'] for v in review),[(v['time'],v['after']) for v in review if v['after']],flush=True)
