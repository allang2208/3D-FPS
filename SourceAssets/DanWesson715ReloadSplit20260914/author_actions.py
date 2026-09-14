"""Distinct tactical/empty 715 reloads with a stable elbow plane.

Nonempty: load directly. Empty: palm presses extractor, all cases fall, load.
Both retain left-opening mechanics and now use a stronger right-wrist impulse.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Euler
DEST=Path(__file__).parent
F=DEST.parent/'DanWesson715ReloadFlick20260914/author_actions.py'
previous=F.read_text(encoding='utf-8')
__file__=str(F)
exec(compile(previous.split('def pose_single(')[0],str(F),'exec'),globals())
__file__=str(DEST/'author_actions.py');O=DEST
(O/'Animations').mkdir(exist_ok=True)
BEGIN=.60;EMPTY_BEGIN=1.50;STEP=1.10;VISIBLE=.10;ALIGN=.40;SEAT=.64;HOLD=.74;RETREAT=.90;TAIL=.70
EMPTY_CLEAR=1.28

def ease(x):
    x=max(0.,min(1.,x));return x*x*x*(x*(6*x-15)+10)

def hand_at(p,old,side,H):
    hn='hand_'+side;delta=H@old[hn].inverted()
    for n in names:
        if n==hn or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n]=delta@old[n]
    un,fn='upperarm_'+side,'lowerarm_'+side
    shoulder=old[un].translation.copy();elbow=old[fn].translation;wrist=old[hn].translation;target=H.translation
    l1=(elbow-shoulder).length;l2=(wrist-elbow).length
    original_axis=(wrist-shoulder).normalized()
    reference_pole=(elbow-shoulder)-original_axis*(elbow-shoulder).dot(original_axis)
    reference_pole.normalize()
    v=target-shoulder;distance=v.length;axis=v.normalized();reach=(l1+l2)*.985
    if distance>reach:shoulder+=axis*(distance-reach);distance=reach
    distance=max(abs(l1-l2)+.0001,distance)
    # Transport the original bend plane with the shoulder-to-wrist direction.
    # Projecting the old elbow vector onto a new axis flips when those align.
    pole=original_axis.rotation_difference(axis)@reference_pole
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    e=shoulder+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    p['clavicle_'+side]=old['clavicle_'+side].copy()
    p['clavicle_'+side].translation+=shoulder-old[un].translation
    for n,pos,direction,was in [(un,shoulder,e-shoulder,elbow-old[un].translation),(fn,e,target-e,wrist-elbow)]:
        p[n]=Matrix.LocRotScale(pos,was.rotation_difference(direction)@old[n].to_quaternion(),old[n].to_scale())
    for n in names:
        if n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):
            base=un if n.startswith('upperarm') else fn;p[n]=p[base]@old[base].inverted()@old[n]
    if 'ik_hand_'+side in p:p['ik_hand_'+side]=H.copy()

def wrist_motion(t,close_begin,finish,empty=False,speed=False):
    load_weight=smooth(t/.50)*(1-smooth((t-close_begin)/(finish-close_begin)))
    opening_bank=key_sample([(0,0),(.13,-9),(.22,-9),(.30,45),(.39,25),(.53,0)],t)
    opening_yaw=key_sample([(0,0),(.21,-4),(.30,21),(.40,9),(.50,0)],t)
    opening_shift=key_sample([(0,0),(.21,-.010),(.30,.047),(.39,.021),(.52,0)],t)
    q=t-close_begin
    closing_bank=key_sample([(0,0),(.11,12),(.24,-46),(.37,-13),(.46,4),(.58,0)],q)
    closing_yaw=key_sample([(0,0),(.11,4),(.24,-19),(.38,-5),(.50,1.5),(.62,0)],q)
    closing_shift=key_sample([(0,0),(.11,.010),(.24,-.044),(.38,-.010),(.47,.003),(.62,0)],q)
    pitch=18*load_weight
    if speed:pitch+=key_sample([(0,0),(.50,0),(.84,-71),(1.10,-71),(1.48,0),(finish,0)],t)
    return idle['WPN_root']@Matrix.LocRotScale(Vector((.016*load_weight+opening_shift+closing_shift,.048*load_weight,.020*load_weight)),Euler((math.radians(pitch),math.radians(8*load_weight+opening_bank+closing_bank),math.radians(7*load_weight+opening_yaw+closing_yaw)),'XYZ').to_quaternion(),Vector((1,1,1)))

press_shape={n:m.copy() for n,m in rest_hand.items()}
for family,values in [('thumb',[.02,.10,.10,-.12,.1]),('index',[.08,.10,.06,0]),('middle',[.10,.12,.08,0]),('ring',[.15,.20,.12,0]),('pinky',[.20,.24,.15,0])]:
    press_shape.update(finger_pose(family,values))

def pouch_point(D):return (D@gunlocal['WPN_Cylinder']).translation+Vector((.135,.205,-.200))

def approach_point(a,b,w):
    w=max(0,min(1,w));return a.lerp(b,ease(w))+Vector((.018,0,.018))*(16*w*w*(1-w)*(1-w))

def stroke(t):return .035*smooth((t-.85)/.18)*(1-smooth((t-1.08)/.14))

def press_goal(D,travel):
    point=D@Vector((0,-.1195+travel,.03092))
    return hand_goal(point,(0,1,0),(0,0,1),'palm')

def empty_intro(t,D,pouch):
    before=press_goal(D,-.027);contact=press_goal(D,0);pressed=press_goal(D,stroke(t))
    if t<.48:return open_hand(t,D),relaxed
    if t<.77:return hand_path(clearance(D),before,(t-.48)/.29),blend_shapes(relaxed,press_shape,smooth((t-.48)/.29))
    if t<.85:return hand_path(before,contact,(t-.77)/.08),press_shape
    if t<1.08:return pressed,press_shape
    if t<1.22:return hand_path(press_goal(D,.035),before,(t-1.08)/.14),press_shape
    return hand_path(before,grasp(pouch),(t-1.22)/.28),blend_shapes(press_shape,relaxed,smooth((t-1.22)/.28))

def case_pose(p,G,D,index,M):
    bn=f'WPN_Case_{index}';p[bn]=M;p[f'WPN_Round_{index}']=M@gunlocal[bn].inverted()@gunlocal[f'WPN_Round_{index}']

def eject_cases(p,G,D,t):
    p['WPN_Extractor']=G@D@Matrix.Translation((0,stroke(t),0))@gunlocal['WPN_Extractor']
    for i in range(6):
        bn=f'WPN_Case_{i}';M=G@D@gunlocal[bn]
        if .85<=t<EMPTY_CLEAR:
            fall=max(0,t-1.03);M=G@D@Matrix.Translation((0,.035*smooth((t-.85)/.18)+.22*fall,0))@gunlocal[bn]
            M.translation+=Vector((0,0,-2.8*fall*fall))
        elif t>=EMPTY_CLEAR:M=M@hidden
        case_pose(p,G,D,i,M)

def pose_single(start,count,t):
    empty=start==0;begin=EMPTY_BEGIN if empty else BEGIN
    close_begin=begin+count*STEP;finish=close_begin+TAIL
    p,old,G,D=begin_pose(t,close_begin,finish,speed=empty)
    pouch=pouch_point(D);shape=relaxed
    weight=smooth(t/.22)*(1-smooth((t-close_begin-.40)/.30))
    if empty:eject_cases(p,G,D,t)
    elif t>=.48:
        for i in range(start,6):case_pose(p,G,D,i,G@D@gunlocal[f'WPN_Case_{i}']@hidden)
    if t<begin:
        if empty:H,shape=empty_intro(t,D,pouch)
        elif t<.40:H=open_hand(t,D)
        else:H=hand_path(clearance(D),grasp(pouch),(t-.40)/.20)
    elif t<close_begin:
        cycle=min(count-1,int((t-begin)/STEP));phase=t-begin-cycle*STEP;index=start+cycle
        mouth=D@rear_points[index];align=mouth+Vector((0,.060,0));retreat=mouth+Vector((0,.055,0))
        if phase<VISIBLE:
            point=pouch;shape=blend_shapes(relaxed,templates['cartridge'],smooth((phase-.015)/.070))
        elif phase<ALIGN:point=approach_point(pouch,align,(phase-VISIBLE)/(ALIGN-VISIBLE));shape=templates['cartridge']
        elif phase<SEAT:point=align.lerp(mouth,ease((phase-ALIGN)/(SEAT-ALIGN)));shape=templates['cartridge']
        elif phase<HOLD:point=mouth;shape=templates['cartridge']
        elif phase<RETREAT:
            point=mouth.lerp(retreat,ease((phase-HOLD)/(RETREAT-HOLD)));shape=blend_shapes(templates['cartridge'],relaxed,smooth((phase-HOLD)/.09))
        else:point=approach_point(retreat,pouch,(phase-RETREAT)/(STEP-RETREAT));shape=relaxed
        H=grasp(point)
        for i in range(start,index):case_pose(p,G,D,i,G@D@gunlocal[f'WPN_Case_{i}'])
        if phase>=VISIBLE:
            offset=point-mouth if phase<SEAT else Vector()
            case_pose(p,G,D,index,G@Matrix.Translation(offset)@D@gunlocal[f'WPN_Case_{index}'])
    else:
        for i in range(start,start+count):case_pose(p,G,D,i,G@D@gunlocal[f'WPN_Case_{i}'])
        H=close_hand(t-close_begin,D,grasp(pouch))
    hand_at(p,old,'l',G@H);apply_hand_shape(p,shape,weight)
    return p

def pose_speed(start,t):
    empty=start==0;duration=3.85 if empty else 3.6;u=t*3.6/duration
    p,old,G,D=begin_pose(u,2.68,3.6,speed=empty)
    if empty:eject_cases(p,G,D,u)
    elif u>=.48:
        for i in range(start,6):case_pose(p,G,D,i,G@D@gunlocal[f'WPN_Case_{i}']@hidden)
    travel=key_sample([(1.28,.19),(1.70,.095),(2.20,.017),(2.42,0),(2.53,.012),(2.78,.20)],u)
    down=key_sample([(1.28,-.22),(1.72,-.075),(2.12,0),(2.53,0),(2.78,-.22)],u)
    sideways=key_sample([(1.28,.10),(1.90,.020),(2.12,0),(2.53,0),(2.78,.10)],u)
    offset=Vector((sideways,travel-.0135,down))
    loadpoint=D@Vector((0,0,.03092))+offset;load=grasp(loadpoint,kind='loader');shape=relaxed
    if 1.40<=u<=2.76:p['WPN_Loader']=G@Matrix.Translation(offset)@D@gunlocal['WPN_Loader']
    if empty and u<1.22:H,shape=empty_intro(u,D,pouch_point(D))
    elif u<.48:H=open_hand(u,D)
    elif u<1.40:
        start_at=1.22 if empty else .48
        A=press_goal(D,-.027) if empty else clearance(D)
        H=hand_path(A,load,(u-start_at)/(1.40-start_at))
        shape=blend_shapes(press_shape if empty else relaxed,templates['loader'],smooth((u-start_at)/(1.40-start_at)))
    elif u<2.68:H=load;shape=templates['loader']
    elif u<2.80:H=hand_path(load,clearance(D),(u-2.68)/.12);shape=blend_shapes(templates['loader'],relaxed,smooth((u-2.68)/.12))
    elif u<3.10:H=clearance(D)
    else:H=hand_path(clearance(D),leftlocal,(u-3.10)/.50)
    hand_at(p,old,'l',G@H);apply_hand_shape(p,shape,smooth(u/.22)*(1-smooth((u-3.10)/.50)))
    for i in range(start,6):
        bn=f'WPN_Case_{i}'
        if 1.44<=u<2.42:case_pose(p,G,D,i,G@Matrix.Translation((sideways,travel,down))@D@gunlocal[bn])
        elif u>=2.42:case_pose(p,G,D,i,G@D@gunlocal[bn])
    return p

bake_source='def bake('+previous.split('def bake(',1)[1].split('\nactions={}',1)[0]
exec(compile(bake_source.replace('DW715_Flick_','DW715_Split_').replace('DW715_FLICK_EXPORTED','DW715_SPLIT_EXPORTED'),str(F),'exec'),globals())
actions={};manifest={'normal_begin':BEGIN,'empty_begin':EMPTY_BEGIN,'step':STEP,'visible':VISIBLE,'align':ALIGN,'seat':SEAT,'hold':HOLD,'empty_case_clear':EMPTY_CLEAR,'tail':TAIL,'sample_rate':120,'clips':{}}
for start in range(6):
    for count in range(1,7-start):
        kind=f'single_{start}_{count}';begin=EMPTY_BEGIN if start==0 else BEGIN;duration=begin+count*STEP+TAIL
        actions[kind]=bake(kind,duration,lambda t,a=start,b=count:pose_single(a,b,t))
        manifest['clips'][kind]={'duration':duration,'destination':'/Game/Weapons/DanWesson715/ReloadSplit20260914/Animations','empty':start==0,'seats':[begin+i*STEP+SEAT for i in range(count)]}
for start in range(6):
    kind=f'speed_{start}';duration=3.85 if start==0 else 3.6
    actions[kind]=bake(kind,duration,lambda t,a=start:pose_speed(a,t))
    manifest['clips'][kind]={'duration':duration,'destination':'/Game/Weapons/DanWesson715/ReloadSplit20260914/Animations','empty':start==0}
rig.animation_data.action=actions['single_0_6'];rig.animation_data.action_slot=actions['single_0_6'].slots[0];s.frame_start=0;s.frame_end=528;s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_ReloadSplit_Editable.blend'))
(O/'animation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('DW715_SPLIT_AUTHORING_COMPLETE',flush=True)
