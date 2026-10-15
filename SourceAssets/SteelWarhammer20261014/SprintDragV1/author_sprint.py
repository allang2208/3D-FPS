"""Low right trailing two-hand carry and its attack handoff; shared grip/arm solver."""
import bpy, json, math, ast, copy
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];SOURCE=P/'RigSource/SteelWarhammer_Editable.blend'
OUT=P/'Export';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data_create();original_idle=bpy.data.actions['A_RusticPickaxe_Idle']
rig.animation_data.action=original_idle;rig.animation_data.action_slot=original_idle.slots[0];scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
idle={b.name:b.matrix.copy() for b in rig.pose.bones};ready=idle['WPN_root']
grips={s:ready.inverted()@idle['hand_'+s] for s in ('l','r')}
finger_basis={b.name:b.matrix_basis.copy() for b in rig.pose.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
CFG=json.loads((ROOT/'SourceAssets/PickaxeSightline20260919/motion.json').read_text())
CFG.update(shoulder_top_lift_m=.005,shoulder_forward_m=.015,shoulder_outward_m=.005,
    elbow_pole_top={'l':[.55,-.35,-.9],'r':[.65,-.30,-.8]},upper_roll_share=.3)
# Reuse the established full-chain solver without replaying its authoring job.
module=ast.parse((ROOT/'SourceAssets/PickaxeSightline20260919/author_attack.py').read_text(encoding='utf-8'))
names={'unwrap','axial_delta','frame_rotation','solve_arm'}
SHOULDER_OVERRIDES={}
for function in module.body:
    if isinstance(function,ast.FunctionDef) and function.name=='solve_arm':
        for index,node in enumerate(function.body):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='shoulder' for t in node.targets):
                function.body[index+1:index+1]=ast.parse('shoulder = SHOULDER_OVERRIDES.get(side, shoulder)').body
                break
ast.fix_missing_locations(module)
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'<shared_pickaxe_arm_solver>','exec'))
settings={'grip_center_m':[.19,.49,-.17],'shaft_direction':[.43,-.85,-.30],'roll_degrees':0.,'carry_seconds':.36,'attack_join_source_seconds':.18}
config=P/'pose.json'
if config.exists():settings.update(json.loads(config.read_text()))
else:config.write_text(json.dumps(settings,indent=2),encoding='utf-8')
pivot=Vector((0,0,.19));direction=Vector(settings['shaft_direction']).normalized()
rotation=(ready.to_quaternion()@Vector((0,0,1))).rotation_difference(direction)@ready.to_quaternion()
rotation=Quaternion(direction,math.radians(settings['roll_degrees']))@rotation
goal=Matrix.LocRotScale(Vector(settings['grip_center_m'])-rotation@pivot,rotation,Vector((1,1,1)))
carry_grips={};grasp_report={}
for side in ('l','r'):
    best=None
    # A bounded circumferential regrip changes the whole palm, never individual
    # fingers. The right hand slides 6 cm toward the lower hand before loading.
    slid=Matrix.Translation((0,0,-.06 if side=='r' else 0.))@grips[side]
    fore_axis=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
    original_guide=Vector(CFG['elbow_pole_top'][side]);sign=1 if side=='r' else -1
    for roll in range(-100,101,5):
        grasp=Quaternion((0,0,1),math.radians(roll)).to_matrix().to_4x4()@slid
        hand=goal@grasp
        for pole_degrees in (range(-100,101,10) if side=='r' else range(-40,41,10)):
            # Search the existing elbow circle rather than extending a segment.
            reach=(hand.translation-idle['upperarm_'+side].translation).normalized()
            guide=Quaternion(reach,math.radians(pole_degrees))@Vector((original_guide.x*sign,original_guide.y,original_guide.z))
            CFG['elbow_pole_top'][side]=[guide.x*sign,guide.y,guide.z]
            probe={n:m.copy() for n,m in idle.items()};solve_arm(probe,side,hand,1.,0.,0.,{})
            fore=(probe['hand_'+side].translation-probe['lowerarm_'+side].translation).normalized()
            neutral=hand.to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@fore_axis
            fold=neutral.angle(fore)
            elbow=probe['lowerarm_'+side].translation
            cost=fold*fold+.018*math.radians(roll)**2+.015*math.radians(pole_degrees)**2
            if elbow.z>hand.translation.z:cost+=5*(elbow.z-hand.translation.z)
            if sign*elbow.x<0:cost+=3
            if best is None or cost<best[0]:best=(cost,grasp.copy(),list(CFG['elbow_pole_top'][side]),roll,pole_degrees,fold)
    carry_grips[side]=best[1];CFG['elbow_pole_top'][side]=best[2]
    grasp_report[side]={'whole_hand_roll_degrees':best[3],'elbow_circle_rotation_degrees':best[4],'wrist_axis_fold_degrees':math.degrees(best[5])}
def ease(t):
    t=max(0.,min(1.,t));return t*t*t*(10.-15.*t+6.*t*t)
def blend_frame(a,b,t):
    return Matrix.LocRotScale((a@pivot).lerp(b@pivot,t),a.to_quaternion().slerp(b.to_quaternion(),t),Vector((1,1,1)))@Matrix.Translation(-pivot)
def carry_pose(t,state):
    w=ease(t);wpn=blend_frame(ready,goal,w);pose={n:m.copy() for n,m in idle.items()}
    for side in ('l','r'):
        g=Matrix.LocRotScale(grips[side].translation.lerp(carry_grips[side].translation,w),grips[side].to_quaternion().slerp(carry_grips[side].to_quaternion(),w),Vector((1,1,1)))
        solve_arm(pose,side,wpn@g,w,0.,0.,state)
    pose['WPN_root']=wpn;return pose
def apply_pose(pose):
    for bone in rig.pose.bones:
        parent_inverse=pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
        bone.matrix_basis=local_rest[bone.name].inverted()@parent_inverse@pose[bone.name]
    bpy.context.view_layer.update()
def new_action(name):
    a=bpy.data.actions.get(name)
    if a:bpy.data.actions.remove(a)
    a=bpy.data.actions.new(name);a.use_fake_user=True;rig.animation_data.action=a
    return a
def bake(name,poses,fps):
    action=new_action(name);scene.render.fps=fps;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=len(poses)-1
    previous={}
    for frame,pose in enumerate(poses):
        scene.frame_set(frame);apply_pose(pose)
        for bone in rig.pose.bones:
            bone.rotation_mode='QUATERNION';q=bone.rotation_quaternion.copy()
            if bone.name in previous and q.dot(previous[bone.name])<0:q.negate()
            bone.rotation_quaternion=q;previous[bone.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):bone.keyframe_insert(channel,frame=frame,group=bone.name)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
    return action
FPS=150;state={};carry=[carry_pose(i/(round(settings['carry_seconds']*FPS)),state) for i in range(round(settings['carry_seconds']*FPS)+1)]
hold=carry[-1]
hold_state=copy.deepcopy(state);carry_cfg=copy.deepcopy(CFG)
# Load the active overhead source. Its .24-second contact remains unchanged.
old=bpy.data.actions.get('A_RusticPickaxe_Swing')
if old:old.name='REF_OriginalPickaxeSwing'
with bpy.data.libraries.load(str(ROOT/'SourceAssets/PickaxeSightline20260919/Pickaxe_Sightline_Editable.blend'),link=False) as (a,b):b.actions=['A_RusticPickaxe_Swing']
shared=b.actions[0];rig.animation_data.action=shared;rig.animation_data.action_slot=shared.slots[0]
source_fps=300;source=[]
for i in range(round(.68*FPS)+1):
    scene.frame_set(int(i*source_fps/FPS));source.append({b.name:b.matrix.copy() for b in rig.pose.bones})
join=settings['attack_join_source_seconds'];attack=[];state=copy.deepcopy(hold_state)
CFG=json.loads((ROOT/'SourceAssets/PickaxeSightline20260919/motion.json').read_text())
source_cfg=copy.deepcopy(CFG)
contact_pose=source[round(.24*FPS)]
wind_axis=Vector((.25,-.90,.35)).normalized()
wind_q=direction.rotation_difference(wind_axis)@goal.to_quaternion()
windup=Matrix.LocRotScale(Vector((.16,.35,-.10))-wind_q@pivot,wind_q,Vector((1,1,1)))
for i,source_pose in enumerate(source):
    seconds=i/FPS
    if seconds>=join:attack.append(source_pose);continue
    pose=contact_pose
    w=ease(seconds/join)
    wp=blend_frame(goal,windup,ease(seconds/.16)) if seconds<=.16 else blend_frame(windup,pose['WPN_root'],((seconds-.16)/(.24-.16))**1.6)
    wpn=wp;out={n:m.copy() for n,m in idle.items()}
    # Interpolate local hand contacts, then solve both complete arm chains.
    for side in ('l','r'):
        CFG['upper_roll_share']=carry_cfg['upper_roll_share']*(1-w)+source_cfg['upper_roll_share']*w
        incoming=pose['WPN_root'].inverted()@pose['hand_'+side]
        grip_w=ease((seconds-.16)/(.24-.16))
        grasp=Matrix.LocRotScale(carry_grips[side].translation.lerp(incoming.translation,grip_w),carry_grips[side].to_quaternion().slerp(incoming.to_quaternion(),grip_w),Vector((1,1,1)))
        SHOULDER_OVERRIDES[side]=hold['upperarm_'+side].translation.lerp(pose['upperarm_'+side].translation,w)
        shoulder=SHOULDER_OVERRIDES[side];target=(wpn@grasp).translation
        l1=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length
        l2=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
        reach=target-shoulder;axis=reach.normalized();distance=reach.length
        if distance>(l1+l2)*.985:
            shoulder+=axis*(distance-(l1+l2)*.985);SHOULDER_OVERRIDES[side]=shoulder
            reach=target-shoulder;axis=reach.normalized();distance=reach.length
        center=shoulder+axis*((l1*l1-l2*l2+distance*distance)/(2*distance))
        from_axis=(hold['hand_'+side].translation-hold['upperarm_'+side].translation).normalized()
        to_axis=(pose['hand_'+side].translation-pose['upperarm_'+side].translation).normalized()
        a=hold['lowerarm_'+side].translation-hold['upperarm_'+side].translation
        b=pose['lowerarm_'+side].translation-pose['upperarm_'+side].translation
        a=from_axis.rotation_difference(axis)@(a-from_axis*a.dot(from_axis)).normalized()
        b=to_axis.rotation_difference(axis)@(b-to_axis*b.dot(to_axis)).normalized()
        angle=unwrap(math.atan2(axis.dot(a.cross(b)),a.dot(b)),state.get(side+'_entry_pole'))
        # Regrip and elbow-plane transport share one release envelope. Moving
        # the elbow ahead of the palm is what folds the loaded wrist.
        state[side+'_entry_pole']=angle;guide=Quaternion(axis,angle*grip_w)@a
        CFG['elbow_pole_top'][side]=[guide.x*(1 if side=='r' else -1),guide.y,guide.z]
        CFG['elbow_pole_impact'][side]=CFG['elbow_pole_top'][side]
        solve_arm(out,side,wpn@grasp,1.,1.,0.,state)
    out['WPN_root']=wpn;attack.append(out)
# Preserve exact boundary samples for predictable carry, contact, and recovery.
attack[0]=copy.deepcopy(hold)
carry_action=bake('A_Warhammer_SprintCarry',carry,FPS)
attack_action=bake('A_Warhammer_SprintAttack',attack,FPS)
rig.animation_data.action=carry_action;rig.animation_data.action_slot=carry_action.slots[0];scene.frame_set(len(carry)-1)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_SprintDrag_Editable.blend'))
hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest['WPN_root'].inverted();local=[inv@v.co for v in hammer.data.vertices]
head=[goal@v for v in local if v.z>.78]
steps=sorted([{'sequence':label,'frame':i+1,'joint':n,'step_cm':(b[n].translation-a[n].translation).length*100} for label,seq in [('carry',carry),('attack',attack[:round(join*FPS)+2])] for i,(a,b) in enumerate(zip(seq,seq[1:])) for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r')],key=lambda x:x['step_cm'],reverse=True)
report={'settings':settings,'fps':FPS,'carry_seconds':settings['carry_seconds'],'attack_seconds':.68,'source_contact_seconds':.24,
 'largest_joint_steps':steps[:6],
 'grasp_support':grasp_report,
 'max_authored_bone_length_error_mm':max(abs((p[b+'_'+s].translation-p[a+'_'+s].translation).length-(rest[b+'_'+s].translation-rest[a+'_'+s].translation).length)*1000 for p in carry+attack[:round(join*FPS)] for s in ('l','r') for a,b in [('upperarm','lowerarm'),('lowerarm','hand')]),
 'max_edited_joint_step_cm':max((b[n].translation-a[n].translation).length*100 for seq in (carry,attack[:round(join*FPS)+2]) for a,b in zip(seq,seq[1:]) for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r')),
 'arm_reach_ratio':{s:(hold['hand_'+s].translation-hold['upperarm_'+s].translation).length/((rest['lowerarm_'+s].translation-rest['upperarm_'+s].translation).length+(rest['hand_'+s].translation-rest['lowerarm_'+s].translation).length) for s in ('l','r')},
 'hands':{s:list(hold['hand_'+s].translation) for s in ('l','r')},'head_forward_depth_m':[min(v.y for v in head),max(v.y for v in head)],
 'source':str(SOURCE),'shared_swing_source':'PickaxeSightline20260919/Pickaxe_Sightline_Editable.blend','gameplay_timing_changed':False}
(P/'authored.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
