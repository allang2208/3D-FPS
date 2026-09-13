"""Extend the accepted mining motion with a trailing carry and ground follow-through.

The accepted bind, weights and grouped finger grip remain the source. This is
an authored adaptation of the accepted EBS composite, not new mocap footage.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260913')
SOURCE=ROOT/'PickaxeSingleHand/Delivery'
OUT=ROOT/'DragGround/Delivery';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'InfectedMiner_Editable.blend'))
rig=bpy.data.objects['MinerRig'];scene=bpy.context.scene;scene.render.fps=30
grip=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Review/Hand_UserAccepted_20260912/grip-authoring.json').read_text())
pivot=Vector(grip['palm']);shaft=Vector(grip['shaft']).normalized()
for obj in scene.objects:
    if obj.type=='MESH' and obj.name.startswith('Pickaxe_'):
        transform=obj.matrix_world.inverted()@Matrix.Translation(pivot)@Matrix.Scale(1.25,4)@Matrix.Translation(-pivot)@obj.matrix_world
        for vertex in obj.data.vertices:vertex.co=transform@vertex.co
        obj.data.update()
hand_rest=rig.matrix_world@rig.data.bones['hand_l'].matrix_local
shaft_local=(hand_rest.inverted().to_3x3()@shaft).normalized()
point_axis=Quaternion(shaft,math.pi/2)@Vector(grip['working_point_axis'])
point_local=(hand_rest.inverted().to_3x3()@point_axis).normalized()
head=bpy.data.objects['Pickaxe_ForgedHead']
head_local=[hand_rest.inverted()@head.matrix_world@v.co for v in head.data.vertices]
arm_names=['upperarm_l','lowerarm_l','hand_l']
ordered=sorted(rig.pose.bones,key=lambda b:len(b.parent_recursive))
sources={state:bpy.data.actions['A_Miner_'+state] for state in ['Idle','Walk','Attack']}
for state,action in sources.items():action.name='Reference_Pickaxe_'+state;action.use_fake_user=True

def set_action(action):
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]

def smooth(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)

def blend_matrix(a,b,t):
    ap,aq,az=a.decompose();bp,bq,bz=b.decompose()
    return Matrix.LocRotScale(ap.lerp(bp,t),aq.slerp(bq,t),az.lerp(bz,t))

def world(name):return rig.matrix_world@rig.pose.bones[name].matrix

def set_world(name,matrix):
    rig.pose.bones[name].matrix=rig.matrix_world.inverted()@matrix
    bpy.context.view_layer.update()

def point_bone(name,child,target):
    matrix=world(name);position,rotation,scale=matrix.decompose()
    before=world(child).translation-position;after=target-position
    set_world(name,Matrix.LocRotScale(position,before.rotation_difference(after)@rotation,scale))

def solve_arm(target):
    shoulder=world('upperarm_l').translation
    elbow=world('lowerarm_l').translation;wrist=world('hand_l').translation
    upper=(elbow-shoulder).length;lower=(wrist-elbow).length
    direction=(target-shoulder).normalized()
    distance=min((target-shoulder).length,upper+lower-.012)
    target=shoulder+direction*distance
    pole=Vector((.55,-.25,1.1))-shoulder
    across=(pole-direction*pole.dot(direction)).normalized()
    projection=(upper*upper+distance*distance-lower*lower)/(2*distance)
    height=math.sqrt(max(0,upper*upper-projection*projection))
    desired_elbow=shoulder+direction*projection+across*height
    point_bone('upperarm_l','lowerarm_l',desired_elbow)
    point_bone('lowerarm_l','hand_l',target)

def place_tip(horizontal,floor):
    matrix=world('hand_l');position,reference,scale=matrix.decompose()
    horizontal=Vector(horizontal).normalized()
    def pose(angle):
        axis=horizontal*math.cos(angle)+Vector((0,0,math.sin(angle)))
        rotation=(reference@shaft_local).rotation_difference(axis)@reference
        desired=Vector((0,0,-1))-axis*Vector((0,0,-1)).dot(axis)
        desired.normalize();current=(rotation@point_local).normalized()
        if desired.dot(current)<0:desired=-desired
        turn=math.atan2(axis.dot(current.cross(desired)),current.dot(desired))
        rotation=Quaternion(axis,turn)@rotation
        result=Matrix.LocRotScale(position,rotation,scale)
        lowest=min((result@point).z for point in head_local)
        return result,lowest
    low,high=math.radians(-65),math.radians(20)
    for _ in range(18):
        angle=(low+high)/2;matrix,height=pose(angle)
        if height<floor:low=angle
        else:high=angle
    set_world('hand_l',pose((low+high)/2)[0])

def arm_layer(kind,alpha,floor=.025):
    if alpha<=0:return
    before={name:rig.pose.bones[name].matrix_basis.copy() for name in arm_names}
    shoulder=world('upperarm_l').translation
    target=shoulder+Vector((.14,.12,-.46)) if kind=='drag' else shoulder+Vector((.035,-.21,-.46))
    solve_arm(target)
    place_tip((.04,1,0) if kind=='drag' else (0,-1,0),floor)
    after={name:rig.pose.bones[name].matrix_basis.copy() for name in arm_names}
    for name in arm_names:rig.pose.bones[name].matrix_basis=blend_matrix(before[name],after[name],alpha)
    bpy.context.view_layer.update()

def body_follow(alpha):
    if alpha<=0:return
    # Hinge the existing upper body forward from the waist; planted feet and
    # original leg motion remain intact, rather than lowering the whole mesh.
    matrix=world('spine_01');p,q,s=matrix.decompose()
    set_world('spine_01',Matrix.LocRotScale(p,Quaternion(Vector((1,0,0)),math.radians(25)*alpha)@q,s))

output={};idle_start=None
for state in ['Idle','Walk','Attack']:
    source=sources[state];count=round(source.frame_range[1]-source.frame_range[0])
    baked=[]
    for frame in range(1,count+2):
        set_action(source);scene.frame_set(frame);bpy.context.view_layer.update()
        if state in ['Idle','Walk']:
            arm_layer('drag',1,.025)
        else:
            ground=smooth(16,25,frame)*(1-smooth(29,40,frame))
            body_follow(smooth(16,25,frame)*(1-smooth(30,45,frame)))
            arm_layer('ground',ground,.005+.22*smooth(29,37,frame))
            drag=(1-smooth(1,9,frame))+smooth(36,55,frame)
            arm_layer('drag',drag,.025+.20*smooth(35,40,frame)*(1-smooth(45,55,frame)))
        pose={b.name:b.matrix_basis.copy() for b in ordered}
        if state=='Attack':
            # Exact carry endpoints and a gentle return to that full-body pose.
            if frame==1:pose={n:m.copy() for n,m in idle_start.items()}
            elif frame>=50:pose={n:blend_matrix(m,idle_start[n],smooth(50,55,frame)) for n,m in pose.items()}
        if frame==count+1 and state in ['Idle','Walk']:pose={n:m.copy() for n,m in baked[0].items()}
        baked.append(pose)
    if state=='Idle':idle_start=baked[0]
    action=bpy.data.actions.new('A_Miner_'+state);action.use_fake_user=True
    action.use_frame_range=True;action.frame_start=1;action.frame_end=count+1
    set_action(action)
    for frame,pose in enumerate(baked,1):
        for bone in ordered:
            bone.matrix_basis=pose[bone.name];bone.rotation_mode='QUATERNION'
            for channel in ['location','rotation_quaternion','scale']:bone.keyframe_insert(channel,frame=frame)
        if action.slots:rig.animation_data.action_slot=action.slots[0]
    output[state]=action
set_action(output['Attack']);scene.frame_start=1;scene.frame_end=55;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'InfectedMiner_Editable.blend'))

# Preserve the accepted vertex-color selection when exporting the unchanged skin.
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
for obj in scene.objects:
    if obj.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in obj.modifiers):
        obj.select_set(True)
        if obj.data.color_attributes.get('MinerForearmColor'):
            for attribute in list(obj.data.color_attributes):
                if attribute.name!='MinerForearmColor':obj.data.color_attributes.remove(attribute)
            obj.data.color_attributes.active_color_name='MinerForearmColor'
bpy.context.view_layer.objects.active=rig
def export(path,animated):
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,bake_anim=animated,bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_mesh_modifiers=True,mesh_smooth_type='FACE')
rig.animation_data.action=None
for bone in rig.pose.bones:bone.matrix_basis.identity()
bpy.context.view_layer.update();export(OUT/'SK_InfectedMiner_DragGround.fbx',False)
for state,action in output.items():
    set_action(action);scene.frame_start=1;scene.frame_end=round(action.frame_range[1]);scene.frame_set(1)
    export(OUT/f'A_Miner_{state}.fbx',True)
contract={'version':'accepted single-hand mining swing with trailing carry and ground follow-through',
    'source_editable':str(SOURCE/'InfectedMiner_Editable.blend'),
    'pickaxe_scale':1.25,'handle_length_m':1.2,'head_span_m':.9,
    'preserved':'body/hand geometry, rest skeleton, skin weights, finger grip, materials; accepted windup source',
    'authored_changes':'left arm carry and ground reach, upper-body forward follow-through, carry endpoints',
    'contact_time':22/30,'contact_end':25/30,'ground_contact_time':24/30,
    'state_blend_seconds':.16,'ground_reference':'flat local ground; not runtime terrain-conforming IK',
    'clips':{state:{'seconds':(action.frame_range[1]-1)/30,'loop':state!='Attack'} for state,action in output.items()},
    'gameplay_tested':False}
(OUT/'rebuild.json').write_text(json.dumps(contract,indent=2),encoding='utf-8')
print('MINER_DRAG_GROUND_AUTHORED '+json.dumps(contract),flush=True)
