"""Tileable earth-yellow camouflage canvas and leather PBR maps for the boonie.

All maps are authored in sRGB display values (BaseColor) or raw data
(Normal/ORM), 8-bit PNG.  The canvas repeat is 25 cm; the leather repeat is
12 cm.  Normals are OpenGL convention; UE flips green on import.

Canvas is 4K with a subdued three-tone earth camouflage print and a stronger
micro-weave normal; leather is 2K with finer grain.  Both are seamless.
"""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = Path("D:/FPS3D/FPSGAME/SourceAssets/FieldHat20261019")
TEX = ROOT / "Textures"
TEX.mkdir(parents=True, exist_ok=True)


def value_noise(size, cells, seed, octaves=4, persistence=0.55):
    rng = np.random.default_rng(seed)
    total = np.zeros((size, size), np.float32)
    amplitude = 1.0
    norm = 0.0
    for octave in range(octaves):
        n = max(2, int(round(cells * (2 ** octave))))
        while size % n:
            n += 1
        grid = rng.random((n, n)).astype(np.float32)
        y = np.arange(size, dtype=np.float32) * n / size
        x = np.arange(size, dtype=np.float32) * n / size
        y0 = np.floor(y).astype(np.int32) % n
        x0 = np.floor(x).astype(np.int32) % n
        y1 = (y0 + 1) % n
        x1 = (x0 + 1) % n
        fy = y - np.floor(y)
        fx = x - np.floor(x)
        fy = (fy * fy * (3 - 2 * fy))[:, None]
        fx = (fx * fx * (3 - 2 * fx))[None, :]
        a = grid[np.ix_(y0, x0)]
        b = grid[np.ix_(y0, x1)]
        c = grid[np.ix_(y1, x0)]
        d = grid[np.ix_(y1, x1)]
        total += ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy) * amplitude
        norm += amplitude
        amplitude *= persistence
    return total / max(norm, 1e-6)


def smoothstep(a, b, x):
    t = np.clip((x - a) / max(float(b - a), 1e-6), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ridged(noise, sharpness=2.0):
    ridge = 1.0 - np.abs(noise * 2.0 - 1.0)
    return np.power(np.clip(ridge, 0.0, 1.0), sharpness)


def normal_from_height(height, strength):
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(height)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack((nx / length, ny / length, nz / length), axis=-1)


def save_srgb(path, rgb):
    data = np.clip(rgb, 0.0, 1.0)
    Image.fromarray((data * 255.0 + 0.5).astype(np.uint8), "RGB").save(path, optimize=True)


def save_data(path, rgb):
    data = np.clip(rgb, 0.0, 1.0)
    Image.fromarray((data * 255.0 + 0.5).astype(np.uint8), "RGB").save(path, optimize=True)


def camouflage(size, seed):
    large = value_noise(size, 7, seed + 10, octaves=4)
    medium = value_noise(size, 15, seed + 11, octaves=3)
    detail = value_noise(size, 37, seed + 12, octaves=2)
    warp = value_noise(size, 5, seed + 13, octaves=3)
    field = 0.58 * large + 0.27 * medium + 0.15 * detail + 0.16 * (warp - 0.5)
    lo, hi = np.percentile(field, [2.0, 98.0])
    field = np.clip((field - lo) / max(float(hi - lo), 1e-6), 0.0, 1.0)
    olive = smoothstep(0.52, 0.63, field)
    brown = smoothstep(0.65, 0.74, field)
    dark = smoothstep(0.79, 0.87, field)
    return field, olive, brown, dark


def canvas(size=4096, thread_count=256, seed=20261019):
    repeat_px = size / thread_count
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    u = x / repeat_px
    v = y / repeat_px
    warp = 0.5 + 0.5 * np.cos(2.0 * np.pi * u)
    weft = 0.5 + 0.5 * np.cos(2.0 * np.pi * v)
    checker = ((np.floor(u).astype(np.int32) + np.floor(v).astype(np.int32)) & 1).astype(np.float32)
    weave = checker * warp + (1.0 - checker) * weft

    rng = np.random.default_rng(seed)
    warp_thread = rng.random(thread_count).astype(np.float32)
    weft_thread = rng.random(thread_count).astype(np.float32)
    thread_index = np.floor(u).astype(np.int32) % thread_count
    warp_row = warp_thread[thread_index[0]]
    weft_row = weft_thread[thread_index[:, 0]]
    thread = 0.5 * (warp_row[None, :] + weft_row[:, None])

    fibre = value_noise(size, 96, seed + 1, octaves=3)
    slub = value_noise(size, 24, seed + 2, octaves=4)
    wax = gaussian_filter(value_noise(size, 6, seed + 3, octaves=4), 2.0, mode="wrap")
    crease = ridged(gaussian_filter(value_noise(size, 5, seed + 4, octaves=4), 3.0, mode="wrap"), 2.6)
    crease = gaussian_filter(crease, 1.2, mode="wrap")
    micro = value_noise(size, 190, seed + 5, octaves=2)

    height = (
        0.52
        + 0.24 * weave
        + 0.08 * (thread - 0.5)
        + 0.035 * (fibre - 0.5)
        + 0.035 * (slub - 0.5)
        + 0.10 * crease
        + 0.025 * wax
        + 0.012 * (micro - 0.5)
    )
    height = gaussian_filter(height, 0.65, mode="wrap")
    height = (height - height.min()) / max(float(height.max() - height.min()), 1e-6)

    field, olive, brown, dark = camouflage(size, seed + 6)
    base = np.array([0.740, 0.620, 0.290], np.float32)
    olive_col = np.array([0.560, 0.510, 0.240], np.float32)
    brown_col = np.array([0.450, 0.360, 0.180], np.float32)
    dark_col = np.array([0.330, 0.260, 0.120], np.float32)
    colour = np.broadcast_to(base, (size, size, 3)).copy()
    colour = colour * (1.0 - 0.50 * olive[..., None]) + olive_col * (0.50 * olive[..., None])
    colour = colour * (1.0 - 0.58 * brown[..., None]) + brown_col * (0.58 * brown[..., None])
    colour = colour * (1.0 - 0.50 * dark[..., None]) + dark_col * (0.50 * dark[..., None])

    tint = np.clip((slub - 0.5) * 0.28 + 0.5, 0.0, 1.0)[..., None]
    colour = colour * (0.96 + 0.10 * tint)
    shade = (0.94 + 0.08 * height) * (0.94 + 0.12 * (thread - 0.5))
    shade *= 1.0 - 0.16 * crease
    shade *= 1.0 + 0.06 * (wax - 0.5)
    shade *= 1.0 - 0.05 * (fibre - 0.5)
    colour = np.clip(colour * shade[..., None], 0.0, 1.0)

    normal = normal_from_height(height, 6.0)
    normal_rgb = normal * 0.5 + 0.5

    ao = 0.78 + 0.22 * height - 0.10 * crease
    ao = np.clip(ao, 0.45, 1.0)
    rough = 0.60 - 0.10 * wax + 0.16 * crease + 0.05 * (thread - 0.5) + 0.025 * (field - 0.5)
    rough = np.clip(rough, 0.38, 0.82)
    orm = np.stack((ao, rough, np.zeros_like(ao)), axis=-1)

    save_srgb(TEX / "T_FieldHat_Canvas_BaseColor.png", colour)
    save_data(TEX / "T_FieldHat_Canvas_Normal.png", normal_rgb)
    save_data(TEX / "T_FieldHat_Canvas_ORM.png", orm)
    return dict(size=size, threads=thread_count, base_mean=colour.reshape(-1, 3).mean(0).tolist(),
                camo_mean=float(field.mean()), camo_std=float(field.std()),
                olive_fraction=float((olive > 0.5).mean()), brown_fraction=float((brown > 0.5).mean()),
                dark_fraction=float((dark > 0.5).mean()),
                height_mean=float(height.mean()), normal_z_mean=float(normal[..., 2].mean()),
                roughness_mean=float(rough.mean()))


def leather(size=2048, seed=20261020):
    y, x = np.mgrid[0:size, 0:size].astype(np.float32) / size
    fine = value_noise(size, 40, seed, octaves=4)
    pebble = ridged(gaussian_filter(value_noise(size, 18, seed + 1, octaves=4), 1.4, mode="wrap"), 2.0)
    crease = ridged(gaussian_filter(value_noise(size, 5, seed + 2, octaves=4), 2.2, mode="wrap"), 2.2)
    pores = value_noise(size, 300, seed + 3, octaves=2)
    pores = np.clip((pores - 0.62) * 5.0, 0.0, 1.0)
    micro = value_noise(size, 420, seed + 4, octaves=2)

    height = 0.5 + 0.28 * pebble + 0.10 * crease + 0.05 * (fine - 0.5) - 0.07 * pores + 0.018 * (micro - 0.5)
    height = gaussian_filter(height, 0.65, mode="wrap")
    height = (height - height.min()) / max(float(height.max() - height.min()), 1e-6)

    base = np.array([0.460, 0.340, 0.220], np.float32)
    colour = np.broadcast_to(base, (size, size, 3)).copy()
    colour *= (0.84 + 0.16 * height)[..., None]
    colour *= (1.0 - 0.12 * crease)[..., None]
    colour *= (1.0 + 0.04 * (fine - 0.5))[..., None]
    colour = np.clip(colour, 0.0, 1.0)

    normal = normal_from_height(height, 9.0)
    normal_rgb = normal * 0.5 + 0.5

    ao = np.clip(0.76 + 0.24 * height - 0.10 * crease, 0.45, 1.0)
    rough = np.clip(0.50 + 0.13 * crease + 0.07 * (1.0 - pebble) + 0.04 * (fine - 0.5), 0.36, 0.78)
    orm = np.stack((ao, rough, np.zeros_like(ao)), axis=-1)

    save_srgb(TEX / "T_FieldHat_Leather_BaseColor.png", colour)
    save_data(TEX / "T_FieldHat_Leather_Normal.png", normal_rgb)
    save_data(TEX / "T_FieldHat_Leather_ORM.png", orm)
    return dict(size=size, base_mean=colour.reshape(-1, 3).mean(0).tolist(),
                height_mean=float(height.mean()), normal_z_mean=float(normal[..., 2].mean()),
                roughness_mean=float(rough.mean()))


def edge_check(path):
    image = np.asarray(Image.open(path).convert("RGB"), np.float32) / 255.0
    return dict(left_right=float(np.abs(image[:, 0] - image[:, -1]).mean()),
                top_bottom=float(np.abs(image[0] - image[-1]).mean()))


if __name__ == "__main__":
    import json
    result = dict(canvas=canvas(), leather=leather())
    result["canvas_edges"] = edge_check(TEX / "T_FieldHat_Canvas_BaseColor.png")
    result["leather_edges"] = edge_check(TEX / "T_FieldHat_Leather_BaseColor.png")
    (ROOT / "textures.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
