"""Overhead cast: protected arm roots, hinged elbows and staggered release.

This edits animation only. The complete existing WPN_root track, 0.24 s
detach event and the recall-entry pose remain the runtime contracts.
"""
import bpy,ast,copy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;R=P.parents[2];OUT=P/'Export'
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ThunderThrowV1/ThunderHammer_Throw_Editable.blend'))
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
    t=max(0.,min(1.,t));return t*t*t*(10.+t*(-15.+t*6.))
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
front_grips={'l':wrap(top_grips['l'],-10.),'r':wrap(top_grips['r'],15.)}
launch=original[names[1]][round(RELEASE*FPS)]['WPN_root']
# The flight handoff is between samples; blend the same original track at .24.
f=RELEASE*FPS;i=int(f);launch=blend(original[names[1]][i]['WPN_root'],original[names[1]][i+1]['WPN_root'],f-i)
released_hands={s:launch@front_grips[s] for s in ('l','r')}
after_hands={s:released_hands[s].copy() for s in ('l','r')}
after_hands['l'].translation+=Vector((-.035,-.008,-.060))
after_hands['r'].translation+=Vector((.015,.012,-.045))
end=original[names[1]][-1]
def definition(kind,frame,src):
    t=frame/FPS;wpn=src['WPN_root'];hands={};shoulders={}
    if kind=='charge':
        load=smooth(t/1.3);support=smooth(t/.40)
        for s in ('l','r'):
            hands[s]=wpn@blend_grip(idle_grips[s],top_grips[s],load)
            shoulders[s]=idle['upperarm_'+s].translation.lerp(shoulder_top[s],support)
    else:
        down=smooth(t/RELEASE)
        for s in ('l','r'):
            if t<=RELEASE:
                hands[s]=wpn@blend_grip(top_grips[s],front_grips[s],down)
                if s=='l':hands[s].translation+=Vector((-.009,0,-.004))*smooth((t-.217)/.023)
            elif t<=.315:
                start=released_hands[s].copy()
                if s=='l':start.translation+=Vector((-.009,0,-.004))
                hands[s]=blend(start,after_hands[s],smooth((t-RELEASE)/.075))
            else:hands[s]=blend(after_hands[s],end['hand_'+s],smooth((t-.315)/.39))
            shoulders[s]=shoulder_top[s].lerp(shoulder_cast[s],down)
            shoulders[s]=shoulders[s].lerp(idle['upperarm_'+s].translation,smooth((t-.44)/.36))
    return {'kind':kind,'t':t,'source':src,'hands':hands,'shoulders':shoulders,'wpn':wpn}
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
        neutral=hand.to_quaternion()@rest[H].to_quaternion().inverted()@b
        best=None
        # Author the elbow on its exact two-bone circle. The cost separates
        # palm comfort, hinge rotation, side-of-body space and eye clearance.
        for k in range(-90,91):
            angle=math.radians(k*2.);pole=Quaternion(axis,angle)@guide;elbow=center+pole*radius
            ua=(elbow-shoulder).normalized();fa=(hand.translation-elbow).normalized();normal=ua.cross(fa).normalized()
            hinge=framed(fa,normal)@framed(b,rn).inverted();full=(neutral.rotation_difference(fa)@hand.to_quaternion()@rest[H].to_quaternion().inverted())
            dq=full@hinge.inverted();twist=(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w)+math.pi)%(2*math.pi)-math.pi
            cost=neutral.angle(fa)**2+.13*max(0.,abs(twist)-math.radians(85))**2+.025*angle*angle
            cost+=600*max(0.,.095-sgn*elbow.x)**2+280*max(0.,.15-elbow.length)**2
            cost+=70*max(0.,elbow.z-hand.translation.z+.018)**2+25*max(0.,.075-elbow.y)**2
            if best is None or cost<best[0]:best=(cost,angle)
        angles.append(unwrap(best[1],angles[-1] if angles else None));specs.append((shoulder,axis,center,radius,guide,hand))
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
            loc[n]=blend(start,closed[n],smooth(t/.65));continue
        # Thumb/pinky release first, index/middle last. Flexion remains in each
        # finger's native local axes; there is no finger translation or scale.
        begins={'thumb':.194,'pinky':.200,'ring':.205,'middle':.212,'index':.218}
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
    if d['kind']=='charge':out=blend_local(out,d['source'],1-smooth(d['t']/.24))
    else:out=blend_local(out,d['source'],smooth((d['t']-.58)/(.86-.58)))
    poses.append(out)
count=len(original[names[0]]);charge,release=poses[:count],poses[count:]
charge[0]=copy.deepcopy(idle);release[0]=copy.deepcopy(charge[-1]);release[-1]=copy.deepcopy(original[names[1]][-1])
# The native baker preserves quaternion signs and exports only this rig.
module=ast.parse((R/'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
for name,rows in zip(names,[charge,release]):bake(name,rows,FPS)
rig.animation_data.action=bpy.data.actions[names[0]];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(312)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThunderHammer_ThrowRefineV3_Editable.blend'))
(P/'motion.json').write_text(json.dumps({'revision':'ThrowRefineV3','fps':FPS,'clips':names,'keys':{n:len(rows) for n,rows in zip(names,[charge,release])},'release_event_seconds':RELEASE,'weapon_track':'preserved from input on every authored key','root_positions_m':{'raised':{s:list(v) for s,v in shoulder_top.items()},'cast':{s:list(v) for s,v in shoulder_cast.items()}},'grip_roll_delta_top_to_cast_degrees':{'left':-10,'right':15},'forearm_twist':{'elbow':0,'twist_01':1,'twist_02':.5},'release_hands':'left support peels first; right guides final release; independent follow-through','recall_entry':'original release end pose retained','runtime_tested':False,'preview_rendered':False},indent=2),encoding='utf-8')
print('THUNDER_THROW_REFINE_V3_AUTHORED',flush=True)
