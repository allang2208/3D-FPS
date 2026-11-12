"""M249 wrist relief in the shared support pose and free box-reload travel.

Palm/contact matrices are fixed during support. Elbow moves on the fixed-length
shoulder/wrist circle; both segments transport together so the elbow hinge is
preserved. Only free travel after cover release can rotate the palm.
"""
import json,pickle,gzip,copy,os
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['MKL_NUM_THREADS']='1'
from scipy.optimize import minimize
from scipy.spatial import ConvexHull
from scipy.ndimage import gaussian_filter1d
from pose import *
d=pickle.load(open(r/'current.pkl','rb'));names=d['names'];ix={n:i for i,n in enumerate(names)};parents=d['parents'];B=matrix(d['bind'])
cl,ua,la,ha,gun=[ix[n] for n in ('clavicle_l','upperarm_l','lowerarm_l','hand_l','WPN_root')]
arm=[ix[n] for n in ('upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l')]
hand=[i for i,n in enumerate(names) if n=='hand_l' or (n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky','ik_hand')))]
owned=[cl]+arm+hand
f0=unit(B[ha,:3,3]-B[la,:3,3]);idlepath=next(p for p in d['clips'] if p.endswith('A_M249_idle'))
g=pickle.load(open(r/'geometry.pkl','rb'));vertices=np.array(g['vertices']);tri=np.array(g['faces']);sections=np.array(g['sections']);box=ix['PKM_Box']
box_ids=np.unique(tri[sections==g['slots'].index('M249_Surface__OldBox')])
planes=ConvexHull(vertices[box_ids]).equations
skin_ids=np.array([i for i,ws in enumerate(g['weights']) if sum(w for b,w in ws if names[b].endswith('_l') and names[b].startswith('lowerarm'))>.50])
skin_bind=np.c_[vertices[skin_ids],np.ones(len(skin_ids))];skin_weights={}
for j,i in enumerate(skin_ids):
    for b,w in g['weights'][i]:skin_weights.setdefault(b,np.zeros(len(skin_ids)))[j]=w
ib=np.linalg.inv(B)
def box_clearance(w):
    pts=np.zeros((len(skin_ids),3));xf=w@ib
    for b,ws in skin_weights.items():pts+=(skin_bind@xf[b,:3,:].T)*ws[:,None]
    undo=B[box]@np.linalg.inv(w[box]);pts=pts@undo[:3,:3].T+undo[:3,3]
    return float(np.max(pts@planes[:,:3].T+planes[:,3],axis=1).min())
def ease(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def wrist(w):
    axis=rot(w[ha])@rot(B[ha]).T@f0
    return np.arccos(np.clip(unit(w[ha,:3,3]-w[la,:3,3])@axis,-1,1))
def frame(x,z):
    x=unit(x);z=unit(z-x*(x@z));return np.column_stack((x,np.cross(z,x),z))
def elbow_pose(w,parameters):
    out=w.copy();shoulder=rot(w[gun])@np.array(parameters[:3]);delta=R.from_rotvec(shoulder).as_matrix()
    shift=rot(w[gun])@np.array(parameters[4:7]) if len(parameters)>4 else np.zeros(3)
    for i in hand:out[i,:3,3]+=shift
    c=w[cl,:3,3];a0=w[ua,:3,3];e0=w[la,:3,3];h0=w[ha,:3,3];h=out[ha,:3,3];a=c+delta@(a0-c)
    out[cl,:3,:3]=delta@w[cl,:3,:3]
    upper_length=np.linalg.norm(e0-a0);lower_length=np.linalg.norm(h0-e0);axis=unit(h-a);distance=np.linalg.norm(h-a)
    along=(upper_length**2-lower_length**2+distance**2)/(2*distance)
    radius=np.sqrt(max(0,upper_length**2-along**2));center=a+axis*along
    pole=unit(e0-center-axis*((e0-center)@axis));elbow=center+R.from_rotvec(axis*parameters[3]).as_matrix()@pole*radius
    old_hinge=unit(np.cross(e0-a0,h0-e0));new_hinge=unit(np.cross(elbow-a,h-elbow))
    du=frame(elbow-a,new_hinge)@frame(e0-a0,old_hinge).T;dl=frame(h-elbow,new_hinge)@frame(h0-e0,old_hinge).T
    for i in arm:
        upper=names[i].startswith('upperarm');turn=du if upper else dl;old_origin=a0 if upper else e0;origin=a if upper else elbow
        out[i,:3,:3]=turn@w[i,:3,:3];out[i,:3,3]=origin+turn@(w[i,:3,3]-old_origin)
    # Keep the hand fixed, transport forearm roll to the actual V9 helper
    # stations (half/full), instead of leaving that rotation at the wrist.
    fore=unit(out[ha,:3,3]-out[la,:3,3]);distal=ix['lowerarm_twist_01_l']
    dh=rot(out[ha])@rot(B[ha]).T;dt=rot(out[distal])@rot(B[distal]).T
    q=R.from_matrix(dh@dt.T).as_quat();tau=2*np.arctan2(q[:3]@fore,q[3])
    q0=R.from_matrix((rot(w[ha])@rot(B[ha]).T)@(rot(w[distal])@rot(B[distal]).T).T).as_quat()
    tau0=2*np.arctan2(q0[:3]@unit(w[ha,:3,3]-w[la,:3,3]),q0[3])
    tau=(tau-tau0+np.pi)%(2*np.pi)-np.pi
    for name,share in [('lowerarm_twist_02_l',.5),('lowerarm_twist_01_l',1.)]:
        i=ix[name];turn=R.from_rotvec(fore*tau*share).as_matrix();origin=out[la,:3,3]
        out[i,:3,:3]=turn@out[i,:3,:3];out[i,:3,3]=origin+turn@(out[i,:3,3]-origin)
    return out
def shared_hold(w,target,weight,shift):
    """Use the SAME support anatomy in idle and action-held phases.

    Earlier box sequences have identical palm contacts but an older elbow frame.
    Applying one angular correction to each old frame keeps that mismatch.
    Interpolate toward the corrected support reference, then solve fixed lengths.
    """
    out=w.copy();h0=w[ha,:3,3];h=h0+shift*weight
    for i in hand:out[i,:3,3]+=shift*weight
    c=(1-weight)*w[cl,:3,3]+weight*target[cl,:3,3]
    shoulder_axis=(1-weight)*(w[ua,:3,3]-w[cl,:3,3])+weight*(target[ua,:3,3]-target[cl,:3,3])
    a=c+unit(shoulder_axis)*np.linalg.norm(w[ua,:3,3]-w[cl,:3,3])
    a0,e0=w[ua,:3,3],w[la,:3,3];u_len=np.linalg.norm(e0-a0);f_len=np.linalg.norm(h0-e0)
    axis=unit(h-a);dist=np.linalg.norm(h-a);along=(u_len*u_len-f_len*f_len+dist*dist)/(2*dist);center=a+axis*along
    desired=(1-weight)*e0+weight*target[la,:3,3];pole=unit(desired-center-axis*((desired-center)@axis))
    e=center+pole*np.sqrt(max(0,u_len*u_len-along*along))
    normal=unit(np.cross(e-a,h-e));old_normal=unit(np.cross(e0-a0,h0-e0))
    ta,te,th=[target[i,:3,3] for i in (ua,la,ha)];target_normal=unit(np.cross(te-ta,th-te))
    for i in [cl]+arm:
        if i==cl:
            qa,qb=rot(w[i]),rot(target[i]);out[i,:3,3]=c
        else:
            up=names[i].startswith('upperarm');direction=e-a if up else h-e
            old_dir=e0-a0 if up else h0-e0;target_dir=te-ta if up else th-te
            old_delta=frame(direction,normal)@frame(old_dir,old_normal).T
            target_delta=frame(direction,normal)@frame(target_dir,target_normal).T
            origin=a if up else e;old_origin=a0 if up else e0;target_origin=ta if up else te
            pa=origin+old_delta@(w[i,:3,3]-old_origin);pb=origin+target_delta@(target[i,:3,3]-target_origin)
            out[i,:3,3]=(1-weight)*pa+weight*pb;qa=old_delta@rot(w[i]);qb=target_delta@rot(target[i])
        turn=(R.from_matrix(qb)*R.from_matrix(qa).inv()).as_rotvec()
        out[i,:3,:3]=(R.from_rotvec(turn*weight).as_matrix()@qa)*np.linalg.norm(w[i,:3,:3],axis=0)
    return out
targets=dict(base=14.,vertical=24.,angled=32.,canted=36.,prism=30.)
d['profiles']['bipod']=json.loads((r/'extra_inputs.json').read_text())['bipod']
profiles=copy.deepcopy(d['profiles']);cache={};report={};fits={}
for family,profile in d['profiles'].items():
    support='base' if family=='bipod' else family
    c=d['clips'][idlepath];home=compose(layer(np.array(c['frames']),idlepath,d['profiles'][support],names,c['times']),parents)[0]
    a=home[ua,:3,3];e=home[la,:3,3]
    parameters=np.array(json.loads((r/'support_fit_final.json').read_text())[support]['parameters'])
    pose=elbow_pose(home,parameters)
    fits[family]=dict(parameters=parameters.tolist(),shoulder_rotation_degrees=np.degrees(parameters[:3]).tolist(),pole_degrees=float(np.degrees(parameters[3])),elbow_cm=float(np.linalg.norm(pose[la,:3,3]-e)),shoulder_cm=float(np.linalg.norm(pose[ua,:3,3]-a)),clearance_cm=box_clearance(pose),before=float(np.degrees(wrist(home))),after=float(np.degrees(wrist(pose))))
    print('SUPPORT_FIT',family,fits[family],flush=True)
    reference=np.linalg.inv(home[gun])@home[ha]
    for path,c in d['clips'].items():
        row=next((x for x in profiles[family]['clips'] if x['base']==path),None)
        if row is None:continue
        t=np.array(c['times']);base=np.array(c['frames']);old=compose(layer(base,path,profile,names,t),parents);new=old.copy()
        is_box=path.endswith(('A_M249_reload','A_M249_reload_empty'));is_side='/SideMagazine' in path
        free_turns=np.zeros((len(t),3))
        weights=[]
        for k,tm in enumerate(t):
            w=old[k];rel=np.linalg.inv(w[gun])@w[ha]
            distance=np.linalg.norm((rel[:3,3]-reference[:3,3])*np.linalg.norm(home[gun,:3,:3],axis=0))
            angle=np.degrees(R.from_matrix(rot(reference).T@rot(rel)).magnitude())
            weight=(1-ease((distance-.4)/2.0))*(1-ease((angle-4.)/16.))
            if is_side:weight*=max(1-ease(tm/.2),ease((tm-(c['duration']-.3))/.3))
            weights.append(weight)
        weights=np.array(weights)
        if len(t)>2 and not path.endswith('A_M249_idle'):
            filtered=gaussian_filter1d(weights,2.5,mode='nearest')
            first=ease(t/.12);last=ease((t-(t[-1]-.12))/.12)
            filtered=weights[0]*(1-first)+filtered*first
            weights=filtered*(1-last)+weights[-1]*last
        # Side-magazine manipulation already has fitted contacts. Only its held
        # start/end share this support correction, not its active manipulation.
        for k,tm in enumerate(t):
            w=old[k];rel=np.linalg.inv(w[gun])@w[ha]
            weight=weights[k]
            if weight>1e-8 and np.linalg.norm(parameters)>1e-8:
                support_weight=weight
                if path.endswith('A_M249_quick_melee'):
                    support_weight*=max(1-ease(tm/.08),ease((tm-(c['duration']-.18))/.18))
                target=w[gun]@np.linalg.inv(home[gun])@pose
                shift=rot(w[gun])@parameters[4:7]
                candidate=shared_hold(w,target,support_weight,shift)
                if path.endswith('A_M249_quick_melee') and np.linalg.norm(shift)>1e-8:
                    # Keep the moved grip seated during the original strike.
                    candidate=shared_hold(w,target,weight,shift)
                minimum=min(.12,box_clearance(w))
                if box_clearance(candidate)<minimum-.005:
                    lo,hi=0.,1.
                    for _ in range(12):
                        mid=(lo+hi)/2
                        if box_clearance(shared_hold(w,target,support_weight*mid,shift))>=minimum:lo=mid
                        else:hi=mid
                    candidate=shared_hold(w,target,support_weight*lo,shift)
                new[k]=candidate
            if is_box:
                empty=path.endswith('_empty');start,full,back,end=(.70,.86,1.18,1.56) if empty else (.72,.88,1.35,1.60)
                free=ease((tm-start)/(full-start))*(1-ease((tm-back)/(end-back)))
                swing=wrist(new[k]);excess=max(0,swing-np.radians(30.))*free
                if excess>1e-8:
                    desired=unit(new[k,ha,:3,3]-new[k,la,:3,3]);palm=rot(new[k,ha])@rot(B[ha]).T@f0
                    free_turns[k]=unit(np.cross(palm,desired))*excess
        if is_box:
            free_turns=gaussian_filter1d(free_turns,2.,axis=0,mode='nearest')
            free_turns*=((ease((t-start)/.06))*(1-ease((t-(end-.06))/.06)))[:,None]
            for k in range(len(t)):
                delta=R.from_rotvec(free_turns[k]).as_matrix();origin=new[k,ha,:3,3].copy()
                for i in hand:
                    new[k,i,:3,:3]=delta@new[k,i,:3,:3];new[k,i,:3,3]=origin+delta@(new[k,i,:3,3]-origin)
        cache[(family,path)]=new
        changed=np.max(abs(new-old))>1e-7
        if not changed:continue
        local=encode(new,parents);effective=encode(old,parents);patch={}
        # Preserve all existing unrelated tracks verbatim. Replace only the
        # local bones actually changed by this correction, relative to the
        # freshly captured compressed base (no old full-animation restoration).
        for i in owned:
            if np.max(abs(local[:,i]-effective[:,i]))<1e-7:continue
            corr=np.zeros((len(t),10));corr[:,:3]=local[:,i,:3]-effective[:,i,:3];corr[:,3:7]=(R.from_quat(local[:,i,3:7])*R.from_quat(effective[:,i,3:7]).inv()).as_quat()
            original=next((x for x in row['tracks'] if x['bone']==names[i]),None)
            ts=np.unique(np.r_[t,original['times'] if original else []])
            addition=sample(corr.ravel(),t,ts)
            if original:v=sample(original['values'],original['times'],ts)
            else:v=np.tile([0.,0.,0.,0.,0.,0.,1.,0.,0.,0.],(len(ts),1))
            v[:,:3]+=addition[:,:3];v[:,3:7]=(R.from_quat(addition[:,3:7])*R.from_quat(v[:,3:7])).as_quat()
            for k in range(1,len(v)):
                if v[k-1,3:7]@v[k,3:7]<0:v[k,3:7]*=-1
            patch[names[i]]=dict(bone=names[i],times=ts.tolist(),values=v.ravel().tolist())
        row['tracks']=[x for x in row['tracks'] if x['bone'] not in patch]+list(patch.values())
        before=metrics(old,B,names);after=metrics(new,B,names)
        report[family+'/'+path.split('.')[-1]]=dict(tracks=list(patch),wrist_before=float(before['wrist_swing'].max()),wrist_after=float(after['wrist_swing'].max()),elbow_movement_cm=float(np.linalg.norm(new[:,la,:3,3]-old[:,la,:3,3],axis=1).max()),hand_movement_cm=float(np.linalg.norm(new[:,ha,:3,3]-old[:,ha,:3,3],axis=1).max()))
    with gzip.open(r/(family+'.json.gz'),'wt') as f:json.dump(dict(family=family,clips=profiles[family]['clips']),f,separators=(',',':'))
pickle.dump(cache,open(r/'candidate.pkl','wb'));(r/'authoring.json').write_text(json.dumps(dict(fits=fits,clips=report),indent=2))
print(json.dumps(fits,indent=2));print('WRIST33_AUTHORED',len(report),'sparse clips')
