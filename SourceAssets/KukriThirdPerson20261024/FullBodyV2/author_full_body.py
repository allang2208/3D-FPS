"""Keep the complete cut/step together; fit grounded, yielding knees to Jason."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[1]
sys.path.insert(0,str(BASE))
from author_actions import mix,slerp,smooth
data=json.loads((BASE/'adapted-actions.json').read_text())
raw=json.loads((BASE/'retargeted-poses.json').read_text())
spin_path=ROOT/'SourceAssets/ThirdPersonMeleeRegression20261010/adapted-actions.json'
spin=json.loads(spin_path.read_text())
names=data['names'];parents=data['parents'];ix={n:i for i,n in enumerate(names)}
if names!=spin['names']:raise RuntimeError('Spin donor requires a different native skeleton map')
def world(f):
    p=f[:,:,:3].copy();q=f[:,:,3:7].copy();s=f[:,:,7:].copy()
    for i,par in enumerate(parents):
        if par<0:continue
        p[:,i]=p[:,par]+R.from_quat(q[:,par]).apply(f[:,i,:3]*s[:,par])
        q[:,i]=(R.from_quat(q[:,par])*R.from_quat(q[:,i])).as_quat();s[:,i]*=s[:,par]
    return p,q
def align(a,b):
    a=a/np.linalg.norm(a,axis=1)[:,None];b=b/np.linalg.norm(b,axis=1)[:,None]
    q=np.c_[np.cross(a,b),1+np.sum(a*b,axis=1)]
    return R.from_quat(q/np.linalg.norm(q,axis=1)[:,None])
def resample(f,count):
    out=[]
    for t in np.linspace(0,len(f)-1,count):
        i=int(t);out.append(mix(f[i],f[min(i+1,len(f)-1)],t-i))
    return np.asarray(out)
idle=np.asarray(data['clips']['Idle']['frames'][0]);idle_p,_=world(idle[None])
arm_indices=[]
for i,n in enumerate(names):
    j=i
    while j>=0:
        if names[j] in ('clavicle_r','clavicle_l','neck_01'):
            arm_indices.append(i);break
        j=parents[j]
report={}
planar={'Slash1':.70,'Slash2':.60,'Thrust':.75,'Pommel':.55,'Dash':.75}
for label,c in data['clips'].items():
    f=np.asarray(c['frames']);old=f.copy();count=len(f)
    if label.startswith('Whirlwind.'):
        # The local Kwang take supplies the actual turning body/legs. Keep the
        # independent single-hand arm chains, not Kwang's two-hand sword grip.
        f=resample(np.asarray(spin['clips'][label]['frames']),count)
        f[:,arm_indices]=old[:,arm_indices]
        f[:,ix['root']]=old[:,ix['root']]
        if label.endswith('Start'):
            for i in range(count):f[i]=mix(idle,f[i],smooth((i/c['rate'])/.14))
        if label.endswith('End'):
            duration=(count-1)/c['rate']
            for i in range(count):f[i]=mix(f[i],idle,smooth((i/c['rate']-duration+.22)/.22))
        c['source']=str(spin_path.relative_to(ROOT));c['source_group']='Kwang local turning body + KayKit single-hand arms'
        c['adaptation']='full turning pelvis/legs/chest; native single-hand arms; no static spin pose'
    if label=='Dash':
        # Retain the source's push-off, tucked legs and landing, with a short
        # combat hop rather than the cartoon donor's 1.5-metre vertical travel.
        hip=ix['pelvis'];z0=float(idle[hip,2]);rise=np.maximum(0,f[:,hip,2]-z0)
        f[:,hip,2]-=rise*.72
    p,q=world(f);targets={s:p[:,ix['foot_'+s]].copy() for s in 'lr'}
    scale=planar.get(label,1.)
    hip=ix['pelvis']
    f[:,hip,:2]=idle[hip,:2]+(f[:,hip,:2]-idle[hip,:2])*scale
    for s in 'lr':
        base=idle_p[0,ix['foot_'+s],:2]
        targets[s][:,:2]=base+(targets[s][:,:2]-base)*scale
    # Source attack knees sometimes reach 0 degrees. Lower the loaded pelvis
    # just enough to retain 20 degrees of flex, keeping each authored ankle.
    p,q=world(f);drop=np.zeros(count)
    for s in 'lr':
        h,k,a=[p[:,ix[n+'_'+s]] for n in ('thigh','calf','foot')]
        l1=np.linalg.norm(k-h,axis=1);l2=np.linalg.norm(a-k,axis=1)
        reach=np.sqrt(l1*l1+l2*l2+2*l1*l2*np.cos(np.deg2rad(20)))
        xy=np.sum((targets[s][:,:2]-h[:,:2])**2,axis=1)
        max_z=targets[s][:,2]+np.sqrt(np.maximum(1,reach*reach-xy))
        drop=np.maximum(drop,h[:,2]-max_z)
    drop=np.maximum(drop,0);f[:,hip,2]-=drop
    p,q=world(f)
    for s in 'lr':
        hidx,kidx,aidx=[ix[n+'_'+s] for n in ('thigh','calf','foot')]
        h,k,a=[p[:,j] for j in (hidx,kidx,aidx)];goal=targets[s]
        l1=np.linalg.norm(k-h,axis=1);l2=np.linalg.norm(a-k,axis=1)
        axis=goal-h;dist=np.linalg.norm(axis,axis=1);axis/=dist[:,None]
        pole=k-h;pole-=axis*np.sum(pole*axis,axis=1)[:,None]
        pole/=np.maximum(np.linalg.norm(pole,axis=1)[:,None],1e-8)
        along=(l1*l1-l2*l2+dist*dist)/(2*dist)
        knee=h+axis*along[:,None]+pole*np.sqrt(np.maximum(0,l1*l1-along*along))[:,None]
        hq=align(k-h,knee-h)*R.from_quat(q[:,hidx])
        kq=align(a-k,goal-knee)*R.from_quat(q[:,kidx])
        f[:,hidx,3:7]=(R.from_quat(q[:,parents[hidx]]).inv()*hq).as_quat()
        f[:,kidx,3:7]=(hq.inv()*kq).as_quat()
        f[:,aidx,3:7]=(kq.inv()*R.from_quat(q[:,aidx])).as_quat()
    after_p,_=world(f)
    c['frames']=f.tolist()
    report[label]=dict(frames=count,pelvis_drop_max_cm=float(drop.max()),planar_scale=scale,
        ankle_fit_error_cm=max(float(np.linalg.norm(after_p[:,ix['foot_'+s]]-targets[s],axis=1).max()) for s in 'lr'))
(OUT/'adapted-actions.json').write_text(json.dumps(data,separators=(',',':')))
(OUT/'authoring-report.json').write_text(json.dumps(report,indent=2))
for label,r in report.items():print(label,'drop',round(r['pelvis_drop_max_cm'],2),'ankle fit',round(r['ankle_fit_error_cm'],5))
