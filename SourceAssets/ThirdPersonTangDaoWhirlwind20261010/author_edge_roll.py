"""Adapt the mounted Tang Dao edge without rebuilding the accepted arm chains."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
SOURCE = ROOT / 'SourceAssets/ThirdPersonMeleeRegression20261010/adapted-actions.json'
data = json.loads(SOURCE.read_text())
result = {
    'source_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'source': str(SOURCE),
    'weapon': 'ue_tang_dao',
    'turn_degrees': 720,
    'description': 'Tang Dao mounted edge is +X in WPN_root; Kwang positive-yaw cut uses -X. '
                   'Roll the round-grip weapon frame during windup, hold through both turns, '
                   'return during late recovery. Preserve all accepted bone tracks.',
    'clips': {},
}

def ease(t):
    t = min(1., max(0., t))
    return t*t*t*(t*(t*6.-15.)+10.)

for phase in ('Start', 'Loop', 'End'):
    take = data['clips']['Whirlwind.' + phase]
    length = (len(take['frames'])-1) / take['rate']
    count = round(length * 120)
    values = []
    for i in range(count+1):
        p = i/count
        weight = ease(p/.85) if phase == 'Start' else 1.-ease((p-.60)/.40) if phase == 'End' else 1.
        # The existing mount consumer applies -SwordGripRoll about WPN_root Z.
        # A fixed half turn retains both axial hand seats on the round handle.
        values.append(-180.*weight)
    result['clips'][phase] = {
        'source_asset': '/Game/Characters/JasonPlayer20261003/KwangSwordRecovery20261010/Animations/J_Kwang_Whirlwind_' + phase,
        'destination': '/Game/Characters/JasonPlayer20261003/TangDaoWhirlwind20261010/Animations/J_TangDao_Whirlwind_' + phase,
        'config_key': 'Melee.FullBody.TangDao.Whirlwind.' + phase,
        'times': [i*length/count for i in range(count+1)],
        'SwordGripRoll': values,
    }
(OUT / 'edge-roll.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('TANG_DAO_WHIRLWIND_AUTHORED ' + ', '.join(result['clips']))
