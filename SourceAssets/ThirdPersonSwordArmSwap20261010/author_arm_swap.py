"""Exchange upper/lower sword grips while retaining each hand's own orientation."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE = ROOT / 'SourceAssets/ThirdPersonSwordGripPair20261010/candidate-actions.json'
helper = ROOT / 'SourceAssets/ThirdPersonSwordGrip20261007/refine_kwang_grip.py'
ns = {'__file__': str(helper)}
exec(compile(helper.read_text().split('clips={}')[0], str(helper), 'exec'), ns)

data = json.loads(SOURCE.read_text())
fk, rot, unit, compose = ns['fk'], ns['rot'], ns['unit'], ns['compose']
report = {'authoring_only': True, 'source': str(SOURCE), 'clips': {}}
for label, clip in data['clips'].items():
    result, slides = [], []
    for i, frame in enumerate(np.asarray(clip['frames'])):
        world = fk(frame)
        weapon = compose(compose(world[ns['ix']['hand_r'], :7], ns['hand_to_weapon']),
            np.r_[0., 0., 0., ns['axis']([0, 0, 1], -math.radians(clip['curves']['SwordGripRoll'][i]))])
        shaft = rot(weapon[3:7], np.array([0., 0., 1.]))
        right, left = (world[ns['ix']['hand_' + side], :7] for side in ('r', 'l'))
        # Exchange their actual heights on the handle. Do not copy opposite-side
        # local rotations: Jason's left and right bones have different rest axes.
        slide = float(np.dot(left[:3] - right[:3], shaft))
        revised = frame.copy()
        for side, displacement in (('r', slide), ('l', -slide)):
            a, b, c = ns['arms'][side]
            l1, l2 = ns['lengths'][side]
            hand = world[c, :7].copy()
            hand[:3] += shaft * displacement
            shoulder, wrist = world[a, :3], hand[:3]
            ray = unit(wrist - shoulder)
            distance = float(np.linalg.norm(wrist - shoulder))
            if not abs(l1 - l2) + .01 < distance < l1 + l2 - .01:
                raise RuntimeError(f'{label} frame {i}: {side} exchanged grip exceeds native reach')
            along = (l1*l1 - l2*l2 + distance*distance) / (2*distance)
            pole = unit(world[b, :3] - shoulder - ray * np.dot(world[b, :3] - shoulder, ray))
            elbow = shoulder + ray * along + pole * math.sqrt(max(0., l1*l1 - along*along))
            ns['fit'](revised, world, side, hand, elbow)
        result.append(revised.tolist())
        slides.append(slide)
    clip['frames'] = result
    # Runtime cancels the owning right hand's axial displacement at the native
    # weapon pivot, using the same action blend as the arm pose.
    clip['curves']['SwordGripSlide'] = slides
    report['clips'][label] = {'frame_count': len(result), 'rate': clip['rate'],
        'right_slide_cm': slides[0], 'left_slide_cm': -slides[0],
        'grip_order': 'left near guard; right near pommel'}

data['provenance'] += '; exchange upper/lower grips: left guard, right pommel; preserve wrist orientations and blade path'
data['accepted_arms_sha256'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
report['source_sha256'] = data['accepted_arms_sha256']
report['preserved'] = 'body and legs, per-hand world orientation, finger pose, bone lengths, timing and blade trajectory'
report['changed'] = 'both arm chains and twist/corrective roots; SwordGripSlide compensates the right-hand mount'
(OUT / 'candidate-actions.json').write_text(json.dumps(data, separators=(',', ':')))
(OUT / 'arm-swap-authoring.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))
