"""Right-shoulder load, sword-speed 75 ms floor strike, braced recovery."""
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
ast.fix_missing_locations(module)
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'unwrap','axial_delta','frame_rotation','solve_arm'}],type_ignores=[]),'<shared_arm_solver>','exec'))
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<baking>','exec'))
FPS=480;PIVOT=Vector((0,0,.19))
def frame(center,axis):
    q=(hold['WPN_root'].to_quaternion()@Vector((0,0,1))).rotation_difference(Vector(axis).normalized())@hold['WPN_root'].to_quaternion()
    return Matrix.LocRotScale(Vector(center)-q@PIVOT,q,Vector((1,1,1)))
top=hold['WPN_root'];over=frame((.12,.28,.30),(.10,-.15,.98));front=frame((.06,.38,.06),(.03,.98,.20))
floor=frame((.0,.36,-.63),(.02,.70,-.714));recover=frame((.18,.30,-.28),(.3,.72,.62))
floor_grips=copy.deepcopy(grips);floor_poles={'l':0.,'r':0.}
def blend(a,b,w):
    return Matrix.LocRotScale((a@PIVOT).lerp(b@PIVOT,w),a.to_quaternion().slerp(b.to_quaternion(),w),Vector((1,1,1)))@Matrix.Translation(-PIVOT)
def solve(wpn,w,state,returning=0.):
    out=copy.deepcopy(idle)
    for side in ('l','r'):
        loaded=Matrix.LocRotScale(grips[side].translation.lerp(floor_grips[side].translation,w),grips[side].to_quaternion().slerp(floor_grips[side].to_quaternion(),w),Vector((1,1,1)))
        grasp=Matrix.LocRotScale(loaded.translation.lerp(idle_grips[side].translation,returning),loaded.to_quaternion().slerp(idle_grips[side].to_quaternion(),returning),Vector((1,1,1)))
        hand=wpn@grasp
        shoulder=hold['upperarm_'+side].translation.lerp(idle['upperarm_'+side].translation+Vector((0,-.035,-.11)),w)
        shoulder=shoulder.lerp(idle['upperarm_'+side].translation,returning)
        reach=hand.translation-shoulder
        limit=((rest['lowerarm_'+side].translation-rest['upperarm_'+side].translation).length+(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).length)*.985
        if reach.length>limit:shoulder+=reach.normalized()*(reach.length-limit)
        SHOULDER_OVERRIDES[side]=shoulder;axis=(hand.translation-shoulder).normalized()
        from_axis=(hold['hand_'+side].translation-hold['upperarm_'+side].translation).normalized()
        radial=hold['lowerarm_'+side].translation-hold['upperarm_'+side].translation
        radial=(radial-from_axis*radial.dot(from_axis)).normalized();transported=from_axis.rotation_difference(axis)@radial
        target=Vector((-.75 if side=='l' else .75,-.2,-.65));target=(target-axis*target.dot(axis)).normalized()
        target=Quaternion(axis,math.radians(floor_poles[side]))@target
        angle=unwrap(math.atan2(axis.dot(transported.cross(target)),transported.dot(target)),state.get(side+'_pole'))
        state[side+'_pole']=angle;guide=Quaternion(axis,angle*w)@transported
        pole=[guide.x*(1 if side=='r' else -1),guide.y,guide.z]
        CFG['elbow_pole_top'][side]=pole;CFG['elbow_pole_impact'][side]=pole
        solve_arm(out,side,hand,1.-returning,1.,0.,state)
    out['WPN_root']=wpn;return out
# Fit a small whole-palm regrip and elbow-plane change at the loaded floor pose.
# Fingers remain authored and closed on the same handle throughout the strike.
grasp_recipe={}
for side in ('l','r'):
    best=None
    for roll in range(-40,41,10):
        floor_grips[side]=Quaternion((0,0,1),math.radians(roll)).to_matrix().to_4x4()@grips[side]
        for pole in range(-30,31,10):
            floor_poles[side]=pole;probe=solve(floor,1.,{})
            fore=(probe['hand_'+side].translation-probe['lowerarm_'+side].translation).normalized()
            neutral=probe['hand_'+side].to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
            cost=neutral.angle(fore)**2+.035*math.radians(roll)**2+.025*math.radians(pole)**2
            if best is None or cost<best[0]:best=(cost,roll,pole,floor_grips[side].copy())
    floor_grips[side]=best[3];floor_poles[side]=best[2];grasp_recipe[side]={'palm_roll_degrees':best[1],'elbow_pole_degrees':best[2]}
charge=[]
for i in range(2*FPS+1):
    t=i/FPS;source_time=.13*ease(t/.65) if t<=.65 else .13+.0566666667*ease((t-.65)/.95)
    scene.frame_set(int(source_time*150),subframe=source_time*150-int(source_time*150))
    charge.append({b.name:b.matrix.copy() for b in rig.pose.bones})
charge[-1]=copy.deepcopy(hold);release=[];state={}
for i in range(FPS+1):
    t=i/FPS;down=ease(t/.075);ret=ease((t-.2875)/.7125)
    if t<=.018:wpn=blend(top,over,ease(t/.018))
    elif t<=.042:wpn=blend(over,front,(t-.018)/.024)
    elif t<=.075:wpn=blend(front,floor,1-(1-(t-.042)/.033)**1.5)
    elif t<=.2875:wpn=floor
    elif t<=.5875:wpn=blend(floor,recover,ease((t-.2875)/.30))
    else:wpn=blend(recover,idle['WPN_root'],ease((t-.5875)/.4125))
    release.append(solve(wpn,down,state,ret))
release[0]=copy.deepcopy(hold);release[-1]=copy.deepcopy(idle)
for name,poses in (('A_Warhammer_HeavyCharge',charge),('A_Warhammer_HeavyRelease',release)):bake(name,poses,FPS)
hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest['WPN_root'].inverted()
head=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
head=[p for p in head if p.z>.78];lowest=min((floor@p).z for p in head)
contact=[p for p in head if (floor@p).z<=lowest+.002];marker=sum(contact,Vector())/len(contact)
receipt={'fps':FPS,'charge_seconds':2.,'release_seconds':1.,'floor_contact_seconds':.075,
    'grasp_recipe':grasp_recipe,
    'reference_positions_m':{n:list(rest[n].translation) for n in ('clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r','WPN_root')},
    'head_marker_author_world_m':list(rest['WPN_root']@marker),'head_marker_author_local_m':list(marker),
    'clips':['A_Warhammer_HeavyCharge','A_Warhammer_HeavyRelease'],'runtime_tested':False,'rendered':False}
rig.animation_data.action=bpy.data.actions['A_Warhammer_HeavyRelease'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(36)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_HeavySlam_Editable.blend'))
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print('WARHAMMER_HEAVY_AUTHORED '+json.dumps(receipt))
