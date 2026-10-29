"""First single-sword windmill study, authored on the native player bodies.

Mabinogi footage is a visual direction, not imported motion data. The broad
horizontal slash, low pivot and free-hand counterbalance are newly keyed here.
The runtime owns the existing -720 degree turn; tracks contain articulation only.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
spec = importlib.util.spec_from_file_location('windmill_native', ROOT / 'SourceAssets/KukriWhirlwindSourceMotion20261025/author.py')
v7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7)
c, old, native = v7.c, v7.old, v7.native
RATE = 120
ROLES = old.ROLES


def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*x*(10.+x*(-15.+6.*x))


def periodic(points, phase):
    return CubicSpline(np.linspace(0., 1., len(points)), points, bc_type='periodic')(np.mod(phase, 1.))


def curve(times, points, u):
    points = np.asarray(points)
    zeros = np.zeros(points.shape[1:])
    return CubicSpline(times, points, bc_type=((1, zeros), (1, zeros)))(u)


def spin_feet(body, frames, angular, turns, size):
    """Alternating toe pivots on the actual angular clock, with low swing arcs."""
    ip, iq = body.world(body.idle)
    actor = -2*np.pi*turns*angular
    half = 2*turns*angular
    goals, rotations, poles = {}, {}, {}
    for side, offset in [('l', 0.), ('r', .5)]:
        x = half-offset
        n, f = np.floor(x), x-np.floor(x)
        swing = np.clip((f-.5)*2, 0., 1.)
        anchor = -2*np.pi*((n+offset+.25)/2 + .5*smooth(swing))
        relative = anchor-actor
        yaw = R.from_euler('z', relative[:, None])
        lift = np.sin(np.pi*swing)**2
        radius = 18.*size*(1.+.08*lift)
        points = yaw.apply(np.c_[(1 if side == 'l' else -1)*radius, np.zeros(len(f)), np.zeros(len(f))])
        heel = np.where(f < .5, -7*np.sin(np.pi*f*2)**2, 5*np.sin(np.pi*swing)**2)
        foot, ball = body.ix['foot_'+side], body.ix['ball_'+side]
        # A stance toe may pivot: the ankle anchor stays put while the foot
        # follows part of the hip turn, reducing torsion through the knee.
        foot_yaw = R.from_euler('z', (.70*relative)[:, None])
        base = foot_yaw*R.from_quat(np.tile(iq[foot], (len(f), 1)))
        rot = foot_yaw*R.from_euler('x', heel[:, None], degrees=True)*R.from_quat(np.tile(iq[foot], (len(f), 1)))
        toe = R.from_quat(iq[foot]).inv().apply(ip[ball]-ip[foot])
        baseline = base.apply(np.tile(toe, (len(f), 1)))
        actual = rot.apply(np.tile(toe, (len(f), 1)))
        points[:, 2] = ip[ball, 2]-baseline[:, 2]+3.5*size*lift
        points += baseline-actual
        goals[side], rotations[side] = points, rot
        knee = R.from_euler('z', (.45*relative)[:, None]).apply(np.tile([25 if side == 'l' else -25, 38, -28], (len(f), 1)))
        poles[side] = frames[:, body.hip, :3]+knee*size
    old.steps.fit_legs(body, frames, goals, rotations, poles)


def make_loop(body, tuning, front, fist, held):
    count = round(tuning['spinSeconds']*RATE)+1
    u = np.linspace(0., 1., count)
    angular = old.arms.phase(u)
    turns = abs(tuning['turnDegrees'])/360.
    phase = turns*angular
    wave = np.sin(2*np.pi*phase)
    effort = np.sin(np.pi*phase)**2
    size = body.scale/94.
    frames = np.repeat(body.idle[None], count, axis=0)
    ip, _ = body.world(body.idle)
    # Low, almost level centre of mass. No axe-style rising overhead arc.
    frames[:, body.hip, :3] = ip[body.hip]+np.c_[1.8*wave, 1.+1.4*np.sin(4*np.pi*phase), -10.5+1.1*np.cos(4*np.pi*phase)]*size
    desired = {}
    for name, pitch, lean, yaw in [
        ('pelvis', -5., 1.5, 5.), ('spine_01', -8., 2., 9.),
        ('spine_02', -10., 2.5, 12.), ('spine_03', -11., 3., 15.),
        ('neck_01', -6., 1., 9.), ('head', -3., .5, 5.)]:
        i = body.ix[name]
        angles = np.c_[pitch+1.3*effort, lean*wave, yaw*wave]
        desired[i] = R.from_euler('xyz', angles, degrees=True)*R.from_quat(body.tq[i])
    body.set_world_rotations(frames, desired)
    spin_feet(body, frames, angular, turns, size)
    old.arms.shoulders(body, frames, np.ones(count), 2.*wave)
    p, _, torso = old.arms.chest(body, frames)
    middle = .5*(p[:, body.ix['upperarm_l']]+p[:, body.ix['upperarm_r']])
    for side in 'rl':
        ui, ei, hi = [body.ix[n+'_'+side] for n in ('upperarm', 'lowerarm', 'hand')]
        length = np.linalg.norm(body.ref[ei, :3])+np.linalg.norm(body.ref[hi, :3])
        if side == 'r':
            # Draw slightly behind the shoulder, sweep forward and carry
            # through. The elbow remains soft throughout both rotations.
            direction = c.unit(periodic([[-1., .28, -.16], [-1., .08, -.09], [-1., -.17, -.14], [-1., .12, -.22], [-1., .28, -.16]], phase))
            reach = periodic([.91, .945, .93, .90, .91], phase)
            goal = p[:, ui]+torso.apply(direction*(length*reach)[:, None])
            pole = p[:, ui]+torso.apply(np.c_[-np.full(count, .38), .13+.05*wave, -np.full(count, .48)]*length)
        else:
            # The free hand travels from a chest guard into a modest outside
            # counterbalance, then returns before the blade's next sweep.
            offset = periodic([[8., 25., -13.], [27., 24., -20.], [23., 30., -24.], [5., 27., -10.], [8., 25., -13.]], phase)*size
            offset[:, 1] = np.maximum(offset[:, 1], front+9.*size)
            goal = middle+torso.apply(offset)
            pole = p[:, ui]+torso.apply(np.c_[.36+.07*effort, .18+.07*wave, -.52+.04*effort]*length)
        old.arms.solve_arm(body, frames, side, goal, pole, np.ones(count), np.ones(count), body.ref[hi, 3:7])
    # Native palm support supplies wrist orientation; only small relative
    # articulation survives, distributed through the native twist helpers.
    for side in 'lr':
        native.upper.support_wrist(body, frames, side)
    old.steps.set_fist(body, frames, fist, .60+.10*effort)
    old.right_fingers(body, frames, held)
    native.native_twists(body, frames)
    frames[-1] = frames[0]
    return frames


def transition(body, boundary, entry, seconds, held):
    count = round(seconds*RATE)+1
    u = np.linspace(0., 1., count)
    times = u*((count-1)/RATE)
    a, b = (body.idle, boundary) if entry else (boundary, body.idle)
    frames = np.array([c.blend(a, b, smooth(t)) for t in u])
    size = body.scale/94.
    envelope = np.sin(np.pi*u)**2
    _, q = body.world(frames)
    desired = {}
    for name, amount in [('pelvis', 8.), ('spine_01', 12.), ('spine_02', 16.), ('spine_03', 19.), ('neck_01', 11.), ('head', 7.)]:
        i = body.ix[name]
        # Preparatory counter-coil and smaller follow-through on braking.
        angles = np.c_[-2.*envelope, np.zeros(count), (amount if entry else -amount*.42)*envelope]
        desired[i] = R.from_euler('xyz', angles, degrees=True)*R.from_quat(q[:, i])
    body.set_world_rotations(frames, desired)
    frames[:, body.hip, 2] -= (2.5 if entry else 2.)*size*envelope
    ap, aq = body.world(a)
    bp, bq = body.world(b)
    windows = {'l': (.04, .55), 'r': (.46, .96)} if entry else {'r': (.03, .56), 'l': (.43, .96)}
    old.steps.step_transition(body, frames, times,
        {s: ap[body.ix['foot_'+s]] for s in 'lr'}, {s: bp[body.ix['foot_'+s]] for s in 'lr'},
        {s: aq[body.ix['foot_'+s]] for s in 'lr'}, {s: bq[body.ix['foot_'+s]] for s in 'lr'},
        {s: (lo*times[-1], hi*times[-1]) for s, (lo, hi) in windows.items()}, size)
    pa = old.arms.local_arm_points(body, a)
    pb = old.arms.local_arm_points(body, b)
    p, q, torso = old.arms.chest(body, frames)
    idle_points = old.arms.local_arm_points(body, body.idle)
    for side in 'rl':
        ui, hi = body.ix['upperarm_'+side], body.ix['hand_'+side]
        start, end = pa[side]['hand'], pb[side]['hand']
        if entry:
            # The left guard arrives first. The weapon is briefly drawn low
            # before the shoulder opens into the broad horizontal sweep.
            if side == 'r':
                hand = curve([0., .40, .78, 1.], [start, .80*start+.20*end+np.array([-4., -6., -4.])*size, .22*start+.78*end+np.array([0., -4., 0.])*size, end], u)
                weight = smooth((u-.06)/.94)
            else:
                weight = smooth(u/.78)
                hand = start+(end-start)*weight[:, None]
        else:
            weight = 1.-smooth(u if side == 'r' else (u-.12)/.88)
            hand = end+(start-end)*weight[:, None]
            hand += envelope[:, None]*np.array([0., 5. if side == 'r' else 2., -3. if side == 'r' else 1.])*size
        joint_blend = smooth(u)
        elbow = pa[side]['elbow']*(1-joint_blend[:, None])+pb[side]['elbow']*joint_blend[:, None]
        old.arms.solve_arm(body, frames, side, p[:, ui]+torso.apply(hand), p[:, ui]+torso.apply(elbow),
            weight, weight, idle_points[side]['hand_local'])
        # Blend the authored supported wrist, so the exact loop endpoint is
        # approached continuously instead of overwritten on the last frame.
        supported = frames.copy()
        native.upper.support_wrist(body, supported, side)
        frames[:, hi, 3:7] = c.slerp(frames[:, hi, 3:7], supported[:, hi, 3:7], weight[:, None])
    old.right_fingers(body, frames, held)
    native.native_twists(body, frames)
    frames[0], frames[-1] = a, b
    old.right_fingers(body, frames, held)
    return frames


def main():
    cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning = json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))['whirlwind']
    if tuning['turnDegrees'] != -720:
        raise RuntimeError('Authoring assumes the existing two clockwise turns')
    report = dict(version='Windmill V8 / first Mabinogi-inspired study', runtime_tested=False, rendered=False,
        first_person_changed=False, gameplay_changed=False, reference_motion_imported=False,
        reference_limit='Distant low-resolution game footage; free-hand/wrist detail is original adaptation, not a verified replica.',
        visual_references=['https://www.youtube.com/watch?v=sY6HjMhnDUg', 'https://www.youtube.com/watch?v=c12vkqocnzI'],
        timing={k:tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds','turnDegrees')}, bodies={})
    for label, data in v7.DATA.items():
        section = cfg if label == 'jason' else cfg['body_variants'][label]
        if section['body_mesh'] != data['mesh'] or section['clips']['Kukri.FullBody.Idle'] != data['idle_asset']:
            raise RuntimeError('Native body or idle changed; refresh the authoring inputs')
        body = c.Body(data)
        front = old.chest_envelope(body, label)
        held = old.grip(body)
        fist = old.fingers.native_fist(body, json.loads(old.fingers.FIST_SOURCE.read_text()))
        loop = make_loop(body, tuning, front, fist, held)
        start = transition(body, loop[0], True, tuning['readySeconds'], held)
        end = transition(body, loop[-1], False, tuning['recoverSeconds'], held)
        clips = {}
        for role, frames in zip(ROLES, (start, loop, end)):
            for k in range(1, len(frames)):
                frames[k, :, 3:7] *= np.where(np.sum(frames[k-1, :, 3:7]*frames[k, :, 3:7], axis=1) < 0., -1., 1.)[:, None]
            clips[role] = dict(rate=RATE, frames=frames.tolist(), contact=0., release=.999,
                source='Original native-body keyframes; Mabinogi Windmill visual direction only',
                adaptation='Low horizontal single-hand sweep, soft weapon elbow, articulated free-hand counterbalance, low alternating toe pivots, counter-coil entry and staggered recovery; native grip; runtime owns the global turn.')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        report['bodies'][label] = dict(mesh=data['mesh'], idle_asset=data['idle_asset'],
            previous_roles={role:section['clips']['Kukri.FullBody.'+role] for role in ROLES},
            authoring_reference_source=data['authoring_reference_source'],
            clips={role:dict(frames=len(item['frames']),rate=item['rate']) for role,item in clips.items()})
        print('KUKRI_WINDMILL_AUTHORED '+label, flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
