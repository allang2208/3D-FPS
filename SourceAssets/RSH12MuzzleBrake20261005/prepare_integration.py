"""Prepare the approved brake's WS texture channels without changing its source model."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

O = Path(__file__).resolve().parent
auth = json.loads((O / 'authoring.json').read_text(encoding='utf8'))
for part, spec in auth['textures'].items():
    orm = np.array(Image.open(O / spec['orm']).convert('RGB'))
    rough = O / 'Textures' / f'T_RSH12_Brake_{part}_Roughness.png'
    mask = O / 'Textures' / f'T_RSH12_Brake_{part}_SurfaceMask.png'
    Image.fromarray(orm[:, :, 1]).save(rough)
    channels = np.zeros((*orm.shape[:2], 4), dtype=np.uint8)
    channels[:, :, 2] = orm[:, :, 0]
    channels[:, :, 3] = 255
    Image.fromarray(channels).save(mask)
    spec['roughness_texture'] = str(rough.relative_to(O))
    spec['surface_mask'] = str(mask.relative_to(O))
(O / 'integration_inputs.json').write_text(json.dumps({
    'textures': auth['textures'],
    'muzzle_tip_cm': [v * 100 for v in auth['interface']['muzzle_exit_local_m']],
    'mount': 'Preserve current RSH12MuzzleAssets::Mount; same authored coordinate frame',
    'runtime_tested': False,
}, indent=2), encoding='utf8')
print('RSH_BRAKE_INTEGRATION_INPUTS_SAVED')
