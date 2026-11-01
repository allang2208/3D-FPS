"""M24: bounded anatomical arm solve and a local, three-finger bipod hook.

Authoring only: no preview renders, gameplay or acceptance tests.
"""
from pathlib import Path
exec(compile((Path(__file__).parent.parent/'M24QuickMeleeContact20261028/library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
import gzip
import numpy as np

geo=json.loads((O/'geometry.json').read_text())
idle,locals0=pose('idle',0)
native_frame=rest['WPN_root']@idle['WPN_root'].inverted();back=native_frame.inverted()
native={n:native_frame@m for n,m in idle.items()}
pivot=K.to_3x3()@Vector(geo['parts']['LegA']['pivot_cm'])/100
tip=K.to_3x3()@Vector(geo['tips_cm'][0])/100
closed=tip.normalized().rotation_difference(Vector((-.005,tip.length,0)).normalized())
DURATION=.48;CONTACT=.12;PULL_END=.30;RETURN=.44;RATE=200

def blend(a,b,w):
    p,q,sc=a.decompose();pp,qq,ss=b.decompose()
    return Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w))

def frame(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed()

def angle(a,b):return math.acos(max(-1.,min(1.,a.normalized().dot(b.normalized()))))
def leg(t):return closed.slerp(Quaternion(),ease((t-CONTACT)/(PULL_END-CONTACT)))
def ramp(a,b,t):return ease((t-a)/(b-a))

hand0=native['hand_l'];hlocal=hand0.inverted()
long=(hlocal@native['middle_01_l'].translation).normalized()
across=hlocal.to_3x3()@(native['index_01_l'].translation-native['pinky_01_l'].translation)
across=(across-long*long.dot(across)).normalized();palm_normal=long.cross(across).normalized()
world_long=hand0.to_quaternion()@long
def palm_frame(x,y):
    x=x.normalized();y=(y-x*x.dot(y)).normalized()
    return Matrix((x,y,x.cross(y))).transposed()
native_palm=palm_frame(world_long,hand0.to_quaternion()@across)
def grip_orientation(t):
    return (palm_frame(world_long,leg(t)@tip.normalized())@native_palm.transposed()).to_quaternion()@hand0.to_quaternion()
q_contact=grip_orientation(CONTACT)
rod_axis=q_contact.inverted()@(closed@tip.normalized())
digits=[f'{d}_{j:02d}_l' for d in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
natural={'index':[48,64,30],'middle':[53,67,33],'ring':[57,65,32],'pinky':[52,58,28]}
grip={};opened={};angles={}
for n in digits:
    d,j,_=n.split('_');j=int(j);e=(local_rest[n].inverted()@locals0[n]).to_euler()
    if d!='thumb':
        # Keep the native abduction plane, removing the wide stock's MCP splay.
        e.x*=.35;e.y*=.45 if j==1 else 1.
        e.z=math.radians(natural[d][j-1]);angles[n]=e.copy()
        grip[n]=local_rest[n].to_quaternion()@e.to_quaternion()
        e.z=math.radians((18,25,12)[j-1]);opened[n]=local_rest[n].to_quaternion()@e.to_quaternion()
    else:
        # Thumb stays on the near side. No endpoint solver is allowed to invert
        # its MCP or pull it across the palm to meet the other fingertips.
        e.z=math.radians((60,5,15)[j-1]);angles[n]=e.copy()
        grip[n]=local_rest[n].to_quaternion()@e.to_quaternion()
        e.z=math.radians((20,-18,-8)[j-1]);opened[n]=local_rest[n].to_quaternion()@e.to_quaternion()

def finger_matrices(quats):
    row={'hand_l':Matrix.Identity(4)}
    for n in names:
        if n=='hand_l' or not under(n,'hand_l'):continue
        p,q,sc=locals0[n].decompose()
        row[n]=row[parents[n]]@Matrix.LocRotScale(p,quats.get(n,q),sc)
    return row

def finger_points(d,row):
    pts=[row[f'{d}_{j:02d}_l'].translation for j in (1,2,3)]
    distal=f'{d}_03_l'
    v=(rest[distal].translation-rest[f'{d}_02_l'].translation)*.75
    pts.append(row[distal]@(rest[distal].to_quaternion().inverted()@v))
    return pts

# Fit a slim support to the inside of the natural hook, with a strong pose prior.
# The local cylinder is then transported rigidly with the mechanical leg.
fm=finger_matrices(grip)
centers=[]
for d in ('index','middle'):
    pts=finger_points(d,fm)
    centers.append((pts[1]+pts[2]+pts[3])/3)
rod_center=q_contact.inverted()@Vector((.037,.077,.025))
def radial(p,c):
    d=p-c;return (d-rod_axis*d.dot(rod_axis)).length

def fit_cost(center,quats):
    row=finger_matrices(quats);score=0.
    for d in ('index','middle','ring','pinky','thumb'):
        pts=finger_points(d,row)
        for k in range(3):
            for f in (.25,.5,.75):
                score+=max(0.,.012-radial(pts[k].lerp(pts[k+1],f),center))**2*14000
        # The little finger follows the hook; it need not crush onto the leg.
        score+=(radial(pts[-1],center)-(.016 if d=='pinky' else .014))**2*({'index':1800,'middle':1800,'thumb':900,'ring':300,'pinky':150}[d])
    return score

seed_center=rod_center.copy();seed_quats=dict(grip)
for step in (.004,.002,.001):
    for _ in range(5):
        for axis in (long,palm_normal):
            choices=[rod_center+axis*(step*i) for i in (-1,0,1)]
            rod_center=min(choices,key=lambda c:fit_cost(c,grip)+(c-seed_center).length_squared*5000)
        for d in ('index','middle','ring','pinky'):
            for j in (1,2,3):
                n=f'{d}_{j:02d}_l';e=angles[n]
                candidates=[]
                for delta in (-math.radians(step*1000),0,math.radians(step*1000)):
                    ee=e.copy();ee.z=max(math.radians(natural[d][j-1]-9),min(math.radians(natural[d][j-1]+9),e.z+delta))
                    qs=dict(grip);qs[n]=local_rest[n].to_quaternion()@ee.to_quaternion()
                    prior=sum(angle(q@Vector((1,0,0)),seed_quats[k]@Vector((1,0,0)))**2*.2 for k,q in qs.items())
                    candidates.append((fit_cost(rod_center,qs)+prior,ee,qs))
                _,angles[n],grip=min(candidates,key=lambda v:v[0])

u,l,h='upperarm_l','lowerarm_l','hand_l'
iu=native[l].translation-native[u].translation;il=native[h].translation-native[l].translation
ru=rest[l].translation-rest[u].translation;rl=rest[h].translation-rest[l].translation
A=iu.length;B=il.length;rest_normal=ru.cross(rl).normalized()
base_normal=iu.cross(il).normalized()
forearm_axis=rest[l].to_quaternion().inverted()@rl.normalized()
rest_hand_rel=rest[l].to_quaternion().inverted()@rest[h].to_quaternion()
hand_long=rest[h].to_quaternion().inverted()@(rest['middle_01_l'].translation-rest[h].translation).normalized()
baseline_rel=(native[l].to_quaternion().inverted()@native[h].to_quaternion())@rest_hand_rel.inverted()
if baseline_rel.w<0:baseline_rel=-baseline_rel
baseline_roll=2*math.atan2(Vector((baseline_rel.x,baseline_rel.y,baseline_rel.z)).dot(forearm_axis),baseline_rel.w)

def arm(hm,activity,pole_angle,base=native):
    # Modest shoulder protraction replaces the old 10 cm shove.
    shift=Vector((.012,.078,.001))*activity
    S=base[u].translation+shift;H=hm.translation;v=H-S;d=v.length
    axis=v.normalized();safe=min(d,A+B-.0001)
    along=(A*A-B*B+safe*safe)/(2*safe);center=S+axis*along
    radius=math.sqrt(max(0,A*A-along*along))
    ref=(base[l].translation-center);ref=(ref-axis*ref.dot(axis)).normalized()
    E=center+(Quaternion(axis,pole_angle)@ref)*radius
    U=E-S;L=H-E;N=U.cross(L).normalized()
    # Transport the actual native reference hinge, not the old posed elbow roll.
    uq=(frame(U,N)@frame(ru,rest_normal).transposed()).to_quaternion()@rest[u].to_quaternion()
    lq=(frame(L,N)@frame(rl,rest_normal).transposed()).to_quaternion()@rest[l].to_quaternion()
    # Exact current support pose remains the entry/exit contract.
    uq0=(frame(U,N)@frame(iu,base_normal).transposed()).to_quaternion()@base[u].to_quaternion()
    lq0=(frame(L,N)@frame(il,base_normal).transposed()).to_quaternion()@base[l].to_quaternion()
    uq=uq0.slerp(uq,activity);lq=lq0.slerp(lq,activity)
    rel=(lq.inverted()@hm.to_quaternion())@rest_hand_rel.inverted()
    if rel.w<0:rel=-rel
    roll=2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(forearm_axis),rel.w)
    wrist=angle(L,hm.to_quaternion()@hand_long)
    return S,E,uq,lq,roll,wrist,d/(A+B),shift

def contact_pose(t,roll):
    axis=leg(t)@tip.normalized()
    q=Quaternion(axis,roll)@grip_orientation(t)
    center=pivot+axis*.055
    return Matrix.LocRotScale(center-q@rod_center,q,Vector((1,1,1)))

# Solve the contact orientation and elbow side together. The hand's local grip
# never changes during the pull; only rotation about the leg is free.
def contact_cost(t,roll,pole,previous=None):
    hm=contact_pose(t,roll);S,E,uq,lq,tw,wrist,reach,_=arm(hm,1.,pole)
    score=max(0,reach-.965)**2*22000+max(0,reach-.999)**2*1e7
    # This rig's native support already has a pronated hand. Penalizing only
    # absolute roll sent the arm away from idle then rapidly back again.
    change=(tw-baseline_roll+math.pi)%(2*math.pi)-math.pi
    score+=wrist*wrist*10+max(0,wrist-math.radians(35))**2*80
    score+=change*change*25+max(0,abs(change)-math.radians(15))**2*500
    score+=pole*pole*.7+(E-native[l].translation).length_squared*20
    score+=max(0,E.z+.025)**2*300
    score+=(hm.translation-native[h].translation).length_squared*8
    if previous:
        score+=((roll-previous[0])**2+(pole-previous[1])**2)*2
    return score

controls=[];previous=None
for t in (CONTACT,.15,.18,.21,.24,.27,PULL_END):
    if previous is None:
        roll,pole=min(((math.radians(a),math.radians(b)) for a in range(-80,81,5) for b in range(-45,46,5)),key=lambda p:contact_cost(t,*p))
    else:roll,pole=previous
    for step in (6,3,1,.5):
        for _ in range(14):
            options=[(max(-math.radians(80),min(math.radians(80),roll+math.radians(a*step))),max(-math.radians(45),min(math.radians(45),pole+math.radians(b*step)))) for a,b in ((0,0),(-1,0),(1,0),(0,-1),(0,1))]
            new=min(options,key=lambda p:contact_cost(t,*p,previous))
            if new==(roll,pole):break
            roll,pole=new
    controls.append((t,roll,pole));previous=(roll,pole)
print('CONTACT_AUTHOR_TARGETS',[(t,list(contact_pose(t,rr).translation),[round(v,4) for v in arm(contact_pose(t,rr),1.,pp)[4:7]]) for t,rr,pp in controls],flush=True)

def control(t):
    i=min(len(controls)-2,max(0,bisect.bisect_right([v[0] for v in controls],t)-1))
    a,b=controls[i:i+2];dt=b[0]-a[0];w=max(0.,min(1.,(t-a[0])/dt))
    def slope(k,j):
        if k==0 or k==len(controls)-1:return 0.
        v0,v1,v2=controls[k-1:k+2]
        d0=(v1[j]-v0[j])/(v1[0]-v0[0]);d1=(v2[j]-v1[j])/(v2[0]-v1[0])
        return 2*d0*d1/(d0+d1) if d0*d1>0 else 0.
    return tuple((2*w**3-3*w*w+1)*a[j]+(w**3-2*w*w+w)*dt*slope(i,j)+(-2*w**3+3*w*w)*b[j]+(w**3-w*w)*dt*slope(i+1,j) for j in (1,2))

def hand(t):
    if t<=0 or t>=RETURN:return hand0.copy(),0.,0.
    if CONTACT<=t<=PULL_END:
        roll,pole=control(t);return contact_pose(t,roll),1.,pole
    if t<CONTACT:
        w=ramp(0,CONTACT,t);hm=blend(hand0,contact_pose(CONTACT,controls[0][1]),w)
        hm.translation+=Vector((-.014,-.004,-.018))*math.sin(math.pi*w)
        return hm,w,controls[0][2]*w
    w=ramp(PULL_END,RETURN,t)
    hm=blend(contact_pose(PULL_END,controls[-1][1]),hand0,w)
    hm.translation+=Vector((-.020,-.006,-.027))*math.sin(math.pi*w)
    return hm,1-w,controls[-1][2]*(1-w)

# The cylinder turns through the finger hook as the hinge opens. Fit each
# contact key in hand space so the fingers follow that direction rather than
# holding a single clenched fist for the entire 90 degree mechanical swing.
finger_controls=[]
initial_axis=rod_axis.copy()
for t,rr,pp in controls:
    hm=contact_pose(t,rr);rod_axis=hm.to_quaternion().inverted()@(leg(t)@tip.normalized())
    qs=dict(grip);es={n:e.copy() for n,e in angles.items()}
    for step in (4,2,1):
        for _ in range(4):
            for n in digits:
                d,j,_=n.split('_');j=int(j)
                for dimension in ((2,) if d!='thumb' or j!=1 else (0,1,2)):
                    candidates=[]
                    for sign in (-1,0,1):
                        ee=es[n].copy();bound=math.radians(5 if d=='thumb' else 8)
                        ee[dimension]=max(angles[n][dimension]-bound,min(angles[n][dimension]+bound,ee[dimension]+math.radians(step)*sign))
                        qcopy=dict(qs);qcopy[n]=local_rest[n].to_quaternion()@ee.to_quaternion()
                        prior=sum((Vector(e)-Vector(angles[k])).length_squared*.35 for k,e in es.items() if k!=n)+(Vector(ee)-Vector(angles[n])).length_squared*.35
                        candidates.append((fit_cost(rod_center,qcopy)+prior,ee,qcopy))
                    _,es[n],qs=min(candidates,key=lambda v:v[0])
    finger_controls.append(qs)
rod_axis=initial_axis

def contact_fingers(t):
    i=min(len(controls)-2,max(0,bisect.bisect_right([v[0] for v in controls],t)-1))
    w=ramp(controls[i][0],controls[i+1][0],t)
    return {n:finger_controls[i][n].slerp(finger_controls[i+1][n],w) for n in digits}

def authored(t,family):
    original,local=pose('idle',0,family);base={n:native_frame@m for n,m in original.items()};row=clone(base)
    if t<=0 or t>=RETURN:return original
    hm,activity,pole=hand(t)
    S,E,uq,lq,roll,wrist,reach,shift=arm(hm,activity,pole,base)
    if reach>=1.:raise ValueError('Author contact exceeds native arm reach '+str((t,reach,list(S),list(hm.translation),controls,list(rod_center))))
    Um=Matrix.LocRotScale(S,uq,Vector((1,1,1)));Lm=Matrix.LocRotScale(E,lq,Vector((1,1,1)))
    # Carry the shoulder opening and its upper-arm helpers in one deformation
    # frame. Translation-only clavicle motion sheared their shared skin ring.
    row['clavicle_l']=Um@base[u].inverted()@base['clavicle_l']
    for n in names:
        if under(n,h):continue
        if under(n,l):row[n]=Lm@base[l].inverted()@base[n]
        elif under(n,u):row[n]=Um@base[u].inverted()@base[n]
    for j in (1,2):
        n=f'upperarm_twist_{j:02d}_l'
        if n in row:row[n]=blend(row[n],Um@rest[u].inverted()@rest[n],activity)
    row[h]=hm
    contact_quats=contact_fingers(t)
    for n in names:
        if n==h or not under(n,h):continue
        p,q,sc=local[n].decompose()
        if n in digits:
            d=n.split('_')[0];delay={'index':0.,'middle':.003,'ring':.006,'pinky':.010,'thumb':.004}[d]
            release=ramp(0,.034,t)*(1-ramp(.365,RETURN,t))
            close=ramp(.065+delay,CONTACT,t)*(1-ramp(PULL_END,PULL_END+.024+delay,t))
            q=q.slerp(opened[n],release).slerp(contact_quats[n],close)
        row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,sc)
    # Absolute reference roll: V9 100/50 stations, not an idle-relative
    # additive roll composed on top of already twisted auxiliary bones.
    for j,w in ((1,1.),(2,.5)):
        n=f'lowerarm_twist_{j:02d}_l';lr=rest[l].inverted()@rest[n]
        target=Lm@Matrix.LocRotScale(lr.translation,Quaternion(forearm_axis,roll*w)@lr.to_quaternion(),lr.to_scale())
        transported=Lm@base[l].inverted()@base[n]
        row[n]=blend(transported,target,activity)
    if 'ik_hand_l' in row:row['ik_hand_l']=row[h]@base[h].inverted()@base['ik_hand_l']
    return {n:back@m for n,m in row.items()}

output={'mesh':'/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9','names':names,'clips':{},'duration':DURATION,'rate':RATE}
count=round(DURATION*RATE)+1
for family in ('base','mag10'):
    rows=[];matrices=[];previous={}
    for i in range(count):
        row=authored(i/RATE,family);matrices.append(row);values=[]
        for n in names:
            local=row[parents[n]].inverted()@row[n] if parents[n] else row[n];p,q,sc=(K@local@K).decompose()
            if n in previous and previous[n].dot(q)<0:q=-q
            previous[n]=q.copy();values.append([*p,q.x,q.y,q.z,q.w,*sc])
        rows.append(values)
    output['clips'][family]={'frames':rows}
    r.animation_data_clear();r.animation_data_create();action=bpy.data.actions.new('A_M24_Bipod_'+family+'_HandElbow30');r.animation_data.action=action
    s.render.fps=RATE;s.frame_start=0;s.frame_end=count-1
    for i,row in enumerate(matrices):
        for n,m in row.items():
            local=row[parents[n]].inverted()@m if parents[n] else m;basis=local_rest[n].inverted()@local;pb=r.pose.bones[n]
            pb.rotation_mode='QUATERNION';pb.location=basis.translation;pb.rotation_quaternion=basis.to_quaternion();pb.scale=basis.to_scale()
            pb.keyframe_insert('location',frame=i);pb.keyframe_insert('rotation_quaternion',frame=i);pb.keyframe_insert('scale',frame=i)
    action.use_fake_user=True
with gzip.open(O/'authored.json.gz','wt',encoding='utf-8') as f:json.dump(output,f)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Bipod_Hands_Editable.blend'))
report={'duration':DURATION,'contact':[CONTACT,PULL_END],'hand_return':RETURN,'shoulder_protraction_cm':[1.2,7.8,.1],
        'contact_controls':controls,'rod_local_center_m':list(rod_center),'rod_local_axis':list(rod_axis),
        'finger_flexion_degrees':{n:[math.degrees(v) for v in e] for n,e in angles.items()},
        'runtime_tested':False,'rendered':False}
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('M24_HAND_ELBOW_AUTHORED',json.dumps(report),flush=True)
