"""Author the blast furnace's original PBR map sets.

Runs with the system interpreter (numpy + PIL), not Blender:

    python SourceAssets/BlastFurnace20260923/prepare_furnace_textures.py

Every map is fully tileable periodic value noise so the firebrick and masonry
sets can repeat over the stack without a visible seam. Colour, roughness,
normal, metallic and occlusion are produced per material; a colour map alone
is not a PBR set.

Albedo is authored in **linear** terms and encoded to sRGB only when the PNG is
written. The first revision authored sRGB values directly, which made the iron
0.027 linear — black metal with no readable specular.

No third-party artwork is read here. All seven materials are generated.
"""
from pathlib import Path
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
TEX = ROOT / 'Authored' / 'Textures'
TEX.mkdir(parents=True, exist_ok=True)

SEED = 20260923
recipes = {}


def rng_for(key):
    return np.random.default_rng(SEED + (abs(hash(key)) % 100000))


def linear_to_srgb(linear):
    """8-bit sRGB encoding of a linear albedo array in 0..1."""
    value = np.clip(linear, 0.0, 1.0)
    encoded = np.where(value <= 0.0031308,
                       value * 12.92,
                       1.055 * np.power(np.maximum(value, 1e-8), 1.0 / 2.4) - 0.055)
    return np.clip(encoded * 255.0, 0, 255)


def albedo(r, g, b):
    """A linear albedo triple (reflectance in 0..1), never sRGB bytes.

    Storing sRGB numbers here instead is how the first revision ended up with
    0.027-linear iron: the PNG is sRGB-encoded on save, so the *inputs* must
    already be linear.
    """
    return np.array([r, g, b], dtype=np.float32)


def vnoise(n, g, rng):
    """Tileable value noise on an n x n grid from a periodic g x g lattice."""
    lat = rng.random((g, g)).astype(np.float32)
    t = np.arange(n, dtype=np.float32) * (g / n)
    i0 = np.floor(t).astype(np.int32) % g
    i1 = (i0 + 1) % g
    f = t - np.floor(t)
    f = f * f * (3.0 - 2.0 * f)
    a = lat[np.ix_(i0, i0)]
    b = lat[np.ix_(i0, i1)]
    c = lat[np.ix_(i1, i0)]
    d = lat[np.ix_(i1, i1)]
    fx = f[None, :]
    fy = f[:, None]
    top = a + (b - a) * fx
    bot = c + (d - c) * fx
    return top + (bot - top) * fy


def fractal(n, rng, base=8, octaves=5, gain=0.5):
    """Tileable multi-octave noise in roughly -1..1."""
    total = np.zeros((n, n), np.float32)
    amp = 1.0
    norm = 0.0
    g = base
    for _ in range(octaves):
        total += vnoise(n, g, rng) * amp
        norm += amp
        amp *= gain
        g = min(g * 2, n)
    return (total / norm) * 2.0 - 1.0


def fbm01(n, rng, base=8, octaves=5, gain=0.5):
    return (fractal(n, rng, base, octaves, gain) + 1.0) * 0.5


def normal_from_height(height, relief):
    """OpenGL-style tangent normal map; matches the project's bottle pipeline.

    `height` is normalised to 0..1 first and `relief` is the peak-to-valley
    relief expressed in *texels*: a step of the full height range taken over
    one texel becomes a slope of `relief`. Passing a raw height field with a
    strength of 1 (as the bottle script does) leaves a near-flat normal map,
    because a realistic 30 cm relief across a 2 m tile is only a few degrees.
    """
    h = height.astype(np.float32)
    lo, hi = float(h.min()), float(h.max())
    h = (h - lo) / (hi - lo) if hi > lo else np.zeros_like(h)
    dy, dx = np.gradient(h)
    nx = -dx * relief
    ny = dy * relief
    nz = np.ones_like(nx)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    normal = np.stack([nx / length, ny / length, nz / length], -1)
    return np.clip(normal * 0.5 + 0.5, 0, 1)


def normal_tilt(normal_map):
    """Largest and mean surface tilt in degrees, as a build-time self check."""
    n = normal_map * 2.0 - 1.0
    tilt = np.degrees(np.arccos(np.clip(n[..., 2], -1, 1)))
    return float(tilt.max()), float(tilt.mean())


def occlusion_from_height(height, radius=9, amount=0.9):
    """Cheap concavity AO: how far a pixel sits below its neighbourhood."""
    h = height.astype(np.float32)
    lo, hi = float(h.min()), float(h.max())
    h = (h - lo) / (hi - lo) if hi > lo else np.zeros_like(h)
    blurred = box_blur(h, radius)
    ao = 1.0 - np.clip((blurred - h) * 6.0, 0.0, 1.0) * amount
    return np.clip(ao, 0.0, 1.0)


def box_blur(a, radius):
    """Separable box blur with wrap-around, so the result stays tileable."""
    if radius < 1:
        return a
    k = radius * 2 + 1
    rows, cols = a.shape
    pad = np.concatenate([a[-radius:], a, a[:radius]], axis=0)
    cs = np.concatenate([np.zeros((1, cols)), np.cumsum(pad, axis=0, dtype=np.float64)], axis=0)
    out = (cs[k:] - cs[:-k]) / k
    pad = np.concatenate([out[:, -radius:], out, out[:, :radius]], axis=1)
    cs = np.concatenate([np.zeros((rows, 1)), np.cumsum(pad, axis=1, dtype=np.float64)], axis=1)
    out = (cs[:, k:] - cs[:, :-k]) / k
    return out.astype(a.dtype)


def block_layout(n, rng, rows, joint, min_parts=1, max_parts=3):
    """Rasterise a running-bond block layout.

    Returns (block_id, joint_mask) with block_id == 0 on every joint pixel.
    Layout is generated with wrap-around so the map still tiles.
    """
    id_map = Image.new('I', (n, n), 0)
    draw = ImageDraw.Draw(id_map)
    heights = rng.uniform(0.75, 1.35, rows)
    heights = heights / heights.sum() * n
    block = 1
    y = 0.0
    for r in range(rows):
        h = heights[r]
        parts = int(rng.integers(min_parts, max_parts + 1))
        widths = rng.uniform(0.6, 1.5, parts)
        widths = widths / widths.sum() * n
        offset = rng.uniform(0, n)
        x = offset
        for w in widths:
            x0, x1 = x, x + w
            for shift in (0, -n, n):
                a = x0 + shift + joint * 0.5
                b = x1 + shift - joint * 0.5
                if b <= a:
                    continue
                draw.rectangle([a, y + joint * 0.5, b, y + h - joint * 0.5], fill=block)
            x = x1
            block += 1
        y += h
    ids = np.asarray(id_map, dtype=np.int32)
    return ids, (ids == 0)


def render(key, size, base_linear, roughness, metallic, height, relief=18):
    """Write one material's map set and record the recipe.

    Only the colour map is sRGB-encoded; roughness, metallic, normal and AO are
    linear data and are written as-is.
    """
    n = size
    base = np.uint8(linear_to_srgb(base_linear))
    rough = np.uint8(np.clip(roughness, 0, 1) * 255)
    metal = np.uint8(np.clip(metallic, 0, 1) * 255)
    normal_f = normal_from_height(height, relief)
    normal = np.uint8(normal_f * 255)
    ao = np.uint8(np.clip(occlusion_from_height(height), 0, 1) * 255)
    maps = {}
    for channel, data in (('BaseColor', base), ('Roughness', rough), ('Metallic', metal),
                          ('Normal', normal), ('AO', ao)):
        path = TEX / (key + '_' + channel + '.png')
        Image.fromarray(data).save(path)
        maps[channel] = str(path.name)
    digest = hashlib.sha256()
    for channel in ('BaseColor', 'Roughness', 'Metallic', 'Normal', 'AO'):
        digest.update((TEX / (key + '_' + channel + '.png')).read_bytes())
    peak, mean = normal_tilt(normal_f)
    recipes[key] = dict(size=size, relief_texels=relief, normal_peak_tilt_deg=round(peak, 2),
                        normal_mean_tilt_deg=round(mean, 2),
                        base_linear_mean=[round(float(v), 4) for v in base_linear.reshape(-1, 3).mean(0)],
                        maps=maps, content_hash=digest.hexdigest())
    print('FURNACE_MAP_SET %s %d relief=%d tilt max %.2f mean %.2f' % (key, size, relief, peak, mean),
          flush=True)


# --- Masonry: dressed ashlar plinth and rubble footing -------------------
def masonry():
    key = 'BlastFurnace_Masonry'
    n, rng = 2048, rng_for(key)
    ids, joint = block_layout(n, rng, rows=9, joint=int(n * 0.011), min_parts=2, max_parts=4)
    count = int(ids.max())
    tone = rng.normal(1.0, 0.085, count + 1).astype(np.float32)
    tone[0] = 1.0
    # Per-block hue drift stays small: a furnace plinth is grey stone, not a
    # patchwork of coloured blocks. Only luminance varies noticeably.
    hue = rng.normal(0.0, 0.022, count + 1).astype(np.float32)
    hue[0] = 0.0
    relief = rng.normal(0.0, 0.05, count + 1).astype(np.float32)
    grain = fractal(n, rng, base=6, octaves=6)
    pit = np.clip(fbm01(n, rng, base=64, octaves=3) - 0.62, 0, None) * 2.6
    chipped = np.clip((fbm01(n, rng, base=24, octaves=4) - 0.66) * 3.0, 0, 1)

    # Linear albedo, dressed limestone: about 0.26 grey.
    base = albedo(0.215, 0.213, 0.205)
    base = base[None, None, :] * tone[ids][..., None]
    base[..., 0] *= 1.0 + hue[ids]
    base[..., 1] *= 1.0 + hue[ids] * 0.35
    base[..., 2] *= 1.0 - hue[ids]
    base *= 1.0 + grain[..., None] * 0.085
    base *= 1.0 - pit[..., None] * 0.24
    base *= 1.0 + chipped[..., None] * 0.07
    mortar = albedo(0.250, 0.245, 0.230)
    base = np.where(joint[..., None], mortar * (1.0 + grain[..., None] * 0.07), base)
    base = np.clip(base, 0.0, 1.0)

    height = 0.52 + relief[ids] + grain * 0.11 - pit * 0.35
    height = np.where(joint, 0.16 + grain * 0.09, height)
    rough = 0.74 + tone[ids] * 0.02 + grain * 0.05 - chipped * 0.06
    rough = np.where(joint, 0.87 + grain * 0.04, rough)
    render(key, n, base, rough, np.zeros((n, n), np.float32), height, relief=15)


# --- Firebrick: refractory courses lining the stack ---------------------
def firebrick():
    key = 'BlastFurnace_Firebrick'
    n, rng = 2048, rng_for(key)
    # 13 courses over the 0.95 m tile the authoring script assigns to the
    # firebrick slot: about a 7 cm brick, which is the real thing.
    ids, joint = block_layout(n, rng, rows=13, joint=int(n * 0.009), min_parts=4, max_parts=6)
    count = int(ids.max())
    tone = rng.normal(1.0, 0.10, count + 1).astype(np.float32)
    tone[0] = 1.0
    relief = rng.normal(0.0, 0.035, count + 1).astype(np.float32)
    grain = fractal(n, rng, base=8, octaves=6)
    soot = np.clip(fbm01(n, rng, base=5, octaves=5) - 0.44, 0, None) * 1.5
    glaze = np.clip((fbm01(n, rng, base=17, octaves=4) - 0.70) * 3.4, 0, 1)
    spall = np.clip((fbm01(n, rng, base=30, octaves=3) - 0.74) * 4.0, 0, 1)

    base = albedo(0.200, 0.140, 0.098)
    base = base[None, None, :] * tone[ids][..., None]
    base *= 1.0 + grain[..., None] * 0.075
    base *= 1.0 - soot[..., None] * 0.46
    base *= 1.0 - spall[..., None] * 0.18
    base += glaze[..., None] * albedo(0.055, 0.040, 0.030) * 0.5
    mortar = albedo(0.270, 0.235, 0.190)
    base = np.where(joint[..., None], mortar * (1.0 + grain[..., None] * 0.06), base)
    base = np.clip(base, 0.0, 1.0)

    height = 0.55 + relief[ids] + grain * 0.09 - spall * 0.30
    height = np.where(joint, 0.20 + grain * 0.07, height)
    rough = 0.79 + grain * 0.045 + soot * 0.05 - glaze * 0.30
    rough = np.where(joint, 0.88 + grain * 0.04, rough)
    render(key, n, base, rough, np.zeros((n, n), np.float32), height, relief=22)


# --- Wrought iron: bands, bolts, blast pipe, doors, moulds --------------
def wrought_iron():
    """Bare wrought iron with forge scale and rust.

    Iron is a *metal*: its base colour is a reflectance, not a paint colour.
    The first revision stored 46/255, i.e. 0.027 linear — black, with no
    specular to read as metal. Bare iron here is ~0.47 linear, forge scale
    ~0.135, rust ~0.10 and dielectric.
    """
    key = 'BlastFurnace_WroughtIron'
    n, rng = 1024, rng_for(key)
    hammer = np.abs(fractal(n, rng, base=22, octaves=4))
    pitting = np.clip((fbm01(n, rng, base=40, octaves=4) - 0.62) * 3.0, 0, 1)
    rust = np.clip((fbm01(n, rng, base=6, octaves=5) - 0.34) * 1.9, 0, 1)
    scale = np.clip((fbm01(n, rng, base=13, octaves=4) - 0.54) * 3.0, 0, 1)
    polish = np.clip((fbm01(n, rng, base=8, octaves=4) - 0.55) * 2.4, 0, 1)
    forge = fractal(n, rng, base=3, octaves=3)

    iron = albedo(0.400, 0.392, 0.380) * 0.97
    rust_color = albedo(0.185, 0.082, 0.038)
    scale_color = albedo(0.135, 0.128, 0.122)

    base = iron[None, None, :] * (1.0 + (hammer[..., None] * 0.10 + forge[..., None] * 0.07))
    base = base * (1.0 - scale[..., None] * 0.85) + scale_color * scale[..., None] * 0.85
    base = base * (1.0 - rust[..., None] * 0.90) + rust_color * rust[..., None] * 0.90
    base *= 1.0 - pitting[..., None] * 0.35
    # Burnished high points stay metallic and bright; that is what makes the
    # bands and bolt heads read as forged metal in raking light.
    base += iron[None, None, :] * (polish * (1.0 - rust) * 0.22)[..., None]
    base = np.clip(base, 0.0, 1.0)

    height = 0.55 + hammer * 0.18 + forge * 0.10 - pitting * 0.42 - rust * 0.06
    rough = 0.46 + hammer * 0.06 + rust * 0.52 + scale * 0.26 + pitting * 0.16 - polish * 0.10
    rough = np.clip(rough, 0.16, 0.98)
    metal = np.clip(0.98 - rust * 0.92 - scale * 0.20 - pitting * 0.18, 0.0, 1.0)
    render(key, n, base, rough, metal, height, relief=26)


# --- Clay luting: tap arch surround and gutter lining -------------------
def clay_luting():
    key = 'BlastFurnace_ClayLuting'
    n, rng = 1024, rng_for(key)
    grain = fractal(n, rng, base=10, octaves=6)
    coarse = fractal(n, rng, base=4, octaves=4)
    sand = fractal(n, rng, base=52, octaves=4)
    # Luting dries into a network of cracks at several scales; a single large
    # cell size reads as leather or camouflage rather than fired clay.
    crack = np.zeros((n, n), np.float32)
    for grid, weight in ((11, 0.34), (23, 0.30), (47, 0.24)):
        band = np.clip(1.0 - np.abs(fractal(n, rng, base=grid, octaves=2)) * (9.0 + grid * 0.6), 0, 1)
        crack = np.maximum(crack, band * weight)
    smear = np.clip((fbm01(n, rng, base=19, octaves=4) - 0.55) * 2.2, 0, 1)

    base = albedo(0.128, 0.082, 0.052)
    base = base[None, None, :] * (1.0 + coarse[..., None] * 0.16 + grain[..., None] * 0.10
                                  + sand[..., None] * 0.12)
    base *= 1.0 - crack[..., None] * 0.20
    base += albedo(0.075, 0.050, 0.034) * (smear * 0.25)[..., None]
    base = np.clip(base, 0.0, 1.0)

    height = 0.55 + coarse * 0.10 + grain * 0.06 + sand * 0.05 - crack * 0.34
    rough = 0.88 + grain * 0.03 + sand * 0.03 - crack * 0.02
    render(key, n, base, rough, np.zeros((n, n), np.float32), height, relief=24)


# --- Slag lining: cut openings and mould cavities ----------------------
def slag_lining():
    key = 'BlastFurnace_SlagLining'
    n, rng = 1024, rng_for(key)
    blobs = np.clip((fbm01(n, rng, base=6, octaves=4) - 0.42) * 2.0, 0, 1)
    fine = fractal(n, rng, base=18, octaves=5)
    glass = np.clip((fbm01(n, rng, base=9, octaves=4) - 0.60) * 2.8, 0, 1)
    scoria = np.clip((fbm01(n, rng, base=26, octaves=4) - 0.68) * 3.2, 0, 1)

    base = albedo(0.062, 0.060, 0.058)
    base = base[None, None, :] * (1.0 + blobs[..., None] * 0.55 + fine[..., None] * 0.30)
    base += albedo(0.110, 0.115, 0.120) * (glass * 0.30)[..., None]
    base *= 1.0 - scoria[..., None] * 0.35
    base = np.clip(base, 0.0, 1.0)

    height = 0.55 + blobs * 0.26 + fine * 0.10 - scoria * 0.28
    rough = 0.62 - glass * 0.34 + scoria * 0.14 + fine * 0.04
    metal = np.clip(0.05 + glass * 0.16, 0, 1)
    render(key, n, base, rough, metal, height, relief=20)


# --- Ember bed: the bowl floor the runtime may swap for an emissive one -
def ember_bed():
    key = 'BlastFurnace_EmberBed'
    n, rng = 1024, rng_for(key)
    clinker = np.clip((fbm01(n, rng, base=7, octaves=5) - 0.38) * 1.9, 0, 1)
    ember = np.clip((fbm01(n, rng, base=13, octaves=4) - 0.55) * 2.6, 0, 1)
    grain = fractal(n, rng, base=22, octaves=5)

    base = albedo(0.040, 0.030, 0.028)
    base = base[None, None, :] * (1.0 + clinker[..., None] * 0.65 + grain[..., None] * 0.35)
    base = base * (1.0 - ember[..., None] * 0.75) + albedo(0.380, 0.090, 0.020) * ember[..., None] * 0.8
    base = np.clip(base, 0.0, 1.0)
    height = 0.55 + clinker * 0.24 + grain * 0.09
    rough = 0.80 - ember * 0.22 + grain * 0.04
    render(key, n, base, rough, np.zeros((n, n), np.float32), height, relief=18)


# --- Ore lump: charge waiting on the plinth ----------------------------
def ore_lump():
    key = 'BlastFurnace_OreLump'
    n, rng = 1024, rng_for(key)
    facets = fractal(n, rng, base=9, octaves=3)
    shard = np.clip((np.abs(fractal(n, rng, base=16, octaves=4)) * -1.0 + 0.34) * 3.0, 0, 1)
    crystal = np.clip((fbm01(n, rng, base=34, octaves=3) - 0.74) * 3.8, 0, 1)
    grit = fractal(n, rng, base=40, octaves=4)

    base = albedo(0.078, 0.066, 0.055)
    base = base[None, None, :] * (1.0 + facets[..., None] * 0.40 + grit[..., None] * 0.20)
    base *= 1.0 - shard[..., None] * 0.30
    base = base * (1 - crystal[..., None]) + albedo(0.320, 0.310, 0.295) * crystal[..., None]
    base = np.clip(base, 0.0, 1.0)
    height = 0.55 + facets * 0.30 + grit * 0.10 - shard * 0.20
    rough = 0.72 + facets * 0.06 - crystal * 0.38 + grit * 0.03
    metal = np.clip(crystal * 0.55, 0, 1)
    render(key, n, base, rough, metal, height, relief=24)


for builder in (masonry, firebrick, wrought_iron, clay_luting, slag_lining, ember_bed, ore_lump):
    builder()

(ROOT / 'Authored' / 'texture-recipes.json').write_text(
    json.dumps(dict(seed=SEED, tileable=True, generator='prepare_furnace_textures.py',
                    albedo_encoding='authored linear, saved as sRGB BaseColor; other channels linear',
                    materials=recipes, runtime_tested=False), indent=2),
    encoding='utf-8')
print('FURNACE_TEXTURES_WRITTEN', len(recipes))
