"""Dense saved-pose review of side-magazine grasp, joints and idle handoff."""
from pathlib import Path
import sys,pickle,json,gzip,numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
r=Path(__file__).resolve().parent
sys.path.insert(0,str(r.parent/'Repair06'));from contact_sweep import matrix
label=sys.argv[1] if len(sys.argv)>1 else 'before'
d=pickle.load(open(r/('saved_compressed.pkl' if label=='saved' else 'native.pkl'),'rb'));names=d['names'];ix={n:i for i,n in enumerate(names)}
B=matrix(d['bind']);inverse=np.linalg.inv(B)
def rot(a):return a[...,:3,:3]/np.linalg.norm(a[...,:3,:3],axis=-2,keepdims=True)
def world(a):
    a=matrix(a)
    for i,p in enumerate(d['parents']):
        if p>=0:a[:,i]=a[:,p]@a[:,i]
    return a
def profile(a,path,family,times):
    a=np.array(a,dtype=float).copy()
    rows=d['profiles'][family]['clips']
    if label not in ('before','saved'):
        incoming=json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips'];keys={c['base'].split('.')[0] for c in incoming}
        rows=[c for c in rows if c['base'].split('.')[0] not in keys]+incoming
    c=next((c for c in rows if c['base'].split('.')[0]==path.split('.')[0]),None)
    if c:
        for track in c['tracks']:
            v=np.array(track['values']).reshape(-1,10);ts=np.array(track['times']);n=ix[track['bone']];tm=np.minimum(times,ts[-1])
            a[:,n,:3]+=np.stack([np.interp(tm,ts,v[:,i]) for i in range(3)],axis=1)
            q=Slerp(ts,R.from_quat(v[:,3:7]))(tm) if len(ts)>1 else R.from_quat(v[0,3:7])
            a[:,n,3:7]=(q*R.from_quat(a[:,n,3:7])).as_quat()
            a[:,n,7:]+=np.stack([np.interp(tm,ts,v[:,i]) for i in range(7,10)],axis=1)
    return a
idlepath=next(k for k in d['clips'] if k.split('.')[0].endswith('_idle'))
idle=d['clips'][idlepath];f0=B[ix['hand_l'],:3,3]-B[ix['lowerarm_l'],:3,3];f0/=np.linalg.norm(f0)
report={};cache={}
for role in ('reload','reload_empty'):
    path='/Game/Weapons/M249/SideMagazine20261108/Animations/A_M249_side_'+role
    if label in ('before','saved'):c=d['clips'][path+'.'+path.split('/')[-1]];a=np.array(c['frames'])
    else:c=json.load(gzip.open(r/'Motion'/(role+'.json.gz'),'rt'));a=np.stack([c['tracks'][n] for n in names],axis=1)
    times=np.arange(len(a))/c['fps']
    for family in d['profiles']:
        w=world(profile(a,path,family,times));iw=world(profile(idle['frames'][:1],idlepath,family,np.array([0.])))
        h=w[:,ix['hand_l']];l=w[:,ix['lowerarm_l']];u=w[:,ix['upperarm_l']]
        axis=h[:,:3,3]-l[:,:3,3];axis/=np.linalg.norm(axis,axis=1)[:,None]
        wrist=rot(h)@rot(B[ix['hand_l']]).T@f0
        angle=np.degrees(np.arccos(np.clip((axis*wrist).sum(1),-1,1)))
        steps={};endpoint={}
        for n in ('clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l'):
            m=w[:,ix[n]];dist=np.linalg.norm(np.diff(m[:,:3,3],axis=0),axis=1);angular=np.degrees((R.from_matrix(rot(m[:-1])).inv()*R.from_matrix(rot(m[1:]))).magnitude())
            steps[n]=dict(cm=float(dist.max()),cm_at=float(times[dist.argmax()]),degrees=float(angular.max()),deg_at=float(times[angular.argmax()]))
            endpoint[n]={phase:dict(cm=float(np.linalg.norm(m[k,:3,3]-iw[0,ix[n],:3,3])),degrees=float(np.degrees(R.from_matrix(rot(m[k])@rot(iw[0,ix[n]]).T).magnitude()))) for phase,k in [('start',0),('end',-1)]}
        relative=np.linalg.inv(w[:,ix['WPN_SOCKET_Magazine']])@h;lock=(times>=.70)&(times<=2.78);ref=relative[np.argmin(abs(times-.72))]
        drift=np.linalg.norm((relative[lock,:3,3]-ref[:3,3])*100,axis=1)
        turn=np.degrees(R.from_matrix(rot(relative[lock])@rot(ref).T).magnitude())
        record=dict(wrist_max_deg=float(angle.max()),wrist_at=float(times[angle.argmax()]),steps=steps,idle_handoff=endpoint,contact_drift_cm=float(drift.max()),contact_rotation_deg=float(turn.max()))
        report[role+'_'+family]=record
        cache[role+'_'+family]=dict(times=times,world=w,idle=iw[0])
        print(role,family,'wrist',round(angle.max(),2),'at',times[angle.argmax()],'end lowerarm',endpoint['lowerarm_l']['end'],'peak joint',max((v['degrees'],k,v['deg_at']) for k,v in steps.items()),flush=True)
(r/(label+'_joints.json')).write_text(json.dumps(report,indent=2))
with (r/(label+'_world.pkl')).open('wb') as f:pickle.dump(cache,f)
