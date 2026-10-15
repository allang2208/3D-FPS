"""V6: wider head thrust, supported shoulders; runtime phases span 0.72 seconds."""
import ast,copy,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=300;DURATION=.5;PREPARE=.09;CONTACT=.15;FOLLOW=.175;RETURN=.33
SWORD=ROOT/'SourceAssets/RuneSword20260913/StrideThrustV16'
DONOR=ROOT/'SourceAssets/ThrustElbowRepair20260923/Standard/Thrust_ElbowSupport_Editable.blend'
sys.path.insert(0,str(SWORD));import thrust_motion as sword
bpy.ops.wm.open_mainfile(filepath=str(DONOR))
donor=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
source_rest={b.name:b.matrix_local.copy() for b in donor.data.bones}
source_parents={b.name:b.parent.name if b.parent else None for b in donor.data.bones}
source_local_rest={n:source_rest[p].inverted()@m if p else m for n,m in source_rest.items() for p in [source_parents[n]]}
source=[];clock=[(0.,0.),(.05,.24),(PREPARE,.40),(CONTACT,.55),(FOLLOW,.58),(.20,.64),(RETURN,.94),(DURATION,1.25)]
for i in range(round(DURATION*FPS)+1):
    t=i/FPS;k=min(len(clock)-2,next((j for j in range(len(clock)-1) if t<=clock[j+1][0]),len(clock)-2))
    a,b=clock[k:k+2];f=(a[1]+(b[1]-a[1])*(t-a[0])/(b[0]-a[0]))*480
    bpy.context.scene.frame_set(int(f),subframe=f-int(f));source.append({b.name:b.matrix.copy() for b in donor.pose.bones})
SOURCE=P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
idle_local={n:idle[p].inverted()@m if p else m for n,m in idle.items() for p in [parents[n]]}
grips={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
pivot=(idle['hand_l'].translation+idle['hand_r'].translation)*.5;pivot_local=idle['WPN_root'].inverted()@pivot
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
module=ast.parse((P.parent/'WhirlwindHandoffV5/author_whirlwind.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'rigid','frame','axial','quintic','solve_arm'}],type_ignores=[]),'<native_grip_support>','exec'))
def alignment(t):return ease(t/PREPARE)*(1-ease((t-RETURN)/(DURATION-RETURN)))

# Keep corrected sword FK support through native rest frames. Widening the
# palms is solved afterward; do not transplant the sword's narrower grip.
references=[]
for i,src in enumerate(source):
    weight=alignment(i/FPS);local={}
    for n in rest:
        a=idle_local[n];p=source_parents.get(n)
        b=(src[p].inverted()@src[n] if p else src[n]) if n in src else a
        if n in source_local_rest:b=local_rest[n]@source_local_rest[n].inverted()@b
        av,aq,scale=a.decompose();bv,bq,_=b.decompose();v=av.lerp(bv,weight)
        if n.startswith(('upperarm','lowerarm','hand_')) and v.length>1e-8:v=v.normalized()*av.length
        local[n]=Matrix.LocRotScale(v,aq.slerp(bq,weight),scale)
    ref={}
    def solve_ref(n):
        if n not in ref:ref[n]=solve_ref(parents[n])@local[n] if parents[n] else local[n]
        return ref[n]
    for n in local:solve_ref(n)
    references.append(ref)

base=idle['WPN_root'].to_quaternion();axis0=base@Vector((0,0,1))
axis=sword.poses(sword.EXTENSION_END)[1].to_quaternion()@Vector((0,0,1));axis.normalize()
aimed=axis0.rotation_difference(axis)@base
loaded=Vector((.10,.30,-.25));zero=Vector((0,0,0))
knots=[(0.,pivot,zero,zero),(.05,Vector((.105,.355,-.245)),Vector((0,-.5,-.2)),zero),
       (PREPARE,loaded,zero,zero),(CONTACT,loaded+axis*.29,axis*3.8,axis*-120.),
       (FOLLOW,loaded+axis*.34,zero,axis*-40.),
       (RETURN,Vector((.105,.34,-.24)),Vector((-.15,0,.12)),Vector((0,2.,0))),
       (DURATION,pivot,zero,zero)]
def weapon(t):
    k=min(len(knots)-2,next((i for i in range(len(knots)-1) if t<=knots[i+1][0]),len(knots)-2))
    a,b=knots[k:k+2];d=b[0]-a[0];p=quintic(*a[1:],*b[1:],d,(t-a[0])/d)
    q=base.slerp(aimed,alignment(t));return rigid(p-q@pivot_local,q)

# Closed palms settle around the shaft toward the corrected donor palm frame.
# Axial spacing, radial distance and all finger poses stay fixed throughout.
PALM_ROLL={};palm_fit={}
for side in ('l','r'):
    fits=[]
    for roll in range(-180,181):
        g=Quaternion((0,0,1),math.radians(roll)).to_matrix().to_4x4()@grips[side]
        angles=[]
        for t in (PREPARE,CONTACT,FOLLOW):
            h=(weapon(t)@g).to_quaternion();ref=references[round(t*FPS)]['hand_'+side].to_quaternion()
            angles.append(2*math.acos(min(1.,abs(h.dot(ref)))))
        fits.append((sum(x*x for x in angles)+.004*(roll/90.)**2,roll,angles))
    _,PALM_ROLL[side],angles=min(fits);palm_fit[side]=[math.degrees(a) for a in angles]

explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
roll_state={};poses=[]
for i,ref in enumerate(references):
    t=i/FPS;w=weapon(t);pose=copy.deepcopy(idle);pose['WPN_root']=w
    for side in ('l','r'):
        grasp=Quaternion((0,0,1),math.radians(PALM_ROLL[side])*alignment(t)).to_matrix().to_4x4()@grips[side]
        support=copy.deepcopy(ref)
        # Carry the larger reach from the shoulder while retaining flexion.
        # The existing complete-chain solver keeps native lengths and distributes
        # any remaining palm roll; no isolated wrist rotation or arm scaling.
        thrust=ease((t-PREPARE)/(CONTACT-PREPARE))*(1-ease((t-FOLLOW)/(RETURN-FOLLOW)))
        down=Vector((0,0,-.045*alignment(t)-.015*thrust))+axis*(.045*thrust)
        for b in rig.data.bones:
            if b.name=='clavicle_'+side or any(p.name=='clavicle_'+side for p in b.parent_recursive):support[b.name].translation+=down
        solve_arm(pose,support,w@grasp,side)
    done=set(explicit)
    def resolve(n):
        if n not in done:
            pose[n]=resolve(parents[n])@idle_local[n] if parents[n] else idle[n].copy();done.add(n)
        return pose[n]
    for n in pose:resolve(n)
    for side in ('l','r'):
        n='ik_hand_'+side
        if n in pose:pose[n]=pose['hand_'+side]@idle['hand_'+side].inverted()@idle[n]
    poses.append(pose)
poses[0]=copy.deepcopy(idle);poses[-1]=copy.deepcopy(idle)

hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest['WPN_root'].inverted()
head=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
head=[p for p in head if p.z>.78];front=max(p.z for p in head)
cap=[p for p in head if p.z>=front-.002];marker=sum(cap,Vector())/len(cap)
header='#pragma once\n#include "CoreMinimal.h"\n// Native WPN_root units: the imported socket already carries the 100x conversion.\nnamespace WarhammerQuickCombat { inline const FVector StrikeLocal(%.9f,%.9f,%.9f); }\n'%(marker.x,-marker.y,marker.z)
(ROOT/'Source/FPSGAME/Production/WarhammerQuickCombatMarker.h').write_text(header,encoding='utf-8')
name='A_Warhammer_QuickCombat';bake(name,poses,FPS)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_QuickCombat_ReachV6_Editable.blend'))
receipt={'revision':'HeadThrustReachV6_20261015','clips':[name],'fps':FPS,'seconds':DURATION,'prepare_seconds':PREPARE,'contact_seconds':CONTACT,'follow_seconds':FOLLOW,
 'source':str(SOURCE),'sword_arm_donor':str(DONOR),'sword_reference':str(SWORD/'thrust_motion.py'),'sword_reference_axis':list(axis),'closed_palm_roll_degrees':PALM_ROLL,
 'palm_fit_to_sword_degrees_prepare_contact_follow':palm_fit,'forward_stroke_m':.34,'contact_forward_stroke_m':.29,'contact_forward_speed_m_s':3.8,'return_corner_seconds':RETURN,
 'runtime_seconds':.72,'runtime_prepare_seconds':.22,'runtime_contact_seconds':.28,'runtime_follow_seconds':.34,
 'runtime_source_map':'Source/FPSGAME/Production/WarhammerQuickCombatMotion.h',
 'extra_shoulder_support_m':{'forward':.045,'down':.015},
 'grip':'Closed native palms/fingers settle circumferentially; fixed axial spacing/radius, no release or slide; full donor-guided arm support',
 'arm_support':'Corrected sword FK and elbow support; native bone lengths, low shoulders and gradual additional forearm roll distribution',
 'strike_local_blender_m':list(marker),'strike_local_ue_native':[marker.x,-marker.y,marker.z],
 'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_HEAD_THRUST_AUTHORED '+json.dumps(receipt))
