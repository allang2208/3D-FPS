"""Rebuild the single uppercut support with native knee hinges and placed feet.

The captured single-arm revision remains the upper-body source. The current
two-handed uppercut supplies compression/rise timing; no jog pose is spliced
into a few frames. All targets are in the body's component space.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
spec = importlib.util.spec_from_file_location('sword_lower', ROOT / 'SourceAssets/KukriUppercutSwordLower20261027/author.py')
lower = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lower)
base, c = lower.base, lower.c
RATE = 120


def phase(times, start, end):
    return base.smooth((times - start) / (end - start))


def hinge_leg(body, frames, side, goal, foot_rotation, heading, weight):
    """Solve both segments from one native flexion plane, without roll drift."""
    hi, ki, ai = [body.ix[n + '_' + side] for n in ('thigh', 'calf', 'foot')]
    ip, iq = body.world(body.idle)
    p, _ = body.world(frames)
    origin = p[:, hi]
    first, second = ip[ki] - ip[hi], ip[ai] - ip[ki]
    l1, l2 = np.linalg.norm(first), np.linalg.norm(second)
    axis = c.unit(goal - origin)
    distance = np.linalg.norm(goal - origin, axis=1)
    if np.max(distance) > (l1 + l2) * .991:
        raise RuntimeError('Leg target exceeds supported native reach: ' + side)
    initial_axis = c.unit(ip[ai] - ip[hi])
    initial_bend = c.unit(first - initial_axis * np.dot(first, initial_axis))
    transported = c.align(np.tile(initial_axis, (len(frames), 1)), axis).apply(np.tile(initial_bend, (len(frames), 1)))
    forward = np.c_[-np.sin(heading), np.cos(heading), np.zeros(len(frames))]
    forward = c.unit(forward - axis * np.sum(forward * axis, axis=1)[:, None])
    # Idle offsets disappear continuously; the active knee follows its own toes.
    bend = c.unit(transported * (1. - weight[:, None]) + forward * weight[:, None])
    along = (l1*l1 - l2*l2 + distance*distance) / (2.*distance)
    knee = origin + axis*along[:, None] + bend*np.sqrt(np.maximum(0., l1*l1 - along*along))[:, None]
    upper, shin = knee - origin, goal - knee
    thigh_q = c.frame(upper, shin) * c.frame(first, second).inv() * R.from_quat(iq[hi])
    calf_q = c.frame(shin, upper) * c.frame(second, first).inv() * R.from_quat(iq[ki])
    body.set_world_rotations(frames, {hi: thigh_q, ki: calf_q, ai: foot_rotation})


def diagnose(body, frames):
    p, q = body.world(frames)
    result = {}
    for side in 'lr':
        hi, ki, ai, bi = [body.ix[n+'_'+side] for n in ('thigh', 'calf', 'foot', 'ball')]
        upper, shin = c.unit(p[:,ki]-p[:,hi]), c.unit(p[:,ai]-p[:,ki])
        flex = np.degrees(np.arccos(np.clip(np.sum(upper*shin, axis=1), -1., 1.)))
        axis = c.unit(p[:,ai]-p[:,hi])
        bend = c.unit(upper-axis*np.sum(upper*axis, axis=1)[:,None])
        toe = c.unit((p[:,bi]-p[:,ai])*[1.,1.,0.])
        knee_yaw = np.arctan2(-bend[:,0], bend[:,1])
        toe_yaw = np.arctan2(-toe[:,0], toe[:,1])
        heading_error = np.abs(np.degrees(np.arctan2(np.sin(knee_yaw-toe_yaw), np.cos(knee_yaw-toe_yaw))))
        calf = R.from_quat(frames[:,ki,3:7])
        calf_step = np.degrees((calf[1:]*calf[:-1].inv()).magnitude())
        foot_step = np.linalg.norm(np.diff(p[:,ai], axis=0), axis=1)
        result[side] = dict(knee_flex_degrees=[float(flex.min()),float(flex.max())],
            max_calf_rotation_degrees_per_frame=float(calf_step.max()),
            max_ankle_cm_per_frame=float(foot_step.max()),
            ankle_peak_time_seconds=float((np.argmax(foot_step)+1)/RATE),
            max_knee_to_toe_heading_degrees=float(heading_error.max()),
            minimum_ball_height_cm=float(p[:,bi,2].min()))
    return result


def build(body, original, sword, clock):
    frames = np.asarray(original['frames'], dtype=float).copy()
    source = frames.copy()
    idle = frames[0].copy()
    body.idle = idle
    n = len(frames)
    times = np.arange(n)/RATE
    duration = times[-1]
    size = body.scale/94.
    ip, iq = body.world(idle)
    _, original_q = body.world(source)
    envelope = phase(times, 0., .22)*(1.-phase(times, .89, duration))
    donor = np.array([c.sample(np.asarray(sword['frames']), float(t), sword['rate']) for t in clock])
    donor[:,0] = idle[0]
    dp, dq = body.world(donor)

    # Keep the two-handed compression and rise, without the jog's pelvis jump.
    # Avoid the original lateral lean while shifting weight onto the lead foot.
    advance = phase(times,.20,.43)*(1.-phase(times,.78,duration))
    frames[:,body.hip,:3] = idle[body.hip,:3]
    frames[:,body.hip,0] += 2.8*size*advance
    frames[:,body.hip,1] += 3.5*size*advance
    height = gaussian_filter1d(dp[:,body.hip,2], 3., mode='nearest')
    frames[:,body.hip,2] += .72*(height-ip[body.hip,2])*envelope
    yaw = lower.heading(body, dq, body.hip)
    yaw = gaussian_filter1d(np.radians(5.)*np.tanh(yaw/np.radians(5.)), 5., mode='nearest')
    upright = R.from_euler('z', yaw[:,None])*R.from_quat(body.tq[body.hip])
    hip_rotation = R.from_quat(c.slerp(iq[body.hip], upright.as_quat(), envelope[:,None]))
    # Compensate the spine boundary so the accepted upright chest/arms keep
    # their exact component rotations while the pelvis supports the new legs.
    body.set_world_rotations(frames, {body.hip:hip_rotation,
        body.ix['spine_01']:R.from_quat(original_q[:,body.ix['spine_01']])})

    goals, rotations, headings, swing_windows = {}, {}, {}, {}
    for side, sign, arrive, leave, target_yaw, lift in [
        ('l',1.,(.15,.355),(1.015,1.255),-9.,5.5),
        ('r',-1.,(.30,.585),(.825,1.07),14.,6.5)]:
        fi, bi = body.ix['foot_'+side], body.ix['ball_'+side]
        a, z = phase(times,*arrive), phase(times,*leave)
        placement = a*(1.-z)
        swing_windows[side] = dict(advance=list(arrive),recovery=list(leave))
        # Moderate stagger: lead foot reaches forward, rear foot follows after
        # push-off. The feet never exchange sides or cross the body's midline.
        target_ankle = ip[fi].copy()
        target_ankle[0] *= .90
        target_ankle[1] = ip[fi,1]+8.*size if side=='l' else -8.*size
        bind_forward = body.tp[bi]-body.tp[fi]
        bind_yaw = np.arctan2(-bind_forward[0],bind_forward[1])
        flat = R.from_euler('z',np.radians(target_yaw)-bind_yaw)*R.from_quat(body.tq[fi])
        toe_local = R.from_quat(iq[fi]).inv().apply(ip[bi]-ip[fi])
        target_ball = target_ankle+flat.apply(toe_local)
        target_ball[2] = ip[bi,2]
        toe = ip[bi]+(target_ball-ip[bi])*placement[:,None]
        # Quintic progress also gives zero vertical speed/acceleration at both
        # ends of the arc. Planted intervals retain fixed component targets.
        toe[:,2] += (lift*np.sin(np.pi*a)**2+4.5*np.sin(np.pi*z)**2)*size
        rotation = R.from_quat(c.slerp(iq[fi],flat.as_quat(),placement[:,None]))
        if side=='r':
            heel = phase(times,.16,.285)*(1.-phase(times,.30,.49))*np.radians(-12.)
            direction = rotation.apply(np.tile(toe_local,(n,1)))
            lateral = c.unit(np.c_[direction[:,1],-direction[:,0],np.zeros(n)])
            rotation = R.from_rotvec(lateral*heel[:,None])*rotation
        # Rotate around the ball of the foot while pushing, rather than rolling
        # the ankle in place and driving the sole through the floor.
        goals[side] = toe-rotation.apply(np.tile(toe_local,(n,1)))
        rotations[side] = rotation
        direction = rotation.apply(np.tile(toe_local,(n,1)))
        headings[side] = np.arctan2(-direction[:,0],direction[:,1])
        for name in ('thigh','calf','foot','ball'):
            index=body.ix[name+'_'+side]
            frames[:,index,:3]=idle[index,:3]
            frames[:,index,7:]=idle[index,7:]
        frames[:,bi,3:7] = idle[bi,3:7]

    # Preserve bend room throughout support. Lower the pelvis smoothly where
    # a planted target would otherwise straighten a leg; never stretch a bone.
    p,_=body.world(frames)
    cap=np.full(n,np.inf)
    for side in 'lr':
        hi,ki,fi=[body.ix[name+'_'+side] for name in ('thigh','calf','foot')]
        length=np.linalg.norm(ip[ki]-ip[hi])+np.linalg.norm(ip[fi]-ip[ki])
        horizontal=np.sum((goals[side][:,:2]-p[:,hi,:2])**2,axis=1)
        maximum=goals[side][:,2]+np.sqrt(np.maximum(1.,(.955*length)**2-horizontal))
        cap=np.minimum(cap,maximum-(p[:,hi,2]-p[:,body.hip,2]))
    drop=.35*np.logaddexp(0.,(frames[:,body.hip,2]-cap)/.35)
    frames[:,body.hip,2]-=gaussian_filter1d(drop, 3., mode='nearest')
    for side in 'lr':
        hinge_leg(body,frames,side,goals[side],rotations[side],headings[side],envelope)

    # Regenerate only leg roll helpers, preserving their original idle offsets.
    helpers=frames.copy();lower.dual.leg_helpers(body,helpers)
    seed=idle[None].copy();lower.dual.leg_helpers(body,seed)
    for i,name in enumerate(body.names):
        if name.startswith(('thigh_twist_','calf_twist_')):
            offset=R.from_quat(idle[i,3:7])*R.from_quat(seed[0,i,3:7]).inv()
            frames[:,i,3:7]=(offset*R.from_quat(helpers[:,i,3:7])).as_quat()
    frames[0]=source[0];frames[-1]=source[-1]
    for k in range(1,n):
        frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0.,-1.,1.)[:,None]
    _, final_q=body.world(frames)
    arm_ids=[i for i,name in enumerate(body.names) if name.startswith(('clavicle_','upperarm_','lowerarm_','hand_'))]
    arm_error=np.degrees((R.from_quat(final_q[:,arm_ids].reshape(-1,4))*R.from_quat(original_q[:,arm_ids].reshape(-1,4)).inv()).magnitude()).max()
    return frames,dict(swing_windows_seconds=swing_windows,source_clock=clock,
        max_arm_component_rotation_change_degrees=float(arm_error),before=diagnose(body,source),after=diagnose(body,frames))


def main():
    inputs=json.loads((OUT/'inputs.json').read_text())
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    sword=json.loads((lower.OUT/'sword-lower-inputs.json').read_text())
    old_report=json.loads((lower.OUT/'authoring.json').read_text())
    report=dict(version='Single uppercut supported legs V1',bodies={},first_person_changed=False,
        dual_changed=False,cpp_changed=False,runtime_tested=False,rendered=False)
    for label,data in base.rig.DATA.items():
        active=cfg if label=='jason' else cfg['body_variants'][label]
        captured=inputs[label]
        if active['body_mesh']!=data['mesh'] or captured['names']!=data['names']:
            raise RuntimeError('Native body input changed: '+label)
        if active['clips']['Kukri.FullBody.Uppercut']!=captured['previous']['asset'] or active['clips']['Melee.FullBody.Uppercut']!=sword[label]['asset']:
            raise RuntimeError('Uppercut input changed: '+label)
        clock=old_report['bodies'][label]['clock']['Uppercut']['source_times']
        original=captured['previous'];frames,detail=build(c.Body(data),original,sword[label],clock)
        length=(len(frames)-1)/RATE
        clip=dict(rate_num=RATE,rate_den=1,frames=frames.tolist(),contact=original['markers']['Contact']/length,
            release=original['markers']['Release']/length,source=sword[label]['asset'],
            adaptation='Native knee hinges; supported alternating uppercut steps and toe-pivot push-off; two-handed sword compression/rise; current single-hand upper-body articulation preserved')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=data['names'],parents=data['parents'],clips={'Uppercut':clip}),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],previous_roles={'Uppercut':original['asset']},
            source_sword=sword[label]['asset'],frames=len(frames),**detail)
        print('SINGLE_UPPERCUT_LEGS_AUTHORED',label,json.dumps(detail['after']),flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
