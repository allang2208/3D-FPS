"""M24-only elbow pose examples. No bind surface, weights, or animation changes."""
import sys,json
from pathlib import Path
O=Path(__file__).resolve().parent
sys.path.insert(0,str(O.parent/'M24LeftElbowReview20261028/PythonDeps'));sys.path.insert(0,str(O.parent/'BareSkinV9Rollout_20261017'))
import numpy as np
from jc import Rig,Driver,pose_name,pose_value,pose_weight
D=json.loads((O/'corrective_source.json').read_text());N=np.load(O/'corrective_source.npz');P0=N['P'];T0=N['T'];S0=N['S']
# UV split duplicates share a deformation; weld only exact baseline positions.
_,first,w=np.unique(np.round(P0,4),axis=0,return_index=True,return_inverse=True)
P=P0[first];T=w[T0];S=S0[:,first];W=[D['weights'][i] for i in first]
E=np.array(D['bones']['lowerarm_l']['t']);distance=np.linalg.norm(P-E,axis=1)
region=np.where(distance<12)[0];remap=np.full(len(P),-1);remap[region]=np.arange(len(region));faces=(distance[T]<12).all(axis=1);T=remap[T[faces]]
P=P[region];S=S[:,region];W=[W[i] for i in region];distance=distance[region]
rig=Rig(P,T,W,np.zeros(len(P)),D['bones'],1);driver=Driver(D['bones'],D['shapes'])
mask=(distance<8.5).astype(float);face_mask=(distance[T]<6.5).all(axis=1)
frames=D['frames'];base=[];matrices=[];sigs=[]
for fr in frames:
 pose=fr['pose'];weights=driver.weights(pose);wv=np.array([weights.get(n,0) if weights.get(n,0)>=.001 else 0 for n in D['shapes']]);delta=np.einsum('k,kvi->vi',wv,S)
 Rm,Tv=rig.pose_matrices(pose);X,A=rig.lbs(P+delta,Rm,Tv);base.append(X);matrices.append(A);sigs.append(driver.signature(pose,'l'))
base=np.array(base);matrices=np.array(matrices)
def counts(X):return np.array([len(rig.inverted(x,face_mask)) for x in X])
before=counts(base);current=base.copy();count=before.copy();new={};logs=[];rejected=set();shapes=set(D['shapes'])
if 'extend' in sys.argv:
 previous=np.load(O/'elbow_correctives.npz')
 for name in previous.files:
  delta=previous[name][first][region];new[name]=delta;shapes.add(name)
  center=[pose_value(x) for x in name.split('_')[3:]];weights=np.array([pose_weight(sig,center) for sig in sigs]);weights[weights<.001]=0
  current+=weights[:,None,None]*np.einsum('fvij,vj->fvi',matrices,delta)
 count=counts(current)
print('ELBOW_CORRECTIVE_BEFORE',len(P),len(frames),int(before.max()),int(before.sum()),flush=True)
for step in range(32):
 candidates=[i for i,c in enumerate(count) if c>0 and i not in rejected and pose_name('l',sigs[i]) not in shapes]
 if not candidates:break
 i=max(candidates,key=lambda j:count[j]);name=pose_name('l',sigs[i]);center=[pose_value(x) for x in name.split('_')[3:]]
 weights=np.array([pose_weight(sig,center) for sig in sigs]);weights[weights<.001]=0
 X=current[i];corr,guard=rig.fold_guard(X,np.zeros_like(P),mask)
 for _ in range(4):corr=.5*corr+.5*(rig.Lop@corr)*(mask>0)[:,None]
 corr,guard=rig.fold_guard(X,corr,mask)
 delta=np.linalg.solve(matrices[i],corr[:,:,None])[:,:,0]/max(weights[i],.001)
 magnitude=np.linalg.norm(delta,axis=1);delta*=np.minimum(1,.8/np.maximum(magnitude,1e-9))[:,None];delta[distance>9.5]=0;delta[np.linalg.norm(delta,axis=1)<.002]=0
 candidate=current+weights[:,None,None]*np.einsum('fvij,vj->fvi',matrices,delta);trial=counts(candidate)
 held=[j for j,f in enumerate(frames) if f['role'] in ('idle','aim')]
 improved=trial[i]<count[i] and (trial.sum()<count.sum() or (trial.max()<count.max() and trial.sum()<=count.sum()*1.15)) and all(trial[j]<=count[j] for j in held)
 entry={'name':name,'source_role':frames[i]['role'],'before_worst':int(count[i]),'after_worst':int(trial[i]),'max_rest_displacement_mm':float(np.linalg.norm(delta,axis=1).max()*10),'accepted':bool(improved)};logs.append(entry);print('ELBOW_EXAMPLE',json.dumps(entry),flush=True)
 if improved:
  new[name]=delta;current=candidate;count=trial;shapes.add(name);rejected.clear()
 else:rejected.add(i)
 if count.max()==0:break
out={}
for name,delta in new.items():
 full=np.zeros((len(first),3));full[region]=delta;out[name]=full[w]
np.savez_compressed(O/'elbow_correctives.npz',**out)
report={'scope':'M24 left elbow only','source_origin':'Fresh saved UE data model and current V9 mesh','frames':len(frames),'before_max':int(before.max()),'after_max':int(count.max()),'before_total':int(before.sum()),'after_total':int(count.sum()),'new_shapes':list(new),'examples':logs,'roles':{role:{'before_max':int(max(before[j] for j,f in enumerate(frames) if f['role']==role)),'after_max':int(max(count[j] for j,f in enumerate(frames) if f['role']==role))} for role in sorted({f['role'] for f in frames})}}
(O/'corrective_report.json').write_text(json.dumps(report,indent=2));print('ELBOW_CORRECTIVES_COMPLETE',json.dumps({k:v for k,v in report.items() if k not in ('examples','roles')}),flush=True)
