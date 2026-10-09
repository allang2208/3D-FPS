"""Original game prop and native V7 motions, revised from BV1Re411e77Q 40-52s.

All count variants share an identical prefix through their final shell contact.
This lets a cancelled push branch into its matching release without jumping.
Geometry is an artistic game attachment, not manufacturing geometry.
"""
import bpy, bmesh, json, math, sys, shutil
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O=Path(__file__).parent; P=O.parents[1]; S=O.parent; X=O/'Exports'; X.mkdir(exist_ok=True)
sys.path.insert(0,str(S/'M1911RevolverInspect20260927'))
import author_support as support
bpy.ops.wm.open_mainfile(filepath=str(S/'BenelliM4Super9020261006/Super90_Gameplay_Editable.blend'))
rig=bpy.data.objects['SK_Super90']; scene=bpy.context.scene; scene.render.fps=60
rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Super90_idle'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}; names=list(rest)
rig.animation_data_clear()
G0=idle['WPN_root']; R0=rest['WPN_root']; GI=G0.inverted()
I=Matrix.Identity(4); one=Vector((1,1,1))
def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)
def phase(f,a,b):return smooth((f-a)/(b-a))
def mix(a,b,t):
    pa,qa,sa=a.decompose();pb,qb,sb=b.decompose()
    return Matrix.LocRotScale(pa.lerp(pb,t),qa.slerp(qb,t),sa.lerp(sb,t))
def T(v):return Matrix.Translation(Vector(v))
def copy(p):return {n:m.copy() for n,m in p.items()}
def uemat(v):return Matrix.LocRotScale(Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10]))

# Existing authored grip layers supply the exact installed foregrip entry/exit.
D=json.loads((S/'Super90Foregrips20261007/native.json').read_text())
C=Matrix.Diagonal((100,-100,100,1)); Ci=C.inverted()
K={n:(C@rest[n]).inverted()@uemat(D['rest'][n]) for n in names}
Ki={n:m.inverted() for n,m in K.items()}
# SOURCE poses carry the imported 0.01 root. Calibrate evaluated inputs to the
# native author root once, without changing any rest bone or mesh scale.
eval_base={}
for n in names:
    eval_base[n]=eval_base.get(parents[n],I)@uemat(D['clips']['idle']['samples'][0]['local'][n])
root=next(n for n in names if parents[n] is None)
evaluation_to_author=idle[root]@(Ci@eval_base[root]@Ki[root]).inverted()
idles={'base':idle}
for family in ('vertical','canted','prism','angled'):
    data=json.loads((S/'Super90Foregrips20261007/Profiles'/(family+'.json')).read_text())
    row=next(c for c in data['clips'] if c['kind']=='idle')
    tracks={t['bone']:t['values'][:10] for t in row['tracks']}
    world={}
    for n in names:
        local=uemat(D['clips']['idle']['samples'][0]['local'][n])
        if n in tracks:
            v=tracks[n];pp,qq,ss=local.decompose()
            local=Matrix.LocRotScale(pp+Vector(v[:3]),Quaternion((v[6],*v[3:6]))@qq,ss+Vector(v[7:10]))
        world[n]=world.get(parents[n],I)@local
    idles[family]={n:evaluation_to_author@Ci@world[n]@Ki[n] for n in names}

# The donor supplies native joint offsets. Its cylinder grasp was refitted to
# this rounded rectangular palm bar using the V7 skin, not a wrist-origin snap.
revision=S/'Super90LoaderRebuild20261007'
grasp_data=json.loads((revision/'handle_grasp.json').read_text(encoding='utf-8'))
repair=S/'Super90ContactR9_20261008'
contact_layout=json.loads((S/'Super90MotionR6_20261008/contact_layout.json').read_text(encoding='utf-8'))
fit_path=repair/'support_fit.json'
support_fit=json.loads(fit_path.read_text()) if fit_path.exists() else {'right_pole_degrees':0.}
hand_fit_path=repair/'hand_fit.json'
hand_fit=json.loads(hand_fit_path.read_text()) if hand_fit_path.exists() else {}
hand_in_handle=Matrix(hand_fit.get('loader_hand_in_handle',grasp_data['hand_in_handle']))
handle_fingers={n:Matrix(v) for n,v in hand_fit.get('loader_finger_local',grasp_data['finger_local']).items()}
finger_names={side:[n for n in names if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))] for side in ('l','r')}

def segment_frame(direction,hinge):
    x=direction.normalized();z=(hinge-x*hinge.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()

skin_stations={}
for side in ('l','r'):
    d=rest['hand_'+side].translation-rest['lowerarm_'+side].translation
    skin_stations[side]={prefix+side:max(0.,min(1.,(rest[prefix+side].translation-rest['lowerarm_'+side].translation).dot(d)/d.length_squared))
        for prefix in ('lowerarm_aux_','lowerarm_twist_02_','lowerarm_twist_01_')}

twist_context={}
def arm(p,source,target,side,relax=0.,contact_pole=0.,pole_rotation=0.,pole_reference=None,continuous=False):
    upper='upperarm_'+side;lower='lowerarm_'+side;hand='hand_'+side
    p['clavicle_'+side]=source['clavicle_'+side].copy()
    shoulder=source[upper].translation.copy();elbow=source[lower].translation.copy();wrist=source[hand].translation
    goal=target.translation;v=goal-shoulder;dist=v.length;axis=v.normalized()
    a=(rest[lower].translation-rest[upper].translation).length
    b=(rest[hand].translation-rest[lower].translation).length
    reach=max((a+b)*.975,(wrist-source[upper].translation).length)
    if dist>reach:
        shift=axis*(dist-reach);shoulder+=shift;p['clavicle_'+side].translation+=shift;dist=reach
    dist=max(abs(a-b)+1e-5,dist);along=(a*a-b*b+dist*dist)/(2*dist)
    old_axis=(wrist-source[upper].translation).normalized()
    pole=elbow-source[upper].translation;pole-=old_axis*pole.dot(old_axis)
    pole=old_axis.rotation_difference(axis)@pole
    if pole.length<1e-6:
        pole=Vector((0,0,-1));pole-=axis*pole.dot(axis)
    if contact_pole>0.:
        # The elbow must support the actual palm direction. Transporting the
        # idle pole alone puts the elbow in front of a rearward loader wrist.
        # Select the point on the same exact two-bone circle nearest the
        # neutral wrist continuation; blend only its angular position.
        palm_axis=rest[hand].to_quaternion().inverted()@(rest[hand].translation-rest[lower].translation).normalized()
        anchor=target if pole_reference is None else pole_reference
        anchor_axis=(anchor.translation-shoulder).normalized()
        wanted=anchor.to_quaternion()@palm_axis
        preferred=anchor.translation-wanted*b-shoulder
        preferred-=anchor_axis*preferred.dot(anchor_axis)
        preferred=anchor_axis.rotation_difference(axis)@preferred
        if preferred.length>1e-6:
            pole=pole.normalized()
            pole=Quaternion().slerp(pole.rotation_difference(preferred.normalized()),contact_pole)@pole
    pole=Quaternion(axis,math.radians(pole_rotation))@pole
    knee=shoulder+axis*along+pole.normalized()*math.sqrt(max(0.,a*a-along*along))
    u0=elbow-source[upper].translation;f0=wrist-elbow;h0=u0.cross(f0)
    u=knee-shoulder;v=goal-knee;h=u.cross(v)
    qa=segment_frame(u,h)@segment_frame(u0,h0).inverted()
    qb=segment_frame(v,h)@segment_frame(f0,h0).inverted()
    upper_q=qa@source[upper].to_quaternion();lower_q=qb@source[lower].to_quaternion()
    if relax>0.:
        ur=rest[lower].translation-rest[upper].translation
        fr=rest[hand].translation-rest[lower].translation;hr=ur.cross(fr)
        upper_neutral=segment_frame(u,h)@segment_frame(ur,hr).inverted()@rest[upper].to_quaternion()
        lower_neutral=segment_frame(v,h)@segment_frame(fr,hr).inverted()@rest[lower].to_quaternion()
        upper_q=upper_q.slerp(upper_neutral,relax);lower_q=lower_q.slerp(lower_neutral,relax)
    p[upper]=Matrix.LocRotScale(shoulder,upper_q,source[upper].to_scale())
    p[lower]=Matrix.LocRotScale(knee,lower_q,source[lower].to_scale())
    axis=v.normalized()
    neutral_hand=lower_q@rest[lower].to_quaternion().inverted()@rest[hand].to_quaternion()
    roll=target.to_quaternion()@neutral_hand.inverted()
    angle=2*math.atan2(Vector((roll.x,roll.y,roll.z)).dot(axis),roll.w);angle=(angle+math.pi)%(2*math.pi)-math.pi
    inherited_roll=target.to_quaternion()@(qb@source[hand].to_quaternion()).inverted()
    inherited_angle=2*math.atan2(Vector((inherited_roll.x,inherited_roll.y,inherited_roll.z)).dot(axis),inherited_roll.w)
    inherited_angle=(inherited_angle+math.pi)%(2*math.pi)-math.pi
    if continuous:
        previous=twist_context.get(side,(angle,inherited_angle))
        angle+=2*math.pi*round((previous[0]-angle)/(2*math.pi))
        inherited_angle+=2*math.pi*round((previous[1]-inherited_angle)/(2*math.pi))
        twist_context[side]=(angle,inherited_angle)
    for n,w in skin_stations[side].items():
        basis=p[lower]@source[lower].inverted()@source[n]
        neutral=lower_q@rest[lower].to_quaternion().inverted()@rest[n].to_quaternion()
        carried=Quaternion(axis,inherited_angle*w)@basis.to_quaternion()
        q=carried.slerp(Quaternion(axis,angle*w)@neutral,relax)
        p[n]=Matrix.LocRotScale(basis.translation,q,basis.to_scale())
    p[hand]=target

# Physical native bind coordinates: +Y muzzle, +X right, +Z up.
# The mouth is fitted to the original loading-gate region; the tube leads back.
mouth=Vector((0.,-.035,-.792))
tube_bind=T(mouth)@Matrix.Rotation(math.radians(contact_layout['tube_pitch_degrees']),4,'X')
handle_turn=Matrix.Rotation(math.pi/2,4,'Y')@Matrix.Rotation(math.radians(support_fit.get('loader_handle_roll_degrees',contact_layout['handle_axial_roll_degrees'])),4,'Z')
up=Vector((0,0,1))
barrel=(idle['WPN_FrontSight'].translation-idle['WPN_RearSight'].translation).normalized()
forward=Vector((barrel.x,barrel.y,0)).normalized();right=forward.cross(up).normalized()
local_rest={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}
# The reload must return to the same corrected skin contact used by idle.
# Keep the native skeleton lengths and solve both complete arm chains.
uncorrected_idles={family:copy(start) for family,start in idles.items()}
for family,start in idles.items():
    source=copy(start)
    for n in source:
        if n.endswith('_r'):source[n].translation+=sum((axis*value for axis,value in zip((right,forward,up),support_fit['idle_right_offset'])),Vector())
    arm(start,source,Matrix(hand_fit['right_hand_in_idle']),'r',pole_rotation=support_fit['idle_right_pole'])
    for n in finger_names['r']:start[n]=start[parents[n]]@Matrix(hand_fit['right_finger_local'][n])
    if family=='base' and 'idle_left_hand_in_idle' in hand_fit:
        arm(start,copy(start),Matrix(hand_fit['idle_left_hand_in_idle']),'l')
        for n in finger_names['l']:start[n]=start[parents[n]]@Matrix(hand_fit['idle_left_finger_local'][n])

# Each digit has its own release, acquisition and final closure clock. The
# source research supports independent channels; no RTM angles are transplanted.
digit_clocks={'thumb':(0,4,57,68,4),'index':(1,5,49,59,1),
              'middle':(2,7,50,61,0),'ring':(3,8,52,63,2),'pinky':(4,9,54,65,3)}
open_fingers={};press_fingers={}
for n in finger_names['l']:
    loc=idle[parents[n]].inverted()@idle[n];pp,qq,ss=loc.decompose()
    amount=0. if 'metacarpal' in n else (.60 if n.startswith('thumb') else .85)
    open_fingers[n]=Matrix.LocRotScale(pp,qq.slerp(local_rest[n].to_quaternion(),amount),ss)
    # Thumb reaches the catch; other fingers stay softly open beside the gun.
    press_fingers[n]=mix(open_fingers[n],handle_fingers[n],.15 if n.startswith('thumb') else .20)
if hand_fit:
    press_fingers={n:Matrix(v) for n,v in hand_fit['press_finger_local'].items()}

# Actual thumb skin patch in hand space, so the empty release contacts with
# a pad instead of placing the wrist beside the mechanism.
skin_input=json.loads((revision/'grasp_skin_inputs.json').read_text(encoding='utf-8'))
press_world={'hand_l':I}
for n in finger_names['l']:press_world[n]=press_world[parents[n]]@press_fingers[n]
thumb_ids=set(grasp_data['contact_vertex_ids']['thumb_03_l'])
thumb_points=[]
for v in skin_input['vertices']:
    if v['id'] not in thumb_ids:continue
    pos=Vector((0,0,0))
    for n,w in v['weights'].items():pos+=(press_world[n]@rest[n].inverted()@Vector(v['p']))*w
    thumb_points.append(pos)
thumb_pad=sum(thumb_points,Vector((0,0,0)))/len(thumb_points)
# Keep the established 60 Hz shell/visibility event clock. Gameplay playback
# is slowed by this attachment's duration multiplier, including all its cues.
# Release/fetch 0-75, dock 75-87, push 87-114, then open palm/direct regrip
# while the separate props fall below the view by 127. Normal ends at 146.
INSERT=90;STEP=4;NORMAL_TAIL=32;EMPTY_TAIL=68;RELEASE_TAIL=44
SHOW_BEGIN=74;HIDE_TAIL=13;CYCLE_START_TAIL=16
DEFAULT_PLAY_RATE=.85
# Native, unweighted helper: the pusher can leave the palm when released.
# Its rest pose and the shared skeleton remain unchanged.
PLUNGER_DRIVER='WPN_SOCKET_Magazine'
PLUNGER_STANDOFF=-.03
PLUNGER_SIDE=.085
def last_frame(count):return INSERT+STEP*(count-1)
def duration(count,empty):return last_frame(count)+(EMPTY_TAIL if empty else NORMAL_TAIL)
def arc(a,b,t,bow):return a.lerp(b,t)+bow*math.sin(math.pi*t)

def bezier(a,b,c,d,t):
    return a*(1-t)**3+b*(3*(1-t)**2*t)+c*(3*(1-t)*t*t)+d*t**3

def push_stroke(f):
    # One continuous push. Start under load and decelerate at the stop while
    # retaining every authored shell-contact frame used by the ammo clock.
    x=max(0.,min(7.,(f-86)/STEP));i=min(6,int(x));t=x-i
    # Shells keep their existing contact frames. Between them, pressure builds
    # then gives at each detent; velocity stays positive through inner contacts.
    speeds=(.18,.72,1.12,1.23,1.16,.99,.68,0.)
    a=speeds[i];b=speeds[i+1]
    t=(-2*t**3+3*t*t)+(t**3-2*t*t+t)*a+(t**3-t*t)*b
    return (i+t)/7.

def weapon_move(f,end,finish,return_begin):
    settle=phase(f,5,30);recover=phase(f,return_begin,finish)
    pivot=idle['hand_r'].translation
    # Support takes the weight before insertion. During the push the right
    # hand yields slightly with the gun; it is not a frozen world-space prop.
    weight=math.sin(math.pi*phase(f,9,45))*(1-recover)
    pressure=(.35*phase(f,79,87)+.65*phase(f,87,110))*(1-phase(f,end,end+7))
    seated_load=math.sin(math.pi*phase(f,81,92))*(1-phase(f,end,end+4))
    rebound=math.sin(math.pi*phase(f,end,end+9))
    yaw=contact_layout['gun_yaw_degrees']*phase(f,8,30)+.6*pressure
    pitch=contact_layout['gun_pitch_degrees']*settle-1.3*pressure
    roll=contact_layout['gun_roll_degrees']*settle+2.5*weight-1.8*pressure+.65*seated_load-.8*rebound
    q=Quaternion(up,math.radians(yaw))@Quaternion(right,math.radians(pitch))@Quaternion(barrel,math.radians(roll))
    q=q.slerp(Quaternion(),recover)
    offset=(-right*.024+forward*.018+up*.010+Vector(contact_layout['extra_offset_native']))*settle*(1-recover)
    offset+=(-forward*.003-up*.002)*pressure*(1-recover)
    offset+=(-forward*.0025+up*.0015)*seated_load*(1-recover)
    return T(pivot+offset)@q.to_matrix().to_4x4()@T(-pivot)

def free_wrist(p,source,location,relax=1.):
    # Transport the wrist with the solved forearm instead of rotating the palm
    # independently in world space during the offscreen fetch and open return.
    arm(p,source,Matrix.LocRotScale(location,source['hand_l'].to_quaternion(),one),'l',relax)
    relative=source['lowerarm_l'].to_quaternion().inverted()@source['hand_l'].to_quaternion()
    relaxed=rest['lowerarm_l'].to_quaternion().inverted()@rest['hand_l'].to_quaternion()
    return Matrix.LocRotScale(location,p['lowerarm_l'].to_quaternion()@relative.slerp(relaxed,.80),one)

def pose_sample(f,count,empty,family='base'):
    start=idles[family];end=last_frame(count);tail=f-end;finish=duration(count,empty)
    return_begin=end+(45 if empty else 8)
    contact=finish-6;release=end+RELEASE_TAIL
    common=phase(f,23,42)*(1-phase(f,return_begin,contact))
    limb_source={n:mix(start[n],idle[n],common) for n in names}
    left_shift=sum((axis*value for axis,value in zip((right,forward,up),support_fit.get('left_shoulder_offset_m',[0.,0.,0.]))),Vector())
    left_shift*=phase(f,42,69)*(1-phase(f,return_begin,contact))
    for n in names:
        if n.endswith('_l'):limb_source[n].translation+=left_shift
    arm_relax=phase(f,7,28)*(1-phase(f,contact-7,finish))
    move=weapon_move(f,end,finish,return_begin);gun=move@G0
    p=copy(idle)
    for n in names:
        if n.startswith('WPN_'):p[n]=move@idle[n]
    p['WPN_root']=gun
    # Empty-only release is an adaptation, not a visible action in the reference.
    opened=1-phase(f,release-2,release+2) if empty else 0.
    p['WPN_bolt']=gun@T((0,0,.1065*opened))@GI@idle['WPN_bolt']
    gate=phase(f,82,87)*(1-phase(f,end+2,end+7))
    p['WPN_Load']=p['WPN_Load']@Matrix.Rotation(math.radians(16)*gate,4,'X')
    mounted=gun@R0.inverted()@tube_bind
    # Arrival comes from below the left frame edge. Once seated the mouth is
    # fixed in gun space until the final contact, including shortened variants.
    carried=mounted.copy();carried.translation+=-right*.115-forward*.075-up*.265
    carried=carried@Matrix.Rotation(math.radians(-11),4,'Z')
    # First bring the tip beside the mouth, then seat it over a shorter travel.
    dock=(.90*phase(f,74,82)+.10*phase(f,82,87));tube=mix(carried,mounted,dock)
    tube.translation=arc(carried.translation,mounted.translation,dock,-right*.018)
    stroke=push_stroke(min(f,end))
    seated=weapon_move(end,end,finish,return_begin)@G0@R0.inverted()@tube_bind
    release_handle=seated@T((PLUNGER_SIDE,-.326+.294*stroke,PLUNGER_STANDOFF))@handle_turn
    release_hand=release_handle@hand_in_handle
    if tail>0:
        # After the fingertips let go, tube and pusher fall together. The palm
        # goes directly forward to the fore-end instead of retrieving the tube.
        tube=seated.copy()
        drop=max(0.,min(float(HIDE_TAIL-6),tail-6))/(60*DEFAULT_PLAY_RATE)
        drift=drop-.02*(1-math.exp(-drop/.02))
        tube.translation+=forward*(1.2*drift)-up*(.65*drift+4.905*drop*drop)
        rotation=Quaternion(right,-.55*drop)@Quaternion(forward,.22*drop)
        tube=Matrix.LocRotScale(tube.translation,rotation@tube.to_quaternion(),one)
    handle=tube@T((PLUNGER_SIDE,-.326+.294*stroke,PLUNGER_STANDOFF))@handle_turn
    held=handle@hand_in_handle
    support_hand=move@start['hand_l']
    # First loosen fingers, then clear the fore-end, then lower the whole arm.
    clear=support_hand.copy();clear.translation+=(-right*.060-up*.030)*phase(f,4,12)
    hidden=idle['upperarm_l'].translation-right*.025+forward*.080-up*.315
    entry=phase(f,7,31)
    location=arc(clear.translation,hidden,entry,-right*.018)
    relaxed=free_wrist(p,limb_source,location,arm_relax)
    hand=mix(clear,relaxed,entry)
    hand=mix(hand,held,phase(f,38,68))
    if tail>0:
        hand=release_hand.copy()
        escape=release_handle.to_3x3()@Vector((0,.070,0))-up*.025
        hand.translation+=escape*phase(f,end+2,end+7)
        departure=release_hand.copy();departure.translation+=escape
        if empty:
            catch=p['WPN_BoltCatch'].translation
            normal=move.to_3x3()@right
            press=release_hand.copy()
            press.translation=catch+normal*(.006-.004*phase(f,release-5,release)+.004*phase(f,release,release+4))-press.to_3x3()@thumb_pad
            if hand_fit:
                press=move@Matrix(hand_fit['press_hand_in_idle'])
                press.translation+=normal*(.024+.004*(1-phase(f,release-5,release))+.004*phase(f,release,release+4))
            to_catch=phase(f,end+8,release-5)
            approach=hand.copy()
            hand=mix(approach,press,to_catch)
            hand.translation=arc(approach.translation,press.translation,to_catch,normal*.080-right*.015-up*.10)
            hand.translation+=normal*.020*phase(f,end+4,end+12)*(1-phase(f,release-8,release))
            departure=press
        if f>=return_begin:
            returning=phase(f,return_begin,contact)
            destination=support_hand.translation
            # Carry the open palm around the outside of the receiver before
            # approaching the fore-end. The guide and falling tube stay inside.
            clearance=-right*.115-up*.035
            location=bezier(departure.translation,
                departure.translation+forward*.035+clearance,
                destination+clearance,destination,returning)
            # Clear the receiver before opening the fingers completely.
            location+=move.to_3x3()@right*.030*phase(f,return_begin,return_begin+6)*(1-phase(f,return_begin+6,contact-3))
            begin_move=weapon_move(return_begin,end,finish,return_begin)
            start_relative=Matrix(hand_fit['press_hand_in_idle']).to_quaternion() if empty and hand_fit else begin_move.to_quaternion().inverted()@release_hand.to_quaternion()
            # Fixed endpoints in gun space avoid a changing shortest-arc branch.
            # Spread the wrist turn over the complete return, including empty.
            rotation=move.to_quaternion()@start_relative.slerp(start['hand_l'].to_quaternion(),returning)
            hand=Matrix.LocRotScale(location,rotation,one)
    contact_pole=phase(f,42,69)*(1-phase(f,return_begin,contact))
    # Carry the last loaded elbow plane through the open-hand return. Deriving
    # it again from the rotating return wrist crosses a zero projection and
    # switches quaternion branches (R7: 13 cm in one frame).
    arm(p,limb_source,hand,'l',arm_relax,contact_pole,
        pole_rotation=(support_fit.get('left_loader_pole_degrees',0.)+
            (support_fit.get('left_press_pole_degrees',0.)*phase(f,end+4,release-5) if empty else 0.))*contact_pole,
        pole_reference=release_hand if tail>0 else None,continuous=True)
    support_weight=phase(f,3,30)*(1-phase(f,finish-24,finish))
    support_source=copy(uncorrected_idles['base'])
    baseline=Vector(support_fit['idle_right_offset']);loaded=Vector((0,0,-.07))
    dx,dy,dz=baseline.lerp(loaded,support_weight)
    shift=right*dx+forward*dy+up*dz
    for n in support_source:
        if n.endswith('_r'):support_source[n].translation+=shift
    arm(p,support_source,move@idle['hand_r'],'r',pole_rotation=support_fit['idle_right_pole']*(1-support_weight)+45.*support_weight,continuous=True)
    # Release digits in sequence while the separate pusher drops. Closing starts
    # as the palm approaches the fore-end, not after a second offscreen fetch.
    for side in ('l','r'):
        source=start if side=='l' else idle
        for n in finger_names[side]:
            par=parents[n];local=source[par].inverted()@source[n]
            if side=='r' and hand_fit:
                local=Matrix(hand_fit['right_finger_local'][n])
            if side=='l':
                digit=n.split('_')[0];ra,rb,ga,gb,delay=digit_clocks[digit]
                original=local
                local=mix(original,open_fingers[n],phase(f,ra+(8 if family in ('canted','prism') else 0),rb+(8 if family in ('canted','prism') else 0)))
                local=mix(local,handle_fingers[n],phase(f,ga,gb))
                if tail>0:
                    relaxed_release=Matrix(hand_fit['release_finger_local'][n])
                    local=mix(local,relaxed_release,phase(f,end+delay*.12,end+3+delay*.15))
                    if empty:
                        local=mix(local,press_fingers[n],phase(f,end+10,release-7)*(1-phase(f,return_begin,return_begin+5)))
                    else:
                        local=mix(local,open_fingers[n],phase(f,end+10,end+17))
                    local=mix(local,original,phase(f,return_begin+delay*.2,return_begin+3+delay*.2) if empty else phase(f,return_begin+delay*.2,contact-8+delay*.2))
                    if n=='thumb_01_l' and family=='base':
                        raised=phase(f,return_begin,return_begin+4)*(1-phase(f,contact,finish-1))
                        local=local@Matrix.Rotation(math.radians(45)*raised,4,'X')
            p[n]=p[par]@local
    parked=phase(f,end+HIDE_TAIL,finish)
    p['WPN_Shell']=mix(tube,move@idle['WPN_Shell'],parked)
    p[PLUNGER_DRIVER]=mix(handle,move@idle[PLUNGER_DRIVER],parked)
    return p,handle,tube

# Sample each source timeline monotonically to unwrap axial rotations before
# distributing them over the skin's twist bones. Quaternion sign correction
# alone cannot fix a +180/-180 scalar branch applied at fractional stations.
pose_cache={}
def pose(f,count,empty,family='base'):
    key=(count,empty,family)
    if key not in pose_cache:
        twist_context.clear();rows=[]
        for frame in range(duration(count,empty)+1):
            rows.append((pose_sample(frame,count,empty,family),dict(twist_context)))
        pose_cache[key]=rows
    rows=pose_cache[key];f=max(0.,min(float(len(rows)-1),f));frame=int(f)
    if f==frame:result=rows[frame][0]
    else:
        twist_context.clear();twist_context.update(rows[frame][1])
        result=pose_sample(f,count,empty,family)
    return copy(result[0]),result[1].copy(),result[2].copy()

def cycle_pose(f,family='base'):
    at=last_frame(1)+CYCLE_START_TAIL+f*(EMPTY_TAIL-CYCLE_START_TAIL)/66
    target=pose(at,1,True,family)[0]
    if f>=12:return target
    t=phase(f,0,12);start=idles[family];p={}
    for n in names:
        par=parents[n]
        a=start[par].inverted()@start[n] if par else start[n]
        b=target[par].inverted()@target[n] if par else target[n]
        p[n]=p.get(par,I)@mix(a,b,t)
    # Preserve native chain lengths and rigid gun contact during entry.
    goal=mix(start['hand_l'],target['hand_l'],t)
    goal.translation+=(-right*.08-up*.04)*math.sin(math.pi*t)
    arm(p,copy(p),goal,'l')
    for n in finger_names['l']:
        par=parents[n];p[n]=p[par]@mix(start[par].inverted()@start[n],target[par].inverted()@target[n],phase(f,4,12))
    source=copy(uncorrected_idles['base'])
    dx,dy,dz=Vector(support_fit['idle_right_offset']).lerp(Vector((0,0,-.07)),t)
    for n in source:
        if n.endswith('_r'):source[n].translation+=right*dx+forward*dy+up*dz
    arm(p,source,p['WPN_root']@GI@idle['hand_r'],'r',pole_rotation=support_fit['idle_right_pole']*(1-t)+45*t)
    for n in finger_names['r']:p[n]=p[parents[n]]@Matrix(hand_fit['right_finger_local'][n])
    return p

def local_rows(world):
    rows=[]
    for p in world:
        row={}
        for n in names:
            local=rest[n].inverted()@rest[parents[n]]@p[parents[n]].inverted()@p[n] if parents[n] else rest[n].inverted()@p[n]
            row[n]=local.decompose()
            if rows and rows[-1][n][1].dot(row[n][1])<0:row[n][1].negate()
        rows.append(row)
    return rows
def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]
def mat(name,color,metal,rough):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if bs is None:
        bs=m.node_tree.nodes.new('ShaderNodeBsdfPrincipled');out=m.node_tree.nodes.new('ShaderNodeOutputMaterial');m.node_tree.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    return m
steel=mat('S90Loader_Steel',(.025,.026,.028),1,.42)
polymer=mat('S90Loader_Polymer',(.018,.018,.019),0,.54)
silver=mat('S90Loader_Rod',(.13,.14,.15),1,.30)
def mesh(name,vertices,faces,material,bevel=0):
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.materials.append(material)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob);select([ob])
    if bevel:
        mod=ob.modifiers.new('Machined edge','BEVEL');mod.width=bevel;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob
def tube(name,y0,y1,r,thickness,material):
    N=80;verts=[]
    for y,rad in ((y0,r),(y1,r),(y0,r-thickness),(y1,r-thickness)):
        verts.extend((math.cos(2*math.pi*i/N)*rad,y,math.sin(2*math.pi*i/N)*rad) for i in range(N))
    faces=[]
    for i in range(N):
        j=(i+1)%N
        faces.extend([(i,j,N+j,N+i),(2*N+i,3*N+i,3*N+j,2*N+j),(i,2*N+i,2*N+j,j),(N+i,N+j,3*N+j,3*N+i)])
    ob=mesh(name,verts,faces,material,.0004)
    for p in ob.data.polygons:p.use_smooth=True
    return ob
def box(name,center,size,material,bevel=.001):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.name=name;ob.dimensions=size
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);ob.data.materials.append(material)
    mod=ob.modifiers.new('Soft manufactured edge','BEVEL');mod.width=bevel;mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
    return ob
def finish_uv(ob):
    select([ob]);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
    mod=ob.modifiers.new('Export tangent triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
def bind(ob,bone,transform):
    ob.data.transform(transform);ob.parent=rig;ob.matrix_parent_inverse=I;ob.matrix_basis=I
    vg=ob.vertex_groups.new(name=bone);vg.add(list(range(len(ob.data.vertices))),1.,'REPLACE')
    mod=ob.modifiers.new('Native rigid mechanism','ARMATURE');mod.object=rig

# Fit the upper rim to the actual receiver underside; the former flat rim
# stopped about 15 mm short. Keep the lower opening aligned to the tube tip.
from mathutils.bvhtree import BVHTree
receiver=bpy.data.objects['Super90_body'];receiver.data.calc_loop_triangles()
surface=BVHTree.FromPolygons([receiver.matrix_world@v.co for v in receiver.data.vertices],
    [tuple(t.vertices) for t in receiver.data.loop_triangles],all_triangles=True)
outline=[(-1,-1),(0,-1),(1,-1)]+[(1,v) for v in (-.6,-.2,.2,.6,1)]+[(0,1),(-1,1)]+[(-1,v) for v in (.6,.2,-.2,-.6)]
rim_z=[]
for x,y in outline:
    at=Vector(((-1 if x<0 else 1)*.014,-.018+y*.043,-.84))
    hit,normal,index,distance=surface.ray_cast(at,Vector((0,0,1)),.10)
    if hit is None:raise RuntimeError('No receiver bearing surface at '+str(at))
    rim_z.append(hit.z+.00035)
verts=[]
for ring in range(4):
    for (x,y),z in zip(outline,rim_z):
        if ring in (0,2):
            verts.append((x*(.014 if ring==0 else .0095),-.018+y*(.043 if ring==0 else .0395),z))
        else:
            verts.append((mouth.x+x*(.023 if ring==1 else .019),mouth.y+y*(.041 if ring==1 else .037),mouth.z-.015))
faces=[]
N=len(outline)
for i in range(N):
    j=(i+1)%N;faces.extend([(i,j,N+j,N+i),(2*N+i,3*N+i,3*N+j,2*N+j),(i,2*N+i,2*N+j,j),(N+i,N+j,3*N+j,3*N+i)])
guide_fit={'upper_rim_z_m':rim_z,'previous_upper_z_m':mouth.z-.003,
    'receiver_overlap_m':.00035,'upper_center_y_m':-.018,'tube_tip_native_m':list(mouth)}
funnel=mesh('SM_Super90_LoaderGuide',verts,faces,steel,.0002)
finish_uv(funnel)
select([funnel]);bpy.ops.export_scene.fbx(filepath=str(X/(funnel.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')

parts=[tube('Loader tube',-.345,0,.014,.0022,polymer),tube('Mouth collar',-.016,.002,.016,.004,steel),tube('Rear collar',-.35,-.334,.016,.004,steel)]
for y in (-.32,-.29,-.26,-.23,-.20,-.17,-.14,-.11,-.08,-.05):parts.append(tube('Circumferential rib',y-.0017,y+.0017,.0148,.0012,polymer))
parts.append(box('Slider guide',(0,-.17,-.014),(.014,.326,.005),steel,.0007))
for ob in parts:finish_uv(ob)
select(parts);bpy.ops.object.join();body=bpy.context.object;body.name='SpeedloaderTube'
bind(body,'WPN_Shell',rest['WPN_Shell'])
handle_parts=[box('Palm bar',(0,0,0),(.032,.030,.094),polymer,.006)]
for z in (-.036,-.025,-.014,.014,.025,.036):handle_parts.append(box('Palm bar rib',(0,-.015,z),(.031,.004,.003),polymer,.001))
for ob in handle_parts:finish_uv(ob)
select(handle_parts);bpy.ops.object.join();plunger=bpy.context.object;plunger.name='SpeedloaderPlunger'
plunger.data.transform(Matrix.Diagonal((*hand_fit.get('loader_bar_scale',[1.,1.,1.]),1.)))
geometry={};exec(compile((repair/'prop_geometry.py').read_text(),str(repair/'prop_geometry.py'),'exec'),geometry)
cv,cf=geometry['connector_mesh']();yoke=mesh('Offset slider link',cv,cf,silver,.0004);finish_uv(yoke)
select([yoke,plunger]);bpy.ops.object.join()
bind(plunger,PLUNGER_DRIVER,rest[PLUNGER_DRIVER])
select([body,plunger,rig]);rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=I
bpy.ops.export_scene.fbx(filepath=str(X/'SK_Super90_LoaderProps.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')

report={'reference':'https://www.bilibili.com/video/BV1Re411e77Q/?t=40','revision':'ContactR9-20261008','original_game_prop':True,'capacity':7,'meshes':{'guide':str(X/'SM_Super90_LoaderGuide.fbx'),'props':str(X/'SK_Super90_LoaderProps.fbx')},'clips':[],'runtime_tested':False,
        'source_fps':60,'default_play_rate':DEFAULT_PLAY_RATE,'reference_study_seconds':[40,52],
        'prop_drivers':{'tube':'WPN_Shell','pusher':PLUNGER_DRIVER},
        'evaluated_input_to_author_root':[list(r) for r in evaluation_to_author],
        'skin_stations':skin_stations,'grasp_authoring':str(revision/'handle_grasp.json'),
        'hand_in_handle':[list(r) for r in hand_in_handle],'digit_clocks':digit_clocks,
        'contact_layout':contact_layout,'support_fit':support_fit,'guide_fit':guide_fit,
        'hand_fit_authoring':str(hand_fit_path),
        'elbow_method':'Transport the loaded bend plane through regrip; native two-bone lengths and fitted right contact',
        'thumb_pad_hand_space':list(thumb_pad),
        'events_frames':{'release':[0,13],'offscreen_fetch':[13,75],'dock':[75,87],'first_contact':INSERT,'contact_step':STEP,'show_begin':SHOW_BEGIN,'hide_after_last':HIDE_TAIL,'normal_tail':NORMAL_TAIL,'empty_tail':EMPTY_TAIL,'release_after_last':RELEASE_TAIL},
        'adaptations':['External slow-motion reference informs the open-palm return and released prop fall; not copied as a 12-second game action','First-person framing and unseen fetch reconstructed on native V7 rig','Empty bolt release is a separate game adaptation; not shown by this reference']}
profiles={family:{'family':family,'clips':[]} for family in ('vertical','canted','prism','angled')}
rig.animation_data_create()
changed=['clavicle_l','upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l']+finger_names['l']
for empty in (False,True):
    for count in range(1,8):
        name=f'A_Super90_loader_{"empty" if empty else "normal"}_{count}'
        frames=list(range(duration(count,empty)+1));world=[pose(f,count,empty)[0] for f in frames]
        support.DURATION=frames[-1]/60;support.bake_action(rig,scene,name,local_rows(world),frames)
        select([rig]);file=X/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
        asset='/Game/Weapons/Super90/Speedloader20261007/Animations/'+name
        report['clips'].append({'name':name,'file':str(file),'count':count,'empty':empty,'duration':support.DURATION,'contacts':[(INSERT+STEP*i)/60 for i in range(count)],'release':(last_frame(count)+RELEASE_TAIL)/60 if empty else None,'props_visible':[SHOW_BEGIN/60,(last_frame(count)+HIDE_TAIL)/60]})
        for family in profiles:
            entry={'base':asset,'duration':support.DURATION,'tracks':[]};tracks={n:[] for n in changed}
            for f,base in zip(frames,world):
                adapted=pose(f,count,empty,family)[0]
                bue={n:C@base[n]@K[n] for n in names};aue={n:C@adapted[n]@K[n] for n in names}
                for n in changed:
                    par=parents[n];bb=bue[par].inverted()@bue[n];aa=aue[par].inverted()@aue[n]
                    q=aa.to_quaternion()@bb.to_quaternion().inverted()
                    if tracks[n] and q.dot(Quaternion((tracks[n][-1][6],*tracks[n][-1][3:6])))<0:q.negate()
                    elif not tracks[n] and q.w<0:q.negate()
                    dp=aa.translation-bb.translation;ds=aa.to_scale()-bb.to_scale()
                    tracks[n].append([*dp,q.x,q.y,q.z,q.w,*ds])
            for n,values in tracks.items():
                zero=[0,0,0,0,0,0,1,0,0,0]
                if all(max(abs(a-b) for a,b in zip(v,zero))<1e-5 for v in values):continue
                entry['tracks'].append({'bone':n,'times':[f/60 for f in frames],'values':[v for row in values for v in row]})
            profiles[family]['clips'].append(entry)
        print('AUTHORED',name,support.DURATION,flush=True)

# A chamber-cycle-only continuation never displays or consumes a loader.
cycle=[cycle_pose(f) for f in range(67)]
name='A_Super90_loader_cycle';support.DURATION=1.1;support.bake_action(rig,scene,name,local_rows(cycle),list(range(67)))
select([rig]);bpy.ops.export_scene.fbx(filepath=str(X/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
report['clips'].append({'name':name,'file':str(X/(name+'.fbx')),'count':0,'empty':True,'duration':1.1,'contacts':[],'release':1.1*(RELEASE_TAIL-CYCLE_START_TAIL)/(EMPTY_TAIL-CYCLE_START_TAIL),'props_visible':None})
for family in profiles:
    tracks={n:[] for n in changed}
    for f,base in enumerate(cycle):
        adapted=cycle_pose(f,family)
        bue={n:C@base[n]@K[n] for n in names};aue={n:C@adapted[n]@K[n] for n in names}
        for n in changed:
            par=parents[n];bb=bue[par].inverted()@bue[n];aa=aue[par].inverted()@aue[n]
            q=aa.to_quaternion()@bb.to_quaternion().inverted()
            if tracks[n] and q.dot(Quaternion((tracks[n][-1][6],*tracks[n][-1][3:6])))<0:q.negate()
            elif not tracks[n] and q.w<0:q.negate()
            dp=aa.translation-bb.translation;ds=aa.to_scale()-bb.to_scale()
            tracks[n].append([*dp,q.x,q.y,q.z,q.w,*ds])
    entry={'base':'/Game/Weapons/Super90/Speedloader20261007/Animations/'+name,'duration':1.1,'tracks':[]}
    for n,values in tracks.items():
        if all(max(abs(a-b) for a,b in zip(v,[0,0,0,0,0,0,1,0,0,0]))<1e-5 for v in values):continue
        entry['tracks'].append({'bone':n,'times':[f/60 for f in range(67)],'values':[v for row in values for v in row]})
    profiles[family]['clips'].append(entry)
# Preserve the native idle gun sway while carrying the corrected contacts.
# Both reload endpoints and the actual runtime idle use these same arm poses.
idle_world=[];idle_adapted={family:[] for family in profiles}
for row in D['clips']['idle']['samples']:
    raw={}
    for n in names:raw[n]=raw.get(parents[n],I)@uemat(row['local'][n])
    raw={n:evaluation_to_author@Ci@raw[n]@Ki[n] for n in names}
    move=raw['WPN_root']@G0.inverted()
    def held_idle(start):
        result=copy(raw)
        for n in names:
            if not n.startswith('WPN_') and n!=root:result[n]=move@start[n]
        return result
    idle_world.append(held_idle(idle))
    for family in profiles:idle_adapted[family].append(held_idle(idles[family]))
name='A_Super90_idle';frames=list(range(len(idle_world)));support.DURATION=frames[-1]/60
if bpy.data.actions.get(name):bpy.data.actions.remove(bpy.data.actions[name])
support.bake_action(rig,scene,name,local_rows(idle_world),frames)
select([rig]);file=X/(name+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
idle_asset='/Game/Weapons/Super90/Cransh20261006/Animations/'+name
report['idle_clip']={'name':name,'file':str(file),'destination':idle_asset.rsplit('/',1)[0],'duration':support.DURATION}
for family in profiles:
    tracks={n:[] for n in changed}
    for base,adapted in zip(idle_world,idle_adapted[family]):
        bue={n:C@base[n]@K[n] for n in names};aue={n:C@adapted[n]@K[n] for n in names}
        for n in changed:
            par=parents[n];bb=bue[par].inverted()@bue[n];aa=aue[par].inverted()@aue[n]
            q=aa.to_quaternion()@bb.to_quaternion().inverted()
            if tracks[n] and q.dot(Quaternion((tracks[n][-1][6],*tracks[n][-1][3:6])))<0:q.negate()
            elif not tracks[n] and q.w<0:q.negate()
            tracks[n].append([*(aa.translation-bb.translation),q.x,q.y,q.z,q.w,*(aa.to_scale()-bb.to_scale())])
    entry={'base':idle_asset,'duration':support.DURATION,'tracks':[]}
    for n,values in tracks.items():
        if all(max(abs(a-b) for a,b in zip(v,[0,0,0,0,0,0,1,0,0,0]))<1e-5 for v in values):continue
        entry['tracks'].append({'bone':n,'times':[f/60 for f in frames],'values':[v for row in values for v in row]})
    profiles[family]['clips'].append(entry)

for family,data in profiles.items():(O/(family+'_profiles.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
rig.animation_data.action=bpy.data.actions['A_Super90_loader_normal_7'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_end=duration(7,False);scene.frame_set(0)
# Keep the guide in its original bind geometry for repeatable static export.
funnel.matrix_world=I
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Super90_Speedloader_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
shutil.copy2(O/'Super90_Speedloader_Editable.blend',repair/'Super90_Speedloader_ContactR9.blend')
(repair/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SUPER90_SPEEDLOADER_AUTHORED',len(report['clips']),flush=True)
