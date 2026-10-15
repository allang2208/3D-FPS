"""Tilt the accepted gather screen-left and fit the release shoulder opening."""
import ast,copy,json,math
import numpy as np
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=240;DURATION=2.05;RELEASE=1.;JOIN=1.05
SOURCE=P.parent/'UppercutV1/Warhammer_Uppercut_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
source=[]
for i in range(round(DURATION*FPS)+1):
    scene.frame_set(i);source.append({b.name:b.matrix.copy() for b in rig.pose.bones})
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
idle=copy.deepcopy(source[0]);idle_local={n:idle[p].inverted()@m if p else m for n,m in idle.items() for p in [parents[n]]}
grips={side:idle['WPN_root'].inverted()@idle['hand_'+side] for side in ('l','r')}
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
module=ast.parse((P.parent/'WhirlwindHandoffV5/author_whirlwind.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'rigid','logq','expq','frame','axial','quintic','solve_arm'}],type_ignores=[]),'<supported_arm_solver>','exec'))
# The sword's supported-arm method resolves total palm roll against a fixed
# anatomical reference. Do not add roll onto already interpolating V4 helpers.
support_source=(ROOT/'SourceAssets/SwordUppercut20261003/GripRecoveryV15/arm_support.py').read_text(encoding='utf-8')
support_module=ast.parse(support_source)
for function in support_module.body:
    if isinstance(function,ast.FunctionDef) and function.name in {'axis_angle','near_angle','solve_supported_arm'}:
        code=ast.get_source_segment(support_source,function)
        # Preserve the donor's 120 Hz pole-speed cap at this clip's 240 Hz.
        code=code.replace('old_angle-10.','old_angle-5.').replace('old_angle+10.','old_angle+5.')
        # The right shoulder ring also carries clavicle weights. Keep that
        # frame anatomically stable while the upper arm rises from it.
        if function.name=='solve_supported_arm':
            code += '''
    if side=='r':
        source_clavicle=pose[n('clavicle')]
        target_clavicle=idle[n('clavicle')].copy()
        target_clavicle.translation+=shoulder-idle[un].translation
        pose[n('clavicle')]=blend(source_clavicle,target_clavicle,weight)
'''
        exec(compile(code,'<fixed_reference_arm>','exec'))
def mat(p,q,scale):return Matrix.LocRotScale(p,q,scale)
ROOT_BONE=next(n for n,p in parents.items() if p is None)
left_state={'pole':0.,'roll':0.}
right_state={'pole':0.,'roll':0.}
roll_state={};zero=Vector((0,0,0))
LEFT_TARGET=Vector((.015,.38,-.125))
GROUP_SHIFT=Vector((.15,.02,-.13));SHIFT_START=.18;GRIP_READY=.42
LOW_DIRECTION=Vector((.18,.30,-.936)).normalized()
SCREEN_TILT_DEGREES=30.
FOLLOW_CARRY=Vector((0,-.08,-.12))
RIGHT_SHOULDER_LIFT=Vector((.055,-.045,.10))
SHOULDERS={'l':Vector((0,.02,-.01)),'r':Vector((.015,.025,-.015))}
arm_bones={b.name for b in rig.data.bones if b.name in {'clavicle_l','clavicle_r'} or any(p.name in {'clavicle_l','clavicle_r'} for p in b.parent_recursive)}
left_bones={b.name for b in rig.data.bones if b.name=='clavicle_l' or any(p.name=='clavicle_l' for p in b.parent_recursive)}
right_bones=arm_bones-left_bones
explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))

# Retain the existing uppercut's complete downward grasp, but support it from
# the normal shoulder height and locate the rear palm within the lower frame.
# Rotate the complete loaded grasp about its rear/left palm in view space.
# The user's accepted 15 cm right / 13 cm down group carry stays separate.
original_load=source[round(RELEASE*FPS)]
old_axis=original_load['WPN_root'].to_quaternion()@Vector((0,0,1))
load_rotation=old_axis.rotation_difference(LOW_DIRECTION)
carry=Matrix.Translation(LEFT_TARGET)@load_rotation.to_matrix().to_4x4()@Matrix.Translation(-original_load['hand_l'].translation)
untilted_weapon=carry@original_load['WPN_root']
def projected_handle_angle(w):
    # Compare the perspective-projected shaft line. A 30 degree camera-axis
    # quaternion around an off-centre grip would over-tilt it on screen.
    a=w@Vector((0,0,0))+GROUP_SHIFT
    b=w@Vector((0,0,.30))+GROUP_SHIFT
    return math.atan2(a.z/a.y-b.z/b.y,a.x/a.y-b.x/b.y)
original_screen_angle=projected_handle_angle(untilted_weapon)
lo,hi=-60.,0.
for _ in range(45):
    degrees=(lo+hi)*.5
    trial=Matrix.Translation(LEFT_TARGET)@Quaternion((0,1,0),math.radians(degrees)).to_matrix().to_4x4()@Matrix.Translation(-LEFT_TARGET)
    angle=projected_handle_angle(trial@untilted_weapon)-original_screen_angle
    angle=math.degrees(math.atan2(math.sin(angle),math.cos(angle)))
    if angle>SCREEN_TILT_DEGREES:lo=degrees
    else:hi=degrees
VIEW_AXIS_TILT_DEGREES=(lo+hi)*.5
SCREEN_TILT=Quaternion((0,1,0),math.radians(VIEW_AXIS_TILT_DEGREES))
carry=Matrix.Translation(LEFT_TARGET)@SCREEN_TILT.to_matrix().to_4x4()@Matrix.Translation(-LEFT_TARGET)@carry
loaded_pose={n:carry@m for n,m in original_load.items()}
loaded_weapon=loaded_pose['WPN_root']
loaded_grips={side:loaded_weapon.inverted()@loaded_pose['hand_'+side] for side in ('l','r')}
loaded_reference=copy.deepcopy(idle)
for side in ('l','r'):
    shift=idle['upperarm_'+side].translation+SHOULDERS[side]-loaded_pose['upperarm_'+side].translation
    names={b.name for b in rig.data.bones if b.name=='clavicle_'+side or any(p.name=='clavicle_'+side for p in b.parent_recursive)}
    for n in names:
        loaded_reference[n]=loaded_pose[n].copy();loaded_reference[n].translation+=shift

def blend(a,b,u):
    ap,aq,ascale=a.decompose();bp,bq,bscale=b.decompose()
    return Matrix.LocRotScale(ap.lerp(bp,u),aq.slerp(bq,u),ascale.lerp(bscale,u))
def sample(t):
    f=t*FPS;i=min(len(source)-2,int(f));u=f-i
    return {n:blend(source[i][n],source[i+1][n],u) for n in idle}
def locals_of(pose):
    return {n:pose[p].inverted()@m if p else m for n,m in pose.items() for p in [parents[n]]}
def reconstruct(local):
    out={}
    for n in local:
        if n.startswith(('upperarm','lowerarm','hand_','thumb','index','middle','ring','pinky')):
            v=local[n].translation
            if v.length>1e-8:local[n].translation=v.normalized()*idle_local[n].translation.length
    def resolve(n):
        if n not in out:out[n]=resolve(parents[n])@local[n] if parents[n] else local[n]
        return out[n]
    for n in local:resolve(n)
    return out
load_local=locals_of(loaded_reference)
def supported_reference(load,u,t,move):
    a={n:blend(idle_local[n],load_local[n],load) for n in idle}
    gathered=reconstruct(a)
    for n in arm_bones:gathered[n].translation+=GROUP_SHIFT*(.30*move)
    a=locals_of(gathered)
    if u<=0:return gathered,a
    # Join the existing forward stroke without returning to the rejected
    # both-hands-out-of-frame V3 gather in between.
    src=sample(JOIN+(t-JOIN)*u);b=locals_of(src)
    local={n:blend(a[n],b[n],u) for n in idle};out={}
    return reconstruct(local),local

loaded_right=loaded_pose['hand_r'].translation+GROUP_SHIFT
base=loaded_weapon.to_quaternion()
def source_rotation(t):return logq(base.inverted()@sample(t)['WPN_root'].to_quaternion())
def derivatives(fn,t):
    h=1/FPS;a,b,c=fn(t-h),fn(t),fn(t+h)
    return b,(c-a)/(2*h),(c-2*b+a)/(h*h)
join_position=derivatives(lambda t:sample(t)['hand_r'].translation,JOIN)
join_rotation=derivatives(source_rotation,JOIN)

def follow_weight(t):
    # Only the raised follow-through is brought slightly back and down. Keep
    # the forward plant at JOIN and release clock; smoothly unwind to idle.
    return ease((t-JOIN)/(.125-.05))*(1-ease((t-1.38)/(.60)))

def support_right(pose,ref,t):
    # A supported shoulder follows the torso, rather than advancing its open
    # proximal cut alongside the high fist. Bone lengths stay native.
    load=ease(t/GRIP_READY);move=ease((t-SHIFT_START)/(RELEASE-SHIFT_START))
    handoff=ease((t-RELEASE)/.10)
    recovery=1-ease((t-1.70)/.35)
    gathered=SHOULDERS['r']*load+GROUP_SHIFT*(.30*move)
    offset=gathered.lerp(RIGHT_SHOULDER_LIFT,handoff)*recovery
    anatomy=copy.deepcopy(idle)
    for n in right_bones:anatomy[n].translation+=offset
    anatomy[ROOT_BONE]=pose[ROOT_BONE].copy()
    weight=ease(t/.18)*recovery
    solve_supported_arm(pose,anatomy,ref,'r',weight,right_state,STATIONS['r'])

poses=[]
for i in range(len(source)):
    t=i/FPS
    if t>=JOIN:
        pose=copy.deepcopy(source[i])
        shift=FOLLOW_CARRY*follow_weight(t)
        for n in arm_bones|{'WPN_root'}:pose[n].translation+=shift
        ref=copy.deepcopy(pose)
        support_right(pose,ref,t)
        for side in ('l','r'):
            n='ik_hand_'+side
            if n in pose:pose[n]=pose['hand_'+side]@idle['hand_'+side].inverted()@idle[n]
        poses.append(pose);continue
    # Grip preparation and group displacement overlap instead of canceling
    # each other's vertical motion at the rear palm throughout the gather.
    load=ease(t/GRIP_READY);move=ease((t-SHIFT_START)/(RELEASE-SHIFT_START))
    u=ease((t-RELEASE)/(JOIN-RELEASE))
    ref,local=supported_reference(load,u,t,move)
    if t<=RELEASE:
        current_grips={side:blend(grips[side],loaded_grips[side],load) for side in ('l','r')}
        q=idle['WPN_root'].to_quaternion().slerp(base,load)
        left=idle['hand_l'].translation.lerp(LEFT_TARGET,load)+GROUP_SHIFT*move
        w=rigid(left-q@current_grips['l'].translation,q)
    else:
        current=sample(t);current_grips={side:blend(loaded_grips[side],current['WPN_root'].inverted()@current['hand_'+side],u) for side in ('l','r')}
        phase=(t-RELEASE)/(JOIN-RELEASE)
        right=quintic(loaded_right,zero,zero,*join_position,JOIN-RELEASE,phase)
        q=base@expq(quintic(zero,zero,zero,*join_rotation,JOIN-RELEASE,phase))
        w=rigid(right-q@current_grips['r'].translation,q)
    pose=copy.deepcopy(ref);pose['WPN_root']=w
    pose['hand_r']=w@current_grips['r']
    support_right(pose,ref,t)
    pose['hand_l']=w@current_grips['l']
    anatomy=copy.deepcopy(idle)
    shoulder_follow=(SHOULDERS['l']*load+GROUP_SHIFT*(.30*move))*(1-u)
    for n in left_bones:anatomy[n].translation+=shoulder_follow
    anatomy[ROOT_BONE]=pose[ROOT_BONE].copy()
    support_weight=ease(t/.18)*(1-ease((t-(JOIN-.02))/.02))
    solve_supported_arm(pose,anatomy,ref,'l',support_weight,left_state,STATIONS['l'])
    done=set(explicit)
    def resolve(n):
        if n not in done:
            pose[n]=resolve(parents[n])@local[n] if parents[n] else local[n]
            done.add(n)
        return pose[n]
    for n in pose:resolve(n)
    for side in ('l','r'):
        n='ik_hand_'+side
        if n in pose:pose[n]=pose['hand_'+side]@idle['hand_'+side].inverted()@idle[n]
    poses.append(pose)
poses[0]=copy.deepcopy(idle);poses[-1]=copy.deepcopy(idle)
# Record the actual native proximal-ring constraints used for this pose edit.
# This is authoring geometry, not an editor/game/render acceptance run.
surface=json.loads((P/'authoring_surface.json').read_text())
ring=next(x for x in surface['rings'] if x['mesh']=='Warhammer_BareArmsV7' and x['weights'][0][0].endswith('_r'))
ring_groups={}
ring_points=np.array([[*p,1.] for p in ring['points']])
for n in {n for skin in ring['skin'] for n in skin}:
    ring_groups[n]=(ring_points@np.asarray(rest[n].inverted()).T,np.array([s.get(n,0.) for s in ring['skin']]))
def shoulder_boundary(pose):
    points=sum((local@np.asarray(pose[n]).T)[:,:3]*weights[:,None] for n,(local,weights) in ring_groups.items())
    # Same conservative 82 degree vertical / 16:9 envelope as the existing
    # melee shoulder-opening authoring recipe, plus a 15 mm garment margin.
    x,y,z=points.T;vertical=math.tan(math.radians(41));horizontal=vertical*16/9
    outside=max(float(np.min(x-horizontal*y)),float(np.min(-z-vertical*y)),float(np.min(-y)))
    return outside-.015
clearance_rows=[{'source_seconds':i/FPS,'margin_m':shoulder_boundary(p)} for i,p in enumerate(poses) if 1.04<=i/FPS<=1.95]
(P/'shoulder_fit.json').write_text(json.dumps({'minimum_margin_m':min(x['margin_m'] for x in clearance_rows),'rows':clearance_rows},indent=2),encoding='utf-8')
name='A_Warhammer_Uppercut';bake(name,poses,FPS)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Uppercut_TiltClearance_Editable.blend'))
# Generate the authority's actual head path from the saved/baked skeleton.
points=[]
for k in range(31):
    scene.frame_set(240+k);p=rig.pose.bones['WPN_root'].matrix@Vector((0,0,.972475657))
    points.append((p.y*100,p.x*100,p.z*100))
header='#pragma once\n#include "CoreMinimal.h"\n// Generated by UppercutTiltClearanceV6/author_uppercut.py; source seconds 1.0..1.125.\nnamespace WarhammerUppercutArc\n{\n    inline const FVector Head[]={\n'
header+=''.join('        FVector(%.6f,%.6f,%.6f),\n'%p for p in points)
header+='    };\n    inline FVector Sample(float T)\n    {\n        const float F=FMath::Clamp((T-1.f)*240.f,0.f,30.f);\n        const int32 I=FMath::Min(29,FMath::FloorToInt(F));\n        return FMath::Lerp(Head[I],Head[I+1],F-I);\n    }\n}\n'
(ROOT/'Source/FPSGAME/Production/WarhammerUppercutArc.h').write_text(header,encoding='utf-8')
receipt={'clips':[name],'fps':FPS,'seconds':DURATION,'revision':'TiltClearanceV6_20261015','source':str(SOURCE),
 'loaded_left_wrist_m':list(LEFT_TARGET+GROUP_SHIFT),'loaded_right_wrist_m':list(loaded_right),
 'loaded_head_center_m':list((loaded_weapon@Vector((0,0,.972475657)))+GROUP_SHIFT),
 'group_translation_m':list(GROUP_SHIFT),'group_translation_seconds':[SHIFT_START,RELEASE],
 'grip_preparation_end_seconds':GRIP_READY,
 'loaded_shaft_direction':list(SCREEN_TILT@LOW_DIRECTION),'gather_seconds':RELEASE,'join_source_seconds':JOIN,
 'gather_screen_counterclockwise_degrees':SCREEN_TILT_DEGREES,'view_axis_rotation_degrees':VIEW_AXIS_TILT_DEGREES,
 'tilt_pivot':'rear left palm before the accepted common group translation',
 'right_shoulder_authoring_minimum_margin_m':min(x['margin_m'] for x in clearance_rows),
 'follow_through_group_recovery_m':list(FOLLOW_CARRY),
 'gather_grip':'Rear left grip remains higher than the right; both hands and weapon translate together down-right after the grip starts settling',
 'arm_support':'Both elbow poles and total axial roll solved against fixed idle anatomy; monotonic skin stations, bounded pole motion, native segment lengths. Right support continues through release and recovery; proximal clavicle frame stabilized.',
 'left_wrist_source_fix':'Do not accumulate additional twist on the V4 interpolating donor helper frames',
 'release':'C2 right-wrist/weapon curve into the existing forward plant at 1.05; raised follow-through comes 8 cm back / 12 cm down while right shoulder stays supported',
 'runtime_clock':'WarhammerUppercutMotion: 55 ms pre-plant strike plus 50 ms post-plant strike',
 'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_UPPERCUT_TILT_CLEARANCE_AUTHORED '+json.dumps(receipt))
