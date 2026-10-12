"""Seat the exchanged upper left grip below the Tang Dao handle's upper rim."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE = ROOT / 'SourceAssets/ThirdPersonSwordArmSwap20261010/candidate-actions.json'
helper = ROOT / 'SourceAssets/ThirdPersonSwordGrip20261007/refine_kwang_grip.py'
ns = {'__file__': str(helper)}
exec(compile(helper.read_text().split('clips={}')[0], str(helper), 'exec'), ns)
data = json.loads(SOURCE.read_text())
fk, compose, rot, unit = ns['fk'], ns['compose'], ns['rot'], ns['unit']
left_slide_cm = -2.4
a, b, c = ns['arms']['l']
l1, l2 = ns['lengths']['l']
for clip in data['clips'].values():
    result = []
    for i, frame in enumerate(np.asarray(clip['frames'])):
        world = fk(frame)
        correction = np.r_[0., 0., -clip['curves']['SwordGripSlide'][i],
            ns['axis']([0, 0, 1], -math.radians(clip['curves']['SwordGripRoll'][i]))]
        weapon = compose(compose(world[ns['ix']['hand_r'], :7], ns['hand_to_weapon']), correction)
        hand = world[c, :7].copy()
        hand[:3] += rot(weapon[3:7], np.array([0., 0., left_slide_cm]))
        shoulder = world[a, :3]
        ray = unit(hand[:3] - shoulder)
        distance = float(np.linalg.norm(hand[:3] - shoulder))
        if not abs(l1 - l2) + .01 < distance < l1 + l2 - .01:
            raise RuntimeError(f'Left grip exceeds native reach at frame {i}')
        along = (l1*l1 - l2*l2 + distance*distance) / (2*distance)
        pole = unit(world[b, :3] - shoulder - ray * np.dot(world[b, :3] - shoulder, ray))
        elbow = shoulder + ray * along + pole * math.sqrt(max(0., l1*l1 - along*along))
        revised = frame.copy()
        ns['fit'](revised, world, 'l', hand, elbow)
        result.append(revised.tolist())
    clip['frames'] = result

data['accepted_arms_sha256'] = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
data['provenance'] += '; upper left hand seated 2.4 cm toward pommel to place index grip below Tang Dao handle rim'
report = {'authoring_only': True, 'source': str(SOURCE),
    'source_sha256': data['accepted_arms_sha256'], 'left_slide_cm': left_slide_cm,
    'basis': 'current swift_grip spans shaft Z -22.7 to -5 cm; old upper-left index MCP is about -3.68 cm',
    'preserved': 'right arm and weapon mount curves, upper/lower hand order, left wrist world orientation, fingers, body and timing',
    'changed': 'left upperarm/lowerarm/hand rotations and twist/corrective roots',
    'clips': list(data['clips'])}
(OUT / 'candidate-actions.json').write_text(json.dumps(data, separators=(',', ':')))
(OUT / 'left-contact-authoring.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))
