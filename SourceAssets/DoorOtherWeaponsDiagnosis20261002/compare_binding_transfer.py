"""Requested source/asset diagnosis of current door-guard Capture equations.

No game execution, rendering, animation changes, or asset writes.
"""
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
bindings = json.loads((HERE / 'current-bindings.json').read_text(encoding='utf-8'))
motion = json.loads((PROJECT / 'SourceAssets/DoorPush20261002/full-pose.json').read_text(encoding='utf-8'))
donor_path = bindings['donor_path']
donor = bindings['sources'][donor_path]['bones']
chain = ('clavicle_l', 'upperarm_l', 'lowerarm_l', 'hand_l')


def r(t):
    return Rotation.from_quat(t['rotation_xyzw']).as_matrix()


def angle(m):
    return float(np.degrees(Rotation.from_matrix(m).magnitude()))


def parent_map(bones):
    names = {b['index']: n for n, b in bones.items()}
    return {n: names.get(b['parent']) for n, b in bones.items()}


dp = parent_map(donor)


def donor_components(key):
    cs = {}
    for name, bone in sorted(donor.items(), key=lambda item: item[1]['index']):
        parent = dp[name]
        local = bone['local']
        lr, lt, ls = r(local), np.array(local['position']), np.array(local['scale'])
        if name in motion['order']:
            source = np.array(key['local'][name])
            lr = source[:3, :3]
            scale = np.array(donor[parent]['component']['scale']) if parent else np.ones(3)
            lt = source[:3, 3] / scale
        if parent:
            pr, pt, ps = cs[parent]
            cs[name] = (pr @ lr, pt + pr @ (ps * lt), ps * ls)
        else:
            cs[name] = (lr, lt, ls)
    return cs


goals = [(key, donor_components(key)) for key in motion['poses'][1:6]]
rows = []
for path, asset in bindings['sources'].items():
    target = asset['bones']
    profile = asset['profile']
    if profile == 'Bow':
        bp = parent_map(target)
        basis = r(target['clavicle_l']['component']) @ r(donor['clavicle_l']['component']).T
        segment_errors = {}
        for name in ('upperarm_l', 'lowerarm_l', 'hand_l'):
            parent = bp[name]
            correction = r(target[parent]['component']).T @ r(donor[parent]['component'])
            actual_offset = np.array(target[name]['local']['position']) * np.array(target[parent]['component']['scale'])
            target_offset = np.array(donor[name]['local']['position']) * np.array(donor[parent]['component']['scale'])
            segment_errors[name] = float(np.linalg.norm(correction @ target_offset - actual_offset))
        rows.append(dict(profile=profile, path=path, branch='Canonical M4 fallback; Bow is the entry/recovery source',
                         status='Guard target uses canonical donor instead of this Bow reference binding',
                         measured_directly_as_guard_target=False,
                         transition_diagnosis=dict(
                             status='Entry and external-source recovery apply reference-rotation correction despite a common skeleton-space basis change',
                             common_skeleton_basis_rotation_degrees=angle(basis),
                             max_chain_component_basis_residual_degrees=max(angle(basis.T @ r(target[n]['component']) @ r(donor[n]['component']).T) for n in chain),
                             max_chain_child_local_rotation_difference_degrees=max(angle(r(target[n]['local']) @ r(donor[n]['local']).T) for n in chain),
                             segment_vector_difference_cm_in_native_binding_units=segment_errors,
                             formula='SourceCameraOrMeshRotation * SourceReferenceRotation.inverse * TargetReferenceRotation; followed by target native local-offset FK',
                             interpretation='This extra correction changes the incoming arm segment direction; vector error is pose independent, but exact whole-arm screen placement requires the live source pose',
                             scope='Entry and recovery only; canonical author guard hold is unaffected')))
        continue
    missing = [n for n in chain if n not in target]
    if missing:
        rows.append(dict(profile=profile, path=path, status='Missing native left chain', missing=missing))
        continue
    tp = parent_map(target)
    native = path == donor_path
    m16 = path.startswith('/Game/Weapons/M16A2/Gameplay20260919/') or path.startswith('/Game/Characters/ModularOutfit20260924/BarePalmV7/M16/')
    ash12 = path == '/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface.SK_ASH12_Surface' or path.startswith('/Game/Characters/ModularOutfit20260924/BarePalmV7/ASH12/')
    authored = native or m16 or ash12
    branch = 'Authored complete chain' if authored else 'Generic reference-rotation delta'
    compatible = []
    for name in motion['order']:
        if name not in target:
            continue
        tparent, dparent = tp[name], dp[name]
        tpos = np.array(target[name]['local']['position']) * np.array(target[tparent]['component']['scale'])
        dpos = np.array(donor[name]['local']['position']) * np.array(donor[dparent]['component']['scale'])
        compatible.append((name, float(np.linalg.norm(tpos-dpos)), tparent == dparent))
    key_rows = []
    for key, dc in goals:
        qr = {n: dc[n][0] if authored else dc[n][0] @ r(donor[n]['component']).T @ r(target[n]['component']) for n in chain}
        camera = {}
        for name in chain:
            local = target[name]['local']
            if name == 'clavicle_l':
                scale = np.array(target[name]['component']['scale'])
                upper_offset = np.array(target['upperarm_l']['local']['position']) * scale
                camera[name] = (qr[name], np.array(key['contact']['shoulder_cm']) - qr[name] @ upper_offset, scale)
            else:
                parent = tp[name]
                pr, pt, ps = camera[parent]
                lt = np.array(local['position'])
                if native:
                    dpr, dpt, dps = dc[dp[name]]
                    lt = dpr.T @ (dc[name][1]-dpt) / dps
                camera[name] = (pr @ (qr[parent].T @ qr[name]), pt + pr @ (ps*lt), ps*np.array(local['scale']))
        key_rows.append(dict(name=key['name'], time_seconds=key['time_seconds'],
            desired_elbow_camera_cm=key['contact']['elbow_cm'], mapped_elbow_camera_cm=camera['lowerarm_l'][1].tolist(),
            elbow_error_cm=float(np.linalg.norm(camera['lowerarm_l'][1]-np.array(key['contact']['elbow_cm']))),
            desired_wrist_camera_cm=key['contact']['wrist_cm'], mapped_wrist_camera_cm=camera['hand_l'][1].tolist(),
            wrist_error_cm=float(np.linalg.norm(camera['hand_l'][1]-np.array(key['contact']['wrist_cm']))),
            hand_rotation_difference_degrees=angle(camera['hand_l'][0] @ dc['hand_l'][0].T)))
    peak_wrist = max(k['wrist_error_cm'] for k in key_rows)
    peak_elbow = max(k['elbow_error_cm'] for k in key_rows)
    rows.append(dict(profile=profile, path=path, skeleton=asset['skeleton'], source_sha256=asset['source_sha256'],
        branch=branch, status=('Clear authored-target mismatch' if max(peak_wrist, peak_elbow)>1.0 else 'No comparable whole-arm mismatch in these source equations'),
        max_wrist_error_cm=peak_wrist, max_elbow_error_cm=peak_elbow,
        hand_rotation_difference_degrees=key_rows[0]['hand_rotation_difference_degrees'],
        native_segment_max_offset_difference_cm=max((e for n,e,p in compatible if n!='clavicle_l'), default=0),
        native_segment_parent_hierarchy_matches=all(p for n,e,p in compatible),
        native_motion_bones_available=len(compatible), guard_keys=key_rows))

report = dict(scope='Requested cross-weapon door-guard whole-left-arm source/asset diagnosis',
    motion_revision=motion['revision'],
    method='Current Capture equations reproduced from current UE asset native binding data; hold keys only',
    interpretation='Numerical authored-target mismatch; not a runtime screenshot, skin deformation verdict, or visual acceptance',
    unavailable_assets=bindings['unavailable'], weapons=rows,
    runtime_source_changed=False, assets_changed=False, assets_saved=False, runtime_tested=False, rendered=False)
(HERE / 'binding-transfer-diagnosis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
for row in rows:
    if 'max_wrist_error_cm' in row:
        print(f"{row['profile']:12s} wrist={row['max_wrist_error_cm']:7.3f}cm elbow={row['max_elbow_error_cm']:7.3f}cm hand={row['hand_rotation_difference_degrees']:7.3f}deg offsets={row['native_segment_max_offset_difference_cm']:.6f}cm {row['branch']} {row['path']}")
    else:
        print(row['profile'], row.get('branch', row['status']))
print('Unavailable assets:', len(bindings['unavailable']))
