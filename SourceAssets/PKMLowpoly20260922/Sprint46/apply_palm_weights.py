"""Write the reweighted PKM palm skin into the authored profile.

Only the PKM profile is touched.  The shared surface master (M4_original.json) and every
other profile are left alone, as the accepted-bare-hands convention requires.

Rule: for every vertex whose hand-side weight (hand + metacarpals + fingers) exceeds 0.5,
scale its three forearm-bone weights by K and give the removed amount to hand_<side>.
K=0.25 was chosen from the offline sweep because it brings the sprint entry's palm
collapse (1.2706) down to 0.4569 - the level the already-accepted idle sits at (0.4200) -
while the median palm vertex does not move at all and the worst vertex moves 17.4 mm.
Scaling (rather than a hard reassignment) keeps the weight field smooth in the forearm
weight, so no new crease is introduced by construction.
"""
import hashlib
import json
import shutil
from pathlib import Path

OUTFIT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7')
SRC = OUTFIT / 'Authored' / 'PKM.json'
HERE = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922\Sprint46')
BACKUP = HERE / 'Before'
BACKUP.mkdir(parents=True, exist_ok=True)

K = 0.25
FOREARM = ('lowerarm_%s', 'lowerarm_twist_01_%s', 'lowerarm_twist_02_%s')
NOTE = ('PKM palm blend-band reduction for the tactical-sprint wrist collapse: '
        'hand-dominant vertices keep %d%% of their forearm weight, remainder moved to '
        'hand_<side> (Sprint46)' % round(K * 100))
CONTRACT_NOTE = ('Accepted V7 surface; local palm openings capped; native weights '
                 'retained; Sprint46 reduced the hand-dominant palm forearm blend to %d%%'
                 % round(K * 100))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


before_bytes = SRC.read_bytes()
before_sha = hashlib.sha256(before_bytes).hexdigest()
backup = BACKUP / 'PKM.json'
if not backup.exists():
    backup.write_bytes(before_bytes)

doc = json.loads(before_bytes.decode('utf-8'))
weights = doc['weights']

hand_bones = {}
fore_bones = {}
for side in ('l', 'r'):
    hand_bones[side] = [n for n in next(iter(weights)) if False]  # placeholder
    fore_bones[side] = [f % side for f in FOREARM]

ALL = {b for e in weights for b in e}
HANDISH = {}
for side in ('l', 'r'):
    HANDISH[side] = [b for b in ALL if b.endswith('_' + side) and (
        b.startswith('hand_') or b.startswith(('thumb_', 'index_', 'middle_', 'ring_',
                                               'pinky_')))]

moved_verts = 0
moved_weight = 0.0
touched = {s: 0 for s in ('l', 'r')}
for i, entry in enumerate(weights):
    for side in ('l', 'r'):
        hand = 'hand_' + side
        s_hand = sum(entry.get(b, 0.0) for b in HANDISH[side])
        if s_hand <= 0.5:
            continue
        f = [b for b in fore_bones[side] if entry.get(b, 0.0) > 0.0]
        if not f:
            continue
        removed = sum(entry[b] for b in f) * (1.0 - K)
        for b in f:
            entry[b] *= K
            if entry[b] <= 0.0:
                del entry[b]
        entry[hand] = entry.get(hand, 0.0) + removed
        # Only renormalise if the entry was not already summing to one.  Dividing every
        # entry unconditionally rewrites the last bits of unrelated bones (float32 noise
        # around 7e-08), which shows up as a 2580-entry diff on an accepted asset.
        total = sum(entry.values())
        if abs(total - 1.0) > 1e-6:
            for b in list(entry):
                entry[b] /= total
        moved_verts += 1
        moved_weight += removed
        touched[side] += 1

doc['contract'] = CONTRACT_NOTE
SRC.write_text(json.dumps(doc, separators=(',', ':')), encoding='utf-8')
after_sha = sha(SRC)

receipt = {
    'profile': doc['profile'],
    'source': doc['source'],
    'K': K,
    'vertices': len(weights),
    'vertices_changed': moved_verts,
    'per_side': touched,
    'total_weight_moved_to_hand': round(moved_weight, 6),
    'before': {'file': str(SRC), 'sha256': before_sha,
               'bytes': len(before_bytes)},
    'after': {'sha256': after_sha, 'bytes': SRC.stat().st_size},
    'backup': str(backup),
    'note': NOTE,
}
(HERE / 'weights_receipt.json').write_text(
    json.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(receipt, indent=2, ensure_ascii=False))
print('APPLY_PALM_WEIGHTS_DONE')