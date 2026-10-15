"""Warhammer L inspect: raise to view, two-hand rocking and finger adjustments,
a right-hand flick, one full turn of the hammer about its own shaft centreline
inside loosened palms, regrip on the shaft, and return to the common idle.

The turn axis is the measured handle centreline in the native WPN_root frame
(local +Z through the grip-section centre). Whenever a hand holds, it keeps the
exact idle hand-to-shaft relation. While loose, a palm only orbits that same
axis, so it stays at its native radial distance and the round handle rolls
inside it. Arms use native bone lengths, idle elbow guides and no shoulder push.
"""
import ast,copy,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
PLAN='--plan' in sys.argv;SEARCH='--search' in sys.argv
FPS=300
RAISE=.52;WIND=1.52;FLICK=1.66;CATCH=2.66;DURATION=3.34;FOLLOW=.30
# Two-hand rocking about the shaft (degrees), ending in the flick wind-up.
ROCKS=[(RAISE,0.),(.80,22.),(1.08,-18.),(1.32,14.),(WIND,-16.)]
WIND_DEG=ROCKS[-1][1];RELEASE_DEG=24.;CATCH_DEG=WIND_DEG+360.;END_DEG=360.
FLICK_SPEED=420.;FOLLOW_STOP=.04;FOLLOW_PEAK_DEG=RELEASE_DEG+8.
SPIN_SIGN=1.
# Chosen from search.json (--search): head in the upper right, lowest wrist
# bend/forearm twist over every held rocking angle, elbows below the frame.
PRESENT_AXIS=Vector((.70,.35,.62)).normalized()
PRESENT_TWIST=-15.
# Closed palms settle around the round handle while it is raised (whole-palm
# circumferential regrip, fingers unchanged); they return with the idle.
PALM_ROLL={'l':-6.,'r':0.}
ELBOW_FOLLOW=.7
PRESENT_SHIFT=Vector((0.,.01,-.025))
SPIN_DRIFT=Vector((0.,-.008,.012))
VERTICAL_FOV=75.;ASPECT=16/9

SOURCE=P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
idle_local={n:idle[p].inverted()@m if p else m for n,m in idle.items() for p in [parents[n]]}
base=idle['WPN_root'].to_quaternion();axis0=(base@Vector((0,0,1))).normalized()
grips={s:idle['WPN_root'].inverted()@idle['hand_'+s] for s in ('l','r')}
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
module=ast.parse((P.parent/'WhirlwindInertiaV8/author_whirlwind.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'sat','smooth','rigid','frame','axial','quintic'}],type_ignores=[]),'<native_grip_support>','exec'))

# Measured handle centreline: bounding-box centre of the round grip sections.
hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest['WPN_root'].inverted()
hammer_local=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
grip_band=[p for p in hammer_local if -.08<=p.z<=.38]
CX=(min(p.x for p in grip_band)+max(p.x for p in grip_band))*.5
CY=(min(p.y for p in grip_band)+max(p.y for p in grip_band))*.5
AXIS_POINT=Vector((CX,CY,0.))
handle_radius=sorted(math.hypot(p.x-CX,p.y-CY) for p in grip_band)[int(len(grip_band)*.98)]
head_local=[p for p in hammer_local if p.z>.875]
head_center_local=sum(head_local,Vector())/len(head_local)
pivot_local=Vector((CX,CY,(grips['l'].translation.z+grips['r'].translation.z)*.5))
idle_pivot=idle['WPN_root']@pivot_local
radial={s:math.hypot(grips[s].translation.x-CX,grips[s].translation.y-CY) for s in ('l','r')}

def turn(degrees):
    return Matrix.Translation(AXIS_POINT)@Matrix.Rotation(math.radians(SPIN_SIGN*degrees),4,'Z')@Matrix.Translation(-AXIS_POINT)
def present_frame(direction,psi):
    q=Quaternion(direction,math.radians(psi))@axis0.rotation_difference(direction)@base
    return rigid(idle_pivot+PRESENT_SHIFT-q@pivot_local,q)
def present_weight(t):return smooth(t/RAISE)*(1-smooth((t-CATCH)/(DURATION-CATCH)))
def spin_hump(t):return smooth((t-WIND)/.35)*(1-smooth((t-(CATCH-.30))/.40))

SPIN_POWER=(CATCH_DEG-RELEASE_DEG)/(FLICK_SPEED*(CATCH-FLICK)-(CATCH_DEG-RELEASE_DEG))
def theta(t):
    if t<=RAISE:return 0.
    if t<=WIND:
        for (t0,a),(t1,b) in zip(ROCKS,ROCKS[1:]):
            if t<=t1:return a+(b-a)*smooth((t-t0)/(t1-t0))
    if t<=FLICK:
        d=FLICK-WIND;return quintic(WIND_DEG,0.,0.,RELEASE_DEG,FLICK_SPEED,0.,d,(t-WIND)/d)
    if t<=CATCH:
        # Released turn: it only slows down, then the closing palms brake it on
        # exactly one revolution from the wind-up.
        d=CATCH-FLICK;u=(t-FLICK)/d
        return RELEASE_DEG+FLICK_SPEED*d*(u-u**(SPIN_POWER+1)/(SPIN_POWER+1))
    return CATCH_DEG+(END_DEG-CATCH_DEG)*smooth((t-CATCH)/(DURATION-CATCH))
def phi(side,t):
    """Each palm's own angle around the shaft axis; equals theta while holding."""
    if t>=CATCH:return theta(t)
    if side=='l':return theta(t) if t<=WIND else WIND_DEG
    if t<=FLICK:return theta(t)
    # The light palm stops just past the release, then rolls back loose.
    if t<=FLICK+FOLLOW_STOP:return quintic(RELEASE_DEG,FLICK_SPEED,0.,FOLLOW_PEAK_DEG,0.,0.,FOLLOW_STOP,(t-FLICK)/FOLLOW_STOP)
    if t<=FLICK+FOLLOW_STOP+FOLLOW:
        return FOLLOW_PEAK_DEG+(WIND_DEG-FOLLOW_PEAK_DEG)*smooth((t-FLICK-FOLLOW_STOP)/FOLLOW)
    return WIND_DEG

PRESENT=None
def weapon_base(t):
    w=present_weight(t);pa=idle_pivot;pb=PRESENT@pivot_local
    q=base.slerp(PRESENT.to_quaternion(),w)
    return rigid(pa.lerp(pb,w)+SPIN_DRIFT*spin_hump(t)-q@pivot_local,q)
def weapon(t):return weapon_base(t)@turn(theta(t))
def hand_target(side,t):return weapon_base(t)@turn(phi(side,t)+PALM_ROLL[side]*present_weight(t))@grips[side]
def elbow_guide(side,carry):
    """Idle elbow, partly carried by the raise (not by rocking or turning)."""
    e0=idle['lowerarm_'+side].translation
    return e0.lerp(carry@e0,ELBOW_FOLLOW)

roll_state={};reach_shift={'l':0.,'r':0.}
def solve_arm(out,ref,target,side,ideal_e):
    U,L,H,C=[x+'_'+side for x in ('upperarm','lowerarm','hand','clavicle')]
    s0,e0,h0=[ref[n].translation for n in (U,L,H)];u0,l0=e0-s0,h0-e0
    normal=u0.cross(l0).normalized();d=target@ref[H].inverted();dq=d.to_quaternion()
    # Keep the elbow on its native circle nearest the guide, without any
    # shoulder push toward the camera-side arm opening.
    h=target.translation
    s=s0.copy();reach=h-s;limit=(u0.length+l0.length)*.96
    if reach.length>limit:
        shift=reach.length-limit;reach_shift[side]=max(reach_shift[side],shift)
        s+=reach.normalized()*shift;reach=h-s
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

DIGITS=('thumb','index','middle','ring','pinky')
LOOSE={'thumb':{'01':.10,'02':.22,'03':.26},'finger':{'01':.26,'02':.32,'03':.30}}
RIPPLE={'01':.34,'02':.42,'03':.38}
RIPPLE_START={'l':.60,'r':.96};RIPPLE_DELAY={'index':0.,'middle':.045,'ring':.09,'pinky':.135};RIPPLE_SECONDS=.17
OPEN={'l':(1.42,.10,2.48,.16),'r':(1.63,.08,2.52,.14)}
def loose_weight(side,t):
    a,da,b,db=OPEN[side];return smooth((t-a)/da)*(1-smooth((t-b)/db))
def finger_local(n,t):
    original=idle_local[n]
    if not n.startswith(DIGITS) or 'metacarpal' in n:return original
    digit,segment,side=n.split('_')
    table=LOOSE['thumb' if digit=='thumb' else 'finger']
    amount=loose_weight(side,t)*table[segment]
    if digit!='thumb':
        u=(t-RIPPLE_START[side]-RIPPLE_DELAY[digit])/RIPPLE_SECONDS
        if 0.<u<1.:amount=max(amount,RIPPLE[segment]*math.sin(math.pi*u)**2)
    if amount<=0.:return original
    p,q,scale=original.decompose()
    return Matrix.LocRotScale(p,q.slerp(local_rest[n].to_quaternion(),amount),scale)

explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
def build_pose(t):
    pose=copy.deepcopy(idle);pose['WPN_root']=weapon(t)
    carry=weapon_base(t)@idle['WPN_root'].inverted()
    for side in ('l','r'):solve_arm(pose,idle,hand_target(side,t),side,elbow_guide(side,carry))
    done=set(explicit)
    def resolve(n):
        if n in done:return pose[n]
        p=parents[n];pose[n]=resolve(p)@finger_local(n,t) if p else idle[n].copy();done.add(n);return pose[n]
    for n in pose:resolve(n)
    for side in ('l','r'):
        n='ik_hand_'+side
        if n in pose:pose[n]=pose['hand_'+side]@idle['hand_'+side].inverted()@idle[n]
    return pose

fore_idle={s:(idle['hand_'+s].translation-idle['lowerarm_'+s].translation).normalized() for s in ('l','r')}
def wrist_bend(pose,s):
    fore=(pose['hand_'+s].translation-pose['lowerarm_'+s].translation).normalized()
    delta=pose['hand_'+s].to_quaternion()@idle['hand_'+s].to_quaternion().inverted()
    return math.degrees((delta@fore_idle[s]).angle(fore))

tan_v=math.tan(math.radians(VERTICAL_FOV*.5));tan_h=tan_v*ASPECT
def screen(p):return (p.x/p.y/tan_h,p.z/p.y/tan_v) if p.y>1e-4 else (9.,9.)
held_angles=[0.,22.,-18.,14.,-16.,RELEASE_DEG,FOLLOW_PEAK_DEG]
def held_cost(frame_,side,roll,follow):
    """Wrist bend change and forearm twist across the held rocking angles."""
    global ELBOW_FOLLOW
    keep=ELBOW_FOLLOW;ELBOW_FOLLOW=follow
    carry=frame_@idle['WPN_root'].inverted();cost=0.;bend_max=0.;twist_max=0.;elbow=None
    for angle in held_angles:
        roll_state.clear();pose=dict(idle)
        solve_arm(pose,idle,frame_@turn(angle+roll)@grips[side],side,elbow_guide(side,carry))
        bend=wrist_bend(pose,side);twist=abs(math.degrees(roll_state[side]))
        cost+=bend*bend+.3*twist*twist;bend_max=max(bend_max,bend);twist_max=max(twist_max,twist)
        if angle==0.:elbow=pose['lowerarm_'+side].translation.copy()
    ELBOW_FOLLOW=keep
    return cost+.04*roll*roll,bend_max,twist_max,elbow
if SEARCH:
    table=[]
    for direction in [(.50,.40,.77),(.62,.38,.69),(.70,.35,.62),(.42,.48,.77),(.78,.30,.55)]:
        direction=Vector(direction).normalized()
        for psi in range(-90,91,15):
            frame_=present_frame(direction,psi)
            head=frame_@head_center_local;long_axis=(frame_.to_quaternion()@Vector((1,0,0))).normalized()
            broadside=math.degrees(long_axis.angle(head.normalized()))
            for follow in (0.,.35,.7):
                total=0.;row={'axis':[round(x,3) for x in direction],'psi':psi,'follow':follow,
                    'head_ndc':[round(x,3) for x in screen(head)],'head_broadside_deg':round(broadside,1)}
                for side in ('l','r'):
                    best=min((held_cost(frame_,side,roll,follow)+(roll,) for roll in range(-90,91,6)),key=lambda x:x[0])
                    total+=best[0];row[side]={'roll':best[4],'bend_max':round(best[1],1),'twist_max':round(best[2],1),
                        'elbow':[round(x,3) for x in best[3]],'elbow_ndc':[round(x,2) for x in screen(best[3])]}
                row['cost']=round(total,1);table.append(row)
    table.sort(key=lambda r:r['cost'])
    (P/'search.json').write_text(json.dumps(table,indent=1),encoding='utf-8')
    for row in table[:25]:print('WARHAMMER_INSPECT_SEARCH '+json.dumps(row))
    raise SystemExit(0)
PRESENT=present_frame(PRESENT_AXIS,PRESENT_TWIST)
roll_state.clear();reach_shift.update(l=0.,r=0.)

frames=round(DURATION*FPS)
times=[i/FPS for i in range(frames+1)]
poses=[];twist_track={'l':[],'r':[]}
for t in times:
    poses.append(build_pose(t))
    for s in ('l','r'):twist_track[s].append(math.degrees(roll_state[s]))
poses[0]=copy.deepcopy(idle);poses[-1]=copy.deepcopy(idle)

sample=hammer_local[::max(1,len(hammer_local)//2400)]
head_sample=head_local[::max(1,len(head_local)//600)]
clear=[];head_inside=[];head_center=[]
for i in range(0,frames+1,6):
    w=poses[i]['WPN_root']
    clear.append(min((w@v).length for v in sample))
    pts=[screen(w@v) for v in head_sample]
    head_inside.append(sum(1 for u,v in pts if abs(u)<=1 and abs(v)<=1)/len(pts))
    head_center.append(screen(w@head_center_local))
spin_rate=[(theta(times[i+1])-theta(times[i]))*FPS for i in range(frames)]
steps=sorted(((poses[i+1][n].translation-poses[i][n].translation).length*100,round(times[i+1],3),n)
    for i in range(frames) for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r'))[-6:]
bone_error=max(abs((p[b+'_'+s].translation-p[a+'_'+s].translation).length-(rest[b+'_'+s].translation-rest[a+'_'+s].translation).length)*1000
    for p in poses for s in ('l','r') for a,b in [('upperarm','lowerarm'),('lowerarm','hand')])
present_index=round(1.40*FPS)
metrics={'wrist_bend_change_max_degrees':{s:round(max(wrist_bend(p,s) for p in poses),2) for s in ('l','r')},
 'shoulder_reach_shift_max_cm':{s:round(v*100,3) for s,v in reach_shift.items()},
 'max_bone_length_error_mm':bone_error,'largest_joint_steps_cm':[[round(a,3),b,c] for a,b,c in steps],
 'hammer_min_camera_distance_m':round(min(clear),4),
 'head_vertices_on_screen_min_fraction':round(min(head_inside[round(RAISE*FPS/6)+1:round(CATCH*FPS/6)]),3),
 'head_center_screen_ndc_presented':[round(x,3) for x in head_center[present_index//6]],
 'head_center_screen_ndc_range_spin':[[round(min(c[k] for c in head_center[round(WIND*FPS/6):round(CATCH*FPS/6)]),3),
     round(max(c[k] for c in head_center[round(WIND*FPS/6):round(CATCH*FPS/6)]),3)] for k in (0,1)],
 'hands_screen_ndc_presented':{s:[round(x,3) for x in screen(poses[present_index]['hand_'+s].translation)] for s in ('l','r')},
 'elbows_presented_m':{s:[round(x,3) for x in poses[present_index]['lowerarm_'+s].translation] for s in ('l','r')},
 'forearm_twist_range_degrees':{s:[round(min(v),1),round(max(v),1)] for s,v in twist_track.items()},
 'spin_rate_deg_s':{'flick_peak':round(max(spin_rate[round(WIND*FPS):round(FLICK*FPS)]),1),
     'free_min':round(min(spin_rate[round(FLICK*FPS):round(CATCH*FPS)]),2),'free_max':round(max(spin_rate[round(FLICK*FPS):round(CATCH*FPS)]),1)},
 'free_turn_monotonic':all(r>=-1e-6 for r in spin_rate[round(WIND*FPS):round(CATCH*FPS)]),
 'right_palm_angle_range_degrees':[round(min(phi('r',t) for t in times if t<CATCH),2),round(max(phi('r',t) for t in times if t<CATCH),2)]}
print('WARHAMMER_INSPECT_PLAN '+json.dumps(metrics))
if PLAN:raise SystemExit(0)

name='A_Warhammer_Inspect';bake(name,poses,FPS)
# Actual skinned arm surface distance from the eye on sampled frames.
arms=bpy.data.objects['Warhammer_BareArmsV7'];arm_clear=[]
for i in range(0,frames+1,15):
    scene.frame_set(i);depsgraph=bpy.context.evaluated_depsgraph_get();evaluated=arms.evaluated_get(depsgraph)
    mesh=evaluated.to_mesh();mw=evaluated.matrix_world
    arm_clear.append(min((mw@v.co).length for v in mesh.vertices));evaluated.to_mesh_clear()
metrics['arm_surface_min_camera_distance_m']=round(min(arm_clear),4)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_Inspect_Editable.blend'))
receipt={'revision':'InspectShaftTurnV1_20261015','clips':[name],'fps':FPS,'seconds':DURATION,
 'runtime_destination':'/Game/Weapons/SteelWarhammer20261014/InspectV1','source':str(SOURCE),
 'phases_seconds':{'raise':[0.,RAISE],'two_hand_rocking':[RAISE,WIND],'right_flick':[WIND,FLICK],
     'free_turn_in_loose_palms':[FLICK,CATCH],'regrip_and_return':[CATCH,DURATION]},
 'rocking_keys_degrees':ROCKS,'turn_degrees_wind_to_catch':CATCH_DEG-WIND_DEG,'release_speed_deg_s':FLICK_SPEED,
 'free_turn_profile':'v(u)=V(1-u^k), k=%.4f: only slows after release; closing palms brake it at one revolution'%SPIN_POWER,
 'turn_axis':'native WPN_root local +Z through measured handle centre','turn_axis_point_local_m':[CX,CY],
 'turn_axis_point_local_ue_cm':[CX*100,-CY*100],'handle_radius_m':handle_radius,'palm_radial_distance_m':radial,
 'presentation':{'shaft_direction':list(PRESENT_AXIS),'pivot_shift_m':list(PRESENT_SHIFT),'twist_degrees':PRESENT_TWIST,
     'palm_roll_degrees':PALM_ROLL,'elbow_follow':ELBOW_FOLLOW,'spin_drift_m':list(SPIN_DRIFT)},
 'grip':'Exact idle hand-to-shaft frames while holding; loose palms orbit only the shaft axis at native radius',
 'left_hand':{'loose_seconds':[OPEN['l'][0],OPEN['l'][2]+OPEN['l'][3]],'finger_ripple_start':RIPPLE_START['l']},
 'right_hand':{'drives_flick_until':FLICK,'follow_through_peak_degrees':FOLLOW_PEAK_DEG,'follow_stop_seconds':FOLLOW_STOP,'roll_back_seconds':FOLLOW,'loose_seconds':[OPEN['r'][0],OPEN['r'][2]+OPEN['r'][3]],
     'finger_ripple_start':RIPPLE_START['r']},
 'fingers':'Native idle wrap; loosen partially toward bind pose (thumb least), staggered index-to-pinky lifts while rocking',
 'arm_support':'Native bone lengths; elbows on native circle nearest the idle elbow partly carried by the raise; no shoulder support offsets',
 'metrics':metrics,'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_INSPECT_AUTHORED '+json.dumps(metrics))
