"""A wider right-hand carry with delayed hammer turnover and an arcing brake.

The left palm exits below the frame, relaxes while the right arm carries the
hammer, then returns from below. Right-hand contact remains exact throughout.
"""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=300;DURATION=1.82;TAIL=1.16;PEAK=1.48
WRIST_PEAK=1.46;HAMMER_PEAK=1.52;OUTWARD_TURN_DEGREES=105.
TUNING=json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8'))['whirlwind']
def playback_time(t):
    if t<=.5:return t*TUNING['readySeconds']/.5
    if t<=1.3:return TUNING['readySeconds']+(t-.5)*TUNING['spinSeconds']/.8
    return TUNING['readySeconds']+TUNING['spinSeconds']+(t-1.3)*TUNING['recoverSeconds']/.52
SOURCE=ROOT/'SourceAssets/Whirlwind20260920/RecoverV6/WhirlwindRecover_Manny_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene;source_rig=bpy.data.objects['SK_RuneSword_Rig']
source_rest={b.name:b.matrix_local.copy() for b in source_rig.data.bones}
source_parents={b.name:b.parent.name if b.parent else None for b in source_rig.data.bones}
source_local_rest={n:source_rest[p].inverted()@m if p else m for n,m in source_rest.items() for p in [source_parents[n]]}
source=[]
for i in range(round(DURATION*FPS)+1):
    f=i/FPS*480;scene.frame_set(int(f),subframe=f-int(f));source.append({b.name:b.matrix.copy() for b in source_rig.pose.bones})

BASELINE=P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(BASELINE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
idle_local={n:idle[p].inverted()@m if p else m for n,m in idle.items() for p in [parents[n]]}
base=idle['WPN_root'].to_quaternion();axis0=base@Vector((0,0,1))
grips={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))

def sat(x):return max(0.,min(1.,x))
def smooth(x):return sat(ease(sat(x)))
def rigid(p,q):return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def logq(q):
    q=q.normalized()
    if q.w<0:q.negate()
    v=Vector((q.x,q.y,q.z));a=2*math.atan2(v.length,q.w)
    return v.normalized()*a if v.length>1e-8 else Vector((0,0,0))
def expq(v):return Quaternion(v.normalized(),v.length) if v.length>1e-8 else Quaternion((1,0,0,0))
def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()
def axial(q,axis):
    a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (a+math.pi)%(2*math.pi)-math.pi

# The donor supplies complete shoulder/elbow motion, not just a few poses.
# Only the entry/exit adapts to the hammer idle. No sword compact grip is used.
references=[];raw_positions=[];raw_rotations=[]
for i,src in enumerate(source):
    t=i/FPS;entry=smooth(t/.32);weight=entry*(1-smooth((t-PEAK)/(DURATION-PEAK)))
    local={}
    for n in rest:
        a=idle_local[n];p=source_parents.get(n)
        b=(src[p].inverted()@src[n] if p else src[n]) if n in src else a
        b=local_rest[n]@source_local_rest[n].inverted()@b if n in source_local_rest else a
        av,aq,ascale=a.decompose();bv,bq,_=b.decompose();v=av.lerp(bv,weight)
        if n.startswith(('upperarm','lowerarm','hand_')) and v.length>1e-8:v=v.normalized()*av.length
        local[n]=Matrix.LocRotScale(v,aq.slerp(bq,weight),ascale)
    ref={}
    def resolve_ref(n):
        if n not in ref:ref[n]=resolve_ref(parents[n])@local[n] if parents[n] else local[n]
        return ref[n]
    for n in local:resolve_ref(n)
    references.append(ref)
    direction=src['WPN_root'].to_quaternion()@Vector((0,0,1))
    fitted=axis0.rotation_difference(direction)@base
    q=base.slerp(fitted,entry)
    raw_positions.append(ref['hand_r'].translation.copy())
    raw_rotations.append(logq(base.inverted()@q))

def derivatives(values,t):
    i=round(t*FPS)
    rate=.8/TUNING['spinSeconds']
    return values[i],(values[i+1]-values[i-1])*(FPS*.5*rate),(values[i+1]-2*values[i]+values[i-1])*(FPS*FPS*rate*rate)
def quintic(p0,v0,a0,p1,v1,a1,d,u):
    # One polynomial carries the incoming velocity/acceleration all the way
    # into the brake, instead of easing separately at many intermediate keys.
    c0=p0;c1=v0*d;c2=a0*(d*d*.5)
    x=p1-c0-c1-c2;y=v1*d-c1-2*c2;z=a1*d*d-2*c2
    c3=10*x-4*y+.5*z;c4=-15*x+7*y-z;c5=6*x-3*y+.5*z
    return c0+c1*u+c2*u*u+c3*u**3+c4*u**4+c5*u**5
zero=Vector((0,0,0))
start_p=derivatives(raw_positions,TAIL);start_q=derivatives(raw_rotations,TAIL)
peak_position=Vector((.42,.48,-.31))
peak_velocity=Vector((0,-.10,-.20))
previous_peak_q=axis0.rotation_difference(Vector((.72,.65,.22)).normalized())@base
takeover_q=base@expq(start_q[0])
original_outward_turn=logq(takeover_q.inverted()@previous_peak_q)
peak_rotation=original_outward_turn.normalized()*math.radians(OUTWARD_TURN_DEGREES)
peak_q=takeover_q@expq(peak_rotation)
# Interpolate the tail around its takeover orientation. Increasing the angle
# must not cross the principal-log branch of an unrelated idle reference.
def takeover_delta(t):
    f=t*FPS;i=min(len(raw_rotations)-2,int(f))
    raw=raw_rotations[i].lerp(raw_rotations[i+1],f-i)
    return logq(takeover_q.inverted()@(base@expq(raw)))
h=1/FPS;rate=.8/TUNING['spinSeconds']
qa,qb,qc=takeover_delta(TAIL-h),takeover_delta(TAIL),takeover_delta(TAIL+h)
turn_start=(zero,(qc-qa)*(FPS*.5*rate),(qc-2*qb+qa)*(FPS*FPS*rate*rate))
turn_end=logq(takeover_q.inverted()@base)

def tail(values,start,peak,end,t,apex_time,apex_velocity):
    if t<=TAIL:
        f=t*FPS;i=min(len(values)-2,int(f));return values[i].lerp(values[i+1],f-i)
    now=playback_time(t);begin=playback_time(TAIL);apex=playback_time(apex_time);finish=playback_time(DURATION)
    # Nonzero restoring acceleration at the apex gives one connected brake
    # and return, without a flat zero-acceleration pause at maximum extension.
    apex_acceleration=(end-peak)*8.
    if t<=apex_time:
        return quintic(*start,peak,apex_velocity,apex_acceleration,apex-begin,(now-begin)/(apex-begin))
    return quintic(peak,apex_velocity,apex_acceleration,end,zero,zero,finish-apex,(now-apex)/(finish-apex))
def weapon(t):
    right=tail(raw_positions,start_p,peak_position,idle['hand_r'].translation,t,WRIST_PEAK,peak_velocity)
    if t<=TAIL:
        f=t*FPS;i=min(len(raw_rotations)-2,int(f))
        q=base@expq(raw_rotations[i].lerp(raw_rotations[i+1],f-i))
    else:
        q=takeover_q@expq(tail(raw_rotations,turn_start,peak_rotation,turn_end,t,HAMMER_PEAK,zero))
    return rigid(right-q@grips['r'].translation,q)

OPEN=.88;RELEASE=1.00;LOW=1.15;RETURN=1.50;CONTACT=1.72
release_rotation=(weapon(RELEASE)@grips['l']).to_quaternion()

# Build the hanging reference from native segment lengths and the idle wrist
# relationship. The elbow remains softly bent; the wrist is not folded down
# independently to force the hand below the camera.
relaxed=copy.deepcopy(idle)
s0,e0,h0=[idle[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
u0,l0=e0-s0,h0-e0
upper=Vector((-.20,.04,-.98)).normalized()*u0.length
fore=Vector((.20,.68,-.70)).normalized()*l0.length
elbow=s0+upper;free_position=elbow+fore
du=frame(upper,upper.cross(fore))@frame(u0,u0.cross(l0)).inverted()
df=(du@l0).rotation_difference(fore)@du
relaxed['upperarm_l']=rigid(s0,du@idle['upperarm_l'].to_quaternion())
relaxed['lowerarm_l']=rigid(elbow,df@idle['lowerarm_l'].to_quaternion())
relaxed['hand_l']=rigid(free_position,df@idle['hand_l'].to_quaternion())
for index in ('01','02'):
    n='upperarm_twist_'+index+'_l'
    relaxed[n]=rigid(s0+du@(idle[n].translation-s0),du@idle[n].to_quaternion())
    n='lowerarm_twist_'+index+'_l'
    relaxed[n]=rigid(elbow+df@(idle[n].translation-e0),df@idle[n].to_quaternion())
free_rotation=logq(release_rotation.inverted()@relaxed['hand_l'].to_quaternion())
free_velocity=Vector((.04,-.02,-.08))
return_position=free_position+Vector((.012,0,-.005))
return_velocity=Vector((.08,.05,.12))
left_chain=['clavicle_l','upperarm_l','upperarm_twist_01_l','upperarm_twist_02_l',
            'lowerarm_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l']

def left_reference(ref,t):
    now=playback_time(t)
    down=smooth((now-playback_time(RELEASE))/(playback_time(LOW)-playback_time(RELEASE)))
    up=smooth((now-playback_time(RETURN))/(playback_time(CONTACT)-playback_time(RETURN)))
    weight=down*(1-up)
    if weight<=0:return ref
    out=copy.deepcopy(ref);done=set()
    def resolve(n):
        if n not in left_chain:return out[n]
        if n in done:return out[n]
        parent=parents[n]
        a=ref[n] if n=='clavicle_l' else ref[parent].inverted()@ref[n]
        b=relaxed[n] if n=='clavicle_l' else relaxed[parent].inverted()@relaxed[n]
        ap,aq,ascale=a.decompose();bp,bq,_=b.decompose();p=ap.lerp(bp,weight)
        if n in {'upperarm_l','lowerarm_l','hand_l'} and p.length>1e-8:p=p.normalized()*ap.length
        m=Matrix.LocRotScale(p,aq.slerp(bq,weight),ascale)
        out[n]=m if n=='clavicle_l' else resolve(parent)@m
        done.add(n);return out[n]
    for n in left_chain:resolve(n)
    return out

def attached_left(t):return weapon(t)@grips['l']
def attached_rotation(t):return logq(release_rotation.inverted()@attached_left(t).to_quaternion())
def motion_derivatives(get_value,t):
    # Both boundaries sit within one playback phase. Express derivatives in
    # real seconds so the 1.3-second spin/recovery boundary has no speed jump.
    h=1/FPS;dt=(playback_time(t+h)-playback_time(t-h))*.5
    prev,now,next_value=get_value(t-h),get_value(t),get_value(t+h)
    return now,(next_value-prev)/(2*dt),(next_value-2*now+prev)/(dt*dt)
release_position=motion_derivatives(lambda t:attached_left(t).translation,RELEASE)
contact_position=motion_derivatives(lambda t:attached_left(t).translation,CONTACT)
release_orientation=motion_derivatives(attached_rotation,RELEASE)
contact_orientation=motion_derivatives(attached_rotation,CONTACT)

def hand_target(w,side,t):
    h=w@grips[side]
    if side=='r' or t<=RELEASE or t>=CONTACT:return h
    now=playback_time(t);begin=playback_time(RELEASE)
    lowered=playback_time(LOW);returning=playback_time(RETURN);finish=playback_time(CONTACT)
    # Lower, continue a small relaxed drift below frame, and reach up to catch.
    # Connected velocity/acceleration avoids stop-start changes of hand space.
    if t<=LOW:
        position=quintic(*release_position,free_position,free_velocity,zero,
                         lowered-begin,(now-begin)/(lowered-begin))
        rotation=quintic(*release_orientation,free_rotation,zero,zero,
                         lowered-begin,(now-begin)/(lowered-begin))
    elif t<=RETURN:
        position=quintic(free_position,free_velocity,zero,return_position,return_velocity,zero,
                         returning-lowered,(now-lowered)/(returning-lowered))
        rotation=free_rotation
    else:
        position=quintic(return_position,return_velocity,zero,*contact_position,
                         finish-returning,(now-returning)/(finish-returning))
        rotation=quintic(free_rotation,zero,zero,*contact_orientation,
                         finish-returning,(now-returning)/(finish-returning))
    return rigid(position,release_rotation@expq(rotation))

roll_state={}
def solve_arm(out,ref,target,side):
    U,L,H,C=[x+'_'+side for x in ('upperarm','lowerarm','hand','clavicle')]
    s0,e0,h0=[ref[n].translation for n in (U,L,H)];u0,l0=e0-s0,h0-e0
    normal=u0.cross(l0).normalized();d=target@ref[H].inverted();dq=d.to_quaternion()
    ideal_e=d@e0;h=target.translation
    ideal_s=ideal_e-(ideal_e-s0).normalized()*u0.length
    support=ideal_s-s0
    # Smooth shoulder assistance has no hard clamp corner in the pose path.
    support*=.055/math.sqrt(.055**2+support.length_squared)
    s=s0+support;reach=h-s;limit=(u0.length+l0.length)*.96
    if reach.length>limit:s+=reach.normalized()*(reach.length-limit);reach=h-s
    axis=reach.normalized();distance=reach.length
    along=(u0.length**2-l0.length**2+distance**2)/(2*distance)
    radius=math.sqrt(max(0.,u0.length**2-along**2));circle=s+axis*along
    guide=ideal_e-circle;guide-=axis*guide.dot(axis)
    if guide.length<1e-6:
        guide=dq@(e0-s0);guide-=axis*guide.dot(axis)
    e=circle+guide.normalized()*radius;upper=e-s;fore=h-e
    plane=upper.cross(fore).normalized();du=frame(upper,plane)@frame(u0,normal).inverted()
    df=(du@l0).rotation_difference(fore)@du
    full=(dq@l0).rotation_difference(fore)@dq;roll=axial(full@df.inverted(),fore.normalized())
    if side in roll_state:roll=roll_state[side]+((roll-roll_state[side]+math.pi)%(2*math.pi)-math.pi)
    roll_state[side]=roll
    out[C]=ref[C].copy();out[C].translation+=s-s0
    out[U]=rigid(s,du@ref[U].to_quaternion());out[L]=rigid(e,df@ref[L].to_quaternion());out[H]=target
    for index in ('01','02'):
        n='upperarm_twist_'+index+'_'+side
        out[n]=rigid(s+du@(ref[n].translation-s0),du@ref[n].to_quaternion())
        n='lowerarm_twist_'+index+'_'+side
        out[n]=rigid(e+df@(ref[n].translation-e0),Quaternion(fore.normalized(),roll*STATIONS[side][n])@df@ref[n].to_quaternion())

def finger_local(n,t):
    original=idle_local[n]
    if not n.endswith('_l') or not n.startswith(('thumb','index','middle','ring','pinky')):return original
    if 'metacarpal' in n:return original
    digit=n.split('_')[0]
    delay={'thumb':0.,'index':.004,'middle':.008,'ring':.012,'pinky':.016}[digit]
    # Open before leaving. Keep an open C-shaped palm through the catch, then
    # close on the actual shaft instead of closing a fist while still in air.
    now=playback_time(t);open_start=playback_time(OPEN)+delay
    close_start=playback_time(CONTACT)+delay
    opened=smooth((now-open_start)/.12)*(1-smooth((now-close_start)/.08))
    # Unclasp to leave the shaft, then let the fingers curl softly while the
    # arm hangs; open into a receiving C-shape before the hand rises to catch.
    relax=smooth((now-playback_time(RELEASE+.08))/.16)*(1-smooth((now-playback_time(RETURN))/.11))
    opened*=1-.45*relax
    amount=(.78 if '_01_' in n else .90) if digit=='thumb' else (.94 if '_01_' in n else .98)
    p,q,scale=original.decompose()
    return Matrix.LocRotScale(p,q.slerp(local_rest[n].to_quaternion(),amount*opened),scale)

explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
poses=[]
for i,ref in enumerate(references):
    t=i/FPS;w=weapon(t);pose=copy.deepcopy(idle);pose['WPN_root']=w
    for side in ('l','r'):
        support=left_reference(ref,t) if side=='l' else ref
        solve_arm(pose,support,hand_target(w,side,t),side)
    done=set(explicit)
    def resolve(n):
        if n in done:return pose[n]
        p=parents[n];pose[n]=resolve(p)@finger_local(n,t) if p else idle[n].copy();done.add(n);return pose[n]
    for n in pose:resolve(n)
    for side in ('l','r'):
        n='ik_hand_'+side
        if n in pose:pose[n]=pose['hand_'+side]@idle['hand_'+side].inverted()@idle[n]
    if i in (0,len(references)-1):pose=copy.deepcopy(idle)
    poses.append(pose)
name='A_Warhammer_Whirlwind';bake(name,poses,FPS)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Whirlwind_Inertia_Editable.blend'))
receipt={'clips':[name],'fps':FPS,'seconds':DURATION,'source':str(SOURCE),'baseline':str(BASELINE),
    'revision':'WiderInertiaV8_20261015','runtime_destination':'/Game/Weapons/SteelWarhammer20261014/WhirlwindV1',
    'accepted_direction_source':str(P.parent/'WhirlwindFlowV4/author_whirlwind.py'),
    'prefix':'Continuous sword shoulder/elbow/FK motion and shaft direction; exact hammer grip width',
    'tail_start_seconds':TAIL,'inertial_apex_seconds':HAMMER_PEAK,'right_wrist_apex_seconds':WRIST_PEAK,
    'right_wrist_apex_m':list(peak_position),'right_wrist_apex_velocity_m_s':list(peak_velocity),
    'previous_right_wrist_apex_m':[.30,.52,-.25],'right_wrist_apex_change_m':[.12,-.04,-.06],
    'tail':'Continuous position/velocity/acceleration spans; wrist rolls down/back through its outward limit, hammer keeps turning for another 60 ms, then one connected recovery',
    'outward_rotation_reference':'Takeover-relative quaternion turn from source 1.16 to the hammer apex at 1.52',
    'previous_outward_turn_degrees':math.degrees(original_outward_turn.length)*2.,
    'outward_turn_degrees':OUTWARD_TURN_DEGREES,
    'outward_turn_multiplier_from_v7':OUTWARD_TURN_DEGREES/(math.degrees(original_outward_turn.length)*2.),
    'hammer_lag_after_wrist_brake_real_seconds':playback_time(HAMMER_PEAK)-playback_time(WRIST_PEAK),
    'playback_phase_seconds':[TUNING[k] for k in ['readySeconds','spinSeconds','recoverSeconds']],
    'tail_clock':'Authored in playback time, compensating the spin-to-recovery sampling-rate boundary',
    'left_release_seconds':[RELEASE,CONTACT],
    'left_open_seconds':[OPEN,CONTACT],
    'left_release_advance_real_seconds':playback_time(1.12)-playback_time(RELEASE),
    'left_release_lead_before_fling_real_seconds':playback_time(TAIL)-playback_time(RELEASE),
    'left_lowered_lead_before_fling_real_seconds':playback_time(TAIL)-playback_time(LOW),
    'handoff':'Retain the early left-palm departure; reconnect its return to the wider moving shaft with the same contact time',
    'left_hand':'Native-length relaxed hanging arm below the frame, gentle low drift, then approach the shaft from below',
    'left_lowered':{'seconds':LOW,'position_m':list(free_position),'velocity_m_s':list(free_velocity)},
    'left_return_start_seconds':RETURN,
    'left_fingers':'Unclasp, relax into a soft curl below frame, reopen to receive the shaft, close only after contact',
    'left_close_seconds':.08,'left_single_hand_window_real_seconds':playback_time(CONTACT)-playback_time(RELEASE),
    'right_hand':'Exact original hammer hand-to-shaft frame throughout',
    'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_WHIRLWIND_INERTIA_AUTHORED '+json.dumps(receipt))
