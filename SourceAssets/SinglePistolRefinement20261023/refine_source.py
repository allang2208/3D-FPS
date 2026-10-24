"""Repair discontinuous source FK rotations, keeping lengths and source clocks."""
import json, hashlib
from pathlib import Path
import numpy as np

ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).parent;SOURCE=ROOT/'SourceAssets/GitHubSinglePistol20261022'
d=json.loads((SOURCE/'retargeted-poses.json').read_text())
for name in ('EndBind_retargeted-poses.json','CrouchInitBind_retargeted-poses.json'):
    d['clips'].update(json.loads((SOURCE/name).read_text())['clips'])
target=d['target'];names=target['names'];parents=target['parents']
upper=names.index('spine_01')
def within(i):
    while i>=0:
        if i==upper:return True
        i=parents[i]
    return False
def mean(q,w=None):
    if w is None:w=np.ones(len(q))
    v=np.linalg.eigh(np.einsum('i,ij,ik->jk',w,q,q))[1][:,-1]
    return v if np.dot(v,q[len(q)//2])>=0 else -v
def angle(a,b):return 2*np.arccos(np.clip(abs(np.dot(a,b)),0,1))
def positions(frames,bone):
    result=[]
    for frame in frames:
        world=[]
        for i,t in enumerate(frame):
            x,y,z,w=t[3:7];m=np.eye(4)
            m[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])@np.diag(t[7:])
            m[:3,3]=t[:3];world.append(m if parents[i]<0 else world[parents[i]]@m)
        result.append(world[names.index(bone)][:3,3])
    return np.array(result)
roles={'Reload.Init':'RevolverReloadInit','Reload.Loop':'RevolverReloadLoop','Reload.End':'RevolverReloadEnd',
    'Crouch.Reload.Init':'RevolverCrouchAimReloadInit','Crouch.Reload.Loop':'RevolverCrouchAimReloadLoop','Crouch.Reload.End':'RevolverCrouchAimReloadEnd'}
result={'target':target,'clips':{},'provenance':'GitHub f19adc2ece4cab0f89c9236223abb97d4d2badea; corrected per-clip binds; quaternion spike repair and FK curve filtering'}
stats={}
for role,name in roles.items():
    clip=d['clips'][name];raw=np.array(clip['frames']);fixed=raw.copy();n=len(raw);spikes=0
    for bone in range(len(names)):
        if not within(bone):continue
        q=raw[:,bone,3:7].copy();q/=np.linalg.norm(q,axis=1)[:,None]
        clean=q.copy()
        for i in range(1,n-1):
            a,b,c=angle(q[i-1],q[i]),angle(q[i],q[i+1]),angle(q[i-1],q[i+1])
            if min(a,b)>np.deg2rad(15) and a+b-c>np.deg2rad(20):
                clean[i]=mean(np.array([q[i-1],q[i+1]]));spikes+=1
        for i in range(n):
            radius,sigma=(5,2.5) if role.endswith('Init') else (3,1.5)
            indices=np.clip(np.arange(i-radius,i+radius+1),0,n-1)
            fixed[i,bone,3:7]=mean(clean[indices],np.exp(-.5*(np.arange(-radius,radius+1)/sigma)**2))
            if i and np.dot(fixed[i,bone,3:7],fixed[i-1,bone,3:7])<0:fixed[i,bone,3:7]*=-1
    if role.endswith('Init'):
        # This free-hand withdrawal has no magazine contact keys. Distribute
        # its travel over the existing duration; the donor concentrated almost
        # all of it in the first few frames, especially in a short partial reload.
        r,l=positions(fixed,'hand_r'),positions(fixed,'hand_l')
        distance=np.maximum(np.linalg.norm(np.diff(r,axis=0),axis=1),np.linalg.norm(np.diff(l,axis=0),axis=1))
        arc=np.r_[0,np.cumsum(np.maximum(distance,1e-5))];arc/=arc[-1]
        u=np.linspace(0,1,n);times=np.interp(u*u*(3-2*u),arc,np.arange(n))
        authored=fixed.copy()
        for i,t in enumerate(times):
            lo=min(int(t),n-2);alpha=t-lo
            for bone in range(len(names)):
                if not within(bone):continue
                qa,qb=authored[lo,bone,3:7],authored[lo+1,bone,3:7]
                if np.dot(qa,qb)<0:qb=-qb
                theta=np.arccos(np.clip(np.dot(qa,qb),-1,1))
                q=(1-alpha)*qa+alpha*qb if theta<1e-6 else (np.sin((1-alpha)*theta)*qa+np.sin(alpha*theta)*qb)/np.sin(theta)
                fixed[i,bone,3:7]=q/np.linalg.norm(q)
    stats[role]={'repaired_bone_keys':spikes,'max_hand_step_before':{},'max_hand_step_after':{}}
    stats[role]['free_withdrawal_arc_retimed']=role.endswith('Init')
    for hand in ('hand_r','hand_l'):
        stats[role]['max_hand_step_before'][hand]=float(np.linalg.norm(np.diff(positions(raw,hand),axis=0),axis=1).max())
        stats[role]['max_hand_step_after'][hand]=float(np.linalg.norm(np.diff(positions(fixed,hand),axis=0),axis=1).max())
    result['clips'][role]={'source':clip['asset'],'rate':30,'duration':clip['duration'],'frames':fixed.tolist()}
(OUT/'refined-fk.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
(OUT/'source-refinement.json').write_text(json.dumps(stats,indent=2),encoding='utf8')
print(json.dumps(stats,indent=2))
