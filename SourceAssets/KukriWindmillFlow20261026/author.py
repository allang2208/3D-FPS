"""V9: one connected two-turn performance, not a repeated outstretched pose.

Author low draw -> outward release -> first sweep -> gathered second sweep ->
forward/down follow-through. Mabinogi is a visual direction, not curve data.
Existing gameplay still supplies the full -720 degree rotation and clock.
"""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
spec = importlib.util.spec_from_file_location('windmill_v8_helpers', ROOT/'SourceAssets/KukriWindmill20261026/author.py')
v8 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v8)
c, old, native = v8.c, v8.old, v8.native
RATE, ROLES = 120, old.ROLES


def spin_feet(body, frames, angular, turns, size):
    """Same signed angular clock; wider steps and visible knee/heel release."""
    ip, iq = body.world(body.idle)
    actor = -2*np.pi*turns*angular
    half = 2*turns*angular
    goals, rotations, poles = {}, {}, {}
    for side, offset in [('l', 0.), ('r', .5)]:
        x = half-offset
        n, f = np.floor(x), x-np.floor(x)
        swing = np.clip((f-.5)*2, 0., 1.)
        anchor = -2*np.pi*((n+offset+.25)/2+.5*v8.smooth(swing))
        relative = anchor-actor
        yaw = R.from_euler('z', relative[:, None])
        lift = np.sin(np.pi*swing)**2
        # Follow an outside arc, not a line through the planted ankle.
        radius = 21.*size*(1.+.16*lift)
        points = yaw.apply(np.c_[(1 if side == 'l' else -1)*radius, np.zeros(len(f)), np.zeros(len(f))])
        heel = np.where(f < .5, -12*np.sin(np.pi*f*2)**2, 8*np.sin(np.pi*swing)**2)
        foot, ball = body.ix['foot_'+side], body.ix['ball_'+side]
        foot_yaw = R.from_euler('z', (.72*relative)[:, None])
        base = foot_yaw*R.from_quat(np.tile(iq[foot], (len(f), 1)))
        rot = foot_yaw*R.from_euler('x', heel[:, None], degrees=True)*R.from_quat(np.tile(iq[foot], (len(f), 1)))
        toe = R.from_quat(iq[foot]).inv().apply(ip[ball]-ip[foot])
        baseline = base.apply(np.tile(toe, (len(f), 1)))
        actual = rot.apply(np.tile(toe, (len(f), 1)))
        points[:, 2] = ip[ball, 2]-baseline[:, 2]+7.*size*lift
        points += baseline-actual
        goals[side], rotations[side] = points, rot
        knee = R.from_euler('z', (.48*relative)[:, None]).apply(np.tile([28 if side == 'l' else -28, 44, -25], (len(f), 1)))
        poles[side] = frames[:, body.hip, :3]+knee*size
    old.steps.fit_legs(body, frames, goals, rotations, poles)


def performance(body, tuning, front, held, fist):
    count = round(tuning['spinSeconds']*RATE)+1
    u = np.linspace(0., 1., count)
    p = old.arms.phase(u)
    knots = [0., .09, .23, .40, .51, .64, .79, .92, 1.]
    size = body.scale/94.
    frames = np.repeat(body.idle[None], count, axis=0)
    ip, _ = body.world(body.idle)
    # Separate loading, push-off and braking. A periodic bob would make both
    # turns appear to be the same rigid stance again.
    hips = [[3.,-3.,-16.],[-2.,0.,-21.],[-3.,2.,-17.],
            [3.,1.,-20.],[4.,-1.,-23.],[-3.,0.,-19.],
            [-4.,3.,-16.],[-1.,5.,-20.],[0.,4.,-18.]]
    frames[:, body.hip, :3] = ip[body.hip]+v8.curve(knots, hips, p)*size
    chest_yaw = v8.curve(knots, [28., 6., -22., -8., 19., 3., -26., -19., -12.], p)
    chest_pitch = v8.curve(knots, [-12.,-21.,-16.,-12.,-19.,-20.,-14.,-18.,-13.], p)
    lean = v8.curve(knots, [3.,-5.,-4.,3.,5.,-5.,-5.,-2.,0.], p)
    desired = {}
    for name, pitch_ratio, yaw_ratio, lean_ratio in [
        ('pelvis', .38, .38, .45), ('spine_01', .65, .65, .70),
        ('spine_02', .85, .85, .90), ('spine_03', 1., 1., 1.),
        ('neck_01', .55, .72, .55), ('head', .30, .48, .30)]:
        i = body.ix[name]
        desired[i] = R.from_euler('xyz', np.c_[chest_pitch*pitch_ratio, lean*lean_ratio, chest_yaw*yaw_ratio], degrees=True)*R.from_quat(body.tq[i])
    body.set_world_rotations(frames, desired)
    spin_feet(body, frames, p, abs(tuning['turnDegrees'])/360., size)

    # Shoulder opening follows each release. The free-side shoulder counters
    # it rather than being a fixed clavicle under a moving wrist.
    _, _, torso = old.arms.chest(body, frames)
    shoulder = {}
    right_open = v8.curve(knots, [-11.,-3.,10.,4.,-9.,1.,12.,9.,5.], p)
    left_open = v8.curve(knots, [-12.,-8.,3.,-4.,-14.,-6.,5.,-3.,-10.], p)
    for side, opening in [('r', right_open), ('l', left_open)]:
        i = body.ix['clavicle_'+side]
        tilt = np.c_[np.zeros(count), np.full(count, -3. if side == 'r' else 1.), opening]
        shoulder[i] = torso*R.from_euler('xyz', tilt, degrees=True)*R.from_quat(body.tq[i])
    body.set_world_rotations(frames, shoulder)
    world, _, torso = old.arms.chest(body, frames)
    middle = .5*(world[:, body.ix['upperarm_l']]+world[:, body.ix['upperarm_r']])
    # Positions are meaningful hand destinations, not a sine added to a fixed
    # arm. Each turn has a different entry and the second finishes forwards.
    right_dirs = [[-.69,-.48,-.54],[-.96,-.14,-.22],[-.77,.62,-.14],
                  [-.94,.20,-.26],[-.76,-.53,-.29],[-.99,-.04,-.13],
                  [-.72,.68,-.14],[-.63,.66,-.40],[-.56,.65,-.51]]
    right_reach = [.76,.92,.94,.88,.82,.945,.935,.88,.81]
    left_points = [[4.,29.,-10.],[13.,30.,-13.],[32.,25.,-22.],
                   [17.,32.,-16.],[0.,31.,-8.],[15.,28.,-14.],
                   [30.,25.,-23.],[13.,30.,-18.],[6.,29.,-13.]]
    for side in 'rl':
        ui, ei, hi = [body.ix[n+'_'+side] for n in ('upperarm','lowerarm','hand')]
        length = np.linalg.norm(body.ref[ei,:3])+np.linalg.norm(body.ref[hi,:3])
        if side == 'r':
            direction = c.unit(v8.curve(knots, right_dirs, p))
            reach = np.clip(v8.curve(knots, right_reach, p), .74, .95)
            goal = world[:,ui]+torso.apply(direction*(length*reach)[:,None])
            pole_curve = v8.curve(knots, [[-.38,-.17,-.47],[-.40,.06,-.47],[-.28,.36,-.46],
                [-.35,.22,-.51],[-.36,-.18,-.47],[-.42,.10,-.44],[-.26,.37,-.48],[-.25,.31,-.54],[-.27,.24,-.58]], p)
        else:
            offset = v8.curve(knots, left_points, p)*size
            offset[:,1] = np.maximum(offset[:,1], front+10.*size)
            goal = middle+torso.apply(offset)
            pole_curve = v8.curve(knots, [[.22,.24,-.55],[.31,.28,-.53],[.52,.13,-.41],
                [.37,.26,-.51],[.18,.26,-.53],[.34,.27,-.51],[.51,.14,-.42],[.35,.25,-.53],[.24,.26,-.54]], p)
        pole = world[:,ui]+torso.apply(pole_curve*length)
        old.arms.solve_arm(body,frames,side,goal,pole,np.ones(count),np.ones(count),body.ref[hi,3:7])
        native.upper.support_wrist(body,frames,side)
    close = np.clip(v8.curve(knots,[.68,.66,.49,.58,.72,.64,.48,.58,.65],p),.46,.74)
    old.steps.set_fist(body,frames,fist,close)
    old.right_fingers(body,frames,held)
    native.native_twists(body,frames)
    # Deliberately distinct endpoints: the final forward/down follow-through
    # continues into recovery instead of teleporting back to the first pose.
    return frames


def main():
    cfg=json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning=json.loads((ROOT/'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))['whirlwind']
    if tuning['turnDegrees'] != -720:
        raise RuntimeError('Current performance assumes the existing two-turn clock')
    report=dict(version='Windmill V9 continuous draw/sweep/follow-through',rendered=False,runtime_tested=False,
        gameplay_changed=False,first_person_changed=False,reference_motion_imported=False,
        reference_limit='Mabinogi gameplay is visual direction only; not a frame-matched replica.',
        timing={k:tuning[k] for k in ('readySeconds','spinSeconds','recoverSeconds','turnDegrees')},bodies={})
    for label,data in v8.v7.DATA.items():
        section=cfg if label=='jason' else cfg['body_variants'][label]
        if section['body_mesh']!=data['mesh'] or section['clips']['Kukri.FullBody.Idle']!=data['idle_asset']:
            raise RuntimeError('Refresh native authoring inputs for changed mesh/idle')
        body=c.Body(data)
        held=old.grip(body)
        fist=old.fingers.native_fist(body,json.loads(old.fingers.FIST_SOURCE.read_text()))
        loop=performance(body,tuning,old.chest_envelope(body,label),held,fist)
        start=v8.transition(body,loop[0],True,tuning['readySeconds'],held)
        end=v8.transition(body,loop[-1],False,tuning['recoverSeconds'],held)
        clips={}
        for role,frames in zip(ROLES,(start,loop,end)):
            for k in range(1,len(frames)):
                frames[k,:,3:7]*=np.where(np.sum(frames[k-1,:,3:7]*frames[k,:,3:7],axis=1)<0,-1.,1.)[:,None]
            clips[role]=dict(rate=RATE,frames=frames.tolist(),contact=0.,release=.999,
                source='Original native-body windmill performance, Mabinogi visual direction',
                adaptation='Distinct low draw, broad horizontal sweep, second-turn reload and forward/down follow-through; free shoulder/elbow counterbalance; deeper weight transfer and low outside stepping; native grip; no repeated pose cycle.')
        (OUT/(label+'-actions.json')).write_text(json.dumps(dict(mesh=data['mesh'],names=body.names,parents=body.parents,clips=clips),separators=(',',':')))
        report['bodies'][label]=dict(mesh=data['mesh'],idle_asset=data['idle_asset'],
            previous_roles={role:section['clips']['Kukri.FullBody.'+role] for role in ROLES},
            authoring_reference_source=data['authoring_reference_source'],
            clips={role:dict(frames=len(item['frames']),rate=item['rate']) for role,item in clips.items()})
        print('KUKRI_WINDMILL_FLOW_AUTHORED '+label,flush=True)
    (OUT/'authoring.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
