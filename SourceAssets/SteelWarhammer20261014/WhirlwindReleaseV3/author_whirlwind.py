"""Two visible hammer drives, left-hand release and a right-hand inertial finish.

The camera still owns the two full revolutions. This clip supplies the weapon's
anticipation, cross-body drives and an independent single-hand follow-through.
Native grip frames, segment lengths and the existing supported arm solver remain.
"""
import ast,bisect,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=300;DURATION=1.82
SOURCE=P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1']
rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
idle_local={n:idle[p].inverted()@m if p else m for n,m in idle.items() for p in [parents[n]]}
ready=idle['WPN_root'];base=ready.to_quaternion()
grips={s:ready.inverted()@idle['hand_'+s] for s in ('l','r')}
pivot=(grips['l'].translation+grips['r'].translation)*.5
center=ready@pivot
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and
    n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))

def sat(x):return max(0.,min(1.,x))
def smooth(x):return sat(ease(sat(x)))
def rigid(p,q):return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def blend(a,b,w):return rigid(a.translation.lerp(b.translation,w),a.to_quaternion().slerp(b.to_quaternion(),w))
def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()
def axial(q,axis):
    a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (a+math.pi)%(2*math.pi)-math.pi
def logq(q):
    q=q.normalized()
    if q.w<0:q.negate()
    angle=2*math.acos(max(-1.,min(1.,q.w)));axis=Vector((q.x,q.y,q.z))
    return axis.normalized()*angle if axis.length>1e-8 else Vector((0,0,0))
def expq(v):return Quaternion(v.normalized(),v.length) if v.length>1e-8 else Quaternion((1,0,0,0))

# Same anticipation / two-drive / follow-through structure as sword V5/V6.
# Positions are authored in camera space (+X right, +Y forward, +Z up).
# The wider hammer grasp needs its own trajectory rather than a scaled sword pose.
KEYS=[
    (0.,None,None),
    (.16,(.75,.04,.66),(.12,.36,-.18)),
    (.36,(.65,.10,.75),(.15,.31,-.19)),
    (.50,(.98,.17,-.10),(.055,.35,-.245)),
    (.63,(.85,.48,-.20),(-.035,.445,-.22)),
    (.82,(.99,.08,.04),(.02,.35,-.26)),
    (.91,(.96,-.05,.27),(.09,.32,-.20)),
    (1.045,(.84,.50,-.21),(-.04,.45,-.225)),
    (1.15,(.95,.24,-.19),(.01,.39,-.26)),
    (1.24,(.85,.45,-.28),(.085,.46,-.255)),
    (1.42,(.70,.70,-.14),None),
    (1.50,(.69,.70,-.17),None),
    (1.62,(.86,.44,.23),None),
    (1.72,(.91,.22,.35),None),
    (DURATION,None,None)]
RIGHT_TARGETS={1.42:(.292,.563,-.269),1.50:(.305,.57,-.285),
               1.62:(.24,.49,-.23),1.72:(.19,.445,-.205)}
times=[k[0] for k in KEYS];positions=[];rotations=[]
for t,direction,grip_center in KEYS:
    if direction is None:q=base.copy();right=idle['hand_r'].translation.copy()
    else:
        q=(base@Vector((0,0,1))).rotation_difference(Vector(direction).normalized())@base
        right=Vector(RIGHT_TARGETS[t]) if grip_center is None else Vector(grip_center)+q@(grips['r'].translation-pivot)
    positions.append(right);rotations.append(logq(base.inverted()@q))

def tangents(values):
    velocity=[Vector((0,0,0)) for _ in values]
    for i in range(1,len(values)-1):
        before=times[i]-times[i-1];after=times[i+1]-times[i]
        a=(values[i]-values[i-1])/before;b=(values[i+1]-values[i])/after
        for axis in range(3):
            if a[axis]*b[axis]>0:
                w1=2*after+before;w2=after+2*before
                slope=(w1+w2)/(w1/a[axis]+w2/b[axis])
                velocity[i][axis]=math.copysign(min(abs(slope),1.5*min(abs(a[axis]),abs(b[axis]))),slope)
    return velocity
position_velocity=tangents(positions);rotation_velocity=tangents(rotations)
def curve(values,velocity,t):
    t=max(times[0],min(times[-1],t));i=min(len(times)-2,max(0,bisect.bisect_right(times,t)-1))
    duration=times[i+1]-times[i];u=(t-times[i])/duration
    a=values[i];d=values[i+1]-a;v0=velocity[i]*duration;v1=velocity[i+1]*duration
    return a+v0*u+(10*d-6*v0-4*v1)*u**3+(-15*d+8*v0+7*v1)*u**4+(6*d-3*v0-3*v1)*u**5
def weapon_frame(t):
    q=base@expq(curve(rotations,rotation_velocity,t));right=curve(positions,position_velocity,t)
    return rigid(right-q@grips['r'].translation,q)

free_left=idle['hand_l'].copy();free_left.translation=Vector((-.23,.32,-.33))
release_hand=weapon_frame(1.17)@grips['l']
free_left=rigid(free_left.translation,idle['hand_l'].to_quaternion().slerp(release_hand.to_quaternion(),.15))
radial=grips['l'].translation-Vector((0,0,grips['l'].translation.z))
radial.normalize()

def hand_target(weapon,side,t):
    contact=weapon@grips[side]
    if side=='r':return contact
    # Open before pulling away. Depart radially from the shaft and then tuck
    # down-left; approach from that same clear side before closing the fingers.
    release=smooth((t-1.17)/.08)
    attach=smooth((t-1.60)/.09)
    away=contact.copy()
    away.translation+=(weapon.to_quaternion()@radial)*(.09*release*(1-attach))
    free=smooth((t-1.24)/.15)*(1-smooth((t-1.49)/.15))
    return blend(away,free_left,free)

def arm(pose,target,side,t):
    U,L,H,C=['upperarm_'+side,'lowerarm_'+side,'hand_'+side,'clavicle_'+side]
    d=target@idle[H].inverted();dq=d.to_quaternion()
    s0,e0,h0=[idle[n].translation for n in (U,L,H)]
    u0,l0=e0-s0,h0-e0;normal=u0.cross(l0).normalized()
    ideal_e=d@e0;h=target.translation
    # Chest follows the right-hand inertial arc, then returns before idle.
    carry=smooth((t-1.15)/.27)*(1-smooth((t-1.50)/.32))
    torso=Vector((.025,.045,-.015))*carry
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
    e=circle+guide.normalized()*radius;upper=e-s;fore=h-e
    plane=upper.cross(fore).normalized()
    du=frame(upper,plane)@frame(u0,normal).inverted()
    df=(du@l0).rotation_difference(fore)@du
    full_fore=(dq@l0).rotation_difference(fore)@dq
    roll=axial(full_fore@df.inverted(),fore.normalized())
    pose[C]=idle[C].copy();pose[C].translation+=s-s0
    pose[U]=rigid(s,du@idle[U].to_quaternion())
    pose[L]=rigid(e,df@idle[L].to_quaternion());pose[H]=target
    for index in ('01','02'):
        k='upperarm_twist_'+index+'_'+side
        pose[k]=rigid(s+du@(idle[k].translation-s0),du@idle[k].to_quaternion())
        k='lowerarm_twist_'+index+'_'+side;station=STATIONS[side][k]
        pose[k]=rigid(e+df@(idle[k].translation-e0),Quaternion(fore.normalized(),roll*station)@df@idle[k].to_quaternion())

def local_finger(n,t):
    original=idle_local[n]
    if not n.endswith('_l') or not n.startswith(('thumb','index','middle','ring','pinky')):return original
    digit=n.split('_')[0]
    delay={'thumb':.0,'index':.008,'middle':.014,'ring':.020,'pinky':.026}[digit]
    opening=smooth((t-1.13-delay)/.075)*(1-smooth((t-1.685-delay)/.075))
    # Relax toward this rig's own open-hand rest rotations; retain each finger
    # base, bone translation and a small natural curl rather than inventing axes.
    factor=.55 if digit=='thumb' else (.58 if '_01_' in n else .86)
    p,q,scale=original.decompose()
    return Matrix.LocRotScale(p,q.slerp(local_rest[n].to_quaternion(),opening*factor),scale)

anchors={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
anchors.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
poses=[]
for i in range(round(DURATION*FPS)+1):
    t=i/FPS;weapon=weapon_frame(t);pose={n:m.copy() for n,m in idle.items()}
    for side in ('l','r'):arm(pose,hand_target(weapon,side,t),side,t)
    pose['WPN_root']=weapon;done=set(anchors)
    def resolve(n):
        if n in done:return pose[n]
        p=parents[n];pose[n]=resolve(p)@local_finger(n,t) if p else idle[n].copy()
        done.add(n);return pose[n]
    for n in pose:resolve(n)
    for side in ('l','r'):
        k='ik_hand_'+side
        if k in pose:pose[k]=pose['hand_'+side]@idle['hand_'+side].inverted()@idle[k]
    if i==0 or i==round(DURATION*FPS):pose=copy.deepcopy(idle)
    poses.append(pose)
name='A_Warhammer_Whirlwind';bake(name,poses,FPS)
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Whirlwind_Release_Editable.blend'))
receipt={'clips':[name],'fps':FPS,'seconds':DURATION,'source':str(SOURCE),
    'sword_reference':str(ROOT/'SourceAssets/Whirlwind20260920/RecoverV6/WhirlwindRecover_Manny_Editable.blend'),
    'revision':'LeftReleaseV3_20261014','runtime_destination':'/Game/Weapons/SteelWarhammer20261014/WhirlwindV1',
    'weapon_key_seconds':times,'weapon_key_right_wrist_m':[list(v) for v in positions],
    'weapon_key_directions':[list(weapon_frame(t).to_quaternion()@Vector((0,0,1))) for t in times],
    'left_hand_open_start':1.13,'left_hand_depart_start':1.17,'left_hand_free_start':1.25,
    'left_hand_return_start':1.49,'left_hand_contact_seconds':1.69,'left_hand_closed_seconds':1.786,
    'right_grip':'Exact idle hand-to-weapon frame throughout',
    'left_grip':'Exact idle grasp before release and after regrip; explicit independent open-hand path during release',
    'arm_policy':'Existing supported two-bone circle with native segment lengths, native skin stations and full hand targets',
    'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_WHIRLWIND_RELEASE_AUTHORED '+json.dumps(receipt))
