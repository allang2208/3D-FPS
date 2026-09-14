"""715 authored right-arm follow-through, using the accepted Split hand contacts.

Raises the actual root-pose baseline and drives movement from reload phases.
No gameplay timing changes, procedural runtime shake, or new finger solving.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Euler
MOTION_DIR=Path(__file__).resolve().parent
SPLIT_FILE=MOTION_DIR.parent/'DanWesson715ReloadSplit20260914/author_actions.py'
split_source=SPLIT_FILE.read_text(encoding='utf-8')
__file__=str(SPLIT_FILE)
exec(compile(split_source.split('\nbake_source=')[0],str(SPLIT_FILE),'exec'),globals())
O=MOTION_DIR;__file__=str(O/'author_actions.py')
(O/'Animations').mkdir(exist_ok=True)

# Physical authoring units: meters and degrees. These are the root's values,
# not multipliers on the former small impulse or camera shake settings.
MOTION={
 'presentation':{'offset_m':[.032,.070,.036],'rotation_deg':[30,14,12]},
 'opening':{
  'bank':[(0,0),(.12,-15),(.22,-15),(.29,66),(.38,34),(.47,-5),(.57,0)],
  'yaw':[(0,0),(.21,-8),(.29,32),(.39,13),(.48,-3),(.57,0)],
  'pitch':[(0,0),(.20,-7),(.29,13),(.40,5),(.54,0)],
  'x':[(0,0),(.21,-.019),(.29,.080),(.38,.032),(.47,-.006),(.57,0)],
  'y':[(0,0),(.21,-.008),(.29,.026),(.40,.012),(.57,0)],
  'z':[(0,0),(.21,-.008),(.29,.036),(.39,.013),(.55,0)]},
 'closing':{
  'bank':[(0,0),(.11,18),(.23,-70),(.35,-24),(.45,8),(.61,0)],
  'yaw':[(0,0),(.11,8),(.23,-31),(.36,-10),(.47,4),(.64,0)],
  'pitch':[(0,0),(.11,7),(.23,-12),(.36,-4),(.46,3),(.64,0)],
  'x':[(0,0),(.11,.019),(.23,-.078),(.36,-.024),(.47,.007),(.64,0)],
  'y':[(0,0),(.11,.008),(.23,-.028),(.36,-.009),(.47,.005),(.64,0)],
  'z':[(0,0),(.11,.010),(.23,-.024),(.36,-.009),(.47,.005),(.64,0)]},
 # Each loop returns exactly to its start. During alignment, settle first;
 # at seating, a small shared root response gives the right hand resistance.
 'single_cycle':{
  'pitch':[(0,0),(.14,-4),(.31,6),(.40,2),(.55,0),(.64,-2.8),(.70,1.0),(.79,0),(.96,-3.5),(1.10,0)],
  'bank':[(0,0),(.16,4),(.34,-4),(.42,-1.5),(.56,0),(.64,1.3),(.74,0),(.96,3),(1.10,0)],
  'yaw':[(0,0),(.14,-4.5),(.32,5),(.42,1.5),(.56,0),(.64,-1.6),(.76,0),(.96,-3),(1.10,0)],
  'x':[(0,0),(.14,.010),(.32,-.010),(.42,-.003),(.56,0),(.64,.003),(.76,0),(.96,.009),(1.10,0)],
  'y':[(0,0),(.14,.012),(.32,-.015),(.42,-.004),(.55,0),(.64,.008),(.72,-.002),(.79,0),(.96,.010),(1.10,0)],
  'z':[(0,0),(.14,-.008),(.32,.013),(.42,.004),(.56,0),(.64,-.004),(.74,0),(.96,-.006),(1.10,0)]},
 'speedloader':{
  'pitch':[(.48,0),(.85,-3),(1.22,-5),(1.72,9),(2.12,3),(2.20,0),(2.42,-4),(2.50,1.5),(2.68,0)],
  'bank':[(.48,0),(.90,3),(1.30,5),(1.78,-6),(2.12,-2),(2.20,0),(2.42,2),(2.53,0),(2.68,0)],
  'yaw':[(.48,0),(.90,-3),(1.30,-7),(1.78,8),(2.12,2),(2.20,0),(2.42,-2.5),(2.53,0),(2.68,0)],
  'x':[(.48,0),(.90,.008),(1.30,.015),(1.78,-.016),(2.12,-.004),(2.20,0),(2.42,.004),(2.53,0),(2.68,0)],
  'y':[(.48,0),(.90,.009),(1.30,.024),(1.78,-.024),(2.12,-.008),(2.20,0),(2.42,.012),(2.52,-.003),(2.68,0)],
  'z':[(.48,0),(.90,.012),(1.30,-.015),(1.78,.020),(2.12,.005),(2.20,0),(2.42,-.006),(2.53,0),(2.68,0)]},
 'empty_press':{
  'pitch':[(0,0),(.50,0),(.84,-83),(1.03,-86),(1.10,-80),(1.25,-42),(1.48,0)],
  'y':[(0,0),(.70,0),(.85,-.006),(1.03,.016),(1.12,-.004),(1.28,0)],
  'z':[(0,0),(.50,0),(.84,.024),(1.03,.030),(1.12,.021),(1.48,0)]}
}

motion_mode='single'
source_pose_single=pose_single;source_pose_speed=pose_speed

def phase_values(keys,t):
    # Every authoring key is eased with zero endpoint velocity/acceleration.
    result={}
    for name,curve in keys.items():
        value=curve[-1][1]
        if t<=curve[0][0]:value=curve[0][1]
        else:
            for (a,x),(b,y) in zip(curve,curve[1:]):
                if t<=b:
                    value=x+(y-x)*ease((t-a)/(b-a));break
        result[name]=value
    return result

def wrist_motion(t,close_begin,finish,empty=False,speed=False):
    # The upstream argument 'speed' identifies the empty-case introduction.
    # Authoring route below distinguishes single loading from the speedloader.
    empty=speed
    weight=ease(t/.50)*(1-ease((t-close_begin)/(finish-close_begin)))
    root=MOTION['presentation'];xyz=[v*weight for v in root['offset_m']]
    pitch,bank,yaw=[v*weight for v in root['rotation_deg']]
    contributions=[phase_values(MOTION['opening'],t),phase_values(MOTION['closing'],t-close_begin)]
    begin=EMPTY_BEGIN if empty else BEGIN
    if motion_mode=='single' and begin<=t<close_begin:
        cycle=int((t-begin)/STEP);phase=t-begin-cycle*STEP
        # Small per-round variation, with identical zero-valued loop endpoints.
        amount=(1.00,.92,1.06)[cycle%3]
        contributions.append({k:v*amount for k,v in phase_values(MOTION['single_cycle'],phase).items()})
    elif motion_mode=='speed' and .48<=t<close_begin:
        contributions.append(phase_values(MOTION['speedloader'],t))
    if empty:contributions.append(phase_values(MOTION['empty_press'],t))
    for values in contributions:
        pitch+=values.get('pitch',0);bank+=values.get('bank',0);yaw+=values.get('yaw',0)
        for i,key in enumerate(('x','y','z')):xyz[i]+=values.get(key,0)
    return idle['WPN_root']@Matrix.LocRotScale(Vector(xyz),Euler(tuple(math.radians(v) for v in (pitch,bank,yaw)),'XYZ').to_quaternion(),Vector((1,1,1)))

def pose_single(start,count,t):
    global motion_mode
    motion_mode='single'
    return source_pose_single(start,count,t)

def pose_speed(start,t):
    global motion_mode
    motion_mode='speed'
    return source_pose_speed(start,t)

# Keep the split animation names/paths and all contact times. The existing
# runtime therefore loads these reimported clips without another native build.
bake_source='def bake('+previous.split('def bake(',1)[1].split('\nactions={}',1)[0]
exec(compile(bake_source.replace('DW715_Flick_','DW715_Motion_').replace('DW715_FLICK_EXPORTED','DW715_MOTION_EXPORTED'),str(SPLIT_FILE),'exec'),globals())
actions={};manifest={'normal_begin':BEGIN,'empty_begin':EMPTY_BEGIN,'step':STEP,'visible':VISIBLE,'align':ALIGN,'seat':SEAT,'hold':HOLD,'empty_case_clear':EMPTY_CLEAR,'tail':TAIL,'sample_rate':120,'motion_parameters':MOTION,'clips':{}}
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
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_ReloadMotion_Editable.blend'))
(O/'animation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('DW715_MOTION_AUTHORING_COMPLETE',flush=True)
