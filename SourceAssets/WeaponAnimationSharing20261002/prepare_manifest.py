"""Prepare the Pit Viper delta batch from its current authoring recipe."""
from pathlib import Path
import json

PROJECT = Path('D:/FPS3D/FPSGAME')
JOB = Path(__file__).parent
WEAPON = 'ue_pit_viper2011'
ROOT = '/Game/Weapons/PitViper2011/Integrated20261002'
PROFILE_ROOT = '/Game/Weapons/AnimationProfiles20261001/' + WEAPON
ROLES = ('quickcombat', 'quickcombat_empty', 'quickcombat_left', 'quickcombat_left_empty')
profiles = []
for side in ('r', 'l'):
    recipe = json.loads((PROJECT / 'SourceAssets/PitViper2011Integration20261002/Dual'
                         / side / 'authoring.json').read_text(encoding='utf-8'))
    stem = 'Dual_PitViper2011_' + side
    prefix = f'{ROOT}/Dual/{side}/Animations/A_{stem}_'
    for family in ('fitted', 'long'):
        pairs = []
        for role in ROLES:
            variant = role.removesuffix('_empty') + '_' + family + ('_empty' if role.endswith('_empty') else '')
            # These are the current exported authoring inputs, not old donor paths.
            recipe['clips'][role]
            recipe['clips'][variant]
            pairs.append(dict(role=role, base=prefix + role, authored=prefix + variant))
        profiles.append(dict(weapon=WEAPON + '/Dual_' + side, family=family,
                             author='WeaponAnimationSharing20261002',
                             mesh=f'{ROOT}/Dual/{side}/SK_{stem}',
                             asset=f'{PROFILE_ROOT}/Dual_{side}/DA_{family}', pairs=pairs))
(JOB / 'manifest.json').write_text(json.dumps(dict(profiles=profiles), indent=2), encoding='utf-8')
print('ANIMATION_SHARING_MANIFEST', len(profiles), 'profiles', sum(len(s['pairs']) for s in profiles), 'pairs')
