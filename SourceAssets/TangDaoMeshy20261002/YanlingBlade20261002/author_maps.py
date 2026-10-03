"""Author the steel body's physical 4K PBR atlas; retain the root's original atlas."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
P = Path(__file__).resolve().parent
OUT = P / 'Textures'
OUT.mkdir(exist_ok=True)
N = 4096

def smooth(a, b, q):
    t = np.clip((q - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def height(x, z):
    phase = x * 1740 + z * 19 + .95 * np.sin(z * 31 + x * 44) + .31 * np.sin(z * 87 - x * 115)
    layers = 2.6e-6 * np.sin(phase * np.pi * 2) + 1.1e-6 * np.sin(phase * 2.37 * np.pi * 2)
    grind = .45e-6 * np.sin(x * np.pi * 2 / .00021 + .6 * np.sin(z * 93))
    return layers + grind

base = np.empty((N, N, 3), dtype=np.uint8)
orm = np.empty_like(base)
normal = np.empty_like(base)
u = (np.arange(N, dtype=np.float32) + .5)[None, :] / N
front = u < .5
t = np.clip(np.where(front, (u - .02) / .46, (.98 - u) / .46), 0, 1)
x = t * .061
edge = 1 - smooth(.23, .34, t)
groove = np.maximum(np.exp(-((t - .64) / .026) ** 4), np.exp(-((t - .80) / .026) ** 4))
for first in range(0, N, 128):
    last = min(first + 128, N)
    v = 1 - (np.arange(first, last, dtype=np.float32) + .5)[:, None] / N
    z = .34 + v * .54
    gate = smooth(.405, .438, z) * (1 - smooth(.745, .785, z))
    waves = x * 1740 + z * 19 + .95 * np.sin(z * 31 + x * 44) + .31 * np.sin(z * 87 - x * 115)
    grain = .55 * np.sin(waves * np.pi * 2) + .28 * np.sin(waves * np.pi * 2 * 2.37)
    soft = np.sin(x * 310 + z * 23 + np.sin(z * 13))
    blend = smooth(.34, .405, z)
    panel = (.50 * (1 - blend) + .355 * blend) * (1 + .085 * grain + .035 * soft)
    polish = .61 + .026 * np.sin((x * .24 + z) * np.pi * 2 / .0014)
    brightness = panel * (1 - edge) + polish * edge
    brightness *= 1 - .14 * groove * gate
    linear = brightness[..., None] * np.array([.97, 1.0, 1.025], np.float32)
    encoded = np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)
    base[first:last] = np.rint(np.clip(encoded, 0, 1) * 255).astype(np.uint8)
    rough = .295 + .018 * grain + .018 * soft - .12 * edge + .095 * groove * gate
    ambient = 1 - .14 * groove * gate
    orm[first:last] = np.rint(np.stack([ambient, np.clip(rough, .155, .44), np.ones_like(ambient)], -1) * 255).astype(np.uint8)
    eps = .000008
    dx = (height(x + eps, z) - height(x - eps, z)) / (2 * eps)
    dz = (height(x, z + eps) - height(x, z - eps)) / (2 * eps)
    strength = 1 - .70 * edge
    dx *= strength * np.where(front, 1, -1)
    dz *= strength
    n = np.stack([-dx, -dz, np.ones_like(dx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    normal[first:last] = np.rint(np.clip(n * .5 + .5, 0, 1) * 255).astype(np.uint8)
for key, values in [('BaseColor', base), ('ORM', orm), ('Normal', normal)]:
    Image.fromarray(values).save(OUT / ('TangDao_Yanling_' + key + '.png'))
(P / 'surface_recipe.json').write_text(json.dumps({
    'resolution': [N, N], 'uv_channel': 0, 'steel_atlas': 'two sides at physical blade scale',
    'root': 'Existing TangDao SurfaceV2 geometry, UV, normal, dragon/cloud detail and material retained',
    'orm_channels': ['ambient_occlusion', 'roughness', 'metallic'],
    'normal_convention': 'OpenGL; Unreal import flips green',
    'forged_layer_relief_micrometres': [2.6, 1.1], 'grind_pitch_mm': .21,
    'cutting_edge_roughness': [.155, .20], 'body_roughness': [.25, .35],
    'fullers': 'Geometry supplies depth; atlas supplies conservative AO and roughness',
    'runtime_tested': False
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('YANLING_4K_PBR_AUTHORED', flush=True)
