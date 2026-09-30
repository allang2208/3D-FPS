"""Check the baked accessory masks before use (plain CPython). Writes Bake/accessory_mask_qa.json.

A mask is used only if few island texels are fully occluded (cavity ~1 with AO ~0) and the
mean AO over the islands stays plausible. Some grips (inward-facing or doubled shells) come
out mostly black; those fall back to the neutral mask rather than darkening the part.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).parent
MAX_OCCLUDED, MIN_AO = 0.17, 0.45
qa = {}
for f in sorted((HERE / 'Bake' / 'Accessories').glob('T_A762_*_WS_Mask.png')):
    a = np.asarray(Image.open(f)).astype(np.float64) / 255
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    island = (R > 0.01) | (G > 0.01) | (B > 0.01)
    occluded = float(((G > 0.8) & (B < 0.15))[island].mean())
    ao = float(B[island].mean())
    qa[f.stem] = {'island_share': round(float(island.mean()), 3), 'occluded_share': round(occluded, 3),
                  'ao_mean': round(ao, 3), 'use': occluded < MAX_OCCLUDED and ao > MIN_AO}
    print(f.stem.ljust(40), qa[f.stem])
(HERE / 'Bake' / 'accessory_mask_qa.json').write_text(json.dumps(qa, indent=1), encoding='utf-8')
