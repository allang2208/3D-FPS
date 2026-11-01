"""Overhand cast: regrasp the shaft, keep elbow branches continuous, relax on release.

This edits animation only. The complete existing WPN_root track, 0.24 s
detach event and the recall-entry pose remain the runtime contracts.
"""
import bpy,ast,copy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;R=P.parents[2];OUT=P/'Export';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ThrowRefineV3/ThunderHammer_ThrowRefineV3_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
FPS=240;RELEASE=.24
names=['A_ThunderHammer_ThrowCharge','A_ThunderHammer_ThrowRelease'];original={}
for name in names:
    a=bpy.data.actions[name];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    rows=[]
    for frame in range(round(a.frame_range[1])+1):
        scene.frame_set(frame);rows.append({b.name:b.matrix.copy() for b in rig.pose.bones})
    original[name]=rows
idle=copy.deepcopy(original[names[0]][0]);top=original[names[0]][-1]
top_grips={s:top['WPN_root'].inverted()@top['hand_'+s] for s in ('l','r')}
idle_grips={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
closed={b.name:top[b.parent.name].inverted()@top[b.name] for b in rig.data.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}
def smooth(t):
    t=max(0.,min(1.,t));return max(0.,min(1.,t*t*t*(10.+t*(-15.+t*6.))))
def blend(a,b,t):
    return Matrix.LocRotScale(a.translation.lerp(b.translation,t),a.to_quaternion().slerp(b.to_quaternion(),t),Vector((1,1,1)))
def unwrap(a,b):return a if b is None else b+(a-b+math.pi)%(2*math.pi)-math.pi
def blend_grip(a,b,t):
    pa,pb=a.translation,b.translation;aa=math.atan2(pa.y,pa.x);ab=unwrap(math.atan2(pb.y,pb.x),aa)
    angle=aa+(ab-aa)*t;radius=math.hypot(pa.x,pa.y)*(1-t)+math.hypot(pb.x,pb.y)*t
    return Matrix.LocRotScale(Vector((radius*math.cos(angle),radius*math.sin(angle),pa.z*(1-t)+pb.z*t)),a.to_quaternion().slerp(b.to_quaternion(),t),Vector((1,1,1)))
def wrap(grip,angle):return Quaternion((0,0,1),math.radians(angle)).to_matrix().to_4x4()@grip
def framed(axis,normal):return Matrix((axis,normal,axis.cross(normal))).transposed().to_quaternion()
def project(v,axis):return (v-axis*v.dot(axis)).normalized()
def pose_local(p):return {b.name:p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name] for b in rig.data.bones}
def blend_local(a,b,t):
    la,lb=pose_local(a),pose_local(b);out={}
    for bone in rig.data.bones:
        m=blend(la[bone.name],lb[bone.name],t);out[bone.name]=out[bone.parent.name]@m if bone.parent else m
    # Weapon is an independent drive bone; it keeps the original rigid path.
    out['WPN_root']=a['WPN_root'].copy();return out
# The left cut end is translated behind the eye before the overhead lift.
# The right shoulder rises to support the raised hand, then advances during the
# cast. Neither arm is shortened or scaled to conceal the root.
shoulder_top={'l':Vector((-.245,-.090,-.230)),'r':Vector((.235,-.040,-.135))}
shoulder_cast={'l':Vector((-.245,-.080,-.240)),'r':Vector((.235,.035,-.240))}
def overhand(grip,s):
    # Reverse thumb direction along the shaft while retaining the whole
    # closed grasp. Rotation around the radial axis preserves its cylinder
    # contact; it is a regrasp, not a 180-degree spin through the forearm.
    radial=Vector((grip.translation.x,grip.translation.y,0)).normalized()
    p=grip.translation.copy()
    if s=='r':p.z-=.09
    return Matrix.LocRotScale(p,Quaternion(radial,math.pi)@grip.to_quaternion(),Vector((1,1,1)))

def curve(keys,t):
    for a,b in zip(keys,keys[1:]):
        if t<=b[0]:return a[1]+(b[1]-a[1])*smooth((t-a[0])/(b[0]-a[0]))
    return keys[-1][1]

roll_keys={'l':[(0,60),(.06,55),(.12,35),(.18,-15),(.24,-30)],
           'r':[(0,-10),(.06,-15),(.12,5),(.18,60),(.24,70)]}
def cast_grip(s,t):
    # Input is the delivered V3 grasp. Its old small circumferential roll is
    # part of that input, so fit the correction against the actual frame.
    f=min(t,RELEASE)*FPS;i=min(int(f),len(original[names[1]])-2)
    p=blend(original[names[1]][i]['WPN_root'],original[names[1]][i+1]['WPN_root'],f-i)
    h=blend(original[names[1]][i]['hand_'+s],original[names[1]][i+1]['hand_'+s],f-i)
    return wrap(overhand(p.inverted()@h,s),curve(roll_keys[s],t))

front_grips={s:cast_grip(s,RELEASE) for s in ('l','r')}
launch=original[names[1]][round(RELEASE*FPS)]['WPN_root']
# The flight handoff is between samples; blend the same original track at .24.
f=RELEASE*FPS;i=int(f);launch=blend(original[names[1]][i]['WPN_root'],original[names[1]][i+1]['WPN_root'],f-i)
released_hands={s:launch@front_grips[s] for s in ('l','r')}
after_hands={s:released_hands[s].copy() for s in ('l','r')}
after_hands['l'].translation+=Vector((-.090,-.025,-.100))
after_hands['r'].translation+=Vector((.035,.015,-.070))
end=original[names[1]][-1]
def definition(kind,frame,src):
    t=frame/FPS;wpn=src['WPN_root'];hands={};shoulders={};support_rot={}
    if kind=='charge':
        load=smooth(t/1.3);support=smooth(t/.40)
        for s in ('l','r'):
            source_grip=wpn.inverted()@src['hand_'+s]
            lo,hi=(.18,.62) if s=='r' else (.60,1.04)
            regrasp=smooth((t-lo)/(hi-lo))
            roll=curve([(0,0),(.6,10 if s=='l' else 5),(1.0,50 if s=='l' else -10),(1.3,60 if s=='l' else -10)],t)
            target=wrap(overhand(source_grip,s),roll)
            support_rot[s]=(wpn@target).to_quaternion()
            hand_grip=blend_grip(source_grip,target,regrasp)
            radial=Vector((hand_grip.translation.x,hand_grip.translation.y,0)).normalized()
            hand_grip.translation+=radial*(.035*math.sin(math.pi*regrasp)**2)
            hands[s]=wpn@hand_grip
            shoulders[s]=idle['upperarm_'+s].translation.lerp(shoulder_top[s],support)
    else:
        down=smooth(t/RELEASE)
        for s in ('l','r'):
            if t<=RELEASE:
                hands[s]=wpn@cast_grip(s,t)
                if s=='l':hands[s].translation+=Vector((-.055,-.012,-.035))*smooth((t-.16)/.08)
            elif t<=.315:
                start=released_hands[s].copy()
                if s=='l':start.translation+=Vector((-.055,-.012,-.035))
                hands[s]=blend(start,after_hands[s],smooth((t-RELEASE)/.075))
            else:hands[s]=blend(after_hands[s],end['hand_'+s],smooth((t-.315)/.39))
            shoulders[s]=shoulder_top[s].lerp(shoulder_cast[s],down)
            shoulders[s]=shoulders[s].lerp(idle['upperarm_'+s].translation,smooth((t-.44)/.36))
    free={}
    for s in ('l','r'):
        if kind=='release':free[s]=smooth((t-(.16 if s=='l' else RELEASE))/(.075 if s=='l' else .085))*(1-smooth((t-.58)/.20))
        else:
            lo,hi=(.18,.62) if s=='r' else (.60,1.04)
            # An open palm follows its relaxed forearm while travelling to
            # the new grip; it is not constrained to grasp the shaft mid-turn.
            free[s]=smooth((t-lo)/.07)*(1-smooth((t-(hi-.09))/.09))
    return {'kind':kind,'t':t,'source':src,'hands':hands,'shoulders':shoulders,'wpn':wpn,'free':free,'support_rot':support_rot}
defs=[definition('charge',i,p) for i,p in enumerate(original[names[0]])]
defs+= [definition('release',i,p) for i,p in enumerate(original[names[1]])]
arm={}
for s in ('l','r'):
    U,F,H=['upperarm_'+s,'lowerarm_'+s,'hand_'+s];sgn=1 if s=='r' else -1
    a=(rest[F].translation-rest[U].translation).normalized();b=(rest[H].translation-rest[F].translation).normalized();rn=a.cross(b).normalized()
    l1=(rest[F].translation-rest[U].translation).length;l2=(rest[H].translation-rest[F].translation).length
    specs=[];angles=[]
    for d in defs:
        shoulder=d['shoulders'][s];hand=d['hands'][s];v=hand.translation-shoulder
        # Preserve authored hand contact. The supporting shoulder supplies the
        # small residual reach, instead of stretching either arm bone.
        limit=(l1+l2)*.965
        if v.length>limit:
            shoulder=shoulder+v.normalized()*(v.length-limit);v=hand.translation-shoulder
        axis=v.normalized();dist=v.length;along=(l1*l1-l2*l2+dist*dist)/(2*dist)
        center=shoulder+axis*along;radius=math.sqrt(max(0.,l1*l1-along*along))
        guide=project(Vector((sgn*.85,-.15,-.40)),axis)
        support_q=hand.to_quaternion()
        if d['kind']=='charge':support_q=support_q.slerp(d['support_rot'][s],d['free'][s])
        neutral=support_q@rest[H].to_quaternion().inverted()@b
        best=None
        # Author the elbow on its exact two-bone circle. The cost separates
        # palm comfort, hinge rotation, side-of-body space and eye clearance.
        for k in range(-90,91):
            angle=math.radians(k*2.);pole=Quaternion(axis,angle)@guide;elbow=center+pole*radius
            ua=(elbow-shoulder).normalized();fa=(hand.translation-elbow).normalized();normal=ua.cross(fa).normalized()
            hinge=framed(fa,normal)@framed(b,rn).inverted();full=(neutral.rotation_difference(fa)@support_q@rest[H].to_quaternion().inverted())
            dq=full@hinge.inverted();twist=(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w)+math.pi)%(2*math.pi)-math.pi
            free=d['free'][s] if d['kind']=='release' else 0.
            cost=(1-free)*(3*neutral.angle(fa)**2+1.5*twist*twist)+.025*angle*angle
            # Stay on the same elbow branch throughout the cast. The palm
            # opens after release, so it must no longer drag the elbow around.
            if angles:
                delta=unwrap(angle,angles[-1])-angles[-1]
                cost+=10.*delta*delta
            cost+=600*max(0.,.095-sgn*elbow.x)**2+280*max(0.,.15-elbow.length)**2
            cost+=70*max(0.,elbow.z-hand.translation.z+.018)**2+25*max(0.,.075-elbow.y)**2
            if best is None or cost<best[0]:best=(cost,angle)
        angle=unwrap(best[1],angles[-1] if angles else None)
        if angles:angle=max(angles[-1]-math.radians(2.5),min(angles[-1]+math.radians(2.5),angle))
        angles.append(angle);specs.append((shoulder,axis,center,radius,guide,hand))
    # Smooth the authored swivel curve rather than independently changing
    # elbow branches on consecutive samples.
    kernel=[1,2,3,4,5,4,3,2,1]
    for _ in range(2):angles=[sum(angles[max(0,min(len(angles)-1,i+j-4))]*w for j,w in enumerate(kernel))/sum(kernel) for i in range(len(angles))]
    arm[s]=(specs,angles,a,b,rn)
def solve(out,s,index,twists):
    specs,angles,a,b,rn=arm[s];shoulder,axis,center,radius,guide,hand=specs[index]
    elbow=center+(Quaternion(axis,angles[index])@guide)*radius
    ua=(elbow-shoulder).normalized();fa=(hand.translation-elbow).normalized();normal=ua.cross(fa).normalized()
    du=framed(ua,normal)@framed(a,rn).inverted();df=framed(fa,normal)@framed(b,rn).inverted()
    U,F,H=['upperarm_'+s,'lowerarm_'+s,'hand_'+s]
    out['clavicle_'+s].translation+=shoulder-idle[U].translation
    out[U]=Matrix.LocRotScale(shoulder,du@rest[U].to_quaternion(),Vector((1,1,1)))
    out[F]=Matrix.LocRotScale(elbow,df@rest[F].to_quaternion(),Vector((1,1,1)))
    for n in ['upperarm_twist_01_'+s,'upperarm_twist_02_'+s]:out[n]=out[U]@rest[U].inverted()@rest[n]
    hand=hand.copy()
    free=defs[index]['free'][s]
    if free>0.:
        neutral=Quaternion(fa,math.radians(15 if s=='r' else -15))@df@rest[H].to_quaternion()
        hand=Matrix.LocRotScale(hand.translation,hand.to_quaternion().slerp(neutral,free),Vector((1,1,1)))
    hand_delta=hand.to_quaternion()@rest[H].to_quaternion().inverted();full=(hand_delta@b).rotation_difference(fa)@hand_delta
    dq=full@df.inverted();raw=(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w)+math.pi)%(2*math.pi)-math.pi
    angle=unwrap(raw,twists.get(s));twists[s]=angle
    # Current V9 skin contract: zero elbow spin, distal twist 100%, middle 50%.
    for n,share in [('lowerarm_twist_01_'+s,1.),('lowerarm_twist_02_'+s,.5)]:
        loc=(out[F]@rest[F].inverted()@rest[n]).translation
        out[n]=Matrix.LocRotScale(loc,Quaternion(fa,angle*share)@df@rest[n].to_quaternion(),Vector((1,1,1)))
    out[H]=hand
    for bone in rig.data.bones:
        if bone.name in closed and bone.name.endswith('_'+s):out[bone.name]=out[bone.parent.name]@closed[bone.name]
def finger_pose(out,d):
    loc=pose_local(out);kind,t=d['kind'],d['t']
    for bone in rig.data.bones:
        if bone.name not in closed:continue
        n=bone.name;digit=n.split('_')[0];side=n[-1]
        if 'metacarpal' in n:
            loc[n]=closed[n].copy();continue
        if kind=='charge':
            src=d['source'];start=src[bone.parent.name].inverted()@src[n]
            base=blend(start,closed[n],smooth(t/.65))
            lo,hi=(.18,.62) if side=='r' else (.60,1.04)
            opening=.82*smooth((t-lo)/.07)*(1-smooth((t-(hi-.09))/.09))
            loc[n]=blend(base,local_rest[n],opening);continue
        # Thumb/pinky release first, index/middle last. Flexion remains in each
        # finger's native local axes; there is no finger translation or scale.
        begins={'thumb':.125,'pinky':.131,'ring':.137,'middle':.145,'index':.152}
        if side=='r':begins={'thumb':.218,'pinky':.222,'ring':.227,'middle':.232,'index':.237}
        maximum={'thumb':.65,'pinky':.73,'ring':.80,'middle':.87,'index':.90}[digit]
        segment=next((int(p) for p in n.split('_') if p.isdigit()),1)
        delay=.006*max(0,segment-1)
        maximum*=1.-.07*max(0,segment-1)
        opening=maximum*smooth((t-begins[digit]-delay)/.065)
        opening=opening*(1-smooth((t-.38)/.22))+min(.70,maximum)*smooth((t-.38)/.22)
        loc[n]=blend(closed[n],local_rest[n],opening)
    for bone in rig.data.bones:out[bone.name]=out[bone.parent.name]@loc[bone.name] if bone.parent else loc[bone.name]
    out['WPN_root']=d['wpn'].copy()
poses=[];twists={}
for i,d in enumerate(defs):
    out=copy.deepcopy(idle)
    for s in ('l','r'):solve(out,s,i,twists)
    out['WPN_root']=d['wpn'].copy();finger_pose(out,d)
    if d['kind']=='charge':out=blend_local(out,d['source'],1-smooth(d['t']/.18))
    else:out=blend_local(out,d['source'],smooth((d['t']-.58)/(.86-.58)))
    poses.append(out)
count=len(original[names[0]]);charge,release=poses[:count],poses[count:]
charge[0]=copy.deepcopy(idle);release[0]=copy.deepcopy(charge[-1]);release[-1]=copy.deepcopy(original[names[1]][-1])
# The native baker preserves quaternion signs and exports only this rig.
module=ast.parse((R/'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
for name,rows in zip(names,[charge,release]):bake(name,rows,FPS)
rig.animation_data.action=bpy.data.actions[names[0]];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(312)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThunderHammer_ThrowRefineV4_Editable.blend'))
(P/'motion.json').write_text(json.dumps({'revision':'ThrowRefineV4','fps':FPS,'clips':names,'keys':{n:len(rows) for n,rows in zip(names,[charge,release])},'release_event_seconds':RELEASE,'weapon_track':'preserved from V3 on every authored key','regrasp_seconds':{'right':[.18,.62],'left':[.60,1.04]},'right_grasp_shaft_shift_m':-.09,'roll_keys':roll_keys,'forearm_twist':{'elbow':0,'twist_01':1,'twist_02':.5},'release_hands':'left frees at .16, right at .24, wrists relax after release','recall_entry':'original release end pose retained','runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
print('THUNDER_THROW_REFINE_V4_AUTHORED',flush=True)
