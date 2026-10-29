"""Single-kukri dash: native shoulder swing and a fixed anatomical elbow hinge."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
PREVIOUS = ROOT / 'SourceAssets/KukriDashHands20261028'
spec = importlib.util.spec_from_file_location('dash_hands_v3', PREVIOUS / 'author.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
c, TIMES, LENGTH = old.c, old.TIMES, old.LENGTH
curve, phase = old.curve, old.phase


def free_arm(body, original):
    f = original.copy()
    idle = original[0].copy()
    body.idle = idle
    left = [i for i, name in enumerate(body.names) if old.carry.left_bone(name)]
    f[:, left] = idle[left]
    ip, iq = body.world(idle)
    p, q = body.world(f)
    ui, ei, hi = [body.ix[name + '_l'] for name in ('upperarm', 'lowerarm', 'hand')]
    ci, ch = body.ix['clavicle_l'], body.ix['spine_05']
    torso = R.from_quat(q[:, ch]) * R.from_quat(body.tq[ch]).inv()
    idle_torso = R.from_quat(iq[ch]) * R.from_quat(body.tq[ch]).inv()
    w = phase(0., .23) * (1. - phase(.90, LENGTH))

    # The shoulder blade follows the torso with only a small retraction.
    keys = [0., .20, .29, .40, .54, .68, .88, 1.08, LENGTH]
    scapula = curve(keys, [0., -1.5, -1., 1.5, 3., 3., 1.5, 0., 0.]) * w
    body.set_world_rotations(f, {
        ci: torso * R.from_euler('z', scapula[:, None], degrees=True)
            * idle_torso.inv() * R.from_quat(iq[ci])})

    # Choose the upper-arm direction itself, not a wrist target plus elbow pole.
    # +Y is forward. The negative sweep carries the elbow and then the hand back.
    forward = np.radians(curve(keys, [12., 18., 14., -12., -39., -42., -23., 5., 12.]))
    outward = np.radians(curve(keys, [16., 16., 15., 14., 15., 16., 16., 16., 16.]))
    target = np.c_[np.sin(outward), np.sin(forward) * np.cos(outward),
                   -np.cos(forward) * np.cos(outward)]
    native_upper = idle_torso.inv().apply(c.unit(ip[ei] - ip[ui]))
    seed = np.tile(native_upper, (len(f), 1))
    swing = c.align(seed, target)
    direction = R.from_rotvec(swing.as_rotvec() * w[:, None]).apply(seed)
    # Minimal transport preserves the native arm roll. There is no pole-vector
    # roll and no wrist-orientation constraint driving the shoulder.
    upper = torso * c.align(seed, direction) * idle_torso.inv() * R.from_quat(iq[ui])

    u0, v0 = c.unit(ip[ei] - ip[ui]), c.unit(ip[hi] - ip[ei])
    hinge = R.from_quat(iq[ui]).inv().apply(c.unit(np.cross(u0, v0)))
    idle_bend = np.arccos(np.clip(u0 @ v0, -1., 1.))
    # The elbow eases open after the shoulder starts its back swing and remains
    # bent; it cannot roll around the reach axis or flip to the other side.
    elbow_keys = [0., .22, .33, .46, .61, .76, .98, 1.12, LENGTH]
    wanted = np.radians(curve(elbow_keys, [45., 48., 46., 35., 27., 31., 44., 48., 45.]))
    bend = idle_bend + (wanted - idle_bend) * w
    fore_local = R.from_rotvec(hinge[None] * (bend - idle_bend)[:, None]) * R.from_quat(idle[ei, 3:7])
    fore = upper * fore_local
    # Relax toward the native wrist instead of trying to hold a world-space palm.
    wrist = R.from_quat(c.slerp(idle[hi, 3:7], body.ref[hi, 3:7], (.28 * w)[:, None]))
    body.set_world_rotations(f, {ui: upper, ei: fore, hi: fore * wrist})
    for i, name in enumerate(body.names):
        if name.endswith('_l') and name.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_')):
            relax = (.10 if name.startswith('thumb_') else .22) * w
            f[:, i, 3:7] = c.slerp(idle[i, 3:7], body.ref[i, 3:7], relax[:, None])
    old.left_helpers(body, f, idle)
    f[0], f[-1] = original[0], original[-1]
    for k in range(1, len(f)):
        f[k, :, 3:7] *= np.where(np.sum(f[k - 1, :, 3:7] * f[k, :, 3:7], axis=1) < 0., -1., 1.)[:, None]
    # World-to-local conversion normalizes all rotations; retain every unowned
    # track byte-for-byte instead of publishing even roundoff outside this arm.
    untouched = [i for i in range(len(body.names)) if i not in left]
    f[:, untouched] = original[:, untouched]
    return f


def main():
    cfg = json.loads((ROOT / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    saved = json.loads((PREVIOUS / 'assets-saved.json').read_text())
    report = dict(version='Single dash free-arm V4', bodies={}, first_person_changed=False,
                  dual_changed=False, runtime_tested=False, rendered=False)
    for label, data in old.base.rig.DATA.items():
        active = cfg if label == 'jason' else cfg['body_variants'][label]
        raw = (PREVIOUS / (label + '-actions.json')).read_bytes()
        source = json.loads(raw)
        receipt = saved['bodies'][label]
        previous = receipt['clips']['Kukri.FullBody.Dash']
        if hashlib.sha256(raw).hexdigest() != receipt['source_sha256'] or active['clips']['Kukri.FullBody.Dash'] != previous:
            raise RuntimeError('The installed single dash is no longer the source: ' + label)
        if source['names'] != data['names'] or source['mesh'] != active['body_mesh']:
            raise RuntimeError('Native mesh source mismatch: ' + label)
        clip = dict(source['clips']['Dash'])
        clip['frames'] = free_arm(c.Body(data), np.asarray(clip['frames'])).tolist()
        clip['source'] = previous
        clip['adaptation'] = 'Single free left arm: minimal shoulder swing, native fixed elbow hinge, delayed backward sweep, relaxed palm; preserved main arm and support'
        output = dict(mesh=source['mesh'], names=source['names'], parents=source['parents'], clips={'Dash': clip})
        (OUT / (label + '-actions.json')).write_text(json.dumps(output, separators=(',', ':')))
        report['bodies'][label] = dict(previous_roles={'Dash': previous}, previous_source_sha256=receipt['source_sha256'])
        print('SINGLE_FREE_ARM_AUTHORED', label, flush=True)
    (OUT / 'authoring.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
