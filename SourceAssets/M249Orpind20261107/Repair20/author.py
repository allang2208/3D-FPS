"""Native anatomical hinge repair, preserving palm contacts and mechanical clocks."""
from pathlib import Path
import sys,pickle,json,gzip,importlib.util,numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
from scipy.ndimage import gaussian_filter1d
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r.parent/'Repair10'))
from motion import matrix,rot,unit,frame,mix,ease
d=pickle.load(open(r/'native.pkl','rb'));names=d['names'];ix={n:i for i,n in enumerate(names)};parents=d['parents'];B=np.array([matrix(v) for v in d['bind']])
spec=importlib.util.spec_from_file_location('hinge',r.parents[1]/'PKMLowpoly20260922/ArmHinge55/author.py');hinge=importlib.util.module_from_spec(spec);spec.loader.exec_module(hinge)
hinge.PRONATION_SHARE={4:0.,5:.5,6:1.};hinge.CREASE_ROLL=0.;hinge.ELBOW_CM=6.
def world(a):
    w=np.array([[matrix(v) for v in row] for row in a])
    for i,p in enumerate(parents):
        if p>=0:w[:,i]=w[:,p]@w[:,i]
    return w
def layer(a,path,family,t):
    a=a.copy();c=next((c for c in d['profiles'][family]['clips'] if c['base']==path),None)
    if c:
        for q in c['tracks']:
            v=np.array(q['values']).reshape(-1,10);ts=np.array(q['times']);at=np.clip(t,ts[0],ts[-1]);i=ix[q['bone']]
            a[:,i,:3]+=np.stack([np.interp(at,ts,v[:,j]) for j in range(3)],axis=1)
            spin=Slerp(ts,R.from_quat(v[:,3:7]))(at) if len(ts)>1 else R.from_quat(v[0,3:7])
            a[:,i,3:7]=(spin*R.from_quat(a[:,i,3:7])).as_quat();a[:,i,7:]+=np.stack([np.interp(at,ts,v[:,j]) for j in range(7,10)],axis=1)
    return a
def binding(side):
    bn=[n[:-1]+side for n in hinge.BONES];b=object.__new__(hinge.Bind);b.R=[rot(B[ix[n]]) for n in bn];P=[B[ix[n],:3,3] for n in bn]
    b.U0=P[4]-P[1];b.F0=P[7]-P[4];b.H0=unit(np.cross(b.U0,b.F0));b.FU0=frame(b.U0,b.H0);b.FL0=frame(b.F0,b.H0);b.st={};b.off={}
    for i,o,axis in [(2,P[1],b.U0),(3,P[1],b.U0),(5,P[4],b.F0),(6,P[4],b.F0)]:
        b.st[i]=(P[i]-o)@axis/(axis@axis);b.off[i]=P[i]-o-b.st[i]*axis
    return b,bn
def wave(t,at,span):
    x=(t-at)/span
    return np.interp(x,[0,.22,.36,.72,1],[0,1,.82,-.24,0]) if 0<x<1 else 0.
def turn_withdrawn_magazine(w,t):
    # The old clip held the magazine at a fixed receiver orientation even at
    # the shoulder-side pickup. That forced ~243 degrees of forearm roll.
    # Once clear of the port, turn the held magazine and whole hand together.
    b,bn=binding('l');angles=[];axes=[]
    for fr in w:
        a,e,h=[fr[ix[n],:3,3] for n in (bn[1],bn[4],bn[7])];f=h-e;n=unit(np.cross(e-a,f));dl=frame(f,n)@b.FL0.T;dh=rot(fr[ix['hand_l']])@b.R[7].T;q=R.from_matrix(dh@dl.T).as_quat();angles.append(2*np.arctan2(q[:3]@unit(f),q[3]));axes.append(unit(f))
    tau=np.unwrap(angles);excess=gaussian_filter1d(np.maximum(tau-np.radians(145.),0.),3.,mode='nearest')
    members=[i for i,n in enumerate(names) if n=='WPN_SOCKET_Magazine' or n=='hand_l' or (n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky','ik_hand')))]
    for k,tm in enumerate(t):
        gain=ease((tm-.85)/.16)*(1-ease((tm-2.02)/.20));spin=R.from_rotvec(axes[k]*(-excess[k]*gain)).as_matrix();p=w[k,ix['hand_l'],:3,3].copy();xf=np.eye(4);xf[:3,:3]=spin;xf[:3,3]=p-spin@p
        for i in members:w[k,i]=xf@w[k,i]
    return w
def body_feedback(w,t,side,empty):
    # All mechanical parts and both palms share this rigid reaction. The camera
    # has its separate RC1 follow/impulses; aim and gameplay clocks stay intact.
    root=w[ix['WPN_root']];offset=np.zeros(3);angles=np.zeros(3)
    if side:
        for at,span,scale in [(.72,.28,.65),(2.55,.24,-.4),(2.70,.28,-1.)]:
            v=wave(t,at,span)*scale;offset+=np.array([.14,.20,-.08])*v;angles+=np.array([.15,-.32,.15])*v
    if empty:
        pull,rear,push,closed=(3.18,3.41,3.53,3.87) if side else (5.13,5.36,5.48,5.82)
        load=ease((t-(pull-.12))/(rear-pull+.12))*(1-ease((t-push)/(closed-push)))
        hit=wave(t,rear,.16);release=wave(t,closed,.34)
        offset+=np.array([.12,-.65,-.15])*load+np.array([0,-.25,-.08])*hit+np.array([-.08,.45,.12])*release
        angles+=np.array([.3,-1.1,.25])*load+np.array([0,-.35,.1])*hit+np.array([-.15,.8,-.16])*release
    q=rot(root);delta=R.from_euler('xyz',angles,degrees=True).as_matrix();xf=np.eye(4);xf[:3,:3]=q@delta@q.T;xf[:3,3]=root[:3,3]+q@offset-xf[:3,:3]@root[:3,3]
    for i,n in enumerate(names):
        if n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','ik_hand','WPN_','PKM_','New_')):w[i]=xf@w[i]
    return w
def encode(w):
    local=w.copy()
    for i,p in enumerate(parents):
        if p>=0:local[:,i]=np.linalg.inv(w[:,p])@w[:,i]
    scales=np.linalg.norm(local[:,:,:3,:3],axis=2);q=R.from_matrix((local[:,:,:3,:3]/scales[:,:,None,:]).reshape(-1,3,3)).as_quat().reshape(len(w),len(names),4)
    for k in range(1,len(q)):
        flip=(q[k-1]*q[k]).sum(1)<0;q[k,flip]*=-1
    return np.concatenate((local[:,:,:3,3],q,scales),axis=2)
def errors(w,side):
    b,bn=binding(side);a,e,h=[w[:,ix[n],:3,3] for n in [bn[1],bn[4],bn[7]]];u=e-a;f=h-e;axis=np.cross(u,f);axis/=np.linalg.norm(axis,axis=1)[:,None];bend=np.degrees(np.arccos(np.clip((u*f).sum(1)/np.linalg.norm(u,axis=1)/np.linalg.norm(f,axis=1),-1,1)))
    m=w[:,ix[bn[3]],:3,:3];m=m/np.linalg.norm(m,axis=1)[:,None,:];n=m@b.R[3].T@b.H0;err=np.degrees(np.arccos(np.clip((n*axis).sum(1),-1,1)))
    return float(err[bend>30].max()) if any(bend>30) else 0.
outdir=r/'Motion';outdir.mkdir(exist_ok=True);profiles={f:[] for f in d['profiles']};report={};cache={}
for path,c in d['clips'].items():
    if path.split('.')[0].endswith('_idle'):continue
    side='/SideMagazine' in path;empty=path.split('.')[0].endswith('_reload_empty');key=('side_' if side else 'box_')+('reload_empty' if empty else 'reload');t=np.arange(len(c['frames']))/c['fps'];a=np.array(c['frames']);base=None;right=None
    for family in profiles:
        w=world(layer(a,path,family,t));original=w.copy()
        if side:w=turn_withdrawn_magazine(w,t)
        old=w.copy();stats={}
        for hand in ('l','r'):
            b,bn=binding(hand);indices=[ix[n] for n in bn]
            if hand=='r' and right is not None:
                w[:,indices]=right;continue
            before=errors(original,hand);hinge.CAP=np.radians(145. if side and hand=='l' else 110.);solved,info=hinge.solve(w[:,indices],b)
            # The stable family idle remains the exact entry and exit pose.
            for k,tm in enumerate(t):
                blend=ease(tm/.25)*(1-ease((tm-(c['duration']-.35))/.35))
                for j in range(1,7):w[k,indices[j]]=mix(old[k,indices[j]],solved[k][j],blend)
            if hand=='r':right=w[:,indices].copy()
            stats[hand]=dict(hinge_before=before,hinge_after=errors(w,hand),upper_roll_max=float(np.max(abs(info['upper']))),forearm_max=float(np.max(abs(info['forearm']))))
        for k,tm in enumerate(t):w[k]=body_feedback(w[k],tm,side,empty)
        rows=encode(w)
        if family=='base':
            base=rows.copy();tracks={n:rows[:,i].tolist() for i,n in enumerate(names)}
            with gzip.open(outdir/(key+'.json.gz'),'wt') as f:json.dump(dict(asset=path.split('.')[0],fps=c['fps'],duration=c['duration'],tracks=tracks),f,separators=(',',':'))
        delta=[]
        for i,n in enumerate(names):
            v=np.zeros((len(t),10));v[:,:3]=rows[:,i,:3]-base[:,i,:3];v[:,3:7]=(R.from_quat(rows[:,i,3:7])*R.from_quat(base[:,i,3:7]).inv()).as_quat();v[:,7:]=rows[:,i,7:]-base[:,i,7:]
            for k in range(1,len(v)):
                if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
            if np.max(abs(v-np.array([0,0,0,0,0,0,1,0,0,0])))>1.e-6:delta.append(dict(bone=n,times=t.tolist(),values=v.ravel().tolist()))
        profiles[family].append(dict(base=path.split('.')[0],duration=c['duration'],tracks=delta));report[key+'_'+family]=stats;cache[key+'_'+family]=dict(times=t,world=w)
        print('M249_HINGE_AUTHORED',key,family,stats,flush=True)
for family,rows in profiles.items():
    with gzip.open(r/(family+'.json.gz'),'wt') as f:json.dump(dict(family=family,clips=rows),f,separators=(',',':'))
(r/'authoring.json').write_text(json.dumps(report,indent=2))
with (r/'candidate_world.pkl').open('wb') as f:pickle.dump(cache,f)
