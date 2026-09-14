"""Detach the free support hand from the closing wrist flick, then regrip.

Inherits Natural's opening, loading, right-hand, cylinder and contact clocks.
Only the final support-arm recovery and the already-released loader change.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

_recovery_dir = Path(__file__).resolve().parent
_natural_file = _recovery_dir.parent/'DanWesson715ReloadNatural20260914/author_actions.py'
__file__ = str(_natural_file)
exec(compile(_natural_file.read_text(encoding='utf-8').split('\nbake_source=')[0], str(_natural_file), 'exec'), globals())
O = _recovery_dir
__file__ = str(O/'author_actions.py')
(O/'Animations').mkdir(exist_ok=True)
_natural_single = pose_single
_natural_speed = pose_speed
_recovery_entries = {}
RECOVERY = {'single_detach_before_close': .20, 'speed_detach': 2.53,
            'clear_after_detach': .26, 'regrip_prepare_after_close': .43,
            'loader_clear_after_detach': .38, 'loader_regrip_prepare_after_close': .55,
            'finger_regrip_after_close': .48, 'loader_stow': 2.91,
            'single_clear_offset': [.035,.035,-.145], 'loader_clear_offset': [.035,.070,-.300],
            'prepare_offset_from_idle': [.065,.045,-.045],
            'space': 'viewmodel/armature space, independent of WPN_root and cylinder after release',
            'position': 'monotone cubic with shared tangents and stationary endpoints',
            'rotation': 'one shortest-arc quaternion blend to idle, quintic easing'}

def recover_left(p, entry, t, detach, close_begin, finish, speed=False):
    """Follow a fixed left/down clearance arc while the RIGHT wrist closes."""
    H0 = entry['hand_l']; H1 = idle['hand_l']
    offset = RECOVERY['loader_clear_offset' if speed else 'single_clear_offset']
    clear = H0.translation + idle['WPN_root'].to_3x3() @ Vector(offset)
    prepare = H1.translation + idle['WPN_root'].to_3x3() @ Vector(RECOVERY['prepare_offset_from_idle'])
    clear_delay=RECOVERY['loader_clear_after_detach' if speed else 'clear_after_detach']
    prepare_delay=RECOVERY['loader_regrip_prepare_after_close' if speed else 'regrip_prepare_after_close']
    times = [detach, detach+clear_delay, close_begin+prepare_delay, finish]
    points = [H0.translation, clear, prepare, H1.translation]
    H = mix(H0, H1, ease((t-detach)/(finish-detach)))
    H.translation = Vector([sample_curve(list(zip(times,[point[axis] for point in points])), t) for axis in range(3)])
    # Re-solve the whole idle-based arm, including its transported elbow plane;
    # do not undo WPN_root on the wrist while leaving forearm/twist bones behind.
    hand_at(p, idle, 'l', H)
    shape = relaxed
    if speed:
        shape = blend_shapes(templates['loader'], relaxed, ease((t-RECOVERY['loader_stow'])/.12))
        if t <= RECOVERY['loader_stow']:
            p['WPN_Loader'] = H @ H0.inverted() @ entry['WPN_Loader']
    grip_start = close_begin+RECOVERY['finger_regrip_after_close']
    apply_hand_shape(p, shape, 1-ease((t-grip_start)/(finish-grip_start)))
    return p

def pose_single(start, count, t):
    p = _natural_single(start, count, t)
    close_begin = (EMPTY_BEGIN if start==0 else BEGIN)+count*STEP
    detach = close_begin-RECOVERY['single_detach_before_close']
    if t < detach: return p
    key = ('single',start,count)
    if key not in _recovery_entries:
        _recovery_entries[key] = _natural_single(start,count,detach)
    return recover_left(p,_recovery_entries[key],t,detach,close_begin,close_begin+TAIL)

def pose_speed(start, t):
    p = _natural_speed(start,t)
    duration = 3.85 if start==0 else 3.6
    u = t*3.6/duration
    detach = RECOVERY['speed_detach']
    if u < detach: return p
    key = ('speed',start)
    if key not in _recovery_entries:
        _recovery_entries[key] = _natural_speed(start,detach*duration/3.6)
    return recover_left(p,_recovery_entries[key],u,detach,2.68,3.6,True)

if __name__ == '__main__':
    bake_source='def bake('+previous.split('def bake(',1)[1].split('\nactions={}',1)[0]
    exec(compile(bake_source.replace('DW715_Flick_','DW715_LeftRecovery_').replace('DW715_FLICK_EXPORTED','DW715_LEFT_RECOVERY_EXPORTED'),str(_natural_file),'exec'),globals())
    actions={}
    destination='/Game/Weapons/DanWesson715/LeftRecovery20260914/Animations'
    manifest={'sample_rate':120, 'recovery':RECOVERY, 'clips':{},
              'scope':'Only released left-arm recovery; right hand, cylinder, ammo and sound clocks retain Natural timing'}
    for start in range(6):
        for count in range(1,7-start):
            kind=f'single_{start}_{count}';begin=EMPTY_BEGIN if start==0 else BEGIN;duration=begin+count*STEP+TAIL
            actions[kind]=bake(kind,duration,lambda t,a=start,b=count:pose_single(a,b,t))
            manifest['clips'][kind]={'duration':duration,'destination':destination,'empty':start==0,
                                    'left_detach':begin+count*STEP-.20,'seats':[begin+i*STEP+SEAT for i in range(count)]}
    for start in range(6):
        kind=f'speed_{start}';duration=3.85 if start==0 else 3.6
        actions[kind]=bake(kind,duration,lambda t,a=start:pose_speed(a,t))
        manifest['clips'][kind]={'duration':duration,'destination':'/Game/Weapons/DanWesson715/LeftRecovery20260914/LoaderStow','empty':start==0,'left_detach':2.53*duration/3.6}
    rig.animation_data.action=actions['single_0_6'];rig.animation_data.action_slot=actions['single_0_6'].slots[0]
    s.frame_start=0;s.frame_end=528;s.frame_set(0)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_LeftRecovery_Editable.blend'))
    (O/'animation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('DW715_LEFT_RECOVERY_AUTHORING_COMPLETE',flush=True)
