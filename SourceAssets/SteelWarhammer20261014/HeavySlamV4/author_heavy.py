"""Waist-driven ground slam; hammer striking axis stays in the sagittal plane."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'RhythmClearanceV2/Warhammer_Clearance_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local_rest={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
source=bpy.data.actions['A_Warhammer_Clearance_Slash1'];rig.animation_data.action=source;rig.animation_data.action_slot=source.slots[0]
scene.frame_set(0);idle={b.name:b.matrix.copy() for b in rig.pose.bones}
finger_basis={b.name:b.matrix_basis.copy() for b in rig.pose.bones if b.name.startswith(('thumb','index','middle','ring','pinky'))}
scene.frame_set(28);hold={b.name:b.matrix.copy() for b in rig.pose.bones}
grips={s:hold['WPN_root'].inverted()@hold['hand_'+s] for s in ('l','r')}
idle_grips={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
CFG=json.loads((ROOT/'SourceAssets/PickaxeSightline20260919/motion.json').read_text())
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
SHOULDER_OVERRIDES={}
module=ast.parse((ROOT/'SourceAssets/PickaxeSightline20260919/author_attack.py').read_text(encoding='utf-8'))
for f in module.body:
    if isinstance(f,ast.FunctionDef) and f.name=='solve_arm':
        for i,node in enumerate(f.body):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='shoulder' for t in node.targets):
                f.body[i+1:i+1]=ast.parse('shoulder = SHOULDER_OVERRIDES[side]').body;break
        for i,node in enumerate(f.body):
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='pole' for t in node.targets):
                f.body[i]=ast.parse('pole = desired').body[0];break
ast.fix_missing_locations(module)
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'unwrap','axial_delta','frame_rotation','solve_arm'}],type_ignores=[]),'<shared_arm_solver>','exec'))
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<baking>','exec'))
FPS=480;PIVOT=Vector((0,0,.19))
def frame(center,axis):
    shaft=Vector(axis).normalized()
    # Local X connects the two striking faces. Local Y is the decorated broad
    # side: explicitly point that side across the view, never back at the eye.
    face=Vector((0,shaft.z,-shaft.y)).normalized()
    q=Matrix((face,shaft.cross(face),shaft)).transposed().to_quaternion()
    return Matrix.LocRotScale(Vector(center)-q@PIVOT,q,Vector((1,1,1)))
top=hold['WPN_root'];front=frame((.04,.41,.04),(0,.70,.714))
floor=frame((0,0,0),(0,.70710678,-.70710678))
hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest['WPN_root'].inverted()
head=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
head=[p for p in head if p.z>.78]
lowest=min((floor@p).z for p in head)
contact=[p for p in head if (floor@p).z<=lowest+.002]
marker=sum(contact,Vector())/len(contact)
# Nominal feet +125 cm; standing stable eye is feet +(56,0,170) cm.
# Author against that real floor, instead of lowering an airborne pose via IK.
floor.translation+=Vector((0,.69,-1.70))-(floor@marker)
CONTACT=.075;HOLD_END=CONTACT+.7;DURATION=HOLD_END+.5
floor_grips=copy.deepcopy(grips);floor_poles={'l':0.,'r':0.}
def blend_grasp(a,b,w):
    # Slide/roll on the outside of the shaft, never through its centre.
    pa,pb=a.translation,b.translation
    aa=math.atan2(pa.y,pa.x);ab=unwrap(math.atan2(pb.y,pb.x),aa)
    angle=aa+(ab-aa)*w;radius=math.hypot(pa.x,pa.y)*(1-w)+math.hypot(pb.x,pb.y)*w
    return Matrix.LocRotScale(Vector((radius*math.cos(angle),radius*math.sin(angle),pa.z*(1-w)+pb.z*w)),a.to_quaternion().slerp(b.to_quaternion(),w),Vector((1,1,1)))
def blend(a,b,w):
    return Matrix.LocRotScale((a@PIVOT).lerp(b@PIVOT,w),a.to_quaternion().slerp(b.to_quaternion(),w),Vector((1,1,1)))@Matrix.Translation(-PIVOT)
def solve_base(wpn,w,state,returning=0.,rolls=None):
    out=copy.deepcopy(idle)
    for side in ('l','r'):
        loaded=blend_grasp(grips[side],floor_grips[side],w)
        grasp=blend_grasp(loaded,idle_grips[side],returning)
        if rolls:grasp=Quaternion((0,0,1),math.radians(rolls.get(side,0.))).to_matrix().to_4x4()@grasp
        hand=wpn@grasp
        # The eye moves +20/-52 cm; shoulders fold with the torso and stay
        # behind that lowered eye. Their roots do not chase the hammer head.
        planted=Vector((-.18 if side=='l' else .18,-.075,-.61))
        shoulder=hold['upperarm_'+side].translation.lerp(planted,w)
        shoulder=shoulder.lerp(idle['upperarm_'+side].translation,returning)
        reach=hand.translation-shoulder
        limit=((rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length+(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length)*.985
        if reach.length>limit:shoulder+=reach.normalized()*(reach.length-limit)
        SHOULDER_OVERRIDES[side]=shoulder;axis=(hand.translation-shoulder).normalized()
        from_axis=(hold['hand_'+side].translation-hold['upperarm_'+side].translation).normalized()
        radial=hold['lowerarm_'+side].translation-hold['upperarm_'+side].translation
        radial=(radial-from_axis*radial.dot(from_axis)).normalized();transported=from_axis.rotation_difference(axis)@radial
        # Elbows hang down/back beside the ribs, rather than flaring sideways.
        target=Vector((-.35 if side=='l' else .35,-.55,-.78));target=(target-axis*target.dot(axis)).normalized()
        target=Quaternion(axis,math.radians(floor_poles[side]))@target
        angle=unwrap(math.atan2(axis.dot(transported.cross(target)),transported.dot(target)),state.get(side+'_pole'))
        state[side+'_pole']=angle;guide=Quaternion(axis,angle*w)@transported
        if returning>0.:
            upper_len=(rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length
            fore_len=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length
            distance=(hand.translation-shoulder).length
            along=(upper_len**2-fore_len**2+distance**2)/(2*distance)
            center=shoulder+axis*along;radius=math.sqrt(max(0.,upper_len**2-along**2))
            ready_pole=idle['lowerarm_'+side].translation-center
            ready_pole=(ready_pole-axis*ready_pole.dot(axis)).normalized()
            unwind=math.atan2(axis.dot(guide.cross(ready_pole)),guide.dot(ready_pole))
            guide=Quaternion(axis,unwind*returning)@guide
            neutral=hand.to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
            ideal=hand.translation-neutral*fore_len-center
            ideal=(ideal-axis*ideal.dot(axis)).normalized()
            correction=math.atan2(axis.dot(guide.cross(ideal)),guide.dot(ideal))
            turn=returning*returning
            limit=math.radians(80)*4*turn*(1-turn)
            correction=max(-limit,min(limit,correction))
            fitted=Quaternion(axis,correction)@guide
            if (center+fitted*radius).x*(1 if side=='r' else -1)>.025:guide=fitted
        pole=[guide.x*(1 if side=='r' else -1),guide.y,guide.z]
        CFG['elbow_pole_top'][side]=pole;CFG['elbow_pole_impact'][side]=pole
        solve_arm(out,side,hand,1.-returning,1.,0.,state)
    out['WPN_root']=wpn;return out
def solve(wpn,w,state,returning=0.):
    rolls={}
    if 0.<returning<1.:
        # A continuous whole-palm roll during recovery keeps the wrist aligned
        # with the forearm. Fingers and the shaft contact frame move together.
        allowance=85.*math.sin(math.pi*returning*returning)
        for side in ('l','r'):
            previous=state.get(side+'_recover_roll',0.);best=None
            for step in (-3.,-1.5,0.,1.5,3.):
                value=max(-allowance,min(allowance,previous+step));trial=dict(rolls);trial[side]=value
                probe=solve_base(wpn,w,copy.deepcopy(state),returning,trial)
                fore=(probe['hand_'+side].translation-probe['lowerarm_'+side].translation).normalized()
                neutral=probe['hand_'+side].to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
                cost=neutral.angle(fore)**2+.015*math.radians(value)**2
                if best is None or cost<best[0]:best=(cost,value)
            rolls[side]=best[1];state[side+'_recover_roll']=best[1]
    return solve_base(wpn,w,state,returning,rolls)
# Fit a small whole-palm regrip and elbow-plane change at the loaded floor pose.
# Fingers remain authored and closed on the same handle throughout the strike.
grasp_recipe={}
for side in ('l','r'):
    best=None
    for roll in range(-90,91,5):
        floor_grips[side]=Quaternion((0,0,1),math.radians(roll)).to_matrix().to_4x4()@Matrix.Translation((0,0,-.10 if side=='r' else 0.))@grips[side]
        for pole in range(-25,26,5):
            floor_poles[side]=pole;probe=solve(floor,1.,{})
            fore=(probe['hand_'+side].translation-probe['lowerarm_'+side].translation).normalized()
            neutral=probe['hand_'+side].to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
            shoulder=probe['upperarm_'+side].translation;elbow=probe['lowerarm_'+side].translation
            # Preserve the natural hanging upper arm as well as wrist comfort.
            outward=max(0.,abs(elbow.x)-abs(shoulder.x)-.045)
            forward=max(0.,elbow.y-shoulder.y-.12)
            cost=neutral.angle(fore)**2+.02*math.radians(roll)**2+.08*math.radians(pole)**2+45.*(outward*outward+forward*forward)
            if best is None or cost<best[0]:best=(cost,roll,pole,floor_grips[side].copy())
    floor_grips[side]=best[3];floor_poles[side]=best[2];grasp_recipe[side]={'palm_roll_degrees':best[1],'elbow_pole_degrees':best[2]}
charge=[]
for i in range(2*FPS+1):
    t=i/FPS;source_time=.13*ease(t/.65) if t<=.65 else .13+.0566666667*ease((t-.65)/.95)
    scene.frame_set(int(source_time*150),subframe=source_time*150-int(source_time*150))
    charge.append({b.name:b.matrix.copy() for b in rig.pose.bones})
charge[-1]=copy.deepcopy(hold);release=[];state={}
for i in range(round(DURATION*FPS)+1):
    t=i/FPS;down=ease(t/CONTACT);ret=ease((t-HOLD_END)/.5)
    if t<=.032:wpn=blend(top,front,(t/.032)**1.6)
    elif t<=CONTACT:wpn=blend(front,floor,1-(1-(t-.032)/(CONTACT-.032))**1.5)
    elif t<=HOLD_END:wpn=floor
    else:wpn=blend(floor,idle['WPN_root'],ret)
    release.append(solve(wpn,down,state,ret))
release[0]=copy.deepcopy(hold);release[-1]=copy.deepcopy(idle)
for name,poses in (('A_Warhammer_HeavyCharge',charge),('A_Warhammer_HeavyRelease',release)):bake(name,poses,FPS)
receipt={'fps':FPS,'charge_seconds':2.,'release_seconds':DURATION,'floor_contact_seconds':CONTACT,'floor_hold_seconds':.7,'floor_hold_end_seconds':HOLD_END,
    'body_bend_degrees':62.,'pelvis_forward_drop_cm':[6.,14.], 'eye_forward_drop_cm':[20.,52.],
    'landing_forward_from_feet_cm':125.,
    'planted_shoulder_author_m':{'l':[-.18,-.075,-.61],'r':[.18,-.075,-.61]},
    'view_pitch_degrees':-52.,'hammer_focus_tracking':False,
    'head_striking_axis':list(floor.to_quaternion()@Vector((1,0,0))),
    'head_broad_side_axis':list(floor.to_quaternion()@Vector((0,1,0))),
    'grasp_recipe':grasp_recipe,
    'reference_positions_m':{n:list(rest[n].translation) for n in ('clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r','WPN_root')},
    'head_marker_author_world_m':list(rest['WPN_root']@marker),'head_marker_author_local_m':list(marker),
    'clips':['A_Warhammer_HeavyCharge','A_Warhammer_HeavyRelease'],'runtime_tested':False,'rendered':False}
rig.animation_data.action=bpy.data.actions['A_Warhammer_HeavyRelease'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(36)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_HeavySlam_Editable.blend'))
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('WARHAMMER_HEAVY_AUTHORED '+json.dumps(receipt))
