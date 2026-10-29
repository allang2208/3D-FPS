"""Single whirlwind V18: supported feet, anatomical weapon arm and relaxed free arm."""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
spec = importlib.util.spec_from_file_location(
    'kukri_supported_whirlwind_v2',
    ROOT / 'SourceAssets/KukriDualWhirlwindRepair20261026/author.py')
supported = importlib.util.module_from_spec(spec)
spec.loader.exec_module(supported)
base, c = supported.base, supported.c
ROLES = ('Whirlwind.Start', 'Whirlwind.Loop', 'Whirlwind.End')


def free_arm(body, frames, tuning, times):
    """Open from the native idle on the turn, with a continuous elbow bend plane."""
    n = len(times)
    ready, spin, recover = [tuning[k] for k in ('readySeconds', 'spinSeconds', 'recoverSeconds')]
    stop = ready + spin
    u = np.clip((times - ready) / spin, 0., 1.)
    leave = base.smooth((times - stop) / recover)
    grid = np.linspace(0., 1., 4097)
    deploy_u = np.interp(145. / abs(tuning['turnDegrees']), base.old.arms.phase(grid), grid)
    amount = base.smooth(u / deploy_u) * (1. - leave)
    ip, iq = body.world(body.idle)

    # The empty hand keeps its native idle fingers, never the dual-knife grip.
    for i, name in enumerate(body.names):
        if name.endswith('_l') and name.startswith((
                'clavicle_', 'upperarm_', 'lowerarm_', 'hand_',
                'thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
            frames[:, i] = body.idle[i]
    p, q = body.world(frames)
    chest = body.ix['spine_05']
    torso = R.from_quat(q[:, chest]) * R.from_quat(body.tq[chest]).inv()
    idle_torso = R.from_quat(iq[chest]) * R.from_quat(body.tq[chest]).inv()
    clavicle = body.ix['clavicle_l']
    carried_clavicle = torso * idle_torso.inv() * R.from_quat(iq[clavicle])
    relaxed_clavicle = torso * R.from_euler('y', -2., degrees=True) * R.from_quat(body.tq[clavicle])
    body.set_world_rotations(frames, {clavicle: R.from_quat(c.slerp(
        carried_clavicle.as_quat(), relaxed_clavicle.as_quat(), amount[:, None]))})

    p, _ = body.world(frames)
    ui, ei, hi = [body.ix[k + '_l'] for k in ('upperarm', 'lowerarm', 'hand')]
    length = np.linalg.norm(body.ref[ei, :3]) + np.linalg.norm(body.ref[hi, :3])
    forward = torso.apply(np.tile([0., 1., 0.], (n, 1)))
    heading = R.from_euler('z', np.arctan2(-forward[:, 0], forward[:, 1])[:, None])
    # A small torso contribution leaves the wrist hanging beside the thigh
    # while the chest inclines, rather than folding it into the waist/chest.
    gravity_frame = R.from_quat(c.slerp(heading.as_quat(), torso.as_quat(), .15))
    hand0 = idle_torso.inv().apply(ip[hi] - ip[ui])
    elbow0 = idle_torso.inv().apply(ip[ei] - ip[ui])
    goal0 = p[:, ui] + torso.apply(np.tile(hand0, (n, 1)))
    settle = np.sin(np.pi * u) ** 2
    sweep_sign = np.sign(tuning['turnDegrees'])
    hanging = np.c_[.26 + .025 * settle,
                    .10 - sweep_sign * .035 * settle,
                    -.84 + .018 * settle] * length
    goal1 = p[:, ui] + gravity_frame.apply(hanging)
    goal = goal0 + (goal1 - goal0) * amount[:, None]
    pole0 = p[:, ui] + torso.apply(np.tile(elbow0, (n, 1)))
    pole1 = p[:, ui] + gravity_frame.apply(np.tile([.18, .55, -.35], (n, 1)) * length)

    # Transport the bend around the reach axis; a straight pole interpolation
    # can pass through that axis and turn a smooth hand path into an elbow flip.
    axis0 = c.unit(goal0 - p[:, ui])
    axis1 = c.unit(goal1 - p[:, ui])
    reach = c.unit(goal - p[:, ui])
    bend0 = pole0 - p[:, ui]
    bend0 = c.unit(bend0 - axis0 * np.sum(bend0 * axis0, axis=1)[:, None])
    bend1 = pole1 - p[:, ui]
    bend1 = c.unit(bend1 - axis1 * np.sum(bend1 * axis1, axis=1)[:, None])
    carried = c.align(axis0, reach).apply(bend0)
    final_bend = c.align(axis0, axis1).apply(bend0)
    roll = np.arctan2(np.sum(axis1 * np.cross(final_bend, bend1), axis=1),
                      np.sum(final_bend * bend1, axis=1))
    bend = R.from_rotvec(reach * (roll * amount)[:, None]).apply(carried)
    _, forearm = supported.limb(body, frames, 'l', ('upperarm', 'lowerarm', 'hand'),
                               goal, p[:, ui] + bend * length)
    # No external palm target: the empty wrist follows its forearm and returns
    # along the same local rotation into the idle, avoiding late world-space roll.
    local_wrist = R.from_quat(c.slerp(body.idle[hi, 3:7], body.ref[hi, 3:7], amount[:, None]))
    body.set_world_rotations(frames, {hi: forearm * local_wrist})
    base.relaxed_free_hand(body, frames, amount, times, ready, spin)
    base.free_hand_helpers(body, frames, amount)

    # Re-derive only the newly authored left arm helpers; the supported right
    # arm already contains its own native idle-offset transition.
    derived = frames.copy()
    base.native.native_twists(body, derived)
    idle_helpers = body.idle[None].copy()
    base.native.native_twists(body, idle_helpers)
    for i, name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('upperarm_twist_', 'lowerarm_twist_')):
            offset = R.from_quat(body.idle[i, 3:7]) * R.from_quat(idle_helpers[0, i, 3:7]).inv()
            correction = R.from_quat(c.slerp([0., 0., 0., 1.], offset.as_quat(), (1. - amount)[:, None]))
            frames[:, i, 3:7] = (correction * R.from_quat(derived[:, i, 3:7])).as_quat()


def main():
    cfg = json.loads((ROOT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    tuning = base.effective_tuning()
    times, cuts, _, _ = base.timeline(tuning)
    report = dict(version='Single whirlwind V18', tuning=tuning, bodies={},
                  first_person_changed=False, gameplay_changed=False,
                  runtime_tested=False, rendered=False,
                  source='Dual V2 supported lower body and right arm; independently authored empty left arm')
    for label, data in base.rig.DATA.items():
        active = cfg if label == 'jason' else cfg['body_variants'][label]
        if active['body_mesh'] != data['mesh'] or active['clips']['Kukri.FullBody.Idle'] != data['idle_asset']:
            raise RuntimeError('Native mesh or idle changed; refresh authoring inputs')
        body = c.Body(data)
        frames, info = supported.make(body, label, tuning, times)
        free_arm(body, frames, tuning, times)
        frames[0] = body.idle
        frames[-1] = body.idle
        base.old.right_fingers(body, frames, base.old.grip(body))
        for k in range(1, len(frames)):
            frames[k, :, 3:7] *= np.where(
                np.sum(frames[k - 1, :, 3:7] * frames[k, :, 3:7], axis=1) < 0., -1., 1.)[:, None]
        clips = {role: dict(rate_num=base.RATE, rate_den=1, frames=frames[a:b].tolist(),
                           contact=0., release=.999,
                           source='Original native-body single whirlwind V18',
                           adaptation='Supported outward knee-toe stance; shoulder-high anatomical weapon arm and fixed grip; relaxed side-hanging empty hand with transported elbow and continuous recovery')
                 for role, (a, b) in zip(ROLES, cuts)}
        (OUT / (label + '-actions.json')).write_text(json.dumps(
            dict(mesh=data['mesh'], names=body.names, parents=body.parents, clips=clips), separators=(',', ':')))
        report['bodies'][label] = dict(mesh=data['mesh'], idle_asset=data['idle_asset'],
            previous_roles={r: active['clips']['Kukri.FullBody.' + r] for r in ROLES},
            weapon_forearm_bank_degrees=info['forearm_bank_degrees']['r'],
            lowering_cm=info['lowering_cm'], stance_toe_half_width_cm=info['stance_toe_half_width_cm'],
            free_hand='Relaxed fingers; wrist follows native forearm; continuous side-hanging elbow arc',
            clips={r: dict(frames=len(v['frames']), rate=base.RATE) for r, v in clips.items()})
        print('SINGLE_WHIRLWIND_V18_AUTHORED', label, flush=True)
    (OUT / 'authoring.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
