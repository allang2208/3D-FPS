"""Generate seamless 2048x2048 3A PBR texture sets (BaseColor, NormalDX, ORM) for the HorseTackR52 Cavalry Suite.

Sets authored under SourceAssets/HillsVillageStable/HorseTackR52/Textures/:
  1. T_TackSteel_*       : Hand-forged hammered knight steel (chanfron, stirrups, horseshoes, buckles)
  2. T_TackLeather_*     : Oiled chestnut full-grain saddle leather (saddle seat/flaps, saddlebags)
  3. T_TackLeatherDark_* : Deep espresso harness strap leather (welts, chinstraps, linings, billets)
  4. T_TackBlanket_*     : Woven crimson-burgundy & charcoal twill wool saddle cloth with antique gold edge pattern
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
OUT_DIR = PROJECT / 'SourceAssets/HillsVillageStable/HorseTackR52/Textures'
N = 2048


def _tile_noise(seed, grid, size=N):
    """Smooth tileable bilinear value noise [0, 1]."""
    rng = np.random.default_rng(seed)
    base = rng.random((grid, grid), dtype=np.float32)
    u = (np.arange(size, dtype=np.float32) / size) * grid
    v = (np.arange(size, dtype=np.float32) / size) * grid
    i0 = np.floor(u).astype(np.int32) % grid
    j0 = np.floor(v).astype(np.int32) % grid
    i1 = (i0 + 1) % grid
    j1 = (j0 + 1) % grid
    fu = (u - np.floor(u))
    fv = (v - np.floor(v))
    fu = fu * fu * (3.0 - 2.0 * fu)
    fv = fv * fv * (3.0 - 2.0 * fv)
    a = base[np.ix_(j0, i0)]
    b = base[np.ix_(j0, i1)]
    c = base[np.ix_(j1, i0)]
    d = base[np.ix_(j1, i1)]
    return (a * (1.0 - fu)[None, :] + b * fu[None, :]) * (1.0 - fv)[:, None] + \
           (c * (1.0 - fu)[None, :] + d * fu[None, :]) * fv[:, None]


def _fbm(seed, freqs=(8, 16, 32, 64, 128), weights=(0.35, 0.28, 0.19, 0.12, 0.06)):
    acc = np.zeros((N, N), dtype=np.float32)
    wsum = 0.0
    for k, (f, w) in enumerate(zip(freqs, weights)):
        acc += _tile_noise(seed + k * 97, f) * w
        wsum += w
    return acc / max(wsum, 1e-6)


def _voronoi_dimples(seed, count_x, count_y):
    """Tileable cellular hammer-peen / leather-pebble height map [0, 1]."""
    rng = np.random.default_rng(seed)
    px = rng.random((count_y, count_x), dtype=np.float32)
    py = rng.random((count_y, count_x), dtype=np.float32)
    u = (np.arange(N, dtype=np.float32) / N) * count_x
    v = (np.arange(N, dtype=np.float32) / N) * count_y
    cx = np.floor(u).astype(np.int32)
    cy = np.floor(v).astype(np.int32)
    fx = u - cx
    fy = v - cy
    min_d2 = np.full((N, N), 1e9, dtype=np.float32)
    sec_d2 = np.full((N, N), 1e9, dtype=np.float32)
    for dy in (-1, 0, 1):
        ny = (cy + dy) % count_y
        for dx in (-1, 0, 1):
            nx = (cx + dx) % count_x
            rx = dx + px[np.ix_(ny, nx)] - fx[None, :]
            ry = dy + py[np.ix_(ny, nx)] - fy[:, None]
            d2 = rx * rx + ry * ry
            closer = d2 < min_d2
            sec_d2 = np.where(closer, min_d2, np.minimum(sec_d2, d2))
            min_d2 = np.where(closer, d2, min_d2)
    d1 = np.sqrt(min_d2)
    d2 = np.sqrt(sec_d2)
    return np.clip(d1, 0.0, 1.0), np.clip(d2 - d1, 0.0, 1.0)


def _height_to_normal_dx(h, strength=4.0):
    """Convert tileable float height [0,1] into DirectX-convention RGB uint8 tangent normal map (+X right, -Y up)."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * strength
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * strength
    nx = -dx
    ny = dy  # DirectX green-down convention
    nz = np.ones_like(h)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz + 1e-8)
    rgb = np.stack([(nx * inv * 0.5 + 0.5), (ny * inv * 0.5 + 0.5), (nz * inv * 0.5 + 0.5)], axis=-1)
    return np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)


def _save_set(prefix, base_rgb, height, ao, rough, metal, normal_strength=4.5):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bc = np.clip(base_rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(bc, mode='RGB').save(OUT_DIR / f'{prefix}_BaseColor.png', optimize=False)
    nrm = _height_to_normal_dx(height, strength=normal_strength)
    Image.fromarray(nrm, mode='RGB').save(OUT_DIR / f'{prefix}_NormalDX.png', optimize=False)
    orm = np.stack([
        np.clip(ao * 255.0 + 0.5, 0, 255),
        np.clip(rough * 255.0 + 0.5, 0, 255),
        np.clip(metal * 255.0 + 0.5, 0, 255),
    ], axis=-1).astype(np.uint8)
    Image.fromarray(orm.astype(np.uint8), mode='RGB').save(OUT_DIR / f'{prefix}_ORM.png', optimize=False)
    print(f'WROTE {prefix} ({N}x{N})', flush=True)


def make_forged_steel():
    """Hand-forged hammered medieval cavalry steel with peen dimples, forge scale, patina & fine battle scratches."""
    d1, edge = _voronoi_dimples(5201, 24, 24)
    peen = 1.0 - np.clip(d1 * 1.18, 0.0, 1.0) ** 1.6  # shallow bowl dimples
    macro = _fbm(5202, (6, 12, 24, 48, 96))
    micro = _fbm(5203, (32, 64, 128, 256))
    # Subtle directional grind & combat scratches
    rng = np.random.default_rng(5204)
    scratch = np.zeros((N, N), dtype=np.float32)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    for _ in range(42):
        ang = rng.uniform(0.0, math.tau)
        cx, cy = rng.uniform(0, N), rng.uniform(0, N)
        length = rng.uniform(90, 340)
        ca, sa = math.cos(ang), math.sin(ang)
        rx = ((xx - cx + N * 0.5) % N) - N * 0.5
        ry = ((yy - cy + N * 0.5) % N) - N * 0.5
        along = rx * ca + ry * sa
        perp = np.abs(-rx * sa + ry * ca)
        w = rng.uniform(0.8, 2.2)
        mask = np.exp(-(perp / w) ** 2) * np.clip(1.0 - (np.abs(along) / length) ** 2, 0.0, 1.0)
        scratch = np.maximum(scratch, mask * rng.uniform(0.35, 0.9))

    scale_pits = np.clip((macro - 0.54) * 3.8, 0.0, 1.0) * (0.45 + 0.55 * micro)
    height = 0.55 + 0.16 * (1.0 - peen) + 0.12 * macro + 0.08 * micro - 0.18 * scale_pits - 0.14 * scratch
    height = np.clip(height, 0.0, 1.0)

    # Dark gunmetal / burnished iron-steel palette matching stable_barding.png & stable_horseshoes.png
    steel_hi = np.array([0.46, 0.45, 0.43], dtype=np.float32)
    steel_mid = np.array([0.23, 0.22, 0.21], dtype=np.float32)
    rust_patina = np.array([0.16, 0.11, 0.07], dtype=np.float32)
    ridge_shine = np.clip(1.0 - peen * 0.85, 0.0, 1.0) * 0.55 + scratch * 0.65
    t = np.clip(ridge_shine * 0.65 + (1.0 - macro) * 0.35, 0.0, 1.0)[..., None]
    base = steel_mid * (1.0 - t) + steel_hi * t
    pat_m = np.clip(scale_pits * 0.85 + peen * 0.22 * (1.0 - macro), 0.0, 0.82)[..., None]
    base = base * (1.0 - pat_m) + rust_patina * pat_m
    base = np.clip(base + scratch[..., None] * 0.22, 0.03, 0.78)

    ao = np.clip(0.95 - 0.28 * scale_pits - 0.16 * peen - 0.10 * scratch, 0.48, 1.0)
    rough = np.clip(0.30 + 0.38 * scale_pits + 0.14 * micro - 0.18 * scratch - 0.09 * (1.0 - peen), 0.16, 0.84)
    metal = np.clip(0.94 - 0.42 * scale_pits, 0.42, 0.98)
    _save_set('T_TackSteel', base, height, ao, rough, metal, normal_strength=6.5)


def make_leather(prefix, seed, col_lo, col_hi, col_scuff, rough_base=0.46):
    """Full-grain oiled saddle leather with fine organic pebble pores, natural creases & hand-burnished tone."""
    d1, edge = _voronoi_dimples(seed, 88, 88)
    pebble = np.clip(1.0 - d1 * 1.45, 0.0, 1.0) ** 0.75
    pore_seam = np.clip(1.0 - edge * 7.5, 0.0, 1.0)
    macro = _fbm(seed + 10, (4, 8, 16, 32))
    crease_raw = _fbm(seed + 20, (6, 12, 24))
    crease = np.exp(-((crease_raw - 0.50) * 14.0) ** 2) * 0.55
    fine = _fbm(seed + 30, (64, 128, 256))

    height = np.clip(0.50 + 0.14 * pebble - 0.10 * pore_seam - 0.16 * crease + 0.10 * macro + 0.05 * fine, 0.0, 1.0)

    c_lo = np.array(col_lo, dtype=np.float32)
    c_hi = np.array(col_hi, dtype=np.float32)
    c_sc = np.array(col_scuff, dtype=np.float32)
    t = np.clip(macro * 0.75 + pebble * 0.25 - crease * 0.30, 0.0, 1.0)[..., None]
    base = c_lo * (1.0 - t) + c_hi * t
    scuff = np.clip((macro - 0.62) * 2.5 + fine * 0.25, 0.0, 0.55)[..., None]
    base = base * (1.0 - scuff * 0.45) + c_sc * (scuff * 0.45)
    base *= (1.0 - 0.18 * pore_seam[..., None] - 0.14 * crease[..., None])

    ao = np.clip(0.96 - 0.20 * pore_seam - 0.22 * crease, 0.52, 1.0)
    rough = np.clip(rough_base + 0.16 * pore_seam + 0.14 * crease - 0.12 * pebble + 0.10 * (fine - 0.5), 0.26, 0.85)
    metal = np.zeros_like(rough)
    _save_set(prefix, base, height, ao, rough, metal, normal_strength=5.2)


def make_saddle_blanket():
    """Heavy woven burgundy-crimson & charcoal cavalry wool twill with antique gold geometric border stripes."""
    u = np.linspace(0.0, 1.0, N, endpoint=False, dtype=np.float32)
    v = np.linspace(0.0, 1.0, N, endpoint=False, dtype=np.float32)
    U, V = np.meshgrid(u, v)

    # Diagonal 2/2 heavy wool twill weave
    twill = 0.5 + 0.5 * np.sin((U * 240.0 + V * 240.0) * math.tau)
    warp = 0.5 + 0.5 * np.sin(U * 320.0 * math.tau)
    weft = 0.5 + 0.5 * np.sin(V * 280.0 * math.tau)
    weave = 0.50 * twill + 0.25 * warp + 0.25 * weft
    fuzz = _fbm(5290, (16, 32, 64, 128, 256))
    macro = _fbm(5291, (4, 8, 16))

    # Woven heraldic cavalry stripe bands along V (border motif)
    band_charcoal = ((np.abs(V - 0.14) < 0.045) | (np.abs(V - 0.86) < 0.045)).astype(np.float32)
    band_gold = ((np.abs(V - 0.082) < 0.014) | (np.abs(V - 0.198) < 0.012) |
                 (np.abs(V - 0.802) < 0.012) | (np.abs(V - 0.918) < 0.014)).astype(np.float32)
    # Diamond motif inside charcoal band
    diamond = (np.abs(((U * 14.0) % 1.0) - 0.5) + np.abs(((V * 14.0) % 1.0) - 0.5) < 0.28).astype(np.float32) * band_charcoal

    crimson = np.array([0.27, 0.055, 0.048], dtype=np.float32)
    charcoal = np.array([0.075, 0.072, 0.070], dtype=np.float32)
    gold = np.array([0.48, 0.35, 0.15], dtype=np.float32)

    base = crimson[None, None, :] * (0.85 + 0.30 * macro[..., None])
    base = base * (1.0 - band_charcoal[..., None]) + charcoal[None, None, :] * band_charcoal[..., None]
    gmask = np.clip(band_gold + diamond * 0.72, 0.0, 1.0)[..., None]
    base = base * (1.0 - gmask) + gold[None, None, :] * gmask
    base *= (0.84 + 0.26 * weave[..., None] + 0.10 * (fuzz[..., None] - 0.5))

    height = np.clip(0.35 + 0.36 * weave + 0.18 * fuzz + 0.08 * gmask[..., 0], 0.0, 1.0)
    ao = np.clip(0.86 + 0.14 * weave - 0.10 * (1.0 - fuzz), 0.58, 1.0)
    rough = np.clip(0.86 + 0.10 * (1.0 - weave) - 0.06 * gmask[..., 0], 0.72, 0.98)
    metal = np.zeros_like(rough)
    _save_set('T_TackBlanket', base, height, ao, rough, metal, normal_strength=7.0)


def main():
    make_forged_steel()
    # Rich oiled chestnut leather matching stable_saddle.png & stable_saddlebags.png
    make_leather('T_TackLeather', 5210,
                 col_lo=(0.14, 0.055, 0.025), col_hi=(0.30, 0.125, 0.055), col_scuff=(0.44, 0.22, 0.10), rough_base=0.44)
    # Deep espresso-brown harness strap/trim leather
    make_leather('T_TackLeatherDark', 5220,
                 col_lo=(0.065, 0.032, 0.018), col_hi=(0.14, 0.068, 0.036), col_scuff=(0.24, 0.12, 0.06), rough_base=0.50)
    make_saddle_blanket()
    print('ALL_TACK_TEXTURES_OK', flush=True)


if __name__ == '__main__':
    main()
