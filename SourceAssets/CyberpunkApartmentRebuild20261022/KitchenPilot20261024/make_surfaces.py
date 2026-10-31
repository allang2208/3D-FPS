"""Original, deterministic kitchen PBR textures. No downloaded image sources.

DirectX tangent-space normals are derived from authored physical height fields.
The preview material flips G to Blender/OpenGL; the PNG remains UE-compatible.
"""
from pathlib import Path
import json
import numpy as np
import zlib,struct

def write_png(path,pixels):
    """Small lossless RGB PNG writer; also works in the background Blender runtime."""
    raw=b''.join(b'\x00'+pixels[i].tobytes() for i in range(pixels.shape[0]))
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    h,w=pixels.shape[:2]
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b''))

R = Path(__file__).resolve().parent
OUT = R / 'TexturesV2'
OUT.mkdir(exist_ok=True)
S = 2048
rng = np.random.default_rng(241024)
y, x = np.mgrid[0:S, 0:S].astype(np.float32) / S

def noise(scale, samples=16):
    result = np.zeros((S, S), np.float32)
    for _ in range(samples):
        a, b = rng.integers(max(1, scale // 4), scale + 1, 2)
        phase = rng.uniform(0, 2 * np.pi)
        result += np.sin(2 * np.pi * (a * x + b * y) + phase).astype(np.float32) / samples
    return result

low, mid, fine = noise(8), noise(70), noise(410)
grain = rng.random((S, S), dtype=np.float32) - .5
records = []

def save(key, height, color, rough, period, metal=0, ao=None):
    # Height in metres, period in metres: the derivative has a physical basis.
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / (2 * period / S)
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) / (2 * period / S)
    normal = np.stack([-dx, dy, np.ones_like(dx)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    srgb = np.where(color <= .0031308, color * 12.92, 1.055 * np.clip(color, 0, 1) ** (1 / 2.4) - .055)
    packed = np.stack([np.ones_like(x) if ao is None else ao, rough, np.full_like(x, metal)], axis=-1)
    for suffix, pixels in [('BC', srgb), ('N', normal * .5 + .5), ('ORM', packed)]:
        write_png(OUT / f'T_KP_{key}_{suffix}.png', np.round(np.clip(pixels, 0, 1) * 255).astype(np.uint8))
    records.append(dict(family=key, size=S, period_m=period, height_peak_to_peak_mm=round(float(np.ptp(height) * 1000), 5),
                        source='Original analytical PBR surface; not a photo scan', normal_green='DirectX',
                        normal_xy_rms=round(float(np.sqrt(np.mean(normal[:, :, :2] ** 2))), 5)))

# Apartment graphite powder coat: neutral charcoal, subtle orange peel only.
h = (mid * .20 + fine * .10) * .000014
base = np.array([.047, .050, .055])
variation = low * .055 + fine * .012
save('PetrolEnamel', h, base[None, None, :] * (1 + variation[:, :, None]), .42 + mid * .065, .38)

# Graphite honed stone: restrained mineral grain and sparse, shallow pores.
pores = np.maximum(0, grain - .475) * 1.0
h = (mid * .13 + fine * .12 - pores * .30) * .000045
base = np.array([.145, .151, .158])
variation = low * .09 + fine * .028 - pores * .14
save('HonedStone', h, base[None, None, :] * (1 + variation[:, :, None]), .46 + mid * .095 + pores * .07, .55)

# Individual ceramic tiles with recessed grout and a shallow pillowed edge.
tx, ty = x * 6, y * 3
fx, fy = tx % 1, ty % 1
edge = np.minimum(np.minimum(fx, 1-fx) * .1, np.minimum(fy, 1-fy) * .3)
edge_factor = np.clip(edge / .0015, 0, 1)
grout = 1 - edge_factor
height = (edge_factor * .0012 + fine * .000011) * (1 - grout * .4)
tile_color = np.array([.270, .282, .298])
var = low * .10 + fine * .025
bc = tile_color[None, None, :] * (1 + var[:, :, None])
bc = bc * (1 - grout[:, :, None]) + np.array([.037, .039, .042]) * grout[:, :, None]
rough = (.28 + mid * .08) * (1-grout) + .90 * grout
save('GlazedTile', height, bc, rough, .60, ao=1-grout*.2)

# Directional brushed steel. Grain is much finer than the visible cabinet edges.
brushing = np.sin((y * 940 + mid * 1.7) * 2*np.pi) * .18 + fine * .12
h = brushing * .000007
color = np.array([.42, .435, .450])[None, None, :] * (1 + low[:, :, None] * .025 + fine[:, :, None] * .014)
save('BrushedSteel', h, color, .30 + brushing * .07, .36, metal=1)

# Smoked walnut, lengthwise fibres with occasional narrow pores.
phase = x * 68 + np.sin(y * 8) * .32 + mid * .18
fibres = np.sin(phase * 2*np.pi) * .18 + np.sin(phase * .247 * 2*np.pi) * .23 + fine * .1
h = fibres * .00005
color = np.array([.073, .066, .057])[None, None, :] * (1 + fibres[:, :, None] * .45)
save('SmokedWalnut', h, color, .45 + fibres * .1, .80)

# Tight towel weave; both warp and weft are visible at close range.
warp = np.cos((x * 192 + .16*np.sin(y*24)) * 2*np.pi)
weft = np.cos((y * 192 + .16*np.sin(x*24)) * 2*np.pi)
h = (warp + weft) * .00012 + fine * .000035
color = np.array([.30, .315, .330])[None, None, :] * (1 + (warp+weft)[:, :, None] * .065 + low[:, :, None] * .05)
save('LinenTowel', h, color, .83 + fine * .05, .22)

# White glazed porcelain, deliberately much smoother than the tile grout.
h = (mid * .12 + fine * .10) * .000014
color = np.array([.64, .655, .67])[None, None, :] * (1 + low[:, :, None] * .017)
save('Porcelain', h, color, .24 + fine * .04, .25)

(R / 'texture-source.json').write_text(json.dumps(dict(size=S, textures=records), indent=2), encoding='utf8')
print('KITCHEN_PBR_WRITTEN', len(records), 'families; BC/N/ORM', S)
