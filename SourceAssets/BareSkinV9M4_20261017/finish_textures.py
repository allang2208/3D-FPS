"""Final UE texture files (Textures/): DirectX normal (G flipped), colour and masks copied as authored."""
import json, shutil, hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from m4data import R

W = R / 'Work'; OUT = R / 'Textures'; OUT.mkdir(exist_ok=True)
n = np.asarray(Image.open(W / 'normal_gl16.png').convert('RGB')).astype(np.float32) / 255
n[..., 1] = 1 - n[..., 1]
Image.fromarray(np.round(n * 255).astype(np.uint8), 'RGB').save(OUT / 'T_M4SkinV9_Normal.png')
for name in ('T_M4SkinV9_Colour.png', 'T_M4SkinV9_Masks.png'): shutil.copy2(W / name, OUT / name)
rows = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob('*.png'))}
(OUT / 'textures.json').write_text(json.dumps(dict(files=rows, normal='DirectX (green flipped from the Blender OpenGL bake)',
                                                  masks='R ambient occlusion, G roughness, B cavity, A scatter amount',
                                                  colour='sRGB albedo', uv='UV0 (V9 unwrap)'), indent=1))
print('TEXTURES', rows)
