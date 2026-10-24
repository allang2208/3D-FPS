"""Match the accepted V9 surface palette to the native female forearm albedo."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from body_surface_fit import regions

WORK = Path('D:/FPS3D/FPSGAME/SourceAssets/KaitlinPlayer20261023')
inputs = json.loads((WORK / 'ViewSkin/material_inputs.json').read_text())
body = json.loads((WORK / 'NativeGeometry/MHC_Kaitlin_Body.json').read_text())
uvs = json.loads((WORK / 'kaitlin_body_uv.json').read_text())['vertex_uvs']
female_file = inputs['kaitlin']['textures']['Basecolor Baked']['file']
v9_file = inputs['v9']['textures']['SkinColour']['file']
female = np.asarray(Image.open(female_file).convert('RGB'), float) / 255.
v9 = np.asarray(Image.open(v9_file).convert('RGB'), float) / 255.
points = np.asarray([uv for vertex in np.flatnonzero(np.isin(regions(body), ['lowerarm_l', 'lowerarm_r']))
                     for uv in uvs[str(vertex)]])
h, w = female.shape[:2]
samples = female[np.clip((points[:, 1] * h).astype(int), 0, h - 1),
                 np.clip((points[:, 0] * w).astype(int), 0, w - 1)]
v9_samples = v9.reshape(-1, 3)
# Exclude padding and non-skin texels when reducing the accepted atlas palette.
v9_samples = v9_samples[(v9_samples[:, 0] > .15) & (v9_samples[:, 0] > v9_samples[:, 1])
                       & (v9_samples[:, 1] > v9_samples[:, 2])]
linear = lambda values: np.where(values <= .04045, values / 12.92, ((values + .055) / 1.055) ** 2.4)
female_color = np.median(linear(samples), axis=0)
v9_color = np.median(linear(v9_samples), axis=0)
tint = female_color / v9_color
(WORK / 'ViewSkin/tint.json').write_text(json.dumps({
    'skin_tint_linear': tint.tolist(), 'female_albedo_linear': female_color.tolist(),
    'v9_albedo_linear': v9_color.tolist(), 'female_source': female_file, 'v9_source': v9_file,
    'surface_contract': 'V9 topology, weights, joint/grip/pose corrective morphs, normal and roughness retained'}, indent=2), encoding='utf-8')
print('KAITLIN_VIEW_SKIN_TINT_AUTHORED', tint.tolist(), flush=True)
