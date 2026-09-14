"""Replace per-cartridge oscillations with slow, continuous support motion."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Euler
NATURAL_DIR=Path(__file__).resolve().parent
MOTION_FILE=NATURAL_DIR.parent/'DanWesson715ReloadMotion20260914/author_actions.py'
motion_source=MOTION_FILE.read_text(encoding='utf-8')
__file__=str(MOTION_FILE)
exec(compile(motion_source.split('\nbake_source=')[0],str(MOTION_FILE),'exec'),globals())
O=NATURAL_DIR;__file__=str(O/'author_actions.py')
(O/'Animations').mkdir(exist_ok=True)

# Retain the deliberate opening/closing impulse, but remove the extra reversal
# after braking and give the large movement more time to accelerate/settle.
MOTION['opening']={
 'bank':[(0,0),(.18,-15),(.32,66),(.47,19),(.62,0)],
 'yaw':[(0,0),(.18,-8),(.33,32),(.49,8),(.62,0)],
 'pitch':[(0,0),(.18,-7),(.34,13),(.50,3),(.62,0)],
 'x':[(0,0),(.18,-.019),(.32,.080),(.48,.018),(.62,0)],
 'y':[(0,0),(.18,-.008),(.34,.026),(.50,.006),(.62,0)],
 'z':[(0,0),(.18,-.008),(.34,.036),(.50,.008),(.62,0)]}
MOTION['closing']={
 'bank':[(0,0),(.10,18),(.27,-70),(.45,-19),(.68,0)],
 'yaw':[(0,0),(.10,8),(.28,-31),(.47,-7),(.68,0)],
 'pitch':[(0,0),(.10,7),(.29,-12),(.49,-2),(.68,0)],
 'x':[(0,0),(.10,.019),(.27,-.078),(.46,-.016),(.68,0)],
 'y':[(0,0),(.10,.008),(.29,-.028),(.48,-.006),(.68,0)],
 'z':[(0,0),(.10,.010),(.29,-.024),(.49,-.005),(.68,0)]}
MOTION.pop('single_cycle')
# One asymmetrical weight shift over the WHOLE loading interval. Axes change
# at different broad landmarks rather than reversing several times per round.
MOTION['loading_support']={
 'pitch':[(0,0),(.24,-1.0),(.69,3.0),(1,0)],
 'bank':[(0,0),(.39,1.4),(.82,-.6),(1,0)],
 'yaw':[(0,0),(.32,-1.2),(.76,1.8),(1,0)],
 'x':[(0,0),(.35,.003),(.76,-.004),(1,0)],
 'y':[(0,0),(.25,.004),(.66,-.006),(1,0)],
 'z':[(0,0),(.31,-.003),(.72,.005),(1,0)]}
MOTION['speedloader']={
 'pitch':[(.48,0),(1.22,-1.6),(2.10,2.7),(2.68,0)],
 'bank':[(.48,0),(1.37,1.8),(2.24,-.6),(2.68,0)],
 'yaw':[(.48,0),(1.28,-1.8),(2.14,2.2),(2.68,0)],
 'x':[(.48,0),(1.29,.004),(2.12,-.005),(2.68,0)],
 'y':[(.48,0),(1.24,.005),(2.10,-.008),(2.68,0)],
 'z':[(.48,0),(1.36,-.004),(2.20,.006),(2.68,0)]}
MOTION['empty_press']={
 'pitch':[(0,0),(.50,0),(.87,-83),(1.06,-84),(1.48,0)],
 'y':[(0,0),(.78,0),(1.04,.006),(1.48,0)],
 'z':[(0,0),(.50,0),(.90,.024),(1.08,.025),(1.48,0)]}
MOTION['support_reference_duration']=4.5
MOTION['interpolation']='monotone cubic Hermite with shared tangents; zero endpoint velocity'

def sample_curve(keys,t):
    if t<=keys[0][0]:return keys[0][1]
    if t>=keys[-1][0]:return keys[-1][1]
    h=[b[0]-a[0] for a,b in zip(keys,keys[1:])]
    slopes=[(b[1]-a[1])/dt for a,b,dt in zip(keys,keys[1:],h)]
    tangent=[0.]*len(keys)
    for j in range(1,len(keys)-1):
        a,b=slopes[j-1],slopes[j]
        if a*b>0:
            wa=2*h[j]+h[j-1];wb=h[j]+2*h[j-1]
            tangent[j]=(wa+wb)/(wa/a+wb/b)
    for i,((a,x),(b,y)) in enumerate(zip(keys,keys[1:])):
        if t<=b:
            u=(t-a)/(b-a);u2=u*u;u3=u2*u
            return (2*u3-3*u2+1)*x+(u3-2*u2+u)*h[i]*tangent[i]+(-2*u3+3*u2)*y+(u3-u2)*h[i]*tangent[i+1]

def phase_values(keys,t):return {name:sample_curve(curve,t) for name,curve in keys.items()}

def wrist_motion(t,close_begin,finish,empty=False,speed=False):
    empty=speed
    weight=ease(t/.55)*(1-ease((t-close_begin)/(finish-close_begin)))
    root=MOTION['presentation'];xyz=[v*weight for v in root['offset_m']]
    pitch,bank,yaw=[v*weight for v in root['rotation_deg']]
    contributions=[phase_values(MOTION['opening'],t),phase_values(MOTION['closing'],t-close_begin)]
    begin=EMPTY_BEGIN if empty else BEGIN
    if motion_mode=='single' and begin<=t<close_begin:
        duration=close_begin-begin
        # Short top-ups sample the same broad intent at a proportionally smaller
        # amplitude, so a single missing round cannot become a quick full swing.
        amount=min(1.,duration/MOTION['support_reference_duration'])
        contributions.append({k:v*amount for k,v in phase_values(MOTION['loading_support'],(t-begin)/duration).items()})
    elif motion_mode=='speed' and .48<=t<close_begin:
        contributions.append(phase_values(MOTION['speedloader'],t))
    if empty:contributions.append(phase_values(MOTION['empty_press'],t))
    for values in contributions:
        pitch+=values.get('pitch',0);bank+=values.get('bank',0);yaw+=values.get('yaw',0)
        for i,key in enumerate(('x','y','z')):xyz[i]+=values.get(key,0)
    return idle['WPN_root']@Matrix.LocRotScale(Vector(xyz),Euler(tuple(math.radians(v) for v in (pitch,bank,yaw)),'XYZ').to_quaternion(),Vector((1,1,1)))

bake_source='def bake('+previous.split('def bake(',1)[1].split('\nactions={}',1)[0]
exec(compile(bake_source.replace('DW715_Flick_','DW715_Natural_').replace('DW715_FLICK_EXPORTED','DW715_NATURAL_EXPORTED'),str(MOTION_FILE),'exec'),globals())
actions={};manifest={'normal_begin':BEGIN,'empty_begin':EMPTY_BEGIN,'step':STEP,'visible':VISIBLE,'align':ALIGN,'seat':SEAT,'hold':HOLD,'empty_case_clear':EMPTY_CLEAR,'tail':TAIL,'sample_rate':120,'motion_parameters':MOTION,'clips':{}}
for start in range(6):
    for count in range(1,7-start):
        kind=f'single_{start}_{count}';begin=EMPTY_BEGIN if start==0 else BEGIN;duration=begin+count*STEP+TAIL
        actions[kind]=bake(kind,duration,lambda t,a=start,b=count:pose_single(a,b,t))
        manifest['clips'][kind]={'duration':duration,'destination':'/Game/Weapons/DanWesson715/ReloadNatural20260914/Animations','empty':start==0,'seats':[begin+i*STEP+SEAT for i in range(count)]}
for start in range(6):
    kind=f'speed_{start}';duration=3.85 if start==0 else 3.6
    actions[kind]=bake(kind,duration,lambda t,a=start:pose_speed(a,t))
    manifest['clips'][kind]={'duration':duration,'destination':'/Game/Weapons/DanWesson715/ReloadNatural20260914/Animations','empty':start==0}
rig.animation_data.action=actions['single_0_6'];rig.animation_data.action_slot=actions['single_0_6'].slots[0];s.frame_start=0;s.frame_end=528;s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_ReloadNatural_Editable.blend'))
(O/'animation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('DW715_NATURAL_AUTHORING_COMPLETE',flush=True)
