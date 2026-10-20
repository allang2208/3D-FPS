"""SVCh: left magazine hand charges the left handle; right hand supports grip.

Only the SVCh reload_empty pose layer is authored. Native V9 skin, bind,
weights, shared sequences, magazine/bolt clocks and normal reload are inputs.
"""
from arm_math import *
import copy

ref = matrices(arms['reference'])
wref = matrices(weapon['reference'])
root, bolt = ids['WPN_root'], ids['WPN_bolt']
clip = motion['clips']['reload_empty']
old = [pose('reload_empty', i) for i in range(len(clip['times']))]
gun = [rigid(p[root] @ np.linalg.inv(wref[root])) for p in old]
guninv = [np.linalg.inv(g) for g in gun]
normal = [np.einsum('ab,nbc->nac', gi, p) for gi, p in zip(guninv, old)]
digits = ('thumb', 'index', 'middle', 'ring', 'pinky')
handbones = {s: [i for i,n in enumerate(names) if n.endswith('_'+s) and n.startswith(('hand',)+digits)] for s in ('l','r')}
armbones = {s: [i for i,n in enumerate(names) if n.endswith('_'+s) and n.startswith(('clavicle','upperarm','lowerarm','hand')+digits)] for s in ('l','r')}

def rr(m): return R.from_matrix(rigid(m)[:3,:3])

def mixrot(a,b,w):
    return Slerp([0,1],R.from_matrix(np.stack([a,b])))([float(w)]).as_matrix()[0]

def mix(a,b,w):
    out=a.copy();out[:3,3]=(1-w)*a[:3,3]+w*b[:3,3]
    out[:3,:3]=mixrot(rigid(a)[:3,:3],rigid(b)[:3,:3],w)*np.linalg.norm(a[:3,:3],axis=0)
    return out

def frame(a,n):
    x=unit(a);z=unit(n-x*np.dot(n,x));return np.column_stack((x,np.cross(z,x),z))

def twist(rotation,axis):
    q=R.from_matrix(rotation).as_quat()
    if q[3]<0:q=-q
    return float(2*np.arctan2(q[:3]@unit(axis),q[3]))

def arm(p, side, target, shoulder, pole, blend=1.):
    """Fixed native segment lengths, anatomical elbow hinge, distal pronation."""
    q=p.copy();u,l,h,c=[ids[n+'_'+side] for n in ('upperarm','lowerarm','hand','clavicle')]
    target=target.copy();target[:3,:3]=rigid(target)[:3,:3]*np.linalg.norm(p[h,:3,:3],axis=0)
    A,E,H=[p[j,:3,3] for j in (u,l,h)];L1=np.linalg.norm(E-A);L2=np.linalg.norm(H-E)
    T=target[:3,3];axis=unit(T-shoulder);d=np.linalg.norm(T-shoulder)
    shoulder_adjust=0.
    # A rigid shoulder follow during the gun's recovery maintains a bent arm.
    # It translates clavicle + upper-arm root together, never scales a segment.
    if d>(L1+L2)*.94:
        shoulder_adjust=d-(L1+L2)*.94
        if shoulder_adjust>6.:raise ValueError(('Excessive shoulder follow',side,shoulder_adjust))
        shoulder=shoulder+axis*shoulder_adjust;d=np.linalg.norm(T-shoulder)
    if d<=abs(L1-L2)+.1:raise ValueError(('Unreachable',side,d,L1+L2))
    pole=unit(pole-axis*np.dot(pole,axis));along=(L1*L1-L2*L2+d*d)/(2*d)
    elbow=shoulder+axis*along+pole*np.sqrt(max(0,L1*L1-along*along))
    ru=ref[l,:3,3]-ref[u,:3,3];rl=ref[h,:3,3]-ref[l,:3,3];rn=np.cross(ru,rl)
    nu=elbow-shoulder;nl=T-elbow;nn=np.cross(nu,nl)
    Du=frame(nu,nn)@frame(ru,rn).T;Dl=frame(nl,nn)@frame(rl,rn).T
    # At the edges blend axial orientation from the accepted moving arm. Both
    # rotations aim the same segment; this cannot elongate a bone.
    Au=swing(E-A,nu);Al=swing(H-E,nl)
    Ru=mixrot(Au@rigid(p[u])[:3,:3],Du@rigid(ref[u])[:3,:3],blend)
    Rl=mixrot(Al@rigid(p[l])[:3,:3],Dl@rigid(ref[l])[:3,:3],blend)
    Qu=Ru@rigid(p[u])[:3,:3].T;Ql=Rl@rigid(p[l])[:3,:3].T
    q[c,:3,3]+=shoulder-A
    for j,n in enumerate(names):
        if n.endswith('_'+side) and n.startswith('upperarm'):
            q[j,:3,3]=shoulder+Qu@(p[j,:3,3]-A)
            q[j,:3,:3]=mixrot(Au@rigid(p[j])[:3,:3],Du@rigid(ref[j])[:3,:3],blend)*np.linalg.norm(p[j,:3,:3],axis=0)
        elif n.endswith('_'+side) and n.startswith('lowerarm'):
            q[j,:3,3]=elbow+Ql@(p[j,:3,3]-E);q[j,:3,:3]=Ql@p[j,:3,:3]
    q[h]=target
    # Native V9: no roll at the elbow; half at twist_02, full at twist_01.
    # Hand orientation is relative to the native forearm frame, not a borrowed
    # opposite-side wrist rotation. Keep flex/deviation at the wrist.
    Dh=rigid(target)[:3,:3]@rigid(ref[h])[:3,:3].T
    currentD=Rl@rigid(ref[l])[:3,:3].T
    tau=twist(currentD.T@Dh,rl)
    for prefix,share in [('lowerarm_twist_02',.5),('lowerarm_twist_01',1.)]:
        j=ids[prefix+'_'+side]
        wanted=R.from_rotvec(unit(nl)*tau*share).as_matrix()@currentD@rigid(ref[j])[:3,:3]
        q[j,:3,:3]=mixrot(rigid(q[j])[:3,:3],wanted,blend)*np.linalg.norm(p[j,:3,:3],axis=0)
    wristR=R.from_rotvec(unit(nl)*tau).as_matrix()@currentD
    flex=np.rad2deg(R.from_matrix(wristR.T@Dh).magnitude())
    return q,{'pronation_deg':float(np.rad2deg(tau)),'wrist_swing_deg':float(flex),'reach':float(d/(L1+L2)),'shoulder_follow_cm':float(shoulder_adjust)}

# Reuse the accepted charging fingers only. Mirror their anatomical deformation
# into the native LEFT hand; do not mirror the shoulder/elbow chain or geometry.
donor=normal[310];mirror=np.diag([-1.,1.,1.,1.]);reflect=mirror.copy()
# Existing calibrated centre of the cylindrical handle, in neutral gun cm.
pivot=np.array([2.8268214315,-33.0027878284,-2.7095764875])
reflect[0,3]=2*pivot[0]
hook={}
for l in handbones['l']:
    r=ids[names[l][:-1]+'r']
    hook[l]=reflect@donor[r]@np.linalg.inv(ref[r])@mirror@ref[l]
lh,rh=ids['hand_l'],ids['hand_r']
hooklocals={j:relative(hook[parents[j]],hook[j]) for j in handbones['l'] if j!=lh}
rightlocals={j:relative(normal[220][parents[j]],normal[220][j]) for j in handbones['r'] if j!=rh}
anchor=248;finish=416
left_start=normal[anchor][lh];left_end=normal[finish][lh]
right_grip=normal[220][rh]

def anchor_shoulder(i,side):
    u=ids['upperarm_'+side]
    if side=='l':
        w=float(ease(anchor,finish,i));return (1-w)*old[anchor][u,:3,3]+w*old[finish][u,:3,3]
    # Keep the accepted body's shoulder path; the arm now solves to the pistol
    # grip instead of following the obsolete reaching right hand.
    return old[i][u,:3,3]

def pole_at(i,side,shoulder,target,angle=0.):
    u,l,h=[ids[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
    p=old[i];axis=unit(target[:3,3]-shoulder)
    if side=='l':
        # Stable outward/downward bend, transported from the end of seating.
        w=float(ease(anchor,finish,i));e=(1-w)*old[anchor][l,:3,3]+w*old[finish][l,:3,3]
    else:
        # The pre-charge elbow is below and outside the grip, not above sights.
        e=old[220][l,:3,3].copy();e[0]=max(e[0],shoulder[0]+9.);e[2]=min(e[2],shoulder[2]-18.)
    pole=unit(e-shoulder-axis*((e-shoulder)@axis))
    # Project the native forearm direction implied by the fixed palm onto the
    # elbow circle. This changes elbow azimuth instead of folding the wrist.
    Dh=rigid(target)[:3,:3]@rigid(ref[h])[:3,:3].T
    L2=np.linalg.norm(p[h,:3,3]-p[l,:3,3])
    desired=target[:3,3]-unit(Dh@(ref[h,:3,3]-ref[l,:3,3]))*L2
    natural=unit(desired-shoulder-axis*((desired-shoulder)@axis))
    natural=R.from_rotvec(axis*np.deg2rad(angle)).apply(natural)
    if side=='l':
        source=unit(p[l,:3,3]-shoulder-axis*((p[l,:3,3]-shoulder)@axis))
        w=float(ease(anchor,280,i)*(1-ease(390,finish,i)))
        natural=R.from_rotvec(R.from_matrix(swing(source,natural)).as_rotvec()*w).apply(source)
    return natural

def roll_hook(deg):
    x=np.eye(4);x[:3,:3]=R.from_rotvec(np.array([1.,0,0])*np.deg2rad(deg)).as_matrix();x[:3,3]=pivot-x[:3,:3]@pivot
    return x@hook[lh]

# The cylinder allows a rigid grip roll. Choose it jointly with a fixed elbow
# pole offset, so a left hand can pull without forcing the wrist or humerus.
choices=[]
for roll in range(-90,91,5):
    for pole_angle in range(-20,21,5):
        cost=0.;stats=[]
        for i in (304,325,344):
            h=roll_hook(roll);h[:3,3]+=normal[i][bolt,:3,3]-donor[bolt,:3,3]
            target=gun[i]@h;S=anchor_shoulder(i,'l')
            q,s=arm(old[i],'l',target,S,pole_at(i,'l',S,target,pole_angle));stats.append(s)
            cost+=s['wrist_swing_deg']**2+max(0,abs(s['pronation_deg'])-85.)**2*2+max(0,s['reach']-.90)**2*10000
        cost+=roll**2*.01+pole_angle**2*.1
        choices.append((cost,roll,pole_angle,stats))
_,grip_roll,pole_angle,fit=min(choices,key=lambda x:x[0]);grip=roll_hook(grip_roll)

def point_curve(i,keys):
    for (a,pa),(b,pb) in zip(keys,keys[1:]):
        if i<=b:
            w=float(ease(a,b,i));return (1-w)*pa+w*pb
    return keys[-1][1]

def left_target(i):
    if i<=304:
        h=mix(left_start,grip,float(ease(260,304,i)))
        h[:3,3]=point_curve(i,[(248,left_start[:3,3]),(270,np.array([-6.5,-34.5,-10.])),(292,grip[:3,3]+[-3.,0.,-.6]),(304,grip[:3,3])])
    elif i<=344:
        h=grip.copy();h[:3,3]+=normal[i][bolt,:3,3]-donor[bolt,:3,3]
    else:
        pulled=grip[:3,3]+normal[344][bolt,:3,3]-donor[bolt,:3,3]
        h=mix(grip,left_end,float(ease(356,416,i)))
        # Let the bolt spring forward on its existing curve while the hand
        # withdraws to the left; never carry the palm through the receiver.
        h[:3,3]=point_curve(i,[(344,pulled),(360,pulled+[-5.,0.,-2.]),(382,np.array([-6.5,-40.,-10.])),(416,left_end[:3,3])])
    return gun[i]@h

out=copy.deepcopy(profile);entry=next(c for c in out['clips'] if c['base']==clip['path'])
changed=sorted(set(armbones['l']+armbones['r']))
values={j:[] for j in changed};recipe=[]
for i,t in enumerate(clip['times']):
    p=old[i];q=p.copy();stats={}
    if anchor<i<finish:
        target=left_target(i);w=float(ease(anchor,280,i)*(1-ease(390,finish,i)))
        S=anchor_shoulder(i,'l');q,stats['left']=arm(q,'l',target,S,pole_at(i,'l',S,target,pole_angle*float(ease(anchor,292,i)*(1-ease(360,finish,i)))) ,w)
        fingerw=float(ease(278,304,i)*(1-ease(344,376,i)))
        for j in handbones['l']:
            if j==lh:continue
            src=relative(p[parents[j]],p[j]);dst=hooklocals[j]
            local=mix(src,dst,fingerw)
            # Never borrow the other hand's lengths or translations.
            local[:3,3]=src[:3,3]
            ps=np.linalg.norm(q[parents[j],:3,:3],axis=0);ls=np.linalg.norm(local[:3,:3],axis=0)
            q[j,:3,3]=q[parents[j],:3,:3]@local[:3,3]+q[parents[j],:3,3]
            q[j,:3,:3]=(rigid(q[parents[j]])[:3,:3]@rigid(local)[:3,:3])*(ps*ls)
    if i>=220:
        target=gun[i]@right_grip
        w=float(ease(220,268,i)*(1-ease(470,515,i)))
        S=anchor_shoulder(i,'r');pole=pole_at(i,'r',S,target)
        # Fade the elbow pole to/from the accepted endpoint while the hand
        # remains on the same pistol-grip anchor throughout.
        axis=unit(target[:3,3]-S);po=unit(p[ids['lowerarm_r'],:3,3]-S-axis*((p[ids['lowerarm_r'],:3,3]-S)@axis))
        pole=R.from_rotvec(R.from_matrix(swing(po,pole)).as_rotvec()*w).apply(po)
        q,stats['right']=arm(q,'r',target,S,pole,w)
        for j in handbones['r']:
            if j==rh:continue
            src=relative(p[parents[j]],p[j]);local=rightlocals[j].copy();local[:3,3]=src[:3,3]
            ps=np.linalg.norm(q[parents[j],:3,:3],axis=0);ls=np.linalg.norm(src[:3,:3],axis=0)
            q[j,:3,3]=q[parents[j],:3,:3]@local[:3,3]+q[parents[j],:3,3]
            q[j,:3,:3]=(rigid(q[parents[j]])[:3,:3]@rigid(local)[:3,:3])*(ps*ls)
    raw=np.asarray(clip['frames'][i]);layer=next(c for c in profile['clips'] if c['base']==clip['path'])
    for j in changed:
        # Retain exact previous deltas outside the new operation windows.
        active=(names[j].endswith('_l') and anchor<i<finish) or (names[j].endswith('_r') and i>=220)
        if not active:
            track=next((tr for tr in layer['tracks'] if tr['bone']==names[j]),None)
            v=sample(t,track) if track else np.array([0,0,0,0,0,0,1,0,0,0],float)
        else:
            loc=relative(q[parents[j]],q[j]);scale=np.linalg.norm(loc[:3,:3],axis=0)
            v=np.r_[loc[:3,3]-raw[j,:3],(R.from_matrix(loc[:3,:3]/scale)*R.from_quat(raw[j,3:7]).inv()).as_quat(),scale-raw[j,7:10]]
        if values[j] and np.dot(values[j][-1][3:7],v[3:7])<0:v[3:7]*=-1
        values[j].append(v)
    if i in [220,248,270,292,304,310,325,344,350,360,382,416,470,515]:recipe.append({'frame':i,'arms':stats})
entry['tracks']=[t for t in entry['tracks'] if ids[t['bone']] not in changed]+[{'bone':names[j],'times':clip['times'],'values':np.round(values[j],10).ravel().tolist()} for j in changed]
(O/'profile_left_bolt.json').write_text(json.dumps(out,separators=(',',':')))
(O/'authoring_recipe.json').write_text(json.dumps({'operation':'Left hand seats magazine, charges left handle, releases and returns to fore-end. Right hand retains pistol grip.','clip':clip['path'],'fps':120,'left_change_frames':[248,416],'right_grip_frames':[220,515],'handle_contact_frames':[304,344],'release_frames':[344,360],'handle_pivot_gun_cm':pivot.tolist(),'rigid_grip_roll_deg':grip_roll,'left_pole_offset_deg':pole_angle,'contact_solver':fit,'key_pose_parameters':recipe,'preserved':['normal reload','source animations','V9 geometry weights bind and materials','WPN tracks','mechanical and audio timing'],'runtime_tested':False,'preview_rendered':False},indent=2))
print('SVCH_LEFT_BOLT_AUTHORED',grip_roll,pole_angle,json.dumps(fit),flush=True)
