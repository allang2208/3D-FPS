"""Repose the complete arm around the tool trajectory with a neutral wrist.

Use the current enlarged model unchanged. Elbow swivel and forearm pronation
carry the tool orientation; the hand joint is no longer an unrestricted IK end.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260913')
SOURCE=ROOT/'DragGround/Delivery';OUT=ROOT/'NaturalWrist/Delivery'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'InfectedMiner_Editable.blend'))
rig=bpy.data.objects['MinerRig'];scene=bpy.context.scene;scene.render.fps=30
rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
neutral=(rest['lowerarm_l'].inverted()@rest['hand_l']).to_quaternion()
forearm_axis=(rest['lowerarm_l'].inverted()@rest['hand_l'].translation).normalized()
wrist_axis=(neutral.inverted()@forearm_axis).normalized()
grip=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Review/Hand_UserAccepted_20260912/grip-authoring.json').read_text())
palm_local=rest['hand_l'].inverted()@Vector(grip['palm'])
shaft_local=(rest['hand_l'].inverted().to_3x3()@Vector(grip['shaft'])).normalized()
head=bpy.data.objects['Pickaxe_ForgedHead']
head_local=[rest['hand_l'].inverted()@head.matrix_world@v.co for v in head.data.vertices]
helpers=['lowerarm_twist_02_l','lowerarm_twist_01_l','lowerarm_correctiveRoot_l']
ordered=sorted(rig.pose.bones,key=lambda b:len(b.parent_recursive))
identity=Quaternion((1,0,0,0))

def canonical(q):
    q=q.normalized()
    if q.w<0:q.negate()
    return q

def twist(q,axis):
    q=canonical(q);part=axis*Vector((q.x,q.y,q.z)).dot(axis)
    result=Quaternion((q.w,*part))
    return canonical(result) if result.magnitude>1e-7 else identity.copy()

def angle(q):return canonical(q).angle

def signed(q,axis):
    q=canonical(q)
    return 2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)

def world(name):return rig.matrix_world@rig.pose.bones[name].matrix

def put(name,position,rotation,scale):
    rig.pose.bones[name].matrix=rig.matrix_world.inverted()@Matrix.LocRotScale(position,rotation,scale)
    bpy.context.view_layer.update()

def constrain_wrist(q):
    axial=twist(q,wrist_axis);swing=canonical(q@axial.inverted())
    if swing.angle>math.radians(18):swing=identity.slerp(swing,math.radians(18)/swing.angle)
    return swing@Quaternion(wrist_axis,max(-math.radians(4),min(math.radians(4),signed(axial,wrist_axis))))

def head_height(position,rotation,scale):
    row=rotation.to_matrix()[2]
    return position.z+min(sum(row[i]*v[i]*scale[i] for i in range(3)) for v in head_local)

def relax(previous):
    upper=world('upperarm_l');lower=world('lowerarm_l');hand=world('hand_l')
    s,uq,us=upper.decompose();e,lq,ls=lower.decompose();w,hq,hs=hand.decompose()
    upper_len=(e-s).length;lower_len=(w-e).length
    axis=hq@shaft_local
    original_height=head_height(w,hq,hs)
    best=None
    bend_axis=wrist_axis.cross(shaft_local).normalized()
    # Solve a neutral wrist first. For each nearby tool pitch, the forearm
    # direction is known; the elbow then lies on the upper-arm reach circle.
    # This preserves bone lengths and head height without twisting the wrist.
    # Keep the same pointed end and palm side for every frame and state.
    for roll in [0]:
        rolled_q=Quaternion(axis,roll)@hq
        pitch_axis=(rolled_q@shaft_local).cross(Vector((0,0,1)))
        if pitch_axis.length<1e-6:pitch_axis=Vector((1,0,0))
        pitch_axis.normalize()
        for pitch in range(-60,61,3):
            goal_q=Quaternion(pitch_axis,math.radians(pitch))@rolled_q
            head_offset=head_height(Vector((0,0,0)),goal_q,hs)
            for flex in [-10,0,10]:
                wrist_q=Quaternion(bend_axis,math.radians(flex))
                desired_lq=goal_q@(neutral@wrist_q).inverted()
                forearm=(desired_lq@forearm_axis).normalized()
                elbow_z=original_height-head_offset-forearm.z*lower_len
                vertical=elbow_z-s.z
                if abs(vertical)>upper_len*.995:continue
                radius=math.sqrt(upper_len**2-vertical**2)
                old_xy=Vector((w.x-forearm.x*lower_len-s.x,w.y-forearm.y*lower_len-s.y,0))
                if old_xy.length<1e-6:old_xy=Vector((1,0,0))
                old_xy.normalize()
                for swivel in [-20,0,20]:
                    xy=Quaternion(Vector((0,0,1)),math.radians(swivel))@old_xy
                    new_e=s+xy*radius+Vector((0,0,vertical))
                    goal_w=new_e+forearm*lower_len
                    arm_delta=(e-s).rotation_difference(new_e-s)
                    new_uq=arm_delta@uq
                    current_forearm=arm_delta@(w-e)
                    base_lq=current_forearm.rotation_difference(forearm)@arm_delta@lq
                    turn=twist(desired_lq@base_lq.inverted(),forearm)
                    pronation=signed(turn,forearm)
                    cost=((goal_w-w).length/.16)**2+.30*((new_e-e).length/upper_len)**2
                    cost+=30*max(0,abs(pronation)-math.radians(80))**2
                    cost+=.12*(pitch/45)**2+.06*(flex/10)**2
                    cost+=80*max(0,s.x-.04-new_e.x)**2
                    if previous:
                        cost+=.5*((new_e-previous['elbow']).length/upper_len)**2
                        cost+=.8*angle(previous['hand'].inverted()@goal_q)**2
                    if best is None or cost<best[0]:
                        best=(cost,new_e,goal_w,new_uq,desired_lq,wrist_q,pronation,forearm,base_lq,angle(wrist_q),roll)
    if best is None:raise RuntimeError('No reachable natural wrist pose at frame '+str(scene.frame_current))
    _,new_e,new_w,new_uq,new_lq,wrist_q,pronation,forearm,untwisted,residual,roll=best
    put('upperarm_l',s,new_uq,us)
    put('lowerarm_l',new_e,new_lq,ls)
    # Spread the additional pronation along the existing Manny twist bones.
    for name in helpers:
        matrix=world(name);p,q,scale=matrix.decompose()
        fraction=max(0,min(1,(p-new_e).dot(forearm)/lower_len))
        q=Quaternion(forearm,-pronation*(1-fraction))@q
        put(name,p,q,scale)
    bone=rig.pose.bones['hand_l'];p,_,scale=bone.matrix_basis.decompose()
    limited=constrain_wrist(wrist_q)
    bone.matrix_basis=Matrix.LocRotScale(p,limited,scale)
    bpy.context.view_layer.update()
    return {'elbow':new_e.copy(),'hand':world('hand_l').to_quaternion()},math.degrees(residual),math.degrees(angle(limited)),math.degrees(pronation),int(round(roll/math.pi))

actions={state:bpy.data.actions['A_Miner_'+state] for state in ['Idle','Walk','Attack']}
for state,action in actions.items():action.name='Reference_DragGround_'+state;action.use_fake_user=True
output={};records={};idle_start=None
for state,source in actions.items():
    count=round(source.frame_range[1]-1);baked=[];previous=None;stats=[]
    for frame in range(1,count+2):
        rig.animation_data.action=source;rig.animation_data.action_slot=source.slots[0]
        scene.frame_set(frame);bpy.context.view_layer.update()
        previous,*values=relax(previous);stats.append(values)
        pose={b.name:b.matrix_basis.copy() for b in ordered}
        if state=='Attack' and frame in [1,count+1]:
            for name in pose:
                if name.startswith(('upperarm_l','lowerarm','hand_l')) and (name.endswith('_l') or name=='upperarm_l'):pose[name]=idle_start[name].copy()
        if state!='Attack' and frame==count+1:pose={n:m.copy() for n,m in baked[0].items()}
        baked.append(pose)
    if state=='Idle':idle_start=baked[0]
    arm_names=[n for n in baked[0] if n=='upperarm_l' or (n.startswith(('lowerarm','hand_l')) and n.endswith('_l'))]
    smoothed=[{n:m.copy() for n,m in pose.items()} for pose in baked]
    # Smooth the small search increments in local rotation space. Local joint
    # translations and lengths remain untouched; loop samples wrap in time.
    for i,pose in enumerate(baked):
        for name in arm_names:
            p,center,scale=pose[name].decompose();total=Vector((0,0,0,0))
            for offset,weight in [(-2,1),(-1,2),(0,3),(1,2),(2,1)]:
                j=(i+offset)%count if state!='Attack' else max(0,min(count,i+offset))
                q=baked[j][name].to_quaternion()
                if q.dot(center)<0:q.negate()
                total+=Vector(tuple(q))*weight
            smoothed[i][name]=Matrix.LocRotScale(p,Quaternion(tuple(total)).normalized(),scale)
    baked=smoothed
    if state!='Attack':baked[-1]={n:m.copy() for n,m in baked[0].items()}
    if state=='Idle':idle_start=baked[0]
    if state=='Attack':
        for edge in ['start','end']:
            for step in range(5):
                index=step if edge=='start' else count-step
                weight=1-step/4;weight=weight*weight*(3-2*weight)
                for name in arm_names:
                    p,q,scale=baked[index][name].decompose()
                    baked[index][name]=Matrix.LocRotScale(p,q.slerp(idle_start[name].to_quaternion(),weight),scale)
    action=bpy.data.actions.new('A_Miner_'+state);action.use_fake_user=True
    action.use_frame_range=True;action.frame_start=1;action.frame_end=count+1
    rig.animation_data.action=action
    for frame,pose in enumerate(baked,1):
        for bone in ordered:
            bone.matrix_basis=pose[bone.name];bone.rotation_mode='QUATERNION'
            for channel in ['location','rotation_quaternion','scale']:bone.keyframe_insert(channel,frame=frame)
        if action.slots:rig.animation_data.action_slot=action.slots[0]
    output[state]=action
    records[state]={'max_requested_wrist_degrees':max(row[0] for row in stats),
        'max_baked_wrist_degrees':max(row[1] for row in stats),'max_forearm_transfer_degrees':max(abs(row[2]) for row in stats),
        'solver_samples':stats}
rig.animation_data.action=output['Attack'];rig.animation_data.action_slot=output['Attack'].slots[0]
scene.frame_start=1;scene.frame_end=55;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'InfectedMiner_Editable.blend'))
# Animation-only FBXs reuse the current enlarged skeletal mesh in UE.
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
for state,action in output.items():
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    scene.frame_start=1;scene.frame_end=round(action.frame_range[1]);scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(OUT/f'A_Miner_{state}.fbx'),use_selection=True,object_types={'ARMATURE'},
        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True)
report=json.loads((SOURCE/'rebuild.json').read_text())
report.update({'version':'neutral-wrist arm reconstruction for drag carry and ground slam',
    'source_editable':str(SOURCE/'InfectedMiner_Editable.blend'),
    'authored_changes':'neutral wrist first, reachable elbow and forearm, distributed twist; up to 10 degrees relaxed wrist bend; local rotation smoothing; tool head height retained before smoothing',
    'geometry_bind_skin_materials_changed':False,'wrist_solver':records,'gameplay_tested':False})
(OUT/'rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MINER_WRIST_REBUILT '+json.dumps({state:{k:v for k,v in data.items() if k!='solver_samples'} for state,data in records.items()}),flush=True)
