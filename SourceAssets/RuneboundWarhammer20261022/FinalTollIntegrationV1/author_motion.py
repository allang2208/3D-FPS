"""Two supported hammer strikes, using Chixiao's down/up intent and hammer grips."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Motion';OUT.mkdir(exist_ok=True)
HEAVY=ROOT/'SourceAssets/SteelWarhammer20261014/HeavySlamV4/Warhammer_HeavySlam_Editable.blend'
UPPER=ROOT/'SourceAssets/SteelWarhammer20261014/UppercutTiltClearanceV6/Warhammer_Uppercut_TiltClearance_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(UPPER));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
def take(action,t,fps):
    rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
    f=t*fps;scene.frame_set(math.floor(f),subframe=f%1)
    return {b.name:b.matrix.copy() for b in rig.pose.bones}
upper=bpy.data.actions['A_Warhammer_Uppercut'];low=take(upper,1.,240);high=take(upper,1.125,240)
with bpy.data.libraries.load(str(HEAVY),link=False) as (a,b):b.actions=['A_Warhammer_HeavyCharge','A_Warhammer_HeavyRelease']
charge,release=b.actions;loaded=take(charge,2.,480);idle=take(release,1.275,480)
finger_basis={b.name:b.matrix_basis.copy() for b in rig.pose.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}
CFG=json.loads((ROOT/'SourceAssets/PickaxeSightline20260919/motion.json').read_text())
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
SHOULDER_OVERRIDES={}
module=ast.parse((ROOT/'SourceAssets/PickaxeSightline20260919/author_attack.py').read_text('utf-8'))
for f in module.body:
    if isinstance(f,ast.FunctionDef) and f.name=='solve_arm':
        for i,n in enumerate(f.body):
            if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='shoulder' for x in n.targets):
                f.body[i+1:i+1]=ast.parse('shoulder = SHOULDER_OVERRIDES[side]').body;break
        for i,n in enumerate(f.body):
            if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='pole' for x in n.targets):f.body[i]=ast.parse('pole = desired').body[0];break
ast.fix_missing_locations(module)
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'unwrap','axial_delta','frame_rotation','solve_arm'}],type_ignores=[]),'<supported_hammer_arm>','exec'))
module=ast.parse((ROOT/'SourceAssets/SteelWarhammer20261014/SprintDragV1/author_sprint.py').read_text('utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<hammer_motion_baker>','exec'))
def mix(a,b,w):return Matrix.LocRotScale(a.translation.lerp(b.translation,w),a.to_quaternion().slerp(b.to_quaternion(),w),a.to_scale().lerp(b.to_scale(),w))
def grasp(a,b,w):
    # Slide and roll around the original handle, never through its middle.
    pa,pb=a.translation,b.translation;angle=math.atan2(pa.y,pa.x)
    other=unwrap(math.atan2(pb.y,pb.x),angle);r=math.hypot(pa.x,pa.y)*(1-w)+math.hypot(pb.x,pb.y)*w
    return Matrix.LocRotScale(Vector((r*math.cos(angle+(other-angle)*w),r*math.sin(angle+(other-angle)*w),pa.z*(1-w)+pb.z*w)),a.to_quaternion().slerp(b.to_quaternion(),w),Vector((1,1,1)))
FPS=240;END=1.25;poses=[];state={}
for frame in range(round(END*FPS)+1):
    t=frame/FPS
    if t<=.10:a,b,w=loaded,low,1-(1-t/.10)**1.7
    elif t<.24:a,b,w=low,low,0.
    elif t<=.42:a,b,w=low,high,ease((t-.24)/.18)
    elif t<.54:a,b,w=high,high,0.
    else:a,b,w=high,idle,ease((t-.54)/(END-.54))
    pose={n:mix(a[n],b[n],w) for n in rest};wpn=mix(a['WPN_root'],b['WPN_root'],w)
    for side in ('l','r'):
        ga=a['WPN_root'].inverted()@a['hand_'+side];gb=b['WPN_root'].inverted()@b['hand_'+side]
        hand=wpn@grasp(ga,gb,w);shoulder=pose['upperarm_'+side].translation.copy()
        l1=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length;l2=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
        axis=(hand.translation-shoulder).normalized();distance=(hand.translation-shoulder).length
        if distance>(l1+l2)*.985:shoulder+=axis*(distance-(l1+l2)*.985)
        SHOULDER_OVERRIDES[side]=shoulder
        elbow=pose['lowerarm_'+side].translation;guide=elbow-shoulder;guide=(guide-axis*guide.dot(axis)).normalized()
        CFG['elbow_pole_top'][side]=[guide.x*(1 if side=='r' else -1),guide.y,guide.z];CFG['elbow_pole_impact'][side]=CFG['elbow_pole_top'][side]
        # The solver distributes arm twist while keeping each native palm frame.
        solve_arm(pose,side,hand,1.,1.,0.,state)
    pose['WPN_root']=wpn
    if frame==0:pose=copy.deepcopy(loaded)
    if frame==round(END*FPS):pose=copy.deepcopy(idle)
    poses.append(pose)
action=bake('A_Runebound_FinalToll_DoubleHeavy',poses,FPS)
rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'FinalToll_DoubleHeavy_Editable.blend'))
(P/'motion_authoring.json').write_text(json.dumps({'fps':FPS,'seconds':END,'contacts':[.10,.42],'second_release':.24,'follow_end':.54,'fps_export':str(OUT/'A_Runebound_FinalToll_DoubleHeavy.fbx'),'source_heavy':str(HEAVY),'source_upper':str(UPPER),'reference_intent':'Chixiao downstrike, supported upward-right return, settle to idle','runtime_tested':False},indent=2),encoding='utf-8')
print('FINAL_TOLL_DOUBLE_HEAVY_AUTHORED',flush=True)
