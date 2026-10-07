"""M27 horizontal hook cuts derived from the accepted forward-reaching V14.

Authoring only: no validation renders or gameplay tests. The blade's inner curve
leads the lateral sweep; both shoulders and elbows remain coherent rigid chains.
"""
from pathlib import Path
import json
import math
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27')
ROOT=BASE/'ClawV16'; OUT=ROOT/'Delivery'; OUT.mkdir(parents=True,exist_ok=True)
SOURCE=BASE/'ClawV3/Delivery'
source_manifest=json.loads((SOURCE/'motion_manifest.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'MantisM27_ClawV3.blend'))
scene=bpy.context.scene; FPS=60; DURATION=.65; COUNT=40
scene.render.fps=FPS;scene.render.fps_base=1.
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
for track in rig.animation_data.nla_tracks:track.mute=True
names=[b.name for b in rig.data.bones]
parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local={n:rest[parent[n]].inverted()@rest[n] if parent[n] else rest[n] for n in names}
rig.animation_data.action=bpy.data.actions['A_M27_LeftSlash_ClawV3']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(1)
idle={n:rig.pose.bones[n].matrix.copy() for n in names}
weights=np.load(BASE/'BindingV2/binding_weights_v2.npz')
topology=np.load(BASE/'BindingV2/connected_source.npz')
p=topology['points']
points=np.column_stack((p[:,0],-p[:,2],p[:,1]-p[:,1].min()))*100.
wi={n:i for i,n in enumerate(weights['names'])}
frames={};cages={}
for side in ['l','r']:
    n='blade_root_'+side
    cloud=points[weights['weights'][:,wi[n]]>.999]
    normal=Vector(np.linalg.svd(cloud-cloud.mean(axis=0),full_matrices=False)[2][-1])
    chord=rest['blade_tip_'+side].translation-rest[n].translation
    chord=(chord-normal*chord.dot(normal)).normalized()
    bulge=rest['blade_mid_'+side].translation-rest[n].translation
    bend=normal.cross(chord).normalized()
    if bend.dot(bulge)<0:bend.negate()
    # Convex bulge is +bend; the concave cutting side is -bend. This sign was
    # missing from V12's unsigned-plane/midpoint constraint.
    frames[side]=(chord,bend)
    inverse=np.asarray(rest[n].inverted())
    cloud=cloud@inverse[:3,:3].T+inverse[:3,3]
    principal=np.linalg.svd(cloud-cloud.mean(axis=0),full_matrices=False)[2][0]
    distance=cloud@principal
    bins=np.minimum(13,((distance-distance.min())/max(.01,np.ptp(distance))*14).astype(int))
    cage=[]
    for k in range(14):
        section=cloud[bins==k]
        if not len(section):continue
        lo,hi=section.min(axis=0),section.max(axis=0)
        cage.extend(Vector((x,y,z)) for x in [lo[0],hi[0]] for y in [lo[1],hi[1]] for z in [lo[2],hi[2]])
    cages[side]=cage

def clamp(x):return min(1.,max(0.,x))
def smooth(x):
    x=clamp(x);return x*x*(3.-2.*x)
def hermite(a,b,ma,mb,x):
    x=clamp(x)
    return (2*x**3-3*x*x+1)*a+(x**3-2*x*x+x)*ma+(-2*x**3+3*x*x)*b+(x**3-x*x)*mb
def cut_progress(t):
    x=clamp((t-.195)/.080)
    # Zero launch speed, acceleration through entry, peak during contact.
    # The final derivative remains nonzero and feeds the braking segment.
    return x*x*(2.-x)
def power(t):
    return smooth(t/.18)-2.10*smooth((t-.177)/.105)+1.10*smooth((t-.34)/.31)
def drive(t):
    return smooth((t-.165)/.10)*(1.-smooth((t-.34)/.31))
def horizontal_bank(t):
    # Roll the signed cutting frame during loading, before acceleration. Return
    # to the accepted guard only during recovery, not while the edge is cutting.
    return math.radians(72.)*smooth(t/.18)*(1.-smooth((t-.35)/.30))
def sweep_lane(t):
    # The leading blade gets the front lane; the other stays behind it. This
    # authored plane turns continuously after loading, permitting a real cross-
    # body arc instead of clipping the active blade to its original body half.
    return smooth((t-.175)/.060)*(1.-smooth((t-.35)/.30))
def stroke_angle(t):
    if t<=.18:return -40.+104.*smooth(t/.18)
    if t<=.195:return 64.
    if t<=.275:return 64.-92.*cut_progress(t)
    if t<=.315:
        # Match the incoming -1150 deg/s, then brake to zero in 40 ms.
        return hermite(-28.,-48.,-46.,0.,(t-.275)/.04)
    if t<=.35:return -48.+5.*smooth((t-.315)/.035)
    return -43.+3.*smooth((t-.35)/.30)
def elbow_flex(side,active,t):
    if side==active:
        return 28.+20.*smooth(t/.18)-44.*smooth((t-.175)/.10)+14.*smooth((t-.275)/.07)+10.*smooth((t-.35)/.30)
    return 28.+19.*smooth((t-.10)/.12)*(1.-smooth((t-.32)/.28))

def body_pose(active,t):
    sign=1. if active=='l' else -1.
    wave=power(t);thrust=drive(t);m={}
    for n in names:
        relative=idle[parent[n]].inverted()@idle[n] if parent[n] else idle[n].copy()
        pose=m[parent[n]]@relative if parent[n] else relative
        if n=='pelvis':
            position=pose.translation+Vector((sign*3.*wave,-20.*thrust,-8.*thrust))
            pose=(Quaternion((0,0,1),math.radians(sign*9.*wave))@pose.to_quaternion()).to_matrix().to_4x4()
            pose.translation=position
        elif n in ['spine_01','spine_02','spine_03']:
            weight={'spine_01':.40,'spine_02':.36,'spine_03':.24}[n]
            turn=Quaternion((0,0,1),math.radians(sign*42.*wave*weight))@Quaternion((1,0,0),math.radians((12.+20.*thrust)*weight))
            position=pose.translation.copy();pose=(turn@pose.to_quaternion()).to_matrix().to_4x4();pose.translation=position
        elif n=='head':
            turn=Quaternion((0,0,1),math.radians(-sign*30.*wave))@Quaternion((1,0,0),math.radians(-12.*thrust))
            position=pose.translation.copy();pose=(turn@pose.to_quaternion()).to_matrix().to_4x4();pose.translation=position
        m[n]=pose
    # Preserve the planted support feet while the hips compress and drive.
    rotations={}
    for side in ['l','r']:
        a,b,c=[part+'_'+side for part in ['thigh','calf','foot']]
        hip=m[a].translation;target=idle[c].translation;axis=(target-hip).normalized()
        l1=(rest[b].translation-rest[a].translation).length;l2=(rest[c].translation-rest[b].translation).length
        distance=max(abs(l1-l2)+.01,min((target-hip).length,l1+l2-.01))
        pole=m[b].translation-hip;pole-=axis*pole.dot(axis);pole.normalize()
        along=(l1*l1-l2*l2+distance*distance)/(2.*distance)
        knee=hip+axis*along+pole*math.sqrt(max(0.,l1*l1-along*along))
        rotations[a]=(m[b].translation-hip).rotation_difference(knee-hip)@m[a].to_quaternion()
        rotations[b]=(m[c].translation-m[b].translation).rotation_difference(target-knee)@m[b].to_quaternion()
        rotations[c]=idle[c].to_quaternion()
    result={}
    for n in names:
        relative=m[parent[n]].inverted()@m[n] if parent[n] else m[n]
        pose=result[parent[n]]@relative if parent[n] else relative.copy()
        if n in rotations:
            position=pose.translation.copy();pose=rotations[n].to_matrix().to_4x4();pose.translation=position
        result[n]=pose
    return result

def flex_forearms(m,active,t):
    turns={}
    for side in ['l','r']:
        chord,bend=frames[side]
        current=m['blade_root_'+side].to_quaternion()@rest['blade_root_'+side].to_quaternion().inverted()
        hinge=(current@chord).cross(current@bend).normalized()
        turns['lowerarm_'+side]=Quaternion(hinge,math.radians(elbow_flex(side,active,t)))
    result={}
    for n in names:
        relative=m[parent[n]].inverted()@m[n] if parent[n] else m[n]
        pose=result[parent[n]]@relative if parent[n] else relative.copy()
        if n in turns:
            position=pose.translation.copy();pose=(turns[n]@pose.to_quaternion()).to_matrix().to_4x4();pose.translation=position
        result[n]=pose
    return result

def axes(a,b):
    a=a.normalized();b=(b-a*b.dot(a)).normalized()
    return Matrix((a,b,a.cross(b))).transposed().to_quaternion()

def arm_turn(m,side,active,t):
    sign=1. if side=='l' else -1.
    if side==active:
        angle=stroke_angle(t)
        # Outside loaded blade -> front crossing -> opposite-side follow-through.
        yaw=28.-28.*smooth((t-.175)/.060)+28.*smooth((t-.34)/.31)
    else:
        withdraw=smooth((t-.10)/.115)*(1.-smooth((t-.32)/.30))
        angle=-40.-23.*withdraw
        yaw=28.+18.*withdraw
    yaw=math.radians(yaw);theta=math.radians(angle)
    forward=Vector((sign*math.sin(yaw),-math.cos(yaw),0.))
    outward=Vector((sign*math.cos(yaw),math.sin(yaw),0.))
    if side==active:
        bank=horizontal_bank(t)
        # Preserve the exact V14 guard at both ends. At full load the cutting
        # plane is almost horizontal, with a slight downward rake for weight.
        guard_tilt=math.atan(.12)
        tilt=guard_tilt+(bank/math.radians(72.))*(math.radians(72.)-guard_tilt)
        diagonal=Vector((0,0,1))*math.cos(tilt)+outward*math.sin(tilt)
    else:
        diagonal=(Vector((0,0,1))+.12*outward).normalized()
    goal_chord=forward*math.cos(theta)+diagonal*math.sin(theta)
    goal_bend=-forward*math.sin(theta)+diagonal*math.cos(theta)
    # For decreasing theta the chord velocity is -bend. Banking the full
    # signed frame keeps the inner edge leading as the cut becomes lateral.
    current=m['blade_root_'+side].to_quaternion()@rest['blade_root_'+side].to_quaternion().inverted()
    chord,bend=frames[side]
    return axes(goal_chord,goal_bend)@axes(current@chord,current@bend).inverted()

def fit_arm(m,side,turn,active,t):
    shoulder=m['upperarm_'+side].translation
    vectors=[m['blade_root_'+side]@p-shoulder for p in cages[side]]
    sign=1. if side=='l' else -1.
    lane=sweep_lane(t)
    active_sign=1. if active=='l' else -1.
    separation=Vector((active_sign*math.cos(lane*math.pi*.5),-math.sin(lane*math.pi*.5),0.))
    side_sign=1. if side==active else -1.
    normal=separation*side_sign
    lane_center=Vector((0.,-55.*lane,0.))
    planes=[(normal,normal.dot(lane_center)+16.),(Vector((0,0,1)),10.)]
    # The front lane is fully established before the retained contact window;
    # its counterpart holds the entire inactive blade behind the sweep.
    for _ in range(36):
        settled=True
        for normal,plane in planes:
            low=min((turn@p for p in vectors),key=lambda p:p.dot(normal))
            bound=plane-shoulder.dot(normal)
            if low.dot(normal)>=bound-.01:continue
            settled=False
            angle=math.acos(max(-1.,min(1.,low.dot(normal)/low.length)))
            desired=math.acos(max(-1.,min(1.,(bound+.06)/low.length)))
            axis=low.cross(normal)
            if axis.length<1.e-5:axis=Vector((1,0,0))
            turn=Quaternion(axis.normalized(),max(0.,angle-desired))@turn
        if settled:break
    return turn.normalized()

manifest={**source_manifest,'revision':'ClawV16','fps':FPS,'duration_seconds':DURATION,
          'method':'Accepted V14 forward reach and timing; signed cutting frame banked for horizontal cross-body hooks; hip/torso windup and rear guard lane',
          'accepted_animation_baseline':'ClawV14',
          'horizontal_authoring':{'cutting_plane_from_vertical_degrees':72.,'pelvis_yaw_degrees':9.,
                                  'spine_yaw_degrees':42.,'front_guard_separation_cm':32.},
          'forward_reach_authoring':{'pelvis_forward_cm':20.,'pelvis_sink_cm':8.,
                                     'spine_extra_pitch_degrees':20.,'primary_elbow_minimum_degrees':4.,
                                     'phase_times':'unchanged from accepted ClawV14'},
          'contact_window_seconds':[.250,.300],'recovery_time_seconds':.10,
          'phase_seconds':{'load':[0.,.180],'suspension':[.180,.195],'accelerating_cut':[.195,.275],
                           'braking':[.275,.315],'recoil':[.315,.350],'return':[.350,.650]},
          'edited_rotation_tracks':['pelvis','spine_01','spine_02','spine_03','head','thigh_l','thigh_r','calf_l','calf_r',
                                    'foot_l','foot_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r'],
          'nonlinear_timing_baked':True,'runtime_tested':False,'rendered':False,'clips':{}}
for role,active in [('LeftSlash','l'),('RightSlash','r')]:
    action=bpy.data.actions.new('A_M27_'+role+'_ClawV16');action.use_fake_user=True
    rig.animation_data.action=action;scene.frame_start=1;scene.frame_end=COUNT
    previous={}
    for i in range(COUNT):
        t=i/FPS;m=flex_forearms(body_pose(active,t),active,t)
        bases={n:local[n].inverted()@(m[parent[n]].inverted()@m[n] if parent[n] else m[n]) for n in names}
        for side in ['l','r']:
            n='upperarm_'+side;pose=m[n]
            turn=fit_arm(m,side,arm_turn(m,side,active,t),active,t)
            rotated=(turn@pose.to_quaternion()).to_matrix().to_4x4();rotated.translation=pose.translation
            relative=local[n].inverted()@m[parent[n]].inverted()@rotated
            bases[n]=Matrix.LocRotScale(bases[n].translation,relative.to_quaternion(),bases[n].to_scale())
        for n in names:
            pb=rig.pose.bones[n];basis=bases[n]
            pb.location=basis.translation;pb.rotation_mode='QUATERNION';pb.scale=basis.to_scale()
            q=basis.to_quaternion()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();pb.rotation_quaternion=q
            for channel in ['location','rotation_quaternion','scale']:pb.keyframe_insert(channel,frame=i+1,group=n)
    scene.frame_set(1);bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    filename=action.name+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(OUT/filename),use_selection=True,object_types={'ARMATURE'},
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',global_scale=1.,axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,use_armature_deform_only=False,armature_nodetype='NULL',bake_anim=True,
        bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0.)
    manifest['clips'][role]={**source_manifest['clips'][role],'file':filename,'frames':COUNT,'seconds':DURATION,
                             'design':('Left-to-right' if active=='l' else 'Right-to-left')+' forward horizontal hook cut with torso-led acceleration and rear scythe guard'}
    print('M27_CLAW_V16_EXPORTED '+role,flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'MantisM27_ClawV16.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('M27_CLAW_V16_AUTHORED',flush=True)
