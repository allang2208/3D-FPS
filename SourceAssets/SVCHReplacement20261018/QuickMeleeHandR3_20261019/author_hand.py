"""Repair the SVCH quick-melee hand as a gun/hand/arm contact group.

Use the current idle pistol grip and V9 fingers. Correct excessive wrist swing
by turning the gun and both hands together about the stock contact, rather
than folding the fixed hand onto its forearm. The shared SVD sequence is read
only; reloads, mesh data and contact timing are not authored here.
"""
from pathlib import Path
import sys,json,copy,hashlib
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'QuickMeleeSVDReferenceR2_20261019'))
from surface import *
from scipy.ndimage import gaussian_filter1d
O=HERE;PRIOR=O.parent/'QuickMeleeSVDReferenceR2_20261019'
manifest=json.loads((PRIOR/'install_receipt.json').read_text())['assets']
installed=json.loads((O/'install_receipt.json').read_text()).get('assets',{}) if (O/'install_receipt.json').exists() else {}
for f,spec in manifest.items():
    path=O.parents[2]/'Content'/(spec['path'].removeprefix('/Game/')+'.uasset')
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual not in (spec['sha256'],installed.get(f,{}).get('sha256')):raise RuntimeError('Changed input '+f)
(O/'Inputs').mkdir(exist_ok=True)
(O/'Inputs/manifest.json').write_text(json.dumps(manifest,indent=2))
clip=motion['clips']['quick_melee'];times=np.array(clip['times']);root=ids['WPN_root']
digits=('thumb','index','middle','ring','pinky')
right=[j for j,n in enumerate(names) if n.endswith('_r') and n.startswith(('clavicle','upperarm','lowerarm','hand')+digits)]
left=[j for j,n in enumerate(names) if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand')+digits)]
wpn=[j for j,n in enumerate(names) if n.startswith('WPN_')]
handbones={s:[j for j,n in enumerate(names) if n.endswith('_'+s) and n.startswith(('hand',)+digits)] for s in ('l','r')}
stock=np.array([-.006067879,-.216416583,.028199226,1.])
ref=matrices(arms['reference'])
def mix(a,b,w):
    w=float(np.clip(w,0.,1.))
    m=a.copy();m[:3,3]=a[:3,3]*(1-w)+b[:3,3]*w
    m[:3,:3]=Slerp([0,1],R.from_matrix([rigid(a)[:3,:3],rigid(b)[:3,:3]]))([float(w)]).as_matrix()[0]*np.linalg.norm(a[:3,:3],axis=0);return m
def wrist_split(L,H,side):
    li,hi=ids['lowerarm_'+side],ids['hand_'+side]
    axis=rigid(ref[li])[:3,:3].T@unit(ref[hi,:3,3]-ref[li,:3,3])
    rel=rigid(ref[li])[:3,:3].T@rigid(ref[hi])[:3,:3]
    Q=R.from_matrix(L.T@H@rel.T);q=Q.as_quat()
    if q[3]<0:q=-q
    tau=2*np.arctan2(q[:3]@axis,q[3]);T=R.from_rotvec(axis*tau)
    return (Q*T.inv()),T,rel,axis,tau
def native_right_chain(p):
    """Align each anatomical bone axis before placing helpers at native stations.

    R2 compensated a mismatched bone rotation by changing the child's local
    translation. Length-only checks missed that rotated translation vector.
    Keep the world joints, align the native axes, and move the clavicle root
    so every child offset remains the approved native skeleton offset.
    """
    q=p.copy();u,l,h,c=[ids[n+'_r'] for n in ('upperarm','lowerarm','hand','clavicle')]
    for main,child in [(u,l),(l,h)]:
        native_axis=rigid(ref[main])[:3,:3].T@unit(ref[child,:3,3]-ref[main,:3,3])
        current_axis=rigid(q[main])[:3,:3]@native_axis
        q[main,:3,:3]=swing(current_axis,q[child,:3,3]-q[main,:3,3])@q[main,:3,:3]
    local=relative(ref[c],ref[u]);q[c,:3,3]=q[u,:3,3]-q[c,:3,:3]@local[:3,3]
    for prefix,par in [('upperarm',u),('lowerarm',l)]:
        for suffix in ('01','02'):
            j=ids[prefix+'_twist_'+suffix+'_r'];native=relative(ref[par],ref[j]);expected=q[par]@native
            q[j,:3,3]=expected[:3,3]
            if prefix=='upperarm':q[j,:3,:3]=expected[:3,:3]
    return q
def left_support(old,target):
    # Carry the approved support arm with the gun as one rigid group. An elbow
    # reach solve changed the wrist's relative angle during recovery.
    group=target@np.linalg.inv(old[ids['hand_l']]);out=old.copy()
    for j in left:out[j]=group@old[j]
    return out

destination=O/'Profiles';destination.mkdir(exist_ok=True)
report={'source':'SVCH saved R2 + its idle pistol grip; SVD source clock',
    'contact_seconds':1/6,'duration':clip['duration'],'V9_written':False,'source_sequence_written':False,'families':{}}
allposes={}
for family,spec in manifest.items():
    source=json.loads((PRIOR/'SavedReadback'/(family+'.json')).read_text())
    (O/'Inputs'/(family+'.json')).write_text(json.dumps(source,separators=(',',':')))
    old=np.array([pose('quick_melee',i,source) for i in range(len(times))]);idle=pose('idle',0,source)
    rh,rl=ids['hand_r'],ids['lowerarm_r'];grip=relative(idle[root],idle[rh]);new=[];deltas_=[]
    localidle={j:relative(idle[parents[j]],idle[j]) for j in handbones['r'] if j!=rh}
    for i,p in enumerate(old):
        p=native_right_chain(p)
        w=float(np.clip(ease(0,.055,times[i])*(1-ease(.77,.9,times[i])),0.,1.))
        target=mix(p[rh],p[root]@grip,w)
        sw,tw,rel,axis,tau=wrist_split(rigid(p[rl])[:3,:3],rigid(target)[:3,:3],'r')
        angle=sw.magnitude();limit=np.deg2rad(16.)
        amount=max(0,angle-limit)*w
        wanted=R.from_rotvec(sw.as_rotvec()*(1-amount/max(angle,1e-9)))*tw
        desired=rigid(p[rl])[:3,:3]@wanted.as_matrix()@rel
        turn=desired@rigid(target)[:3,:3].T
        # A rigid gun turn around the existing stock contact preserves the
        # gameplay strike path and time while taking side-bend off the wrist.
        center=(p[root]@stock)[:3];G=np.eye(4);G[:3,:3]=turn;G[:3,3]=center-turn@center
        q=p.copy();newhand=G@target;shift=newhand[:3,3]-p[rh,:3,3]
        for j in right:q[j,:3,3]+=shift
        q[rh]=newhand
        for j in handbones['r']:
            if j!=rh:q[j]=q[parents[j]]@mix(relative(p[parents[j]],p[j]),localidle[j],w)
        # Keep the approved weapon and left support trajectory. Carry the
        # corrected right support chain back into that unchanged weapon frame;
        # correcting a wrist must not swing the stock into the player's eye.
        inverse_group=np.linalg.inv(G)
        for j in right:q[j]=inverse_group@q[j]
        for j in wpn:q[j]=p[j]
        for j in left:q[j]=p[j]
        if i in (0,len(times)-1):q=p.copy()
        new.append(q);deltas_.append(float(np.degrees(R.from_matrix(turn).magnitude())))
    new=np.array(new)
    # R2 interpolated helper COMPONENT positions independently during return.
    # The main bone lengths stayed correct, but the helpers left their native
    # stations by up to 7.7 cm and dragged the V9 palm with their skin weights.
    # Restore the native parent-local offsets on EVERY frame, not only the
    # upperarm/lowerarm/hand endpoints. The approved mesh/weights do not change.
    helper_errors=[]
    for i,p in enumerate(new):
        for prefix in ('upperarm','lowerarm'):
            par=ids[prefix+'_r']
            for suffix in ('01','02'):
                j=ids[prefix+'_twist_'+suffix+'_r'];local=relative(ref[par],ref[j])
                expected=p[par]@local
                helper_errors.append(float(np.linalg.norm(p[j,:3,3]-expected[:3,3])))
                p[j,:3,3]=expected[:3,3]
                if prefix=='upperarm':p[j,:3,:3]=expected[:3,:3]
    # Twist helpers use a common continuous branch. No independent half-turn
    # selection is allowed on twist_02 during the recovery blend.
    for side in ('r',):
        li,hi=ids['lowerarm_'+side],ids['hand_'+side]
        rolls=np.unwrap([wrist_split(rigid(p[li])[:3,:3],rigid(p[hi])[:3,:3],side)[4] for p in new])
        for i,p in enumerate(new):
            if i in (0,len(new)-1):continue
            L=rigid(p[li])[:3,:3];axis=rigid(ref[li])[:3,:3].T@unit(ref[hi,:3,3]-ref[li,:3,3])
            w=float(np.clip(ease(0,.055,times[i])*(1-ease(.77,.9,times[i])),0.,1.))
            for prefix,share in [('lowerarm_twist_01',1.),('lowerarm_twist_02',.5)]:
                j=ids[prefix+'_'+side];rel=rigid(ref[li])[:3,:3].T@rigid(ref[j])[:3,:3]
                target=L@R.from_rotvec(axis*rolls[i]*share).as_matrix()@rel
                p[j,:3,:3]=Slerp([0,1],R.from_matrix([rigid(p[j])[:3,:3],target]))([w]).as_matrix()[0]*np.linalg.norm(p[j,:3,:3],axis=0)
    out=copy.deepcopy(source);entry=next(c for c in out['clips'] if c['base']==clip['path']);tracks=[]
    # Encode the complete local pose; preserve each non-target clip verbatim.
    for j,n in enumerate(names):
        values=[]
        for i,p in enumerate(new):
            loc=relative(p[parents[j]],p[j]) if parents[j]>=0 else p[j];raw=np.array(clip['frames'][i][j]);v=np.zeros(10)
            v[:3]=loc[:3,3]-raw[:3];v[3:7]=(R.from_matrix(rigid(loc)[:3,:3])*R.from_quat(raw[3:7]).inv()).as_quat();v[7:]=np.linalg.norm(loc[:3,:3],axis=0)-raw[7:]
            if values and values[-1][3:7]@v[3:7]<0:v[3:7]*=-1
            values.append(v)
        ar=np.array(values);zero=np.array([0,0,0,0,0,0,1,0,0,0])
        if np.max(abs(ar-zero))>1e-7:tracks.append({'bone':n,'times':times.tolist(),'values':np.round(ar,10).ravel().tolist()})
    entry['tracks']=tracks
    (destination/(family+'.json')).write_text(json.dumps(out,separators=(',',':')))
    sig=np.array([driver.signature(matrix_pose(p),'r') for p in new])
    report['families'][family]={'max_gun_rotation_change_deg':0.,'max_support_chain_rotation_change_deg':max(deltas_),'right_wrist_flex_dev_peak_deg':np.max(abs(sig[:,1:3]),axis=0).tolist(),
        'contact_shift_cm':max(float(np.linalg.norm((a[root]@stock-b[root]@stock)[:3])) for a,b in zip(old,new)),
        'maximum_corrected_helper_offset_cm':max(helper_errors)}
    allposes[family]=new
    if family=='base':allposes['before']=old
np.savez_compressed(O/'poses.npz',**allposes)
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
