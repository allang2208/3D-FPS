"""Fit eight-influence skinning to the native trouser surface over crouch poses."""
import gc,json
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
from scipy.spatial.transform import Rotation
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
inputs=read(R/'inputs.json');pants=read(R/'Authored/ue_leather_pants/LeatherPants.json');names=list(pants['bones']);index={n:i for i,n in enumerate(names)}
frames=[sample['bones'] for row in inputs['clips'].values() for sample in row['samples']];F=len(frames);M=np.zeros((F,len(names),3,4))
for fi,frame in enumerate(frames):
    for j,n in enumerate(names):
        rest=np.eye(4);rest[:3,:3]=np.array(pants['bones'][n]['axes']).T;rest[:3,3]=pants['bones'][n]['position'];pose=np.eye(4);pose[:3,:3]=Rotation.from_quat(frame[n]['q']).as_matrix()@np.diag(frame[n]['s']);pose[:3,3]=frame[n]['p'];m=pose@np.linalg.inv(rest);m[:3,3]-=frame['pelvis']['p'];M[fi,j]=m[:3]
pp=np.array(pants['positions']);posed=np.zeros((F,len(pp),3))
for n in names:
    ww=np.array([w.get(n,0) for w in pants['weights']]);ids=np.flatnonzero(ww)
    if len(ids):posed[:,ids]+=np.einsum('fij,vj->fvi',M[:,index[n]],np.c_[pp[ids],np.ones(len(ids))])*ww[ids][None,:,None]
report=[]
for profile in ('Jason','Owner_Jason'):
    path=R/'Authored/ue_field_sweater'/(profile+'.json');d=read(path);p=np.array(d['positions']);mapping=np.load(R/(profile+'_transfer.npz'));errors=[];count=0
    for vi,tri,bc in zip(mapping['ids'],mapping['triangles'],mapping['barycentric']):
        if p[vi,2]>=104.8:continue
        base=d['weights'][vi];candidates=set(base)
        for v in tri:candidates.update(pants['weights'][v])
        candidates=sorted(candidates);bs=np.array([index[n] for n in candidates]);w0=np.array([base.get(n,0) for n in candidates]);point=p[vi];anchor=bc@pp[tri]
        # Match the actual interpolated, posed triangle, then carry the existing
        # outer-layer offset using the same local blended deformation gradient.
        target=np.einsum('v,fvj->fj',bc,posed[:,tri]);A=np.einsum('b,fbij->fij',w0,M[:,bs,:,:3]);target+=np.einsum('fij,j->fi',A,point-anchor)
        prediction=np.einsum('fbij,j->fbi',M[:,bs],np.r_[point,1]);design=prediction.transpose(0,2,1).reshape(F*3,-1)
        lhs=np.vstack((design,np.ones((1,len(bs)))*60,np.eye(len(bs))*.10));rhs=np.r_[target.ravel(),60,w0*.10]
        solution,_=nnls(lhs,rhs,maxiter=len(bs)*20)
        top=np.argsort(solution)[-8:];fit,_=nnls(lhs[:,top],rhs,maxiter=200);fit/=max(fit.sum(),1e-12)
        new={candidates[k]:float(v) for k,v in zip(top,fit) if v>1e-8};blend=1-float(smooth((point[2]-100.1)/4.7));combined={n:base.get(n,0)*(1-blend)+new.get(n,0)*blend for n in set(base)|set(new)}
        best=sorted(combined,key=combined.get,reverse=True)[:8];total=sum(combined[n] for n in best);d['weights'][vi]={n:combined[n]/total for n in best if combined[n]>1e-8}
        final=np.array([d['weights'][vi].get(n,0) for n in candidates]);error=np.linalg.norm(np.einsum('b,fbi->fi',final,prediction)-target,axis=1);errors.append(float(error.max()));count+=1
    d['contract']+='; Eight-weight constrained multi-pose surface transfer against 36 native crouch samples; no new bones or runtime deformation'
    d['crouch_waist_fit']['multi_pose_weights']=dict(poses=F,vertices=count,max_influences=8,max_target_error_cm=max(errors),p95_target_error_cm=float(np.quantile(errors,.95)))
    write(path,d);report.append(dict(profile=profile,**d['crouch_waist_fit']['multi_pose_weights']));print('CROUCH_WEIGHT_FIT',json.dumps(report[-1]),flush=True);del d;gc.collect()
write(R/'weight_fit.json',dict(completed=True,records=report))
