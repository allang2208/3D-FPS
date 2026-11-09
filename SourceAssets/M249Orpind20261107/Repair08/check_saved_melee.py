"""Only the requested melee contact/wrist/continuity check; no gameplay or bipod test."""
from pathlib import Path
import pickle,json,numpy as np
from scipy.spatial.transform import Rotation as R
r=Path(__file__).resolve().parent
def mat(a):
    a=np.array(a);m=np.zeros((*a.shape[:-1],4,4));m[...,3,3]=1
    m[...,:3,:3]=R.from_quat(a[...,3:7].reshape(-1,4)).as_matrix().reshape(*a.shape[:-1],3,3)*a[...,None,7:10];m[...,:3,3]=a[...,:3];return m
def rot(m):return m[...,:3,:3]/np.linalg.norm(m[...,:3,:3],axis=-2,keepdims=True)
def worlds(d):
    local=mat(d['frames']);out={}
    for i,n in enumerate(d['names']):
        parent=d['parents'][i];out[n]=out[d['names'][parent]]@local[:,i] if parent>=0 else local[:,i]
    return out
geo=pickle.load(open(r.parent/'Repair06/geometry.pkl','rb'));B=mat(geo['bind']);F=B[geo['names'].index('hand_r'),:3,3]-B[geo['names'].index('lowerarm_r'),:3,3]
F/=np.linalg.norm(F);handbind=rot(B[geo['names'].index('hand_r')]);report={}
for prefix in ('DATA_MODEL','SAVED'):
    d=pickle.load(open(r/(prefix+'_quick_melee.pkl'),'rb'));w=worlds(d);idle=worlds(pickle.load(open(r/(prefix+'_idle.pkl'),'rb')))
    grip=np.linalg.inv(idle['WPN_root'])@idle['hand_r'];ideal=w['WPN_root']@grip
    error=np.linalg.norm(ideal[:,:3,3]-w['hand_r'][:,:3,3],axis=1)
    actual=w['hand_r'][:,:3,3]-w['lowerarm_r'][:,:3,3];actual/=np.linalg.norm(actual,axis=1)[:,None]
    axis=rot(w['hand_r'])@handbind.T@F;angles=np.degrees(np.arccos(np.clip((actual*axis).sum(1),-1,1)))
    steps={n:float(np.degrees(R.from_matrix(np.swapaxes(rot(w[n][:-1]),1,2)@rot(w[n][1:])).magnitude()).max()) for n in ['upperarm_r','lowerarm_r','lowerarm_twist_01_r','lowerarm_twist_02_r','hand_r']}
    lengths={s:np.linalg.norm(w[b][:,:3,3]-w[a][:,:3,3],axis=1) for s,a,b in [('upper','upperarm_r','lowerarm_r'),('fore','lowerarm_r','hand_r')]}
    report[prefix]=dict(samples=len(error),fps=d['fps'],max_grip_error_cm=float(error.max()),max_wrist_axis_deg=float(angles.max()),
        max_step_deg=steps,segment_lengths_cm={k:[float(v.min()),float(v.max())] for k,v in lengths.items()},
        end_grip_error_cm=float(error[-1]))
(r/'melee_check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
