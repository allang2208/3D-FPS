"""Walking warhammer inspect: only the shaft-turn half of the accepted InspectV1,
three times faster and three times harder.

No rocking or finger drumming. The hammer rises quickly to the same accepted
presentation while both hands wind it up, the right hand flicks it at three
times the release speed, it makes one revolution about the measured handle
centreline at three times the V1 turn rate, and the closing palms catch it
while it still carries speed, so the gripping hands give with it before the
return to idle. Grip, palm-orbit, elbow and finger rules are reused unchanged
from InspectV1/author_inspect.py.
"""
import ast,copy,json,math,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
V1=P.parent/'InspectV1'
PLAN='--plan' in sys.argv
# SpeedV3: the walking turn is doubled again (6x the V1 turn rate).
FPS=300;SPEED=6.;FORCE=3.
accepted=json.loads((V1/'authored.json').read_text())
present=accepted['presentation']
PRESENT_AXIS=Vector(present['shaft_direction']).normalized();PRESENT_TWIST=present['twist_degrees']
PALM_ROLL=dict(present['palm_roll_degrees']);ELBOW_FOLLOW=present['elbow_follow'];PRESENT_SHIFT=Vector(present['pivot_shift_m'])

# InspectV1 turn half: 40 deg drive in 0.14 s to 420 deg/s, 1.0 s free turn,
# palm stops 8 deg past release in 0.04 s.
V1_DRIVE_DEG=40.;V1_DRIVE=accepted['phases_seconds']['right_flick'][1]-accepted['phases_seconds']['right_flick'][0]
V1_FREE=accepted['phases_seconds']['free_turn_in_loose_palms'][1]-accepted['phases_seconds']['free_turn_in_loose_palms'][0]
V1_SPEED=accepted['release_speed_deg_s'];V1_FOLLOW_DEG=8.;FOLLOW_STOP=accepted['right_hand']['follow_stop_seconds']

WIND_START=.10;RAISE=.32;WIND=RAISE;WIND_DEG=-16.;RELEASE_DEG=16.
FLICK_SPEED=V1_SPEED*SPEED
# Same drive velocity shape as V1 (no reversal), three times the rate.
DRIVE=V1_DRIVE*(RELEASE_DEG-WIND_DEG)/V1_DRIVE_DEG/SPEED
FLICK=WIND+DRIVE;FREE=V1_FREE/SPEED;CATCH=FLICK+FREE
CATCH_DEG=WIND_DEG+360.;END_DEG=360.
# The palms clamp while a quarter of the release speed remains; the hands and
# hammer roll on together and stop (monotonic quintic: travel = v*d/2).
CATCH_SPEED=FLICK_SPEED*.25;ABSORB=.07;ABSORB_DEG=.5*CATCH_SPEED*ABSORB
SETTLE=CATCH+ABSORB;DURATION=SETTLE+.53
# WristV2: the 3x wrist snap past release (24 deg, wrist bend 42.5 deg) looked
# forced. Halve it; the stop keeps the no-reversal shape (travel = v*d/2).
FOLLOW_OVERSHOOT_DEG=12.;FOLLOW_STOP=FOLLOW_OVERSHOOT_DEG/(.5*FLICK_SPEED)
FOLLOW_PEAK_DEG=RELEASE_DEG+FOLLOW_OVERSHOOT_DEG
# The shorter free turn must hold the palm back at the wind-up angle before
# its fingers start closing for the catch.
FOLLOW_BACK=min(.25,(CATCH-.06)-(FLICK+FOLLOW_STOP))
if FOLLOW_BACK<.06:raise RuntimeError('Free turn too short for the right palm to roll back')
_c=1-CATCH_SPEED/FLICK_SPEED;_vd=FLICK_SPEED*FREE;FREE_POWER=_c/(1-(CATCH_DEG-RELEASE_DEG)/_vd)-1
if FREE_POWER<=1.:raise RuntimeError('Free-turn profile needs k>1 for a smooth release')

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
# Accepted InspectV1 grip/arm/finger rules and their constants, not its timeline.
module=ast.parse((V1/'author_inspect.py').read_text(encoding='utf-8'))
REUSED_FUNCTIONS={'turn','present_frame','weapon_base','weapon','hand_target','elbow_guide','solve_arm','loose_weight','finger_local','build_pose','wrist_bend'}
REUSED_CONSTANTS={'SPIN_SIGN','SPIN_DRIFT','VERTICAL_FOV','ASPECT','DIGITS','LOOSE','RIPPLE','RIPPLE_DELAY','RIPPLE_SECONDS'}
exec(compile(ast.Module(body=[n for n in module.body if (isinstance(n,ast.FunctionDef) and n.name in REUSED_FUNCTIONS) or
    (isinstance(n,ast.Assign) and all(isinstance(t,ast.Name) and t.id in REUSED_CONSTANTS for t in n.targets))],type_ignores=[]),'<inspect_v1_rules>','exec'))

hammer=bpy.data.objects['SM_SteelWarhammer'];inv=rest['WPN_root'].inverted()
hammer_local=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
grip_band=[p for p in hammer_local if -.08<=p.z<=.38]
CX=(min(p.x for p in grip_band)+max(p.x for p in grip_band))*.5
CY=(min(p.y for p in grip_band)+max(p.y for p in grip_band))*.5
AXIS_POINT=Vector((CX,CY,0.))
if abs(CX-accepted['turn_axis_point_local_m'][0])>1e-6 or abs(CY-accepted['turn_axis_point_local_m'][1])>1e-6:
    raise RuntimeError('Handle centreline differs from InspectV1')
head_local=[p for p in hammer_local if p.z>.875]
head_center_local=sum(head_local,Vector())/len(head_local)
pivot_local=Vector((CX,CY,(grips['l'].translation.z+grips['r'].translation.z)*.5))
idle_pivot=idle['WPN_root']@pivot_local
explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
fore_idle={s:(idle['hand_'+s].translation-idle['lowerarm_'+s].translation).normalized() for s in ('l','r')}
roll_state={};reach_shift={'l':0.,'r':0.}
# No rocking-phase finger drumming in the walking variant.
RIPPLE_START={'l':-10.,'r':-10.}
OPEN={'l':(WIND-.08,.08,CATCH-.07,.06),'r':(FLICK-.015,.04,CATCH-.06,.055)}

def present_weight(t):return smooth(t/RAISE)*(1-smooth((t-SETTLE)/(DURATION-SETTLE)))
def spin_hump(t):return smooth((t-WIND)/.12)*(1-smooth((t-(CATCH-.10))/.20))
def theta(t):
    if t<=WIND_START:return 0.
    if t<=WIND:return WIND_DEG*smooth((t-WIND_START)/(WIND-WIND_START))
    if t<=FLICK:return quintic(WIND_DEG,0.,0.,RELEASE_DEG,FLICK_SPEED,0.,DRIVE,(t-WIND)/DRIVE)
    if t<=CATCH:
        # Free turn only slows: v(u)=V(1-c*u^k), still c*V short of zero at the clamp.
        u=(t-FLICK)/FREE
        return RELEASE_DEG+FLICK_SPEED*FREE*(u-_c*u**(FREE_POWER+1)/(FREE_POWER+1))
    if t<=SETTLE:return quintic(CATCH_DEG,CATCH_SPEED,0.,CATCH_DEG+ABSORB_DEG,0.,0.,ABSORB,(t-CATCH)/ABSORB)
    return CATCH_DEG+ABSORB_DEG+(END_DEG-CATCH_DEG-ABSORB_DEG)*smooth((t-SETTLE)/(DURATION-SETTLE))
def phi(side,t):
    """Each palm's own angle around the shaft axis; equals theta while holding."""
    if t>=CATCH:return theta(t)
    if side=='l':return theta(t) if t<=WIND else WIND_DEG
    if t<=FLICK:return theta(t)
    if t<=FLICK+FOLLOW_STOP:return quintic(RELEASE_DEG,FLICK_SPEED,0.,FOLLOW_PEAK_DEG,0.,0.,FOLLOW_STOP,(t-FLICK)/FOLLOW_STOP)
    if t<=FLICK+FOLLOW_STOP+FOLLOW_BACK:
        return FOLLOW_PEAK_DEG+(WIND_DEG-FOLLOW_PEAK_DEG)*smooth((t-FLICK-FOLLOW_STOP)/FOLLOW_BACK)
    return WIND_DEG

PRESENT=present_frame(PRESENT_AXIS,PRESENT_TWIST)
frames=round(DURATION*FPS)
times=[i/FPS for i in range(frames+1)]
poses=[];twist_track={'l':[],'r':[]}
for t in times:
    poses.append(build_pose(t))
    for s in ('l','r'):twist_track[s].append(math.degrees(roll_state[s]))
poses[0]=copy.deepcopy(idle);poses[-1]=copy.deepcopy(idle)

tan_v=math.tan(math.radians(VERTICAL_FOV*.5));tan_h=tan_v*ASPECT
def screen(p):return (p.x/p.y/tan_h,p.z/p.y/tan_v) if p.y>1e-4 else (9.,9.)
sample=hammer_local[::max(1,len(hammer_local)//2400)]
head_sample=head_local[::max(1,len(head_local)//600)]
clear=[];head_inside=[]
for i in range(0,frames+1,3):
    w=poses[i]['WPN_root'];clear.append(min((w@v).length for v in sample))
    if WIND<=times[i]<=SETTLE:
        pts=[screen(w@v) for v in head_sample];head_inside.append(sum(1 for u,v in pts if abs(u)<=1 and abs(v)<=1)/len(pts))
rate=[(theta(times[i+1])-theta(times[i]))*FPS for i in range(frames)]
span=lambda a,b:rate[round(a*FPS):round(b*FPS)]
steps=sorted(((poses[i+1][n].translation-poses[i][n].translation).length*100,round(times[i+1],3),n)
    for i in range(frames) for n in ('upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r'))[-6:]
bone_error=max(abs((p[b+'_'+s].translation-p[a+'_'+s].translation).length-(rest[b+'_'+s].translation-rest[a+'_'+s].translation).length)*1000
    for p in poses for s in ('l','r') for a,b in [('upperarm','lowerarm'),('lowerarm','hand')])
metrics={'seconds':round(DURATION,4),'wrist_bend_change_max_degrees':{s:round(max(wrist_bend(p,s) for p in poses),2) for s in ('l','r')},
 'forearm_twist_range_degrees':{s:[round(min(v),1),round(max(v),1)] for s,v in twist_track.items()},
 'shoulder_reach_shift_max_cm':{s:round(v*100,3) for s,v in reach_shift.items()},
 'max_bone_length_error_mm':bone_error,'largest_joint_steps_cm':[[round(a,3),b,c] for a,b,c in steps],
 'hammer_min_camera_distance_m':round(min(clear),4),'head_vertices_on_screen_min_fraction_turn':round(min(head_inside),3),
 'spin_rate_deg_s':{'drive_peak':round(max(span(WIND,FLICK)),1),'free_start':round(rate[round(FLICK*FPS)],1),
     'free_min':round(min(span(FLICK,CATCH)),1),'catch':round(rate[round(CATCH*FPS)-1],1)},
 'turn_monotonic_until_settle':all(r>=-1e-6 for r in span(WIND,SETTLE)),
 'turn_seconds_wind_to_catch':round(CATCH-WIND,4),'v1_turn_seconds_wind_to_catch':round(V1_DRIVE+V1_FREE,4),
 'right_palm_angle_range_degrees':[round(min(phi('r',t) for t in times if t<CATCH),2),round(max(phi('r',t) for t in times if t<CATCH),2)]}
print('WARHAMMER_INSPECT_WALK_PLAN '+json.dumps(metrics))
if PLAN:raise SystemExit(0)

name='A_Warhammer_InspectWalk';bake(name,poses,FPS)
arms=bpy.data.objects['Warhammer_BareArmsV7'];arm_clear=[]
for i in range(0,frames+1,8):
    scene.frame_set(i);depsgraph=bpy.context.evaluated_depsgraph_get();evaluated=arms.evaluated_get(depsgraph)
    mesh=evaluated.to_mesh();mw=evaluated.matrix_world
    arm_clear.append(min((mw@v.co).length for v in mesh.vertices));evaluated.to_mesh_clear()
metrics['arm_surface_min_camera_distance_m']=round(min(arm_clear),4)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_InspectWalk_Editable.blend'))
receipt={'revision':'InspectWalkSpeedV3_20261015','previous_revision':'InspectWalkWristV2_20261015',
 'change':'Turn rate doubled again (%.0fx V1): release %.0f deg/s, drive %.4f s, free turn %.4f s; palm overshoot kept %.1f deg (stop %.4f s), roll-back %.4f s'%(SPEED,FLICK_SPEED,DRIVE,FREE,FOLLOW_OVERSHOOT_DEG,FOLLOW_STOP,FOLLOW_BACK),'clips':[name],'fps':FPS,'seconds':DURATION,
 'runtime_destination':'/Game/Weapons/SteelWarhammer20261014/InspectV1','source':str(SOURCE),
 'accepted_reference':str(V1/'author_inspect.py'),'speed_multiplier':SPEED,'force_multiplier':FORCE,
 'phases_seconds':{'raise_with_windup':[0.,RAISE],'right_flick':[WIND,FLICK],'free_turn_in_loose_palms':[FLICK,CATCH],
     'catch_absorb':[CATCH,SETTLE],'return':[SETTLE,DURATION]},
 'omitted_from_v1':'raise hold, two-hand rocking and finger drumming',
 'windup_degrees':WIND_DEG,'release_degrees':RELEASE_DEG,'release_speed_deg_s':FLICK_SPEED,'drive_seconds':DRIVE,
 'free_turn_seconds':FREE,'free_turn_profile':'v(u)=V(1-c*u^k), c=%.3f, k=%.4f'%(_c,FREE_POWER),
 'turn_degrees_wind_to_catch':CATCH_DEG-WIND_DEG,'catch_speed_deg_s':CATCH_SPEED,'catch_absorb_degrees':ABSORB_DEG,'catch_absorb_seconds':ABSORB,
 'right_follow_through_peak_degrees':FOLLOW_PEAK_DEG,'right_follow_stop_seconds':FOLLOW_STOP,'right_roll_back_seconds':FOLLOW_BACK,
 'presentation':present,'turn_axis_point_local_m':[CX,CY],
 'grip':'InspectV1 rules: exact idle hand-to-shaft frames while holding; loose palms orbit only the shaft axis at native radius',
 'metrics':metrics,'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_INSPECT_WALK_AUTHORED '+json.dumps(metrics))
