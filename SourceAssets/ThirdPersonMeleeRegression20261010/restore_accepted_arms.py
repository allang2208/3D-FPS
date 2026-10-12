"""Recover the accepted Kwang performance; do not rerun the V3 elbow optimizer.

Preserve the complete V2 arm chains, including Jason skin-support bones. V3's
wrist-swing objective rotated the elbow plane too far and changed those helpers.
The authored sample rate is finalized by the UE save step, independently of pose.
"""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
source = OUT.parent/'ThirdPersonSwordKwang20261006/adapted-actions.json'
accepted = json.loads(source.read_text())
accepted['recovery_source'] = str(source)
accepted['recovery_source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
accepted['provenance'] += '; 20261010 accepted arm-chain recovery; no elbow reoptimization'
for clip in accepted['clips'].values():
    # Runtime still supports V3 assets elsewhere; this recovery uses the
    # accepted fixed grip frame and therefore needs no inverse shaft roll.
    clip['curves'] = {'SwordGripRoll': [0.] * len(clip['frames'])}
(OUT/'adapted-actions.json').write_text(json.dumps(accepted, separators=(',', ':')))
print('ACCEPTED_ARM_SOURCE_READY ' + str(OUT/'adapted-actions.json'))
