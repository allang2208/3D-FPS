"""User-requested targeted diagnosis of the single dash left-arm twist."""
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import author as a


def measure(body, frames):
    p, q = body.world(frames)
    ui, ei, hi = [body.ix[n + '_l'] for n in ('upperarm', 'lowerarm', 'hand')]
    ref = R.from_quat(body.ref[ui, 3:7])
    current = R.from_quat(frames[:, ui, 3:7])
    axis = a.c.unit(body.ref[ei, :3])
    swing = a.c.align(np.tile(ref.apply(axis), (len(frames), 1)), current.apply(np.tile(axis, (len(frames), 1))))
    axial = np.degrees((ref.inv() * swing.inv() * current).magnitude())
    lref = R.from_quat(frames[0, ei, 3:7])
    ip, iq = body.world(frames[0])
    hinge = R.from_quat(iq[ui]).inv().apply(a.c.unit(np.cross(ip[ei] - ip[ui], ip[hi] - ip[ei])))
    local_delta = (R.from_quat(frames[:, ei, 3:7]) * lref.inv()).as_rotvec()
    off_hinge = local_delta - (local_delta @ hinge)[:, None] * hinge
    u, v = a.c.unit(p[:, ei] - p[:, ui]), a.c.unit(p[:, hi] - p[:, ei])
    elbow = np.degrees(np.arccos(np.clip(np.sum(u * v, axis=1), -1., 1.)))
    chest = body.ix['spine_05']
    torso = R.from_quat(q[:, chest]) * R.from_quat(body.tq[chest]).inv()
    relative = torso.inv().apply(p[:, hi] - p[:, ui])
    steps = {}
    for n in ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l']:
        rot = R.from_quat(frames[:, body.ix[n], 3:7])
        steps[n] = float(np.degrees((rot[:-1].inv() * rot[1:]).magnitude()).max())
    return dict(max_shoulder_axial_degrees=float(axial.max()),
        max_elbow_off_hinge_degrees=float(np.degrees(np.linalg.norm(off_hinge, axis=1)).max()),
        elbow_flex_range_degrees=[float(elbow.min()), float(elbow.max())],
        most_backward_hand_cm=float(relative[:, 1].min()), max_local_step_degrees=steps,
        sample_hand_in_torso_cm={str(t): np.round(relative[round(t * 120)], 3).tolist() for t in [.2, .4, .55, .7, .9, 1.1]})


report = dict(scope='single dash left arm only; source-space diagnosis', bodies={}, runtime_tested=False, rendered=False)
for label, data in a.old.base.rig.DATA.items():
    body = a.c.Body(data)
    old = np.asarray(json.loads((a.PREVIOUS / (label + '-actions.json')).read_text())['clips']['Dash']['frames'])
    new = np.asarray(json.loads((a.OUT / (label + '-actions.json')).read_text())['clips']['Dash']['frames'])
    untouched = [i for i, n in enumerate(body.names) if not a.old.carry.left_bone(n)]
    assert np.array_equal(new[:, untouched], old[:, untouched]), 'Non-left tracks changed'
    assert np.array_equal(new[[0, -1]], old[[0, -1]]), 'Carry boundary changed'
    assert np.array_equal(new[:, :, :3], old[:, :, :3]), 'Bone lengths or translation changed'
    before, after = measure(body, old), measure(body, new)
    assert after['max_shoulder_axial_degrees'] < 45.
    assert after['max_elbow_off_hinge_degrees'] < .001
    assert after['elbow_flex_range_degrees'][0] > 20.
    assert max(after['max_local_step_degrees'].values()) < 5.
    report['bodies'][label] = dict(before=before, after=after, non_left_tracks_identical=True, boundaries_identical=True)
    print(label, json.dumps(report['bodies'][label]), flush=True)
(a.OUT / 'diagnosis.json').write_text(json.dumps(report, indent=2))
