"""Native third-person uppercut: CC0 UAL2 Sword Regular A / A Rec.

The source supplies the body's chamber, turn and recovery. Native leg/arm IK
adapts its deep scissor step and diagonal sword cut into a rising kukri cut.
The capsule continues to own the existing gameplay lunge; no root translation
or changes to first-person timing/damage are introduced here.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = ROOT/'SourceAssets/KukriThirdPerson20261024/ComboV3'


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


combo = module('kukri_uppercut_body', BASE/'author.py')
fingers = module('kukri_uppercut_fist', ROOT/'SourceAssets/KukriThrustHand20261025/author.py')
RATE, LENGTH = 60, 38/30
TIMES = np.arange(round(LENGTH*RATE)+1)/RATE
KEYS = np.array([0., .14, .23, .29, .35, .433, .57, .72, .96, 1.10, LENGTH])


def rotations(times, quats, query):
    values = []
    for t in query:
        i = int(np.clip(np.searchsorted(times, t, side='right')-1, 0, len(times)-2))
        w = combo.ease((t-times[i])/(times[i+1]-times[i]))
        values.append(combo.slerp(quats[i], quats[i+1], w))
    return R.from_quat(np.asarray(values))


def blade_rotation(direction):
    tip = combo.unit(np.asarray(direction, dtype=float))
    # +Z is the blade; +X cutting edge leads the rising cut. Build a complete
    # blade frame before converting to the native hand mount (no wrist Euler fix).
    edge = combo.unit(np.array([0., 0., 1.])-tip*tip[2])
    return combo.frame(edge, np.cross(tip, edge))


def source_body(body):
    attack = body.retarget(np.asarray(combo.SOURCE['clips']['Sword_Regular_A']['frames']))
    recovery = body.retarget(np.asarray(combo.SOURCE['clips']['Sword_Regular_A_Rec']['frames']))
    attack_clock = [0., .10, .22, .29, .35, .433, .57]
    attack_source = [0., .08, .17, .205, .242, .30, (len(attack)-1)/RATE]
    recovery_clock = [.57, .73, .98, 1.10, LENGTH]
    recovery_source = [0., .17, .60, .82, (len(recovery)-1)/RATE]
    a = PchipInterpolator(attack_clock, attack_source)
    r = PchipInterpolator(recovery_clock, recovery_source)
    frames = []
    for t in TIMES:
        pose = combo.sample(attack, float(a(t))) if t <= .57 else combo.sample(recovery, float(r(t)))
        # Retain the take's spine/shoulder motion while reducing its extreme
        # backward finishing twist for a short, single-handed weapon.
        weight = .82*combo.ease(t/.14)*(1-combo.ease((t-1.02)/(LENGTH-1.02)))
        frames.append(combo.blend(body.idle, pose, weight))
    return np.asarray(frames), dict(attack_clock=attack_clock, attack_source=attack_source,
        recovery_clock=recovery_clock, recovery_source=recovery_source, source_pose_weight=.82)


def author_body(label, data, previous, fist_source):
    body = combo.Body(data)
    size = body.scale/94.
    idle_p, idle_q = body.world(body.idle)
    frames, timewarp = source_body(body)
    hip0 = idle_p[body.hip]
    # Lower into the chamber, then extend the legs through the strike. The
    # source remains in a deep lunge at its apex; that is deliberately adapted.
    hips = hip0+np.array([[0,0,0],[0,-5,-11],[0,-4,-13],[0,0,-9],
        [0,6,1],[0,9,4],[0,7,2],[0,4,1],[0,1,0],[0,0,0],[0,0,0]])*size
    frames[:,body.hip,:3] = PchipInterpolator(KEYS, hips)(TIMES)

    # Right foot passes into the lead as the left foot gathers behind. Each
    # return step has its own lift; no straight-kneed static lower-body pose.
    ft = np.array([0., .10, .20, .27, .35, .433, .58, .78, .98, 1.13, LENGTH])
    foot_goals, foot_rotations = {}, {}
    for side in 'lr':
        j = body.ix['foot_'+side]
        p0 = idle_p[j]
        if side == 'r':
            xy = [p0[:2], [-26,-23], [-25,4], [-24,25], [-24,35], [-24,35],
                  [-24,35], [-25,16], [-28,-23], p0[:2], p0[:2]]
            lift = [0,7,12,7,0,0,0,11,7,0,0]
            yaw = [0,0,-4,-7,-8,-8,-8,-4,0,0,0]
            heel = np.zeros(len(ft))
        else:
            xy = [p0[:2], p0[:2], [28,18], [25,-3], [24,-24], [24,-27],
                  [24,-27], [25,-5], [28,25], p0[:2], p0[:2]]
            lift = [0,0,5,10,3,0,0,9,5,0,0]
            yaw = [0,0,2,4,5,5,5,3,0,0,0]
            heel = np.array([0,0,0,-5,-14,-14,-8,0,0,0,0])
        xy = np.asarray(xy, dtype=float)
        # Explicit start/end positions are already native centimetres.
        for k in range(len(ft)):
            if k not in (0,9,10) and not (side=='l' and k==1): xy[k] *= size
        q = (R.from_euler('z', np.asarray(yaw)[:,None], degrees=True)*R.from_euler('x', heel[:,None], degrees=True)*
             R.from_quat(np.tile(idle_q[j], (len(ft),1)))).as_quat()
        rot = rotations(ft, q, TIMES)
        # Rotate about the toe during the push so a heel raise doesn't drive
        # the toe below the floor. Flight arcs are added on top of that pivot.
        ball = body.ix['ball_'+side]
        toe_local = R.from_quat(idle_q[j]).inv().apply(idle_p[ball]-p0)
        toe_delta = rot.apply(np.tile(toe_local,(len(TIMES),1)))
        toe_height = idle_p[ball,2]
        goal = np.c_[PchipInterpolator(ft,xy)(TIMES),
                     toe_height-toe_delta[:,2]+PchipInterpolator(ft,np.asarray(lift)*size)(TIMES)]
        foot_goals[side], foot_rotations[side] = goal, rot

    # Lower the pelvis only where required by native leg reach, before either
    # leg is solved. This is part of fitting, not root-motion displacement.
    p, _ = body.world(frames)
    drop = np.zeros(len(frames))
    for side in 'lr':
        h,k,a = [p[:,body.ix[n+'_'+side]] for n in ('thigh','calf','foot')]
        reach = (np.linalg.norm(k-h,axis=1)+np.linalg.norm(a-k,axis=1))*.985
        goal = foot_goals[side]
        maximum = goal[:,2]+np.sqrt(np.maximum(1.,reach*reach-np.sum((goal[:,:2]-h[:,:2])**2,axis=1)))
        drop = np.maximum(drop,h[:,2]-maximum)
    frames[:,body.hip,2] -= drop
    planted_hips = frames[:,body.hip,:3].copy()
    active = combo.ease(TIMES/.14)*(1-combo.ease((TIMES-.98)/(LENGTH-.98)))
    for side in 'lr':
        pole = planted_hips+np.array([-27 if side=='r' else 27,42,-30])*size
        pole = idle_p[body.ix['calf_'+side]]*(1-active[:,None])+pole*active[:,None]
        body.solve(frames,[n+'_'+side for n in ('thigh','calf','foot')],
                   foot_goals[side],pole,foot_rotations[side])

    # Right hand: low outside chamber -> front-centre rising cut -> high guard.
    # The complete native arm is solved to the hand; the blade is not moved
    # independently of the wrist or the equipment socket.
    right = np.array([idle_p[body.ix['hand_r']]-hip0,[-31,2,11],[-34,12,0],
        [-30,25,6],[-17,49,41],[-3,30,77],[3,14,79],[-8,24,62],[-27,12,32],
        idle_p[body.ix['hand_r']]-hip0,idle_p[body.ix['hand_r']]-hip0])
    left = np.array([idle_p[body.ix['hand_l']]-hip0,[27,32,39],[27,32,41],
        [26,33,46],[24,33,49],[24,25,46],[24,25,46],[26,30,42],[27,39,32],
        idle_p[body.ix['hand_l']]-hip0,idle_p[body.ix['hand_l']]-hip0])
    right[1:9]*=size;left[1:9]*=size
    handq0 = idle_q[body.ix['hand_r']]
    directions = [[.03,.65,-.76],[.03,.54,-.84],[.02,.85,-.53],
                  [0,.99,.14],[-.06,.50,.86],[-.12,.24,.96],[-.10,.58,.81],[-.05,.95,.31]]
    handq = np.array([handq0]+[(blade_rotation(d)*body.blade_local.inv()).as_quat() for d in directions]+[handq0,handq0])
    guardq0 = idle_q[body.ix['hand_l']]
    guardq = (R.from_euler('xz',[-12,-10],degrees=True)*R.from_quat(guardq0)).as_quat()
    leftq = np.array([guardq0]+[guardq]*7+[combo.slerp(guardq,guardq0,.5),guardq0,guardq0])
    p,_ = body.world(frames)
    for side, offsets, qs in [('r',right,handq),('l',left,leftq)]:
        goals = planted_hips+PchipInterpolator(KEYS,offsets)(TIMES)
        # Outward elbow poles remain continuous through the high cut and
        # recovery. The source's spine, clavicle and shoulder turn stay active.
        offset = np.array([-39,9,30] if side=='r' else [41,10,24])*size
        pole = planted_hips+offset
        if side=='r':
            high = combo.ease((TIMES-.30)/.14)*(1-combo.ease((TIMES-.64)/.30))
            pole += np.array([7,0,27])*size*high[:,None]
        pole = idle_p[body.ix['lowerarm_'+side]]*(1-active[:,None])+pole*active[:,None]
        body.solve(frames,[n+'_'+side for n in ('upperarm','lowerarm','hand')],goals,pole,rotations(KEYS,qs,TIMES))

    fist = fingers.native_fist(body,fist_source)
    driven = []
    for i,name in enumerate(body.names):
        digit = name.split('_')[0]
        if not name.endswith('_l') or digit not in ('thumb','index','middle','ring','pinky'): continue
        delay = {'pinky':0.,'ring':.006,'middle':.012,'index':.020,'thumb':.045}[digit]
        w = combo.ease((TIMES-delay)/.15)*(1-combo.ease((TIMES-.75)/.40))
        frames[:,i,3:7] = combo.slerp(frames[:,i,3:7],fist[i,3:7],w[:,None])
        driven.append(name)
    frames = body.twists(frames)
    # Exact endpoints preserve the current equipment stance including helper
    # bones. There is no extra recovery state for this skill in the runtime.
    frames[0] = body.idle
    for i,t in enumerate(TIMES):
        frames[i] = combo.blend(frames[i],body.idle,combo.ease((t-1.10)/(LENGTH-1.10)))
    frames[-1] = body.idle
    clip = dict(frames=frames.tolist(),rate=RATE,loop=False,contact=.350/LENGTH,release=.433/LENGTH,
        source='; '.join(combo.SOURCE['clips'][key]['asset'] for key in ('Sword_Regular_A','Sword_Regular_A_Rec')),
        adaptation='Original CC0 A/A Rec torso motion; native low chamber, leg extension, scissor step and toe-pivot push; rising blade frame on the real palm mount; closed left guard; complete idle recovery; capsule owns world lunge.')
    result = dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips={'Uppercut':clip})
    (OUT/(label+'-actions.json')).write_text(json.dumps(result,separators=(',',':')))
    return dict(mesh=data['mesh'],skeleton=data['skeleton'],previous_uppercut=previous,
        frames=len(frames),rate=RATE,seconds=LENGTH,contact_seconds=.350,release_seconds=.433,
        source_timewarp=timewarp,stance_keys=KEYS.tolist(),hip_keys_cm=hips.tolist(),
        finger_bones=driven,root_motion=False)


def main():
    cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    fist_source = json.loads((ROOT/'SourceAssets/UnarmedIdle20261001/full-pose.json').read_text())
    receipt = dict(bodies={},source_license='CC0 Quaternius Universal Animation Library 2',
        source_url='https://quaternius.com/packs/universalanimationlibrary2.html',
        source_cache=str((BASE/'inputs.json').relative_to(ROOT)),runtime_tested=False,rendered=False,
        gameplay_changed=False,first_person_changed=False)
    for label,data in combo.INPUT['targets'].items():
        active = cfg if label=='jason' else cfg['body_variants'][label]
        receipt['bodies'][label] = author_body(label,data,active['clips']['Kukri.FullBody.Uppercut'],fist_source)
        print('KUKRI_UPPERCUT_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
