"""Repair only hand contact and arm support on the installed double-cut trajectory."""
import json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;V1=P.parent/'ChixiaoDoubleHeavyV1'
env={'__file__':str(V1/'author_motion.py')}
exec(compile((V1/'author_motion.py').read_text('utf-8').split('receipt=')[0],str(V1/'author_motion.py'),'exec'),env)
A=env['A'];pose_at=env['pose_at'];rigid=env['grip_frame'];blend_pose=env['blend_pose'];serialize=env['serialize']
receipt={'revision':'ChixiaoGripV2','clips':{},'weapon_motion_changed':False,'timing_changed':False}
for variant in ('Standard','LongGrip'):
    original=json.loads((V1/variant/'editable_keys.json').read_text('utf-8'))
    idle=pose_at(original,1.);land=pose_at(original,.12)
    grip={s:rigid(land['WPN_root']).inverted()@rigid(land['hand_'+s]) for s in ('l','r')}
    final_grip={s:rigid(idle['WPN_root']).inverted()@rigid(idle['hand_'+s]) for s in ('l','r')}
    turns={s:math.atan2(math.sin(math.atan2(final_grip[s].translation.y,final_grip[s].translation.x)-math.atan2(grip[s].translation.y,grip[s].translation.x)),
        math.cos(math.atan2(final_grip[s].translation.y,final_grip[s].translation.x)-math.atan2(grip[s].translation.y,grip[s].translation.x))) for s in ('l','r')}
    # The entire finger hierarchy is a rigid grasp. Never blend individual
    # finger world transforms between two moving hand frames.
    fingers={s:{n:land['hand_'+s].inverted()@land[n] for n in A.HANDS[s]} for s in ('l','r')}
    bpy.ops.wm.open_mainfile(filepath=str(A.SOURCE));bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest={n:rest[A.PARENTS[n]].inverted()@m if A.PARENTS[n] in rest else m for n,m in rest.items()}
    reference={n:A.canonical(A.native(row)) for n,row in A.DATA['reference'].items()}
    correction={n:reference[n].inverted()@rest[n] for n in rest}
    skin={s:A.fit_skin_stations([o for o in scene.objects if o.type=='MESH'],reference,s) for s in ('l','r')}
    states={s:{'pole':0.,'roll':0.} for s in ('l','r')}
    grasp_angles={s:0. for s in ('l','r')};return_angles={};angle_velocity={s:0. for s in ('l','r')}
    residual={s:(Quaternion(Vector((0,0,1)),turns[s])@grip[s].to_quaternion()).inverted()@final_grip[s].to_quaternion() for s in ('l','r')}
    def make_grasp(side,angle,recovery):
        local=Quaternion(Vector((0,0,1)),angle).to_matrix().to_4x4()@grip[side]
        q=local.to_quaternion()@Quaternion().slerp(residual[side],recovery)
        local=A.mat(local.translation,q)
        local.translation.z=grip[side].translation.z*(1-recovery)+final_grip[side].translation.z*recovery
        return local
    def relax_wrist_chain(pose,side,weight):
        hn,ln,un=['hand_'+side,'lowerarm_'+side,'upperarm_'+side]
        h,l,u=[pose[n] for n in (hn,ln,un)]
        lower=h.translation-l.translation;upper=l.translation-u.translation
        axis=(h.to_quaternion()@idle[hn].to_quaternion().inverted())@(idle[hn].translation-idle[ln].translation).normalized()
        bend=math.degrees(axis.angle(lower.normalized()))
        if weight<=0.:return 0.
        direction=lower.normalized().slerp(axis,weight*max(0.,bend-28.)/max(.001,bend))
        elbow=h.translation-direction*lower.length
        shoulder=elbow+(u.translation-elbow).normalized()*upper.length
        # Keep the native open arm root below/outside the real 75-degree
        # vertical view, while retaining the wrist and both bone lengths.
        vf=math.tan(math.radians(75)/2);hf=vf*1100/600
        planes=[Vector((0,vf,1)),Vector((-1 if side=='r' else 1,hf,0))]
        if shoulder.y>-.02 and all(n.dot(shoulder)>-.08 for n in planes):
            options=[]
            for n in planes:
                normal=n.normalized();offset=(-.08-n.dot(elbow))/n.length
                if abs(offset)>=upper.length:continue
                center=elbow+normal*offset;radius=math.sqrt(upper.length**2-offset**2)
                tangent=shoulder-center-normal*(shoulder-center).dot(normal)
                if tangent.length<1.e-7:continue
                options.append(center+tangent.normalized()*radius)
            if options:
                safe=min(options,key=lambda p:(p-shoulder).length)
                shoulder=elbow+(shoulder-elbow).normalized().slerp((safe-elbow).normalized(),weight)*upper.length
        upper_q=upper.normalized().rotation_difference((elbow-shoulder).normalized())
        lower_q=lower.normalized().rotation_difference(direction)
        for bone in (un,'upperarm_twist_01_'+side,'upperarm_twist_02_'+side):
            m=pose[bone];pose[bone]=A.mat(shoulder+upper_q@(m.translation-u.translation),upper_q@m.to_quaternion(),m.to_scale())
        for bone in (ln,'lowerarm_twist_01_'+side,'lowerarm_twist_02_'+side):
            m=pose[bone];pose[bone]=A.mat(elbow+lower_q@(m.translation-l.translation),lower_q@m.to_quaternion(),m.to_scale())
        shift=shoulder-u.translation;pose['clavicle_'+side]=pose['clavicle_'+side].copy();pose['clavicle_'+side].translation+=shift
        return shift.length
    rig.animation_data_create();action=bpy.data.actions.new('Chixiao_GripV2_'+variant);action.use_fake_user=True;rig.animation_data.action=action
    samples=[];previous={};blend_previous={}
    for frame,sample in enumerate(original['samples']):
        t=sample['seconds'];pose=A.pose_from_rows(sample['bones'])
        if .12<t<1.:
            recovery=A.smooth((t-.38)/.62)
            base=blend_pose(land,idle,recovery)
            support=A.smooth((t-.12)/.06)*(1.-A.smooth((t-.84)/.16))
            for s in ('l','r'):
                old_angle=grasp_angles[s]
                if t>=.80:
                    if s not in return_angles:return_angles[s]=old_angle
                    candidates=[return_angles[s]+(turns[s]-return_angles[s])*A.smooth((t-.8)/.2)]
                else:candidates=[old_angle+math.radians(d) for d in (-8,-5,-2,0,2,5,8)]
                best=None
                for angle in candidates:
                    local=make_grasp(s,angle,recovery);target=rigid(pose['WPN_root'])@local
                    target=A.mat(target.translation,target.to_quaternion(),land['hand_'+s].to_scale())
                    candidate=dict(pose);state=dict(states[s])
                    for n,m in fingers[s].items():candidate[n]=target@m
                    A.solve_supported_arm(candidate,idle,base,s,support,state,skin[s])
                    shoulder_shift=relax_wrist_chain(candidate,s,support)
                    hand,elbow=candidate['hand_'+s],candidate['lowerarm_'+s]
                    axis=(hand.to_quaternion()@idle['hand_'+s].to_quaternion().inverted())@(idle['hand_'+s].translation-idle['lowerarm_'+s].translation).normalized()
                    bend=math.degrees(axis.angle((hand.translation-elbow.translation).normalized()))
                    roll=abs(math.degrees(state['roll']))
                    step=math.degrees(angle-old_angle)
                    cost=(max(0.,bend-18.)/12.)**2+(max(0.,roll-65.)/20.)**2
                    cost+=.025*(step/5.)**2+.01*((step-angle_velocity[s])/4.)**2
                    cost+=.015*(math.degrees(angle-turns[s]*recovery)/100.)**2
                    cost+=.25*(shoulder_shift/.10)**2
                    if best is None or cost<best[0]:best=(cost,angle,candidate,state)
                _,angle,pose,states[s]=best
                angle_velocity[s]=math.degrees(angle-old_angle);grasp_angles[s]=angle
                pose['ik_hand_'+s]=pose['hand_'+s]@idle['hand_'+s].inverted()@idle['ik_hand_'+s]
        keys=sample['bones'] if t<=.12 or t>=1. else serialize(pose,previous)
        samples.append({'seconds':t,'bones':keys})
        scene.frame_set(frame);world={n:pose[n]@correction[n] for n in rest}
        for b in rig.pose.bones:
            parent=world[b.parent.name] if b.parent else Matrix.Identity(4)
            b.matrix_basis=local_rest[b.name].inverted()@parent.inverted()@world[b.name]
            b.rotation_mode='QUATERNION';q=b.rotation_quaternion.copy()
            if b.name in blend_previous and q.dot(blend_previous[b.name])<0:q=-q
            b.rotation_quaternion=q;blend_previous[b.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=frame,group=b.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.render.fps=original['fps'];scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=len(samples)-1;scene.frame_set(0)
    out=P/variant;out.mkdir(exist_ok=True);keys=out/'editable_keys.json'
    keys.write_text(json.dumps(dict(original,samples=samples),separators=(',',':')),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Chixiao_GripV2_Editable.blend'))
    receipt['clips'][variant]={'keys':str(keys),'circular_return_degrees':{s:math.degrees(a) for s,a in turns.items()}}
    print('CHIXIAO_GRIP_AUTHORED',variant,flush=True)
(P/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
