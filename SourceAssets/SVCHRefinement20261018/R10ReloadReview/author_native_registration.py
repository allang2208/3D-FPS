"""Transfer the accepted arm as one rigid chain; never re-pose its wrist/fingers."""
import copy
import json
from pathlib import Path
import numpy as np

O = Path(__file__).parent
R9 = O.parent / 'R9ReloadGrip'
env = {'__file__': str(R9 / 'author_reload_grip.py')}
code = (R9 / 'author_reload_grip.py').read_text().split("report={'method'")[0]
exec(compile(code, str(R9 / 'author_reload_grip.py'), 'exec'), env)
globals().update({k: v for k, v in env.items() if k not in ('O', '__file__', '__builtins__')})
before = json.loads((R9 / 'profile_reload_grip.json').read_text())
baseline = json.loads((R9 / 'Inputs/profile_before.json').read_text())
output = copy.deepcopy(before)
report = {'method': 'Rigid native left-arm registration at clavicle with refined magazine contact',
          'registration_window_frames': [0,20,280,302], 'clips': {}}
ci = NI['clavicle_l']
contact_delta = np.asarray(json.loads((O / 'contact_refinement.json').read_text())['delta_magazine_local']) if (O / 'contact_refinement.json').exists() else np.eye(4)
grasp = np.asarray(json.loads((R9 / 'authoring_receipt.json').read_text())['clips']['reload']['magazine_local_registration'])
arcs = json.loads((O / 'contact_arcs.json').read_text())['arcs'] if (O / 'contact_arcs.json').exists() else []
for role in ('reload', 'reload_empty'):
    clip = motion['clips'][role]
    old = next(c for c in before['clips'] if c['base'] == clip['path'])
    original = next(c for c in baseline['clips'] if c['base'] == clip['path'])
    entry = next(c for c in output['clips'] if c['base'] == clip['path'])
    values = []
    shifts = []
    for i, time in enumerate(clip['times']):
        base = np.asarray(clip['frames'][i])
        native = old_pose(base, original, time)
        source = comp(matrices(native))
        current = source.copy()
        native_source = comp(matrices(base))
        # Complete shell registration before the fingers reach the wider SVCH
        # magazine, and keep it until the opened hand has cleared that shell.
        # The source finger/contact and mechanical clocks are never retimed.
        weight = float(ease(0,20,time*120)*(1-ease(280,302,time*120)))
        if weight > 1e-9:
            anchor = rigid(current[MAG])
            desired = anchor @ contact_delta @ grasp @ np.linalg.inv(anchor) @ native_source[HAND]
            current[HAND] = mix(current[HAND], desired, weight)
        for arc in arcs:
            a,b,c,d = arc['window_frames']
            arc_weight = float(ease(a,b,time*120)*(1-ease(c,d,time*120)))
            current[HAND,:3,3] += rigid(current[MAG])[:3,:3] @ np.asarray(arc['translation_magazine_cm']) * arc_weight
        registration = current[HAND] @ np.linalg.inv(source[HAND])
        target_clavicle = registration @ source[ci]
        local = np.linalg.solve(source[PI[ci]], target_clavicle)
        q = R.from_matrix(rigid(local)[:3, :3]) * R.from_quat(base[ci, 3:7]).inv()
        v = [*(local[:3, 3] - base[ci, :3]), *q.as_quat(), *(native[ci, 7:] - base[ci, 7:])]
        if values and np.dot(values[-1][3:7], v[3:7]) < 0:
            v[3:7] = [-x for x in v[3:7]]
        values.append(v)
        shifts.append(float(np.linalg.norm(target_clavicle[:3, 3] - source[ci, :3, 3])))
    entry['tracks'] = [t for t in entry['tracks'] if t['bone'] not in left_chain]
    entry['tracks'] += [copy.deepcopy(t) for t in original['tracks'] if t['bone'] in left_chain and t['bone'] != 'clavicle_l']
    entry['tracks'].append({'bone': 'clavicle_l', 'times': clip['times'], 'values': np.round(values, 10).ravel().tolist()})
    report['clips'][role] = {'max_root_registration_cm': max(shifts), 'native_local_arm_preserved': True,
                              'magazine_motion_preserved': True, 'R9_anchor_refined': True, 'root_shift_cm': shifts}
    print('NATIVE_ARM_REGISTERED', role, 'max_clavicle_shift_cm', max(shifts), flush=True)
(O / 'profile_native_registration.json').write_text(json.dumps(output, separators=(',', ':')))
(O / 'native_registration_receipt.json').write_text(json.dumps(report, indent=2))
