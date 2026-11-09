"""Dense saved-native bipod joint, grasp and handoff measurements."""
from pathlib import Path
import pickle,json,sys,numpy as np
from scipy.spatial.transform import Rotation as R,Slerp
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'Repair06'))
from contact_sweep import matrix,intersect
import trimesh
r=Path(__file__).resolve().parent
g=pickle.load(open(r/'geometry.pkl','rb'));names=g['names'];index={n:i for i,n in enumerate(names)};B=matrix(g['bind']);invB=np.linalg.inv(B)
def world(d):
    a=matrix(d['frames'])
    for i,p in enumerate(g['parents']):
        if p>=0:a[:,i]=a[:,p]@a[:,i]
    return a
def rot(m):return m[...,:3,:3]/np.linalg.norm(m[...,:3,:3],axis=-2,keepdims=True)
label=sys.argv[1] if len(sys.argv)>1 else 'before'
if label=='before':data=pickle.load(open(r/'bipod_saved.pkl','rb'))
elif label=='final':data=pickle.load(open(r/'final_saved.pkl','rb'))
else:
    import gzip
    data=json.load(gzip.open(r/'bipod.json.gz','rt'));data['frames']=np.stack([data['tracks'][n] for n in names],axis=1)
w=world(data);idle=world(pickle.load(open(r/'idle_saved.pkl','rb')))
if label=='final':
    hold=pickle.load(open(r/'hold_world.pkl','rb'));idle=np.array([[hold[n] for n in names]])
runtime_scale=1.5 if label=='before' else .9/.48
report={};l=index['lowerarm_l'];h=index['hand_l'];u=index['upperarm_l'];f0=B[h,:3,3]-B[l,:3,3];f0/=np.linalg.norm(f0)
actual=w[:,h,:3,3]-w[:,l,:3,3];actual/=np.linalg.norm(actual,axis=1)[:,None]
wristaxis=rot(w[:,h])@rot(B[h]).T@f0;angles=np.degrees(np.arccos(np.clip((actual*wristaxis).sum(1),-1,1)))
steps={};source_times=np.arange(len(w))/data['fps'];sample_times=source_times[source_times+1/(60*runtime_scale)<=source_times[-1]];later=sample_times+1/(60*runtime_scale)
for n in ['clavicle_l','upperarm_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l']:
    m=w[:,index[n]];q=Slerp(source_times,R.from_matrix(rot(m)));angle=np.degrees((q(sample_times).inv()*q(later)).magnitude());at=np.stack([np.interp(sample_times,source_times,m[:,a,3]) for a in range(3)],axis=1);to=np.stack([np.interp(later,source_times,m[:,a,3]) for a in range(3)],axis=1);dist=np.linalg.norm(to-at,axis=1)
    steps[n]=dict(max_60hz_deploy_cm=float(dist.max()),time=float(sample_times[dist.argmax()]*runtime_scale),max_60hz_deg=float(angle.max()),angle_time=float(sample_times[angle.argmax()]*runtime_scale))
report.update(max_wrist_deg=float(angles.max()),wrist_at_runtime_seconds=float(angles.argmax()/data['fps']*runtime_scale),joint_steps=steps,
    endpoints={n:dict(start_cm=float(np.linalg.norm(w[0,index[n],:3,3]-idle[0,index[n],:3,3])),end_cm=float(np.linalg.norm(w[-1,index[n],:3,3]-idle[0,index[n],:3,3]))) for n in ('hand_l','upperarm_l','lowerarm_l')})
if '--joints-only' in sys.argv:
    (r/(label+'_joints.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));raise SystemExit
# Surface sweep through the shared reversible action.
v=np.array(g['vertices']);faces=np.array(g['faces']);sections=np.array(g['sections']);dom=np.array([max(ws,key=lambda a:a[1])[0] for ws in g['weights']])
left=np.array([n.endswith('_l') for n in names])[dom];lf=faces[left[faces].all(1)]
groups=[]
for bone in sorted({b for ws in g['weights'] for b,_ in ws}):
    pairs=[(i,weight) for i,ws in enumerate(g['weights']) for b,weight in ws if b==bone]
    ids=np.array([i for i,_ in pairs]);groups.append((bone,ids,np.c_[v[ids],np.ones(len(ids))]*np.array([a for _,a in pairs])[:,None]))
slots=g['slots'];print('SLOTS',list(enumerate(slots)),flush=True)
body={slot:faces[sections==i] for i,slot in enumerate(slots) if not any(s in slot for s in ('Skin','Arm','Bipod','New','Glass','Reticle','Belt','Bullet')) and not left[faces[sections==i]].any()}
geom=json.loads((r.parent/'Repair08/bipod_geometry.json').read_text());rodparts={}
for i,key in enumerate(('LegLeft','LegRight')):
    raw=np.load(r.parent/'Geometry'/(key+'.npz'));rawp=raw['positions'];comp=np.c_[5.45+100*rawp[:,1],100*rawp[:,0]-28.6,100*rawp[:,2]-5.3]
    leg=geom['legs'][i];pivot=np.array(leg['pivot']);tip=np.array(leg['tip']);fold=np.array(leg['folded_tip']);a=tip/np.linalg.norm(tip);b=fold/np.linalg.norm(fold)
    closed=R.from_quat(np.r_[np.cross(a,b),1+a@b]);points=(comp-B[index['WPN_root'],:3,3])@rot(B[index['WPN_root']])-pivot
    rodparts[key]=(points,raw['faces'],pivot,closed)
contact=[];samples=sorted(set([0,*range(0,len(w),max(1,round(data['fps']/60))),len(w)-1]));frameout={}
for k in samples:
    pose=w[k];xf=pose@invB;points=np.zeros_like(v)
    for b,ids,p in groups:points[ids]+=p@xf[b,:3,:].T
    t=k/data['fps'];phase=np.clip((t-.12)/.18,0,1);opened=phase*phase*(3-2*phase);root=pose[index['WPN_root']];rq=rot(root)
    obstacles={name:(points,fs) for name,fs in body.items()}
    for name,(p,fs,pivot,closed) in rodparts.items():
        q=R.from_rotvec(closed.as_rotvec()*(1-opened)).as_matrix();pos=(p@q.T+pivot)@rq.T+root[:3,3];obstacles[name]=(pos,fs)
    hand=points[lf];mins=hand.min(1);maxs=hand.max(1);collisions={}
    for name,(p,fs) in obstacles.items():
        mesh=trimesh.Trimesh(p,fs,process=False);tri=p[fs];lo=tri.min((0,1));hi=tri.max((0,1));near=np.nonzero(((maxs>=lo)&(mins<=hi)).all(1))[0];hits=[];bones=set()
        for j in near:
            for b in mesh.triangles_tree.intersection(np.r_[mins[j],maxs[j]]):
                if intersect(hand[j],tri[b]):hits.append(int(j));bones.update(names[i] for i in dom[lf[j]]);break
        if hits:collisions[name]=dict(triangles=len(hits),bones=sorted(bones))
    contact.append(dict(source_time=t,runtime_time=t*1.5,collisions=collisions))
    if collisions:print('CONTACT',round(t,4),collisions,flush=True)
    frameout[str(round(t,6))]=dict(vertices=points,legs={name:obstacles[name] for name in rodparts})
report['surface_sweep']=contact
(r/(label+'_measurements.json')).write_text(json.dumps(report,indent=2))
with (r/(label+'_surface.pkl')).open('wb') as f:pickle.dump(frameout,f)
print(json.dumps({k:v for k,v in report.items() if k!='surface_sweep'},indent=2),flush=True)
