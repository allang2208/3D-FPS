"""Pack WS1 structure masks and extend baked islands for mip-safe sampling."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

O = Path(__file__).parent
receipt = json.loads((O / 'bake_receipt.json').read_text())
result = {'complete': False, 'mask_channels': 'R=0, G=cavity, B=AO, A=exposure', 'parts': {}}
for part, row in receipt['objects'].items():
    rough_path = Path(row['outputs']['Roughness'])
    rough = np.asarray(Image.open(rough_path).convert('L')).copy()
    ao = np.asarray(Image.open(row['outputs']['AO']).convert('L')).copy()
    # Roughness is a strictly positive face attribute; zero denotes empty atlas.
    valid = rough > 0
    if not valid.any():
        raise RuntimeError('Roughness attribute bake is empty: ' + part)
    nearest = distance_transform_edt(~valid, return_distances=False, return_indices=True)
    rough[~valid] = rough[tuple(nearest[:, ~valid])]
    ao[~valid] = ao[tuple(nearest[:, ~valid])]
    Image.fromarray(rough).save(rough_path)
    mask = np.stack([np.zeros_like(ao), 255 - ao, ao, ao], axis=-1)
    mask_path = O / 'Textures' / f'T_SVCH_R8_{part}_SurfaceMask.png'
    Image.fromarray(mask).save(mask_path)
    result['parts'][part] = {'roughness': str(rough_path), 'surface_mask': str(mask_path),
                             'normal': row['outputs']['Normal'], 'cm_per_uv': row['cm_per_uv']}
result['complete'] = True
(O / 'texture_receipt.json').write_text(json.dumps(result, indent=2))
print('SVCH_R8_MASKS_PACKED', len(result['parts']))
