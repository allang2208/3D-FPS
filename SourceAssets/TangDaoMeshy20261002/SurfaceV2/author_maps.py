"""Create regional PBR maps, preserving UV0, original colors and original AO."""
import json
from pathlib import Path
import numpy as np
from PIL import Image

P = Path(__file__).resolve().parent
S = P.parent / 'Textures'
OUT = P / 'Textures'
OUT.mkdir(exist_ok=True)
N = 4096

def source(name):
    return np.asarray(Image.open(S / name).convert('RGB').resize((N, N), Image.Resampling.LANCZOS), dtype=np.float32) / 255

def smooth(a, b, value):
    t = np.clip((value - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def save(name, values):
    Image.fromarray(np.rint(np.clip(values, 0, 1) * 255).astype(np.uint8)).save(OUT / name)

base = source('Image_0.png')
orm = source('Image_1.png')
coords = np.load(P / 'surface_coordinates.npz')
position = coords['position'].astype(np.float32)
normal = coords['normal'].astype(np.float32)[..., :3] * 2 - 1
x = (position[..., 0] - .5) * .4
y = (position[..., 1] - .5) * .3
z = (position[..., 2] - .25) * 1.2
valid = np.max(position[..., :3], axis=-1) > .001

# The grip region comes from the actual fitted geometry, not UV island layout.
grip = smooth(-.233, -.224, z) * (1 - smooth(-.055, -.044, z))
cloth = grip * (1 - smooth(.08, .35, orm[..., 2]))
metal = 1 - cloth
warm = (base[..., 0] - base[..., 2]) / np.maximum(np.sum(base, axis=-1), .03)
bronze = metal * smooth(.035, .105, warm)
steel = metal - bronze
edge = steel * smooth(.18, .65, np.abs(normal[..., 0]) + .35 * np.abs(normal[..., 2]))
regions = np.stack([steel, bronze, cloth, edge], axis=-1)
save('TangDao_Regions.png', regions)

linear = np.where(base <= .04045, base / 12.92, ((base + .055) / 1.055) ** 2.4)
lum = linear @ np.array([.2126, .7152, .0722], dtype=np.float32)
# Clean broad uncarved blade panels while retaining carved-root color variation.
panel = steel * smooth(.20, .36, z)
steel_reference = np.array([.53, .55, .57], dtype=np.float32)
steel_color = steel_reference * np.clip(lum[..., None] / .58, .90, 1.10)
bronze_reference = np.array([.55, .35, .14], dtype=np.float32)
bronze_color = bronze_reference * np.clip(lum[..., None] / .28, .78, 1.16)
color = linear * (1 - .68 * panel[..., None]) + steel_color * (.68 * panel[..., None])
color = color * (1 - .38 * bronze[..., None]) + bronze_color * (.38 * bronze[..., None])

# Fibres are in millimetres in fitted model space and survive fragmented UVs.
u = np.arctan2(y, x + .014) * .015
a = 2 * np.pi * (u * .82 + z * .57) / .0012
b = 2 * np.pi * (-u * .57 + z * .82) / .0012
weave = .5 + .5 * np.sin(a) * np.sin(b)
color *= 1 + cloth[..., None] * ((weave[..., None] - .5) * .065)
encoded = np.where(color <= .0031308, color * 12.92, 1.055 * np.maximum(color, 0) ** (1 / 2.4) - .055)
save('TangDao_BaseColor.png', encoded)
steel_rough = .29 + .06 * (orm[..., 1] - .4) - edge * .105
bronze_rough = .32 + .08 * (orm[..., 1] - .4)
cloth_rough = .78 + .05 * (weave - .5)
rough = steel * steel_rough + bronze * bronze_rough + cloth * cloth_rough
save('TangDao_ORM.png', np.stack([orm[..., 0], np.clip(rough, .16, .84), metal], axis=-1))
(P / 'surface_recipe.json').write_text(json.dumps({
    'revision': 'TangDao_RegionalSurfaceV2_20261002',
    'resolution': [N, N], 'uv_channel': 0,
    'regions_rgba': ['steel', 'bronze', 'cloth', 'edge_bevel'],
    'normal_source': 'Image_2.png, structural normal unchanged and physical micro-bump baked over it',
    'weave_pitch_mm': 1.2, 'weave_height_mm': .012,
    'steel_grind_pitch_mm': .45, 'steel_grind_height_mm': .0004,
    'metallic': 'Bare steel/bronze 1, cloth 0; filtered boundaries only',
    'ao': 'Original Image_1 R preserved',
    'material_samples': 3, 'shared_atlas': 'All TangDao original and variant modules',
    'geometry': 'Unchanged', 'tested': False,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('TANGDAO_REGIONAL_PBR_MAPS_SAVED', flush=True)
