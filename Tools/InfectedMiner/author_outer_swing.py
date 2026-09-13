"""Author one continuous exterior pickaxe orbit instead of shortest-arc flips.

Retain the current model, grip and body motion. The shaft/head share an
unwrapped swing angle; the full rigid tool guides the arm throughout recovery.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260913')
SOURCE=ROOT/'NaturalWrist/Delivery';OUT=ROOT/'OuterSwing/Delivery'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'InfectedMiner_Editable.blend'))
rig=bpy.data.objects['MinerRig'];scene=bpy.context.scene;scene.render.fps=30
rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
neutral=(rest['lowerarm_l'].inverted()@rest['hand_l']).to_quaternion()
forearm_axis=(rest['lowerarm_l'].inverted()@rest['hand_l'].translation).normalized()
ordered=sorted(rig.pose.bones,key=lambda b:len(b.parent_recursive))
helpers=['lowerarm_twist_02_l','lowerarm_twist_01_l','lowerarm_correctiveRoot_l']
head=bpy.data.objects['Pickaxe_ForgedHead']
head_local=[rest['hand_l'].inverted()@head.matrix_world@v.co for v in head.data.vertices]
source=bpy.data.actions['A_Miner_Attack']
source.name='Reference_NaturalWrist_Attack';source.use_fake_user=True
rig.animation_data.action=source;rig.animation_data.action_slot=source.slots[0]
scene.frame_set(1)

def world(name):return rig.matrix_world@rig.pose.bones[name].matrix
def put(name,p,q,s):
    rig.pose.bones[name].matrix=rig.matrix_world.inverted()@Matrix.LocRotScale(p,q,s)
    bpy.context.view_layer.update()
def canonical(q):
    q=q.normalized()
    if q.w<0:q.negate()
    return q
def twist(q,axis):
    q=canonical(q);part=axis*Vector((q.x,q.y,q.z)).dot(axis)
    result=Quaternion((q.w,*part))
    return canonical(result) if result.magnitude>1e-6 else Quaternion()
def signed(q,axis):
    q=canonical(q)
    return 2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)

start_hand=world('hand_l');start_w,start_q,start_scale=start_hand.decompose()
start_wrist=rig.pose.bones['hand_l'].rotation_quaternion.copy()
grip=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Review/Hand_UserAccepted_20260912/grip-authoring.json').read_text())
shaft_local=(rest['hand_l'].inverted().to_3x3()@Vector(grip['shaft'])).normalized()
start_axis=start_q@shaft_local
start_angle=math.degrees(math.atan2(start_axis.z,start_axis.y))
start_pose={b.name:b.matrix_basis.copy() for b in ordered}

# One turn in the exterior sagittal plane. Never slerp the beginning and end
# tool orientations directly: that would choose the path through the torso.
angle_keys=[(1,start_angle),(5,-28),(10,0),(14,28),(16,38),
            (19,100),(22,172),(25,211),(29,214),(34,230),(41,271),(48,303),(55,start_angle+360)]
roll_keys=[(1,0),(5,-65),(9,-130),(13,-155),(29,-155),(41,-155),(46,-115),(51,-35),(55,0)]
position_keys=[(1,tuple(start_w)),(5,(.43,.01,1.11)),(10,(.46,.05,1.57)),
               (14,(.42,.04,1.73)),(16,(.42,-.02,1.76)),(19,(.43,-.26,1.60)),
               (22,(.42,-.42,1.12)),(25,(.41,-.36,.85)),(29,(.42,-.35,.87)),
               (34,(.48,-.23,1.03)),(41,(.48,-.02,1.28)),(48,(.40,.01,1.13)),(55,tuple(start_w))]

def curve(keys,frame):
    # Monotone cubic Hermite interpolation prevents angle overshoot and
    # keeps angular velocity continuous through the authored waypoints.
    values=[Vector(v) if isinstance(v,tuple) else v for _,v in keys]
    for i in range(len(keys)-1):
        a,b=keys[i][0],keys[i+1][0]
        if frame>b:continue
        h=b-a;t=(frame-a)/h
        def tangent(k):
            if k in [0,len(keys)-1]:return values[k]*0
            left=(values[k]-values[k-1])/(keys[k][0]-keys[k-1][0])
            right=(values[k+1]-values[k])/(keys[k+1][0]-keys[k][0])
            if isinstance(left,Vector):return (left+right)*.5
            return 0 if left*right<=0 else 2*left*right/(left+right)
        return (2*t**3-3*t*t+1)*values[i]+(t**3-2*t*t+t)*h*tangent(i)+(-2*t**3+3*t*t)*values[i+1]+(t**3-t*t)*h*tangent(i+1)
    return values[-1]

def solve(frame):
    upper=world('upperarm_l');lower=world('lowerarm_l');hand=world('hand_l')
    s,uq,us=upper.decompose();e,lq,ls=lower.decompose();w,_,hs=hand.decompose()
    l1=(e-s).length;l2=(w-e).length
    angle=curve(angle_keys,frame)
    q=Quaternion(Vector((1,0,0)),math.radians(angle-start_angle))@start_q
    # Forearm turnover happens while the head stays outside/behind the body.
    # Its direction opens the elbow outwards; it never changes shaft heading.
    q=Quaternion(q@shaft_local,math.radians(curve(roll_keys,frame)))@q
    target=curve(position_keys,frame)
    desired_lq=q@(neutral@start_wrist).inverted()
    direction=(desired_lq@forearm_axis).normalized()
    head_offset=min((q@Vector(tuple(v[i]*hs[i] for i in range(3)))).z for v in head_local)
    # A forward contact at the existing frame, followed by lifting the head
    # clear before its low outside recovery arc.
    floor=.01
    if frame>=30:floor=.01+.13*math.sin(math.pi*min(1,(frame-30)/25))
    elbow_z=max(target.z,floor-head_offset)-direction.z*l2
    elbow_z=max(s.z-l1*.99,min(s.z+l1*.99,elbow_z))
    if 25<=frame<=29:elbow_z=max(s.z-l1*.99,min(s.z+l1*.99,floor-head_offset-direction.z*l2))
    def smooth(a,b):
        t=max(0,min(1,(frame-a)/(b-a)));return t*t*(3-2*t)
    exterior_x=start_w.x+(.36-start_w.x)*smooth(1,7)*(1-smooth(48,55))
    required_radius=max(0,exterior_x-s.x-direction.x*l2)
    if required_radius<l1:
        max_vertical=math.sqrt(l1*l1-required_radius*required_radius)
        elbow_z=s.z+max(-max_vertical,min(max_vertical,elbow_z-s.z))
    radius=math.sqrt(max(0,l1*l1-(elbow_z-s.z)**2))
    desired_e=target-direction*l2
    xy=Vector((desired_e.x-s.x,desired_e.y-s.y,0))
    if xy.length<1e-6:xy=Vector((1,0,0))
    xy.normalize()
    if radius>1e-6 and xy.x*radius<required_radius:
        x=min(.9999,required_radius/radius)
        xy=Vector((x,math.copysign(math.sqrt(1-x*x),xy.y),0))
    new_e=s+xy*radius+Vector((0,0,elbow_z-s.z))
    new_w=new_e+direction*l2
    parent=rig.pose.bones['upperarm_l'].parent.name
    neutral_upper=world(parent).to_quaternion()@(rest[parent].inverted()@rest['upperarm_l']).to_quaternion()
    upper_axis=(rest['upperarm_l'].inverted()@rest['lowerarm_l'].translation).normalized()
    new_uq=(neutral_upper@upper_axis).rotation_difference(new_e-s)@neutral_upper
    delta=new_uq@uq.inverted()
    base_lq=(delta@(w-e)).rotation_difference(direction)@delta@lq
    turn=twist(desired_lq@base_lq.inverted(),direction)
    pronation=signed(turn,direction)
    put('upperarm_l',s,new_uq,us);put('lowerarm_l',new_e,desired_lq,ls)
    for name in helpers:
        p,hq,scale=world(name).decompose()
        fraction=max(0,min(1,(p-new_e).dot(direction)/l2))
        put(name,p,Quaternion(direction,-pronation*(1-fraction))@hq,scale)
    bone=rig.pose.bones['hand_l'];p,_,scale=bone.matrix_basis.decompose()
    bone.matrix_basis=Matrix.LocRotScale(p,start_wrist,scale)
    bpy.context.view_layer.update()
    return {'frame':frame,'unwrapped_shaft_pitch_degrees':angle,'wrist':list(new_w)}

baked=[];samples=[]
for frame in range(1,56):
    rig.animation_data.action=source;rig.animation_data.action_slot=source.slots[0]
    scene.frame_set(frame);bpy.context.view_layer.update()
    samples.append(solve(frame))
    pose={b.name:b.matrix_basis.copy() for b in ordered}
    if frame in [1,55]:pose={n:m.copy() for n,m in start_pose.items()}
    baked.append(pose)
action=bpy.data.actions.new('A_Miner_Attack');action.use_fake_user=True
action.use_frame_range=True;action.frame_start=1;action.frame_end=55
rig.animation_data.action=action
for frame,pose in enumerate(baked,1):
    for bone in ordered:
        bone.matrix_basis=pose[bone.name];bone.rotation_mode='QUATERNION'
        for channel in ['location','rotation_quaternion','scale']:bone.keyframe_insert(channel,frame=frame)
    if action.slots:rig.animation_data.action_slot=action.slots[0]
scene.frame_start=1;scene.frame_end=55;scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'InfectedMiner_Editable.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_Miner_Attack.fbx'),use_selection=True,object_types={'ARMATURE'},
    add_leaf_bones=False,bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,
    bake_anim_use_all_actions=False,bake_anim_simplify_factor=0,axis_forward='-Y',axis_up='Z',apply_unit_scale=True)
report=json.loads((SOURCE/'rebuild.json').read_text())
report.pop('wrist_solver',None)
report.update({'version':'continuous outside pickaxe swing and recovery','source_editable':str(SOURCE/'InfectedMiner_Editable.blend'),
    'authored_changes':'continuous unwrapped weapon orbit and complete left arm; current idle/walk/body/grip retained',
    'weapon_angle_keys':angle_keys,'forearm_roll_keys':roll_keys,'wrist_position_keys':position_keys,'authoring_samples':samples,'gameplay_tested':False})
(OUT/'rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MINER_OUTER_SWING_AUTHORED',flush=True)
