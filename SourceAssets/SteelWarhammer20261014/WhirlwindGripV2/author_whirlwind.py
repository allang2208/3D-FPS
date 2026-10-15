"""Keep the complete hammer idle grasp; use a supported whole-arm solve.

The source supplies timing and the weapon arc, never sword hand/finger poses.
The shoulders support fixed-length elbow circles; palm pronation is distributed
over existing skin stations and the hands remain fixed on the original shaft.
"""
import ast,copy,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=300;DURATION=1.82
SOURCE=P.parent/'WhirlwindV1/Warhammer_Whirlwind_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig']
rig.animation_data.action=bpy.data.actions['A_Warhammer_Whirlwind'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
trajectory=[]
for i in range(round(DURATION*FPS)+1):
    scene.frame_set(i);trajectory.append(rig.pose.bones['WPN_root'].matrix.copy())
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
idle_local={n:idle[p].inverted()@m if p else m for n,m in idle.items() for p in [parents[n]]}
ready=idle['WPN_root'];grips={s:ready.inverted()@idle['hand_'+s] for s in ('l','r')}
pivot=(grips['l'].translation+grips['r'].translation)*.5;center=ready@pivot
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and
    n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
def sat(x):return max(0.,min(1.,x))
def smooth(x):return sat(ease(x))
def rigid(p,q):return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()
def axial(q,axis):
    a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (a+math.pi)%(2*math.pi)-math.pi
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
def curve(keys,t):
    if t<=keys[0][0]:return keys[0][1]
    for a,b in zip(keys,keys[1:]):
        if t<=b[0]:
            d=b[0]-a[0];u=(t-a[0])/d
            return (2*u**3-3*u*u+1)*a[1]+(u**3-2*u*u+u)*d*a[2]+(-2*u**3+3*u*u)*b[1]+(u**3-u*u)*d*b[2]
    return keys[-1][1]
OUTWARD=[(0.,0.,0.),(1.3,0.,0.),(1.405,.075,.65),(1.48,.115,0.),(1.545,.108,-.15),(1.82,0.,0.)]
def weapon_frame(src,t,amount):
    if t<=1.3:
        q=ready.to_quaternion().slerp(src.to_quaternion(),amount)
        c=center.lerp(src@pivot,amount)
    else:
        # V1's late sword-to-hammer hand blend introduces a shaft-frame jump.
        # Recover from the exact spin-end frame; do not inherit that old tail.
        end=trajectory[390]
        start_q=ready.to_quaternion().slerp(end.to_quaternion(),amount)
        restore=.7*smooth((t-1.3)/.18)+.3*smooth((t-1.48)/.34)
        q=start_q.slerp(ready.to_quaternion(),sat(restore))
        c=center.lerp(end@pivot,amount).lerp(center,smooth((t-1.48)/.34))
    out=curve(OUTWARD,t)
    c+=Vector((.22*out,out,-.18*out))
    return rigid(c-q@pivot,q)

def arm(pose,weapon,side,t):
    U,L,H,C=['upperarm_'+side,'lowerarm_'+side,'hand_'+side,'clavicle_'+side]
    d=weapon@ready.inverted();dq=d.to_quaternion()
    s0,e0,h0=[idle[n].translation for n in (U,L,H)]
    u0,l0=e0-s0,h0-e0;normal=u0.cross(l0).normalized()
    ideal_e=d@e0;h=d@h0
    torso=Vector((0,.04,-.008))*sat(curve(OUTWARD,t)/.115)
    reference=s0+torso
    ideal_s=ideal_e-(ideal_e-reference).normalized()*u0.length
    support=ideal_s-reference
    if support.length>.055:support=support.normalized()*.055
    s=reference+support;reach=h-s;limit=(u0.length+l0.length)*.96
    if reach.length>limit:s+=reach.normalized()*(reach.length-limit);reach=h-s
    axis=reach.normalized();distance=reach.length
    along=(u0.length**2-l0.length**2+distance**2)/(2*distance)
    radius=math.sqrt(max(0.,u0.length**2-along**2));circle=s+axis*along
    guide=ideal_e-circle;guide-=axis*guide.dot(axis)
    if guide.length<1e-6:
        guide=dq@(e0-s0);guide-=axis*guide.dot(axis)
    e=circle+guide.normalized()*radius;upper=e-s;l=h-e
    # Continuous closest supported elbow on a fixed-length two-bone circle.
    # Limit shoulder assistance and distribute forearm pronation over the skin.
    plane=upper.cross(l).normalized()
    du=frame(upper,plane)@frame(u0,normal).inverted()
    df=(du@l0).rotation_difference(l)@du
    full_fore=(dq@l0).rotation_difference(l)@dq
    roll=axial(full_fore@df.inverted(),l.normalized())
    pose[C]=idle[C].copy();pose[C].translation+=s-s0
    pose[U]=rigid(s,du@idle[U].to_quaternion())
    pose[L]=rigid(e,df@idle[L].to_quaternion());pose[H]=weapon@grips[side]
    for index in ('01','02'):
        k='upperarm_twist_'+index+'_'+side
        pose[k]=rigid(s+du@(idle[k].translation-s0),du@idle[k].to_quaternion())
        k='lowerarm_twist_'+index+'_'+side;station=STATIONS[side][k]
        pose[k]=rigid(e+df@(idle[k].translation-e0),Quaternion(l.normalized(),roll*station)@df@idle[k].to_quaternion())
    swing=u0.normalized().rotation_difference(upper.normalized())
    return {'shoulder_shift_m':(s-s0).length,'elbow_degrees':math.degrees(upper.angle(l)),
            'forearm_roll_degrees':math.degrees(roll),'upper_roll_degrees':math.degrees(axial(du@swing.inverted(),upper.normalized())),
            'extra_wrist_bend_degrees':math.degrees((dq@l0).angle(l)),
            'upper_length_m':upper.length,'lower_length_m':l.length}

def make_pose(src,t,amount):
    weapon=weapon_frame(src,t,amount);pose={n:m.copy() for n,m in idle.items()}
    measures={side:arm(pose,weapon,side,t) for side in ('l','r')}
    anchors={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
    anchors.update(n for n in pose if n.startswith(('upperarm_twist','lowerarm_twist')))
    pose['WPN_root']=weapon
    # Helpers and digits preserve their accepted idle relationship to the
    # actual parent segment, including both upperarm twist branches.
    done=set(anchors)
    def resolve(n):
        if n in done:return pose[n]
        p=parents[n];pose[n]=resolve(p)@idle_local[n] if p else idle[n].copy();done.add(n);return pose[n]
    for n in pose:resolve(n)
    for side in ('l','r'):
        k='ik_hand_'+side
        if k in pose:pose[k]=pose['hand_'+side]@idle['hand_'+side].inverted()@idle[k]
    if t<=0. or t>=DURATION:pose=copy.deepcopy(idle)
    return pose,measures

if '--design-inputs' in sys.argv:
    report={}
    for amount in (0.,.15,.25,.35,.5,.65):
        rows=[make_pose(src,i/FPS,amount)[1] for i,src in enumerate(trajectory)]
        report[str(amount)]={s:{'max_shoulder_shift_cm':100*max(x[s]['shoulder_shift_m'] for x in rows),
            'elbow_degrees':[min(x[s]['elbow_degrees'] for x in rows),max(x[s]['elbow_degrees'] for x in rows)],
            'forearm_roll_max':max(abs(x[s]['forearm_roll_degrees']) for x in rows),
            'wrist_bend_max':max(x[s]['extra_wrist_bend_degrees'] for x in rows),
            'wrist_peak_seconds':max(range(len(rows)),key=lambda i:rows[i][s]['extra_wrist_bend_degrees'])/FPS,
            'spin_wrist_bend_max':max(x[s]['extra_wrist_bend_degrees'] for x in rows[:391]),
            'upper_roll_max':max(abs(x[s]['upper_roll_degrees']) for x in rows)} for s in ('l','r')}
    (P/'design_inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report));raise SystemExit(0)
AMOUNT=.65
poses=[];measurements=[]
for i,src in enumerate(trajectory):
    pose,m=make_pose(src,i/FPS,AMOUNT);poses.append(pose);measurements.append(m)
name='A_Warhammer_Whirlwind';bake(name,poses,FPS)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Whirlwind_IdleGrip_Editable.blend'))
receipt={'clips':[name],'fps':FPS,'seconds':DURATION,'source':str(SOURCE),'sword_arc_weight':AMOUNT,
    'runtime_destination':'/Game/Weapons/SteelWarhammer20261014/WhirlwindV1',
    'grip':'Exact complete warhammer idle hand-to-weapon matrices and idle digit poses throughout',
    'grip_width_m':(idle['hand_r'].translation-idle['hand_l'].translation).length,
    'outward_peak_m':.115,'outward_peak_seconds':1.48,'spin_end_seconds':1.3,
    'arm_policy':'Exact idle hand-to-shaft frames; continuous supported elbow circles; small distributed forearm pronation; fixed segment lengths',
    'max_shoulder_shift_cm':{s:100*max(x[s]['shoulder_shift_m'] for x in measurements) for s in ('l','r')},
    'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_IDLE_GRIP_WHIRLWIND_AUTHORED '+json.dumps(receipt))
