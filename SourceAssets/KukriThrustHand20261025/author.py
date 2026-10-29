"""Refine only the free left hand of the existing native Combo V3 thrust.

The staff/unarmed closed fist supplies anatomical finger directions and thumb
opposition. Each world body retains its own bone lengths, wrist and arm motion.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
BASE = ROOT / 'SourceAssets/KukriThirdPerson20261024/ComboV3'
FIST_SOURCE = ROOT / 'SourceAssets/UnarmedIdle20261001/full-pose.json'
spec = importlib.util.spec_from_file_location('kukri_combo_source', BASE / 'author.py')
combo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(combo)


def native_fist(body, source):
    rest = {n: np.asarray(m) for n, m in source['rest'].items()}
    pose = {n: np.asarray(m) for n, m in source['poses'][0]['component'].items()}
    source_hand = R.from_matrix(rest['hand_l'][:3, :3])
    target_hand = R.from_quat(body.tq[body.ix['hand_l']])
    source_points = [source_hand.inv().apply(rest[d+'_01_l'][:3, 3] - rest['hand_l'][:3, 3])
                     for d in ('index', 'middle', 'pinky')]
    target_points = [target_hand.inv().apply(body.tp[body.ix[d+'_01_l']] - body.tp[body.ix['hand_l']])
                     for d in ('index', 'middle', 'pinky')]
    a, b = source_points, target_points
    mount = combo.frame(b[1], b[0]-b[2]) * combo.frame(a[1], a[0]-a[2]).inv()
    transfer = target_hand * mount * R.from_matrix(pose['hand_l'][:3, :3]).inv()
    desired = {}
    for digit in ('thumb', 'index', 'middle', 'ring', 'pinky'):
        chain = [f'{digit}_{j:02d}_l' for j in range(1, 4)]
        for j, name in enumerate(chain):
            left, right = (j, j+1) if j < 2 else (1, 2)
            source_axis = R.from_matrix(rest[name][:3, :3]).inv().apply(
                rest[chain[right]][:3, 3] - rest[chain[left]][:3, 3])
            i = body.ix[name]
            native_axis = R.from_quat(body.tq[i]).inv().apply(
                body.tp[body.ix[chain[right]]] - body.tp[body.ix[chain[left]]])
            desired[i] = transfer * R.from_matrix(pose[name][:3, :3]) * combo.align(native_axis, source_axis)
    fist = body.ref[None].copy()
    body.set_world_rotations(fist, {i: R.from_quat(q.as_quat()[None]) for i, q in desired.items()})
    # Native MetaHuman half-joint helpers counter-rotate with the bent digit.
    for i, name in enumerate(body.names):
        parent = body.parents[i]
        if name.endswith('_l') and '_half_' in name and parent in desired:
            delta = R.from_quat(body.ref[parent, 3:7]).inv() * R.from_quat(fist[0, parent, 3:7])
            half = R.from_rotvec(-.5 * delta.as_rotvec())
            fist[0, i, 3:7] = (half * R.from_quat(body.ref[i, 3:7])).as_quat()
    return fist[0]


def author():
    source = json.loads(FIST_SOURCE.read_text())
    cfg = json.loads((ROOT/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
    receipt = dict(source=str(FIST_SOURCE.relative_to(ROOT)), bodies={}, runtime_tested=False, rendered=False)
    for label, data in combo.INPUT['targets'].items():
        body = combo.Body(data)
        baseline = json.loads((BASE/(label+'-actions.json')).read_text())
        clip = baseline['clips']['Thrust']
        frames = np.asarray(clip['frames'])
        fist = native_fist(body, source)
        times = np.arange(len(frames))/clip['rate']
        driven = []
        for i, name in enumerate(body.names):
            digit = name.split('_')[0]
            if not name.endswith('_l') or digit not in ('thumb', 'index', 'middle', 'ring', 'pinky'):
                continue
            # Fingers close into the chamber; the thumb settles across them.
            delay = {'index': .02, 'middle': .012, 'ring': .006, 'pinky': 0., 'thumb': .045}[digit]
            weight = combo.ease((times-delay)/.17) * (1-combo.ease((times-.68)/.40))
            frames[:, i, 3:7] = combo.slerp(frames[:, i, 3:7], fist[i, 3:7], weight[:, None])
            driven.append(name)
        clip['frames'] = frames.tolist()
        clip['source'] = str((BASE/(label+'-actions.json')).relative_to(ROOT))+' / Thrust + '+str(FIST_SOURCE.relative_to(ROOT))
        clip['adaptation'] = 'Left closed guard fist; native anatomical digit transfer, opposed thumb and half-joint helpers; staggered closure and recovery. Existing wrist/arm/blade/body and contact clock retained.'
        result = dict(mesh=data['mesh'], names=data['names'], parents=data['parents'], clips={'Thrust': clip})
        (OUT/(label+'-actions.json')).write_text(json.dumps(result, separators=(',', ':')))
        active = cfg if label == 'jason' else cfg['body_variants'][label]
        receipt['bodies'][label] = dict(mesh=data['mesh'], previous_thrust=active['clips']['Kukri.FullBody.Thrust'],
            source_thrust=baseline['clips']['Thrust']['source'], edited_bones=driven, frames=len(frames), rate=clip['rate'],
            seconds=(len(frames)-1)/clip['rate'], fingers_closed_by=.215, relax_start=.68, relax_end=1.08)
        print('KUKRI_THRUST_FIST_AUTHORED '+label, flush=True)
    (OUT/'authoring.json').write_text(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    author()
