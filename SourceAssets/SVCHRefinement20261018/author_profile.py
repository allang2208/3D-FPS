"""Bake sparse contact corrections against the actual saved 120 Hz SVD clips."""
from contact_inputs import *
FIT=json.loads((O/'contact_fit.json').read_text())
FINGERS=json.loads((O/'finger_fit.json').read_text())['bones']
desc={}
for i,n in enumerate(N):
    desc[i]=[]
    for j in range(len(N)):
        k=j
        while k>=0:
            if k==i:desc[i].append(j);break
            k=PI[k]
def unit(v): return v/max(np.linalg.norm(v),1e-12)
def swing(a,b):
    a,b=unit(a),unit(b);c=np.cross(a,b);dot=np.clip(a@b,-1,1)
    if np.linalg.norm(c)<1e-9:return np.eye(3)
    return Rotation.from_rotvec(unit(c)*np.arctan2(np.linalg.norm(c),dot)).as_matrix()
def smooth(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def invapply(transform,point):return (np.linalg.inv(transform)@np.r_[point,1])[:3]
def correct_arm(p,hand,side):
    ui,fi,hi=[N.index(n+'_'+side) for n in ('upperarm','lowerarm','hand')]
    old=p.copy();a=old[ui,:3,3].copy();e=old[fi,:3,3].copy();h=old[hi,:3,3].copy();t=hand[:3,3]
    l1,l2=np.linalg.norm(e-a),np.linalg.norm(h-e)
    span=np.linalg.norm(t-a)
    # Preserve the native bone lengths. Only an unreachable target moves the
    # clavicle/arm root by the minimal excess, rather than stretching the mesh.
    if span>(l1+l2)*.995:
        offset=unit(t-a)*(span-(l1+l2)*.995)
        ci=N.index('clavicle_'+side)
        for j in desc[ci]:p[j,:3,3]+=offset
        old=p.copy();a=old[ui,:3,3];e=old[fi,:3,3];h=old[hi,:3,3]
    axis=unit(t-a);dist=np.linalg.norm(t-a)
    pole=unit(e-a-axis*((e-a)@axis))
    along=(l1*l1-l2*l2+dist*dist)/(2*max(dist,1e-9))
    enew=a+axis*along+pole*np.sqrt(max(l1*l1-along*along,0))
    up=old[ui].copy();up[:3,:3]=swing(e-a,enew-a)@up[:3,:3]
    fore=old[fi].copy();fore[:3,:3]=swing(h-e,t-enew)@fore[:3,:3];fore[:3,3]=enew
    for index,new in ((ui,up),(fi,fore),(hi,hand)):
        delta=new@np.linalg.inv(old[index])
        for j in desc[index]:p[j]=delta@old[j]
    return p
def rows(mats):
    pos=mats[:,:3,3];scale=np.linalg.norm(mats[:,:3,:3],axis=1)
    quat=Rotation.from_matrix(mats[:,:3,:3]/scale[:,None,:]).as_quat()
    return np.c_[pos,quat,scale]

idle_local={s:np.linalg.inv(IDLE[ROOT])@IDLE[N.index('hand_'+s)] for s in FIT}
profile={'family':'base','clips':[]}
summary={'runtime_tested':False,'source':'saved SVD clips sampled at 120 Hz','clips':{}}
for role,clip in D['clips'].items():
    deltas=[];weights=[];maxreach=0
    for frame in clip['frames']:
        local=matrices(frame);base=components(local);p=base.copy();strength={}
        for side,f in FIT.items():
            hi=N.index('hand_'+side)
            rel=np.linalg.inv(base[ROOT])@base[hi]
            # Fade the hold correction out as the authored hand departs its
            # contact; use the same source time, with no new runtime clock.
            dist=np.linalg.norm(rel[:3,3]-idle_local[side][:3,3])*100
            alpha=1-smooth((dist-1.0)/4.0)
            strength[side]=float(alpha)
            if alpha<1e-6:continue
            rot=Rotation.from_rotvec(np.array(f['rotation_vector'])*alpha).as_matrix()
            pivot=np.array(f['pivot_bind_cm']);shift=np.array(f['translation_cm'])*alpha
            c=np.eye(4);c[:3,:3]=rot;c[:3,3]=pivot+shift-rot@pivot
            root_space=VRI[ROOT]@c@VR[ROOT]
            hand=base[ROOT]@root_space@rel
            p=correct_arm(p,hand,side)
        newlocal=p.copy()
        for i,parent in enumerate(PI):
            if parent>=0:newlocal[i]=np.linalg.inv(p[parent])@p[i]
        for name,fit in FINGERS.items():
            i=N.index(name);alpha=strength[fit['side']]
            delta=Rotation.from_rotvec(np.asarray(fit['rotation_vector'])*alpha).as_matrix()
            newlocal[i,:3,:3]=delta@newlocal[i,:3,:3]
        before,after=rows(local),rows(newlocal)
        q=(Rotation.from_quat(after[:,3:7])*Rotation.from_quat(before[:,3:7]).inv()).as_quat()
        deltas.append(np.c_[after[:,:3]-before[:,:3],q,after[:,7:]-before[:,7:]])
        weights.append(strength)
    values=np.array(deltas);tracks=[]
    for i,n in enumerate(N):
        v=values[:,i].copy()
        for k in range(1,len(v)):
            if v[k,3:7]@v[k-1,3:7]<0:v[k,3:7]*=-1
        rotation=Rotation.from_quat(v[:,3:7]).magnitude()
        if max(np.max(abs(v[:,:3])),np.max(rotation),np.max(abs(v[:,7:])))<2e-6:continue
        if np.max(abs(v-v[0]))<2e-6:
            times=[0.];v=v[:1]
        else:times=[min(j/120,clip['duration']) for j in range(len(v))]
        tracks.append({'bone':n,'times':times,'values':np.round(v,9).ravel().tolist()})
    profile['clips'].append({'base':clip['path'],'duration':clip['duration'],'tracks':tracks})
    summary['clips'][role]={'tracks':[t['bone'] for t in tracks],'keys':sum(len(t['times']) for t in tracks),
                           'start_hold':weights[0],'end_hold':weights[-1]}
    print('SVCH_PROFILE',role,len(tracks),flush=True)
(O/'shared_profile.json').write_text(json.dumps(profile,separators=(',',':')))
(O/'profile_receipt.json').write_text(json.dumps(summary,indent=1))

# These are bone-local METRES. The UE component ref pose already includes the
# FBX x100 scale and Y reflection; never invert Blender's rest matrix here.
markers=json.loads((SRC/'Authoring/authoring.json').read_text())['markers_m']
const={name:invapply(VR[ROOT],np.asarray(markers[bone])*100).tolist() for name,bone in
       [('RearSight','WPN_RearSight'),('FrontSight','WPN_FrontSight'),('MuzzlePoint','WPN_SOCKET_Muzzle'),('EjectPort','WPN_SOCKET_Eject')]}
const['SightUp']=unit(np.linalg.inv(VR[ROOT][:3,:3])@np.array([0,0,1])).tolist()
(O/'calibration.json').write_text(json.dumps(const,indent=1))
print('SVCH_CALIBRATION',json.dumps(const),flush=True)
