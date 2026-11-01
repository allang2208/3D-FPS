"""Pack native UV0 masks and the authored guard-carrier region; no image synthesis."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

P = Path(__file__).resolve().parent
SOURCE = P.parent / 'RuneSwordVisualPolish20260922'
data = np.load(SOURCE / 'surface_mapping.npz')
cover = data['guard_coverage']
x, y, z = np.moveaxis(data['guard_xyz'], -1, 0)
# Same native carrier retained by BOTH Meshy guard author_model.py recipes.
# The original guard variants deform only beyond |X|=7.2 cm, outside this mask.
region = cover & (z >= .040) & (np.abs(x) <= .052)
coverage = region.astype(np.float32)
distance, near = ndi.distance_transform_edt(~cover, return_indices=True)
pad = (~cover) & (distance <= 8)
coverage[pad] = coverage[near[0][pad], near[1][pad]]
blade_ink = np.asarray(Image.open(SOURCE / 'T_RuneSword_NativeMask.png'))[:, :, 0]
guard_ink = np.asarray(Image.open(SOURCE / 'T_RuneSword_GuardNativeMask.png'))[:, :, 0]
packed = np.stack((blade_ink, guard_ink, np.uint8(coverage * 255)), axis=-1)
Image.fromarray(packed).save(P / 'T_RuneSword_FullBladeFinishMask.png')
(P / 'mask-source.json').write_text(json.dumps({
    'source': str(SOURCE / 'surface_mapping.npz'),
    'channels': {'R': 'blade native ink', 'G': 'guard native ink', 'B': 'guard blade-root carrier'},
    'carrier_bounds_m': {'min_z': .040, 'abs_x_max': .052},
    'uv_padding_pixels': 8,
    'note': 'Meshy join caps are buried inside the assembly and retain their separate join material.'
}, indent=2) + '\n', encoding='utf8')
print('FULL_BLADE_FINISH_MASK_BAKED')
