"""Use the sword's continuous FK motion and a single connected inertial tail.

V3's repeated custom direction reversals and parked free hand are rejected.
The right palm stays attached; the left opens and clears the shaft on one arc.
"""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=300;DURATION=1.82;TAIL=1.16;PEAK=1.48
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
peak_position=Vector((.22,.50,-.245))
peak_q=axis0.rotation_difference(Vector((.72,.65,.22)).normalized())@base
peak_rotation=logq(base.inverted()@peak_q)
start_p=derivatives(raw_positions,TAIL);start_q=derivatives(raw_rotations,TAIL)

def tail(values,start,peak,end,t):
    if t<=TAIL:
        f=t*FPS;i=min(len(values)-2,int(f));return values[i].lerp(values[i+1],f-i)
    now=playback_time(t);begin=playback_time(TAIL);apex=playback_time(PEAK);finish=playback_time(DURATION)
    if t<=PEAK:
        return quintic(*start,peak,zero,zero,apex-begin,(now-begin)/(apex-begin))
    return quintic(peak,zero,zero,end,zero,zero,finish-apex,(now-apex)/(finish-apex))
def weapon(t):
    right=tail(raw_positions,start_p,peak_position,idle['hand_r'].translation,t)
    q=base@expq(tail(raw_rotations,start_q,peak_rotation,zero,t))
    return rigid(right-q@grips['r'].translation,q)

radial=grips['l'].translation-Vector((0,0,grips['l'].translation.z));radial.normalize()
def hand_target(w,side,t):
    h=w@grips[side]
    if side=='r':return h
    # A single smooth clearance loop; there is no parked hand or alternating
    # blend between weapon-space and world-space waypoints.
    u=sat((playback_time(t)-playback_time(1.17))/(playback_time(1.71)-playback_time(1.17)))
    release=math.sin(math.pi*u)**4
    h.translation+=(Vector((-.28,-.10,-.06))+(w.to_quaternion()@radial)*.04)*release
    # The free palm relaxes toward its existing idle orientation as it retreats.
    return rigid(h.translation,h.to_quaternion().slerp(idle['hand_l'].to_quaternion(),release*.40))

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
    digit=n.split('_')[0];delay={'thumb':0.,'index':.006,'middle':.012,'ring':.018,'pinky':.024}[digit]
    opened=smooth((t-1.10-delay)/.10)*(1-smooth((t-1.70-delay)/.08))
    amount=.55 if digit=='thumb' else (.58 if '_01_' in n else .86)
    p,q,scale=original.decompose()
    return Matrix.LocRotScale(p,q.slerp(local_rest[n].to_quaternion(),amount*opened),scale)

explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
poses=[]
for i,ref in enumerate(references):
    t=i/FPS;w=weapon(t);pose=copy.deepcopy(idle);pose['WPN_root']=w
    for side in ('l','r'):solve_arm(pose,ref,hand_target(w,side,t),side)
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
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Whirlwind_Flow_Editable.blend'))
receipt={'clips':[name],'fps':FPS,'seconds':DURATION,'source':str(SOURCE),'baseline':str(BASELINE),
    'revision':'SwordFlowV4_20261014','runtime_destination':'/Game/Weapons/SteelWarhammer20261014/WhirlwindV1',
    'prefix':'Continuous sword shoulder/elbow/FK motion and shaft direction; exact hammer grip width',
    'tail_start_seconds':TAIL,'inertial_apex_seconds':PEAK,'right_wrist_apex_m':list(peak_position),
    'tail':'Two C2 quintic spans with matched incoming velocity and acceleration; one brake and no held plateau',
    'playback_phase_seconds':[TUNING[k] for k in ['readySeconds','spinSeconds','recoverSeconds']],
    'tail_clock':'Authored in playback time, compensating the spin-to-recovery sampling-rate boundary',
    'left_release_seconds':[1.17,1.71],'left_hand':'One smooth clearance loop, no fixed free-hand waypoint',
    'right_hand':'Exact original hammer hand-to-shaft frame throughout',
    'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_WHIRLWIND_FLOW_AUTHORED '+json.dumps(receipt))
