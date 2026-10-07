"""Fit Mutant3's three pounce phases to M27, preserving its original V2 rig."""
from pathlib import Path
import json,math
import bpy
import numpy as np
from mathutils import Vector,Matrix,Quaternion

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
ROOT=BASE/'PounceV5';OUT=ROOT/'Delivery';OUT.mkdir(parents=True,exist_ok=True)
DATA=json.loads((ROOT/'native_pounce_poses.json').read_text())
FPS=60
bpy.ops.wm.open_mainfile(filepath=str(BASE/'BindingV2/Delivery/MantisM27_BindingV2.blend'))
scene=bpy.context.scene;scene.render.fps=FPS;scene.render.fps_base=1
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
body=next(o for o in bpy.data.objects if o.type=='MESH' and len(o.data.vertices)>100000)
names=[b.name for b in rig.data.bones]
parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
rig.animation_data.action=bpy.data.actions['A_M27_Idle_BindingV2']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(1)
idle={n:rig.pose.bones[n].matrix.copy() for n in names}
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
reflection=Matrix.Diagonal((1.,-1.,1.))
helpers=lambda n:n.startswith(('blade_','hand_','ball_','headfront','head_tip','chain_','membrane_'))

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)
def quat(data):return Quaternion(data['q'])
def pos(data):return Vector(data['p'])
def convert_delta(a,b):return (reflection@(quat(a)@quat(b).inverted()).to_matrix()@reflection).to_quaternion()

def build(rot,hip):
    result={}
    for n in names:
        m=result[parent[n]]@local[n] if parent[n] else local[n].copy()
        if n in rot:
            p=m.translation.copy();m=rot[n].to_matrix().to_4x4();m.translation=p
        if n=='pelvis':m.translation=hip
        result[n]=m
    return result

def blend(a,b,t):
    q={n:a[n].to_quaternion().slerp(b[n].to_quaternion(),t) for n in names if not helpers(n)}
    return build(q,a['pelvis'].translation.lerp(b['pelvis'].translation,t))

ref=DATA['clips']['PounceWindup']['reference']
raw={}
for role,data in DATA['clips'].items():
    frames=[]
    for source in data['frames']:
        rotations={n:convert_delta(source[n],ref[n])@rest[n].to_quaternion() for n in names if not helpers(n)}
        # Preserve the donor's pelvis compression and recoil in target centimeters.
        motion=reflection@(pos(source['pelvis'])-pos(ref['pelvis']))
        hip=rest['pelvis'].translation+motion
        frames.append(build(rotations,hip))
    raw[role]=frames

def sample(role,t):
    f=max(0,min(len(raw[role])-1,t*FPS));i=int(f);j=min(i+1,len(raw[role])-1)
    return blend(raw[role][i],raw[role][j],f-i)

# Foot-core offsets come from the preserved V2 weights. They are production
# constraints for the ground fit; the display mesh and weights are never edited.
weights=np.load(BASE/'BindingV2/binding_weights_v2.npz')
topology=np.load(BASE/'BindingV2/connected_source.npz')
points=topology['points'];ground=points[:,1].min()
points=np.column_stack((points[:,0],-points[:,2],points[:,1]-ground))*100
wi={n:i for i,n in enumerate(weights['names'])}
foot_offsets={};floor={}
for side in ['l','r']:
    n='foot_'+side;ids=weights['weights'][:,wi[n]]>.999
    inv=rest[n].inverted()
    foot_offsets[side]=np.asarray([inv@Vector(p) for p in points[ids]])
    m=np.asarray(idle[n]);floor[side]=float((foot_offsets[side]@m[:3,:3].T+m[:3,3])[:,2].min())

def ground_legs(m,role,time):
    rotations={n:v.to_quaternion() for n,v in m.items() if not helpers(n)}
    for side in ['l','r']:
        a,b,c=['%s_%s'%(part,side) for part in ['thigh','calf','foot']]
        original=raw[role][0][c].translation
        desired=m[c].translation-original
        target=idle[c].translation.copy();target.x+=desired.x*.35;target.y+=desired.y*.35
        footq=idle[c].to_quaternion().slerp(m[c].to_quaternion(),.28)
        rotated=foot_offsets[side]@np.asarray(footq.to_matrix()).T
        target.z=floor[side]-float(rotated[:,2].min())
        hip=m[a].translation;delta=target-hip;axis=delta.normalized()
        l1=(rest[b].translation-rest[a].translation).length;l2=(rest[c].translation-rest[b].translation).length
        distance=max(abs(l1-l2)+.01,min(delta.length,l1+l2-.01))
        pole=m[b].translation-hip;pole-=axis*pole.dot(axis)
        if pole.length<.01:pole=Vector((0,-1,0))-axis*Vector((0,-1,0)).dot(axis)
        pole.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
        knee=hip+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
        # Transport the donor knee plane with its segment rather than forcing
        # both knees into a fixed world axis during the torso rotation.
        rotations[a]=(m[b].translation-hip).rotation_difference(knee-hip)@m[a].to_quaternion()
        rotations[b]=(m[c].translation-m[b].translation).rotation_difference(target-knee)@m[b].to_quaternion()
        rotations[c]=footq
    return build(rotations,m['pelvis'].translation)

def fit_long_blades(m,active):
    # The inactive scythe follows the chest with a reduced counter-swing. Keep
    # all three active arm joints on the donor's common source time.
    inactive='r' if active=='l' else 'l'
    rotations={n:v.to_quaternion() for n,v in m.items() if not helpers(n)}
    for part in ['clavicle','upperarm','lowerarm']:
        n=part+'_'+inactive;p=parent[n]
        authored=m[p].to_quaternion().inverted()@m[n].to_quaternion()
        neutral=idle[p].to_quaternion().inverted()@idle[n].to_quaternion()
        qparent=rotations[p] if p in rotations else m[p].to_quaternion()
        rotations[n]=qparent@neutral.slerp(authored,.42)
    m=build(rotations,m['pelvis'].translation)
    # Raise a complete arm about its shoulder only when the much longer blade
    # would go below its ground-clearance plane. No wrist or blade bending.
    for side in ['l','r']:
        shoulder=m['upperarm_'+side].translation
        points=[m['blade_'+part+'_'+side].translation for part in ['root','mid','tip']]
        low=min(points,key=lambda p:p.z);v=low-shoulder
        clearance=14.
        if low.z<clearance and v.length>.01:
            elevation=math.asin(max(-1,min(1,v.z/v.length)))
            wanted=math.asin(max(-1,min(1,(clearance-shoulder.z)/v.length)))
            amount=wanted-elevation;axis=v.cross(Vector((0,0,1)))
            if axis.length>.01:
                turn=Quaternion(axis.normalized(),max(0,amount))
                for part in ['upperarm','lowerarm']:
                    n=part+'_'+side;rotations[n]=turn@m[n].to_quaternion()
                m=build(rotations,m['pelvis'].translation)
    return m

def clear_both_blades(m):
    rotations={n:v.to_quaternion() for n,v in m.items() if not helpers(n)}
    for side in ['l','r']:
        shoulder=m['upperarm_'+side].translation
        low=min((m['blade_'+part+'_'+side].translation for part in ['root','mid','tip']),key=lambda p:p.z)
        direction=low-shoulder
        if low.z<16. and direction.length>.01:
            axis=direction.cross(Vector((0,0,1)))
            elevation=math.asin(max(-1,min(1,direction.z/direction.length)))
            wanted=math.asin(max(-1,min(1,(16.-shoulder.z)/direction.length)))
            if axis.length>.01:
                turn=Quaternion(axis.normalized(),max(0,wanted-elevation))
                for part in ['upperarm','lowerarm']:
                    n=part+'_'+side;rotations[n]=turn@m[n].to_quaternion()
                m=build(rotations,m['pelvis'].translation)
    return m

manifest={'revision':'PounceV5','fps':FPS,'mesh_revision':'BindingV2','clips':{},
          'source_license':'Existing local Epic Paragon Khaimera / Mutant3 derivatives; UE-only; not CC0',
          'tested':False,'runtime_tested':False,'rendered':False,
          'design':'Whole-body pounce; bilateral scythes; grounded windup/landing; capsule owns airborne translation'}
for role in ['PounceWindup','PounceFlight','PounceLand']:
    duration=DATA['clips'][role]['seconds'];count=round(duration*FPS)+1
    action=bpy.data.actions.new('A_M27_'+role+'_PounceV5');action.use_fake_user=True
    rig.animation_data.action=action;scene.frame_start=1;scene.frame_end=count
    for i in range(count):
        t=min(i/FPS,duration);m=sample(role,t)
        if role=='PounceWindup' and t<.08:m=blend(idle,m,smooth(t/.08))
        if role=='PounceLand' and t>duration-.16:m=blend(m,idle,smooth((t-duration+.16)/.16))
        if role!='PounceFlight':m=clear_both_blades(ground_legs(m,role,t))
        else:
            # Body curl remains; world height comes exclusively from the real
            # CharacterMovement ballistic arc, not a second root/hip trajectory.
            rotations={n:v.to_quaternion() for n,v in m.items() if not helpers(n)}
            hip=m['pelvis'].translation.copy();hip.z=raw[role][0]['pelvis'].translation.z
            m=build(rotations,hip)
        for n in names:
            basis=local[n].inverted()@(m[parent[n]].inverted()@m[n] if parent[n] else m[n])
            pb=rig.pose.bones[n];pb.location=basis.translation;pb.rotation_mode='QUATERNION'
            q=basis.to_quaternion()
            if i and pb.rotation_quaternion.dot(q)<0:q.negate()
            pb.rotation_quaternion=q;pb.scale=(1,1,1)
            pb.keyframe_insert('location',frame=i+1,group=n);pb.keyframe_insert('rotation_quaternion',frame=i+1,group=n)
    scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    filename=action.name+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(OUT/filename),use_selection=True,object_types={'ARMATURE'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',global_scale=1,axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,
        bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    manifest['clips'][role]={'file':filename,'source':DATA['clips'][role]['source'],'seconds':duration,'frames':count}
    print('M27_POUNCE_V5_EXPORTED '+role,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MantisM27_PounceV5.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('M27_POUNCE_V5_AUTHORED',flush=True)
