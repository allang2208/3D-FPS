"""A continuous post-release arc with staggered arms and a trailing wrist.
Preserves the complete V6 charge and all throw samples through .24 seconds.
"""
import ast, copy, json, math
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Quaternion
P=Path(__file__).resolve().parent;R=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ChargeRestoreV6/ThunderHammer_ChargeRestoreV6_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];FPS=240
name='A_ThunderHammer_ThrowRelease';action=bpy.data.actions[name]
rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
source=[]
for frame in range(round(action.frame_range[1])+1):
    scene.frame_set(frame);source.append({b.name:b.matrix.copy() for b in rig.pose.bones})
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
START_FRAME=57;START=START_FRAME/FPS;END=(len(source)-1)/FPS
initial=source[START_FRAME];last=source[-1]

def ease(t):
    t=max(0.,min(1.,t));return t*t*t*(10.+t*(-15.+6.*t))
def project(v,a):return (v-a*v.dot(a)).normalized()
def framed(a,n):return Matrix((a,n,a.cross(n))).transposed().to_quaternion()
def unwrap(a,b):return b+(a-b+math.pi)%(2*math.pi)-math.pi
def local_pose(p):return {b.name:p[b.parent.name].inverted()@p[b.name] if b.parent else p[b.name] for b in rig.data.bones}
def mix(a,b,w):
    p,q,s=a.decompose();p2,q2,s2=b.decompose()
    return Matrix.LocRotScale(p.lerp(p2,w),q.slerp(q2,w),s.lerp(s2,w))
def local_mix(a,b,w):
    la,lb=local_pose(a),local_pose(b);out={}
    for bone in rig.data.bones:
        m=mix(la[bone.name],lb[bone.name],w)
        out[bone.name]=out[bone.parent.name]@m if bone.parent else m
    out['WPN_root']=b['WPN_root'].copy();return out

def spline(keys,t):
    # Explicit shared tangents: middle keys carry momentum instead of stopping.
    for (ta,pa,va),(tb,pb,vb) in zip(keys,keys[1:]):
        if t<=tb:
            dt=tb-ta;u=max(0.,min(1.,(t-ta)/dt))
            return pa*(2*u**3-3*u*u+1)+va*(dt*(u**3-2*u*u+u))+pb*(-2*u**3+3*u*u)+vb*(dt*(u**3-u*u))
    return keys[-1][1].copy()

paths={};arm={}
for s in ('l','r'):
    U,F,H=['upperarm_'+s,'lowerarm_'+s,'hand_'+s]
    p=initial[H].translation;v=(p-source[START_FRAME-1][H].translation)*FPS
    # Left support falls away first. Right palm follows the cast forward/down,
    # then folds back with the elbow. The small rebound stays below the frame.
    points=([(START,p),(.325,Vector((-.245,.300,-.315))),(.49,Vector((-.275,.255,-.485))),
             (.65,Vector((-.175,.300,-.490))),(END,last[H].translation)] if s=='l' else
            [(START,p),(.355,Vector((.090,.485,-.290))),(.53,Vector((.195,.345,-.505))),
             (.68,Vector((.190,.315,-.515))),(END,last[H].translation)])
    keys=[]
    for i,(t,pos) in enumerate(points):
        tangent=v if i==0 else Vector((0,0,0)) if i==len(points)-1 else (points[i+1][1]-points[i-1][1])/(points[i+1][0]-points[i-1][0])
        keys.append((t,pos,tangent))
    paths[s]=keys
    a=(rest[F].translation-rest[U].translation).normalized();b=(rest[H].translation-rest[F].translation).normalized();rn=a.cross(b).normalized()
    l1=(rest[F].translation-rest[U].translation).length;l2=(rest[H].translation-rest[F].translation).length
    def pole(pose):
        sh,el,hand=[pose[n].translation for n in (U,F,H)]
        axis=(hand-sh).normalized();return axis,project(el-sh,axis)
    start_axis,start_pole=pole(initial);end_axis,end_pole=pole(last)
    start_fa=(initial[H].translation-initial[F].translation).normalized()
    start_ua=(initial[F].translation-initial[U].translation).normalized()
    start_df=framed(start_fa,start_ua.cross(start_fa).normalized())@framed(b,rn).inverted()
    # Store the starting wrist relative to the hinge, then let its bend lag
    # the elbow and release into a relaxed palm without another wrist snap.
    wrist=start_df.inverted()@initial[H].to_quaternion()@rest[H].to_quaternion().inverted()
    end_fa=(last[H].translation-last[F].translation).normalized();end_ua=(last[F].translation-last[U].translation).normalized()
    end_df=framed(end_fa,end_ua.cross(end_fa).normalized())@framed(b,rn).inverted()
    end_wrist=end_df.inverted()@last[H].to_quaternion()@rest[H].to_quaternion().inverted()
    arm[s]=(a,b,rn,l1,l2,start_axis,start_pole,end_axis,end_pole,wrist,end_wrist)

start_locals=local_pose(initial);end_locals=local_pose(last)
poses=[];twists={};metrics=[]
for frame,src in enumerate(source):
    t=frame/FPS
    if t<=.24:
        poses.append(copy.deepcopy(src));continue
    out=copy.deepcopy(src)
    for s in ('l','r'):
        U,F,H=['upperarm_'+s,'lowerarm_'+s,'hand_'+s];sgn=1 if s=='r' else -1
        a,b,rn,l1,l2,ax0,po0,ax1,po1,wrist0,wrist1=arm[s]
        hand=spline(paths[s],t)
        # Upper arm settles first; wrist travels on its own trailing arc.
        shoulder=initial[U].translation.lerp(last[U].translation,ease((t-.26)/.46))
        if s=='l':shoulder+=Vector((0,-.035,-.050))*math.sin(math.pi*max(0.,min(1.,(t-.35)/(END-.35))))**2
        v=hand-shoulder;axis=v.normalized();dist=v.length
        if dist>(l1+l2)*.97:
            shoulder+=axis*(dist-(l1+l2)*.97);v=hand-shoulder;dist=v.length
        center=shoulder+axis*((l1*l1-l2*l2+dist*dist)/(2*dist));radius=math.sqrt(max(0.,l1*l1-(center-shoulder).length_squared))
        p0=project(ax0.rotation_difference(axis)@po0,axis);p1=project(ax1.rotation_difference(axis)@po1,axis)
        swivel=math.atan2(axis.dot(p0.cross(p1)),p0.dot(p1))*ease((t-.27)/.52)
        elbow=center+(Quaternion(axis,swivel)@p0)*radius
        ua=(elbow-shoulder).normalized();fa=(hand-elbow).normalized();normal=ua.cross(fa).normalized()
        du=framed(ua,normal)@framed(a,rn).inverted();df=framed(fa,normal)@framed(b,rn).inverted()
        out['clavicle_'+s]=mix(initial['clavicle_'+s],last['clavicle_'+s],ease((t-.26)/.46))
        out['clavicle_'+s].translation+=shoulder-initial[U].translation.lerp(last[U].translation,ease((t-.26)/.46))
        # Transport each endpoint orientation onto its current segment axis.
        # Rotating about that axis changes the roll without bending the whole
        # chain through a local-quaternion blend (which can re-enter the view).
        ending=ease((t-.60)/(END-.60))
        end_ua=(last[F].translation-last[U].translation).normalized()
        end_fa=(last[H].translation-last[F].translation).normalized()
        uq=(du@rest[U].to_quaternion()).slerp(end_ua.rotation_difference(ua)@last[U].to_quaternion(),ending)
        fq=(df@rest[F].to_quaternion()).slerp(end_fa.rotation_difference(fa)@last[F].to_quaternion(),ending)
        out[U]=Matrix.LocRotScale(shoulder,uq,Vector((1,1,1)))
        out[F]=Matrix.LocRotScale(elbow,fq,Vector((1,1,1)))
        for stem in ('upperarm_twist_01','upperarm_twist_02'):
            n=stem+'_'+s
            out[n]=out[U]@mix(rest[U].inverted()@rest[n],last[U].inverted()@last[n],ending)
        relax=ease((t-(.255 if s=='l' else .285))/.16)
        neutral=Quaternion(b,math.radians(-12 if s=='l' else 12))
        wrist=wrist0.slerp(neutral,relax)
        # Gentle flexion trails the first drop, then decays; no repeated shake.
        lag=math.sin(math.pi*max(0.,min(1.,(t-.28)/.32)))**2
        wrist=Quaternion(rn,math.radians(-7)*lag)@wrist
        wrist=wrist.slerp(wrist1,ease((t-.63)/(END-.63)))
        hq=df@wrist@rest[H].to_quaternion()
        hq=hq.slerp(end_fa.rotation_difference(fa)@last[H].to_quaternion(),ending)
        out[H]=Matrix.LocRotScale(hand,hq,Vector((1,1,1)))
        hand_delta=hq@rest[H].to_quaternion().inverted();full=(hand_delta@b).rotation_difference(fa)@hand_delta;dq=full@df.inverted()
        raw=(2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(fa),dq.w)+math.pi)%(2*math.pi)-math.pi
        twist=unwrap(raw,twists.get(s,raw));twists[s]=twist
        for stem,share in [('lowerarm_twist_01',1.),('lowerarm_twist_02',.5)]:
            n=stem+'_'+s;loc=(out[F]@rest[F].inverted()@rest[n]).translation
            tq=(Quaternion(fa,twist*share)@df@rest[n].to_quaternion()).slerp(end_fa.rotation_difference(fa)@last[n].to_quaternion(),ending)
            out[n]=Matrix.LocRotScale(loc,tq,Vector((1,1,1)))
        for bone in rig.data.bones:
            n=bone.name
            if n.endswith('_'+s) and n.startswith(('thumb','index','middle','ring','pinky')):
                # Each finger softens slightly after its hand, while retaining
                # the existing open release and exact recall-entry hand pose.
                w=ease((t-(.36 if s=='l' else .40))/(END-(.36 if s=='l' else .40)))
                out[n]=out[bone.parent.name]@mix(start_locals[n],end_locals[n],w)
    # Initial continuity only. Late recovery keeps the authored world-space
    # chain; endpoint roll has already been fitted without moving the wrist.
    out=local_mix(src,out,ease((t-START)/.035))
    out['WPN_root']=src['WPN_root'].copy();poses.append(out)
poses[-1]=copy.deepcopy(last)
module=ast.parse((R/'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
bake(name,poses,FPS)
scene.frame_set(90)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThunderHammer_FollowThroughV7_Editable.blend'))
(P/'motion.json').write_text(json.dumps({'revision':'ThrowFollowThroughV7','fps':FPS,'clips':[name],
    'keys':len(poses),'preserve_through_seconds':.24,'release_event_seconds':.24,
    'charge':'ChargeRestoreV6 unchanged; no charge import','source':'ChargeRestoreV6',
    'hand_paths':{s:[{'t':t,'position':list(p),'tangent':list(v)} for t,p,v in keys] for s,keys in paths.items()},
    'wrist_lag':'left begins .255, right .285; single 7 degree flexion wave',
    'end_pose':'exact V6 source endpoint retained','runtime_tested':False},indent=2),encoding='utf-8')
print('THUNDER_FOLLOW_THROUGH_V7_AUTHORED',flush=True)
