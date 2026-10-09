"""Native Super90 sprint: three base clips and four sparse grip layers.

Uses the current production mesh/idle and the rifle sprint release/raise/return
contract. Animation export only: no mesh reimport, render or runtime test.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

O=Path(__file__).parent; S=O.parent; X=O/'Exports'; X.mkdir(exist_ok=True)
sys.path.insert(0,str(S/'M1911RevolverInspect20260927'))
import author_support as support
bpy.ops.wm.open_mainfile(filepath=str(S/'BenelliM4Super9020261006/Super90_Gameplay_Editable.blend'))
rig=bpy.data.objects['SK_Super90']; scene=bpy.context.scene; scene.render.fps=60
rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Super90_idle']
rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0); bpy.context.view_layer.update()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
names=list(rest); I=Matrix.Identity(4)
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
rig.animation_data_clear()
rig.animation_data_create()
local_rest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}

def uemat(v):
    return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))

D=json.loads((S/'Super90Foregrips20261007/native.json').read_text())
C=Matrix.Diagonal((100,-100,100,1)); Ci=C.inverted()
K={n:(C@rest[n]).inverted()@uemat(D['rest'][n]) for n in names}
Ki={n:k.inverted() for n,k in K.items()}
# AnimPose SOURCE includes the imported root scale (0.01). Match the unchanged
# base root to the Blender author root before applying metre-space trajectories.
# This converts evaluated input poses only; it never scales the mesh or rig.
eval_base={}
for n in names:
    eval_base[n]=eval_base.get(parents[n],I)@uemat(D['clips']['idle']['samples'][0]['local'][n])
root=next(n for n in names if parents[n] is None)
evaluation_to_author=idle[root]@(Ci@eval_base[root]@Ki[root]).inverted()
idles={'base':idle}
for family in ('vertical','canted','prism','angled'):
    data=json.loads((S/'Super90Foregrips20261007/Profiles'/(family+'.json')).read_text())
    entry=next(c for c in data['clips'] if c['kind']=='idle')
    tracks={t['bone']:t['values'][:10] for t in entry['tracks']}
    world={}
    for n in names:
        local=uemat(D['clips']['idle']['samples'][0]['local'][n])
        if n in tracks:
            v=tracks[n]; p,q,s=local.decompose()
            local=Matrix.LocRotScale(p+Vector(v[:3]),Quaternion((v[6],*v[3:6]))@q,s+Vector(v[7:10]))
        world[n]=world.get(parents[n],I)@local
    idles[family]={n:evaluation_to_author@Ci@world[n]@Ki[n] for n in names}

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a))); return t*t*(3-2*t)

def segment_frame(direction,hinge):
    x=direction.normalized(); z=(hinge-x*hinge.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()

# The Super90 V7 proximal skin is on aux at the elbow, with the other
# stations at one-third / two-thirds. Infer them from this rig's own bind;
# the old .2/.5/.8 recipe rotated the elbow skin as if it were mid-forearm.
forearm_rest=rest['hand_l'].translation-rest['lowerarm_l'].translation
skin_stations={n:max(0.,min(1.,(rest[n].translation-rest['lowerarm_l'].translation).dot(forearm_rest)/forearm_rest.length_squared))
               for n in ('lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l')}

def arm(p,source,side,target,relax=0.):
    upper='upperarm_'+side; lower='lowerarm_'+side; hand='hand_'+side
    p['clavicle_'+side]=source['clavicle_'+side].copy()
    shoulder=source[upper].translation.copy(); elbow=source[lower].translation; wrist=source[hand].translation
    goal=target.translation; delta=goal-shoulder; axis=delta.normalized(); distance=delta.length
    a=(elbow-shoulder).length; b=(wrist-elbow).length
    reach=(a+b)*.975
    if distance>reach:
        shift=axis*(distance-reach); shoulder+=shift
        p['clavicle_'+side].translation+=shift; distance=reach
    distance=max(abs(a-b)+1e-5,distance)
    along=(a*a-b*b+distance*distance)/(2*distance)
    original_axis=(wrist-source[upper].translation).normalized()
    pole=elbow-source[upper].translation
    if side=='l':
        # Parallel-transport the idle bend plane with the shoulder-wrist axis.
        # Projecting a fixed old elbow onto every new axis passes through zero
        # during this downward arc and abruptly flips the IK pole by 180 deg.
        pole-=original_axis*pole.dot(original_axis)
        pole=original_axis.rotation_difference(axis)@pole
    else:
        pole-=axis*pole.dot(axis)
    if pole.length<1e-6:
        pole=Vector((0,0,-1)); pole-=axis*pole.dot(axis)
    knee=shoulder+axis*along+pole.normalized()*math.sqrt(max(0.,a*a-along*along))
    if side=='l':
        u0=elbow-source[upper].translation; f0=wrist-elbow
        u=knee-shoulder; f=goal-knee; h0=u0.cross(f0); h=u.cross(f)
        # ArmHinge55 principle adapted to the native Super90 rig: both segment
        # rotations share the same physical elbow hinge, calibrated to this
        # grip's accepted idle. Do not carry palm roll into the upper arm.
        qa=segment_frame(u,h)@segment_frame(u0,h0).inverted()
        qb=segment_frame(f,h)@segment_frame(f0,h0).inverted()
    else:
        qa=(elbow-source[upper].translation).rotation_difference(knee-shoulder)
        qb=(wrist-elbow).rotation_difference(goal-knee)
    upper_q=qa@source[upper].to_quaternion();lower_q=qb@source[lower].to_quaternion()
    if side=='l' and relax>0.:
        # A released arm uses its native anatomical bend plane. Calibrating
        # only against an installed grip preserves that grip's upper-arm roll
        # (about 29 degrees for vertical), even after the hand has let go.
        ur=rest[lower].translation-rest[upper].translation
        fr=rest[hand].translation-rest[lower].translation;hr=ur.cross(fr)
        upper_neutral=segment_frame(knee-shoulder,h)@segment_frame(ur,hr).inverted()@rest[upper].to_quaternion()
        lower_neutral=segment_frame(goal-knee,h)@segment_frame(fr,hr).inverted()@rest[lower].to_quaternion()
        upper_q=upper_q.slerp(upper_neutral,relax)
        lower_q=lower_q.slerp(lower_neutral,relax)
    p[upper]=Matrix.LocRotScale(shoulder,upper_q,source[upper].to_scale())
    p[lower]=Matrix.LocRotScale(knee,lower_q,source[lower].to_scale())
    axis=(goal-knee).normalized()
    roll=target.to_quaternion()@(qb@source[hand].to_quaternion()).inverted()
    angle=2*math.atan2(Vector((roll.x,roll.y,roll.z)).dot(axis),roll.w)
    angle=(angle+math.pi)%(2*math.pi)-math.pi
    if side=='l':
        neutral_hand=p[lower].to_quaternion()@rest[lower].to_quaternion().inverted()@rest[hand].to_quaternion()
        roll=target.to_quaternion()@neutral_hand.inverted()
        angle=2*math.atan2(Vector((roll.x,roll.y,roll.z)).dot(axis),roll.w)
        angle=(angle+math.pi)%(2*math.pi)-math.pi
        for n,weight in skin_stations.items():
            base=p[lower]@source[lower].inverted()@source[n]
            neutral=p[lower].to_quaternion()@rest[lower].to_quaternion().inverted()@rest[n].to_quaternion()
            relaxed=Quaternion(axis,angle*weight)@neutral
            # Preserve the exact installed idle at entry/exit. While releasing,
            # relax its inherited twist along the actual skin stations as well
            # as relaxing the wrist; changing only hand_l left a twisted band.
            q=base.to_quaternion().slerp(relaxed,relax)
            p[n]=Matrix.LocRotScale(base.translation,q,base.to_scale())
    else:
        for prefix,weight in (('lowerarm_aux_',.2),('lowerarm_twist_02_',.5),('lowerarm_twist_01_',.8)):
            n=prefix+side; base=p[lower]@source[lower].inverted()@source[n]
            p[n]=Matrix.LocRotScale(base.translation,Quaternion(axis,angle*weight)@base.to_quaternion(),base.to_scale())
    p[hand]=target
    carry=target@source[hand].inverted()
    for n in names:
        if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):
            p[n]=carry@source[n]

up=Vector((0,0,1))
barrel=(idle['WPN_FrontSight'].translation-idle['WPN_RearSight'].translation).normalized()
forward=Vector((barrel.x,barrel.y,0)).normalized(); right=forward.cross(up).normalized()
upright=forward*math.cos(math.radians(76))+up*math.sin(math.radians(76))
raise_q=Quaternion(up,math.radians(-7))@Quaternion(upright,math.radians(-8))@barrel.rotation_difference(upright)

def pose(progress,phase=None,family='base'):
    source=idles[family]; p={n:m.copy() for n,m in source.items()}
    if progress<=0:return p
    released=smooth(0,.22,progress); withdrawn=smooth(.10,.60,progress); raised=smooth(.25,1,progress)
    side=math.sin(phase) if phase is not None else 0.
    step=math.sin(2*phase) if phase is not None else 0.
    offset=(right*.110+forward*.095-up*.018)*raised
    offset+=(right*(.005*side)+forward*(.007*step)-up*(.006*step))*raised
    rotation=Quaternion().slerp(Quaternion(right,math.radians(side))@Quaternion(up,math.radians(.6*step))@raise_q,raised)
    pivot=idle['hand_r'].translation
    carry=Matrix.Translation(pivot+offset)@rotation.to_matrix().to_4x4()@Matrix.Translation(-pivot)
    for n in names:
        if n.startswith('WPN_'):p[n]=carry@idle[n]
    arm(p,idle,'r',carry@idle['hand_r'])
    shoulder=source['upperarm_l'].translation
    clear=source['hand_l'].translation+(-right*.045-forward*.005-up*.055)*released
    a=(source['lowerarm_l'].translation-shoulder).length
    b=(source['hand_l'].translation-source['lowerarm_l'].translation).length
    dx=-.055-.004*side; dy=.015+.025*side; distance=.975*(a+b)
    target=shoulder+right*dx+forward*dy-up*math.sqrt(max(0.,distance*distance-dx*dx-dy*dy))
    v0=clear-shoulder; v1=target-shoulder; r0=v0.length; r1=v1.length
    d0=v0.normalized(); d1=v1.normalized(); axis=d0.cross(d1)
    direction=(d0.lerp(d1,withdrawn).normalized() if axis.length<1e-6 else Quaternion(axis.normalized(),d0.angle(d1)*withdrawn)@d0)
    direction=(direction-right*(.30*math.sin(math.pi*withdrawn))).normalized()
    location=shoulder+direction*(r0+(r1-r0)*(1-(1-withdrawn)**4))
    wrist_idle=source['lowerarm_l'].to_quaternion().inverted()@source['hand_l'].to_quaternion()
    wrist_rest=rest['lowerarm_l'].to_quaternion().inverted()@rest['hand_l'].to_quaternion()
    local_wrist=wrist_idle.slerp(wrist_rest,min(1.,.55*released+.40*withdrawn))
    arm_relax=smooth(0,.60,progress)
    arm(p,source,'l',Matrix.LocRotScale(location,source['hand_l'].to_quaternion(),source['hand_l'].to_scale()),arm_relax)
    wrist=p['lowerarm_l'].to_quaternion()@local_wrist
    arm(p,source,'l',Matrix.LocRotScale(location,wrist,source['hand_l'].to_scale()),arm_relax)
    for n in names:
        if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky')):
            local=source[parents[n]].inverted()@source[n]; pos,q,scale=local.decompose()
            relax=.60*released if '_metacarpal_' not in n else 0.
            p[n]=p[parents[n]]@Matrix.LocRotScale(pos,q.slerp(local_rest[n].to_quaternion(),relax),scale)
    # RifleHipFraming leaves this native shoulder 13.8 cm in front of the eye.
    # Dropping just elbow/wrist exposes the sleeve's clavicle/upper-arm end as
    # an upward hook. Withdraw the complete released left chain, including its
    # clavicle, towards the body. This is a rigid translation after the solve:
    # bone lengths, skin station alignment and wrist posture stay intact.
    # At progress zero every grip is exact; exit follows the same path backwards.
    shoulder_retract=smooth(.16,.78,progress)
    shoulder_shift=(-forward*.19-right*.08-up*.015)*shoulder_retract
    for n in names:
        if n.endswith('_l'):p[n].translation+=shoulder_shift
    return p

profiles={f:{'family':f,'clips':[]} for f in idles if f!='base'}
report={'source':'BenelliM4Super9020261006/Super90_Gameplay_Editable.blend','sample_rate':120,'runtime_tested':False,
        'revision':'ShoulderReturnR3-20261007','barrel':list(barrel),'clips':[],'families':list(profiles),
        'left_skin_stations':skin_stations,'evaluated_input_to_author_root':[list(row) for row in evaluation_to_author],
        'method':'Whole left shoulder/clavicle/arm return towards body; native anatomical hinge relaxation after release; existing gun and right arm motion',
        'shoulder_return_m':{'back':.19,'out':.08,'down':.015,'progress_window':[.16,.78]},
        'references':['Docs/Weapons/akm-sprint-left-wrist-relax-20260917.md','skills/ue5-fps-arms-animation/references/thrust-elbow-clearance.md','skills/ue5-fps-arms-animation/references/grip-arm-refinement.md#45']}
for kind,end in (('enter',18),('loop',36),('exit',18)):
    frames=[i*.5 for i in range(end*2+1)]; poses=[]; rows=[]
    for frame in frames:
        t=frame/end; progress=1. if kind=='loop' else 1-t if kind=='exit' else t
        p=pose(progress,2*math.pi*t if kind=='loop' else None); poses.append(p); row={}
        for n in names:
            local=local_rest[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])
            row[n]=local.decompose()
            if rows and rows[-1][n][1].dot(row[n][1])<0:row[n][1].negate()
        rows.append(row)
    name='A_Super90_sprint_'+kind; support.DURATION=end/60
    support.bake_action(rig,scene,name,rows,frames)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    file=X/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
    asset='/Game/Weapons/Super90/TacticalSprint20261007/Animations/'+name
    report['clips'].append({'name':name,'role':'sprint_'+kind,'file':str(file),'asset':asset,'duration':end/60})
    for family,payload in profiles.items():
        tracks={n:[] for n in names}; entry={'base':asset,'duration':end/60,'tracks':[]}
        for frame,base in zip(frames,poses):
            t=frame/end; progress=1. if kind=='loop' else 1-t if kind=='exit' else t
            adapted=pose(progress,2*math.pi*t if kind=='loop' else None,family)
            bu={n:C@base[n]@K[n] for n in names}; au={n:C@adapted[n]@K[n] for n in names}
            for n in names:
                parent=parents[n]; bb=bu[parent].inverted()@bu[n] if parent else bu[n]; aa=au[parent].inverted()@au[n] if parent else au[n]
                q=aa.to_quaternion()@bb.to_quaternion().inverted()
                if tracks[n] and q.dot(Quaternion((tracks[n][-1][6],*tracks[n][-1][3:6])))<0:q.negate()
                elif not tracks[n] and q.w<0:q.negate()
                tracks[n].append([*(aa.translation-bb.translation),q.x,q.y,q.z,q.w,*(aa.to_scale()-bb.to_scale())])
        zero=[0,0,0,0,0,0,1,0,0,0]
        for n,values in tracks.items():
            if all(max(abs(a-b) for a,b in zip(v,zero))<1e-5 for v in values):continue
            constant=all(max(abs(a-b) for a,b in zip(v,values[0]))<1e-6 for v in values)
            entry['tracks'].append({'bone':n,'times':[0.] if constant else [f/60 for f in frames],'values':values[0] if constant else [v for row in values for v in row]})
        payload['clips'].append(entry)
    print('SUPER90_SPRINT_AUTHORED',kind,end/60,flush=True)
for family,payload in profiles.items():(O/(family+'_profiles.json')).write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
rig.animation_data.action=bpy.data.actions['A_Super90_sprint_enter'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=18;scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_TacticalSprint_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
