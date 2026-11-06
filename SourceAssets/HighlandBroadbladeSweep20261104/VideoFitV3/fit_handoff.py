"""Fit the transition from the native heavy landing to the video's ready pose."""
from pathlib import Path
import json
import numpy as np
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix
p=Path(__file__).resolve().parent
inputs=p/'heavy-handoff-inputs.json'
if not inputs.exists():
    samples={}
    for name in ['Standard','LongGrip']:
        fs=json.loads((p.parent/'Review/VideoFitV3'/name/'surface.json').read_text(encoding='utf-8-sig'))['frames'][:29]
        samples[name]={s:[[f['bones'][b+'_'+s]['p'] for b in ['upperarm','lowerarm','hand','middle_01']] for f in fs] for s in ['r','l']}
    inputs.write_text(json.dumps(samples,separators=(',',':')))
unit=lambda a:a/np.maximum(1e-8,np.linalg.norm(a,axis=-1,keepdims=True))
results={}
for grip,sides in json.loads(inputs.read_text()).items():
    results[grip]={}
    for side,rows in sides.items():
        poses=np.asarray(rows)*[1.,-1.,1.];S,E,H,M=poses.transpose(1,0,2);n=len(H);length=np.median(np.linalg.norm(E-H,axis=1));axis=unit(M-H);seed=unit(E-H);t=np.arange(n); ease=np.clip((26-t)/6,0,1)[:,None]; b=np.median(np.linalg.norm(S-E,axis=1));target_shoulder=np.interp(t,[0,28],[1,0])[:,None]*S[0]+np.interp(t,[0,28],[0,1])[:,None]*S[-1];boundary=np.maximum(np.clip((3-t)/3,0,1),np.clip((t-22)/6,0,1))[:,None]
        def loss(flat):
            x=flat.reshape(n,3);direction=unit(x);elbow=H+direction*length;shoulder=elbow+b*unit(target_shoulder-elbow);cos=np.sum(-direction*axis,axis=1)
            cost=np.c_[((np.linalg.norm(x,axis=1)-1)*5), (direction-seed)*4, (direction+axis)*6, np.maximum(.805-cos,0)*200, np.maximum(16-elbow[:,1],0)*ease[:,0]*3, np.maximum(22-np.linalg.norm(elbow,axis=1),0)*ease[:,0]*6, np.maximum(elbow[:,2]+8,0)*ease[:,0]*2, (shoulder-target_shoulder)*.5, (direction-seed)*boundary*110];return np.r_[cost.ravel(),(np.diff(direction,axis=0)*20).ravel(),(np.diff(elbow,n=2,axis=0)*1.8).ravel()]
        # Couple neighbouring directions in time without selecting another elbow branch.
        total=loss(seed.ravel()).size;per=(total-(2*n-3)*3)//n; pat=lil_matrix((total,n*3),dtype=np.int8)
        for i in range(n):pat[i*per:(i+1)*per,i*3:(i+1)*3]=1
        row=n*per
        for order in [1,2]:
            for i in range(n-order):pat[row+3*i:row+3*i+3,3*i:3*(i+order+1)]=1
            row+=3*(n-order)
        res=least_squares(loss,seed.ravel(),jac_sparsity=pat.tocsr(),max_nfev=120,ftol=1e-6);d=unit(res.x.reshape(n,3));results[grip][side]=d.tolist();print(grip,side,round(float(np.rad2deg(np.arccos(np.clip((-d*axis).sum(1),-1,1))).max()),1))
(p/'heavy-handoff.json').write_text(json.dumps(results,separators=(',',':')))
