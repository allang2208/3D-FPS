"""Author 2K seamless physically-based weathered Hemp Rope and Woven Stable Wool Blanket PBR maps."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
OUT = PROJECT / 'SourceAssets/HillsVillageStable/PropsR43/Textures'
OUT.mkdir(parents=True, exist_ok=True)


def linear_to_srgb(arr):
    arr = np.clip(arr, 0.0, 1.0)
    return np.where(arr <= 0.0031308, arr * 12.92, 1.055 * (arr ** (1.0 / 2.4)) - 0.055)


def periodic_noise(rng, n, cells_x, cells_y):
    """Smooth tileable bilinear/bicubic noise via wrapped grid."""
    grid = rng.random((cells_y, cells_x), dtype=np.float32)
    # Tile 3x3 before upsampling to guarantee exact seamless periodic wrap
    tiled = np.tile(grid, (3, 3))
    up = np.array(Image.fromarray((tiled * 255).astype(np.uint8)).resize(
        (n * 3, n * 3), Image.Resampling.BICUBIC
    ), dtype=np.float32) / 255.0
    return up[n:2 * n, n:2 * n]


def save_png(path: Path, data_01):
    arr = np.uint8(np.clip(data_01, 0.0, 1.0) * 255.0)
    Image.fromarray(arr).save(path)


def height_to_normal_dx(height, strength=3.2, smooth_sigma=1.1):
    """Low-pass filtered DirectX tangent-space normal map (asserts Z-mean >= 0.90 per checklist)."""
    h = gaussian_filter(height.astype(np.float32), sigma=smooth_sigma, mode='wrap')
    gx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * (0.5 * strength)
    gy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * (0.5 * strength)
    # DirectX convention: +X right, +Y down
    nx, ny, nz = -gx, -gy, np.ones_like(gx)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx *= inv
    ny *= inv
    nz *= inv
    z_mean = float(nz.mean())
    assert z_mean >= 0.90, f'Normal Z-mean too steep ({z_mean:.3f}); reduce strength or increase low-pass!'
    return np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], axis=2), z_mean


def author_weathered_rope(n=2048):
    """3-strand twisted weathered raw-hemp rope: U = along rope, V = around circumference."""
    rng = np.random.default_rng(4401)
    v, u = np.mgrid[0:n, 0:n].astype(np.float32) / n  # u = axis 1 (horizontal), v = axis 0 (vertical)

    broad = periodic_noise(rng, n, 12, 12)
    med = periodic_noise(rng, n, 48, 48)
    fine = periodic_noise(rng, n, 256, 256)

    # Diagonal 3-strand helical lay: phase wraps smoothly in both u and v (integer multipliers = seamless!)
    lay_phase = 2.0 * np.pi * (u * 8.0 + v * 3.0) + 0.14 * (broad - 0.5)
    # Rounded strand crowns with deep V-valleys between strands
    strand_wave = np.abs(np.sin(lay_phase * 0.5)) ** 0.65
    valley = np.clip((0.38 - strand_wave) / 0.38, 0.0, 1.0) ** 1.4

    # Secondary twisted sub-yarns angled inside each strand
    yarn_phase = 2.0 * np.pi * (u * 36.0 + v * 15.0) + 0.5 * np.sin(lay_phase)
    yarns = 0.5 + 0.5 * np.sin(yarn_phase)

    # Fine longitudinal hemp fibers running along yarn twist direction
    fiber_phase = 2.0 * np.pi * (u * 140.0 + v * 58.0) + 2.2 * med
    fibers = 0.5 + 0.5 * np.sin(fiber_phase)

    height = 0.68 * strand_wave + 0.16 * yarns * strand_wave + 0.09 * fibers + 0.07 * fine
    normal_dx, z_mean = height_to_normal_dx(height, strength=4.2, smooth_sigma=1.35)

    # Linear albedo: warm dusty raw-hemp ochre/brown, sun-faded on crowns, dirt-darkened in valleys
    crown_col = np.array([0.27, 0.195, 0.108], dtype=np.float32)
    mid_col = np.array([0.165, 0.115, 0.062], dtype=np.float32)
    valley_col = np.array([0.055, 0.038, 0.022], dtype=np.float32)

    albedo_lin = (
        mid_col[None, None, :] * (0.78 + 0.44 * broad[:, :, None])
        + (crown_col - mid_col)[None, None, :] * (strand_wave[:, :, None] * (0.65 + 0.35 * yarns[:, :, None]))
    )
    # Subtle fibrous streaks and dusty wear
    albedo_lin *= (0.86 + 0.24 * fibers[:, :, None] + 0.12 * (fine[:, :, None] - 0.5))
    albedo_lin = albedo_lin * (1.0 - 0.72 * valley[:, :, None]) + valley_col[None, None, :] * (0.72 * valley[:, :, None])
    albedo_lin = np.clip(albedo_lin, 0.015, 0.65)

    ao = np.clip(0.98 - 0.58 * valley - 0.14 * (1.0 - yarns) - 0.08 * (1.0 - fine), 0.28, 1.0)
    rough = np.clip(0.84 + 0.10 * valley + 0.06 * (1.0 - fibers) + 0.04 * (broad - 0.5), 0.76, 0.98)
    metal = np.zeros_like(ao)
    orm = np.stack([ao, rough, metal], axis=2)

    save_png(OUT / 'T_StableRope_BaseColor.png', linear_to_srgb(albedo_lin))
    save_png(OUT / 'T_StableRope_NormalDX.png', normal_dx)
    save_png(OUT / 'T_StableRope_ORM.png', orm)
    return dict(
        name='T_StableRope',
        size=n,
        albedo_lin_mean=albedo_lin.mean(axis=(0, 1)).round(4).tolist(),
        normal_z_mean=round(z_mean, 4),
        ao_mean=round(float(ao.mean()), 4),
        rough_mean=round(float(rough.mean()), 4),
    )


def author_wool_blanket(n=2048):
    """Heavy woven wool stable saddle blanket with authentic twill weave, woven stripes & dirt/sweat aging."""
    rng = np.random.default_rng(4409)
    v, u = np.mgrid[0:n, 0:n].astype(np.float32) / n

    broad = periodic_noise(rng, n, 10, 10)
    stain = periodic_noise(rng, n, 24, 24)
    fuzz = periodic_noise(rng, n, 384, 384)

    # Heavy 2/2 diagonal wool twill weave (192 threads across tile)
    threads = 192.0
    twill_u = 0.5 + 0.5 * np.cos(2.0 * np.pi * u * threads)
    twill_v = 0.5 + 0.5 * np.cos(2.0 * np.pi * v * threads)
    step = (np.floor(u * threads) + np.floor(v * threads)) % 4.0
    over = (step < 2.0).astype(np.float32)
    weave_h = over * (0.45 + 0.55 * twill_u) + (1.0 - over) * (0.45 + 0.55 * twill_v)

    # Subtle traditional rustic horse-blanket woven stripes along V (burgundy-rust & dark charcoal wool bands)
    def band(coord, center, half_w):
        return np.clip(1.0 - np.abs(coord - center) / half_w, 0.0, 1.0) ** 0.5

    # Wrap-safe stripe mask
    rust_stripe = np.maximum(band(v, 0.14, 0.032), band(v, 0.86, 0.032))
    rust_stripe = np.maximum(rust_stripe, band(v, 0.50, 0.014))
    charcoal_stripe = np.maximum(
        np.maximum(band(v, 0.095, 0.012), band(v, 0.185, 0.012)),
        np.maximum(band(v, 0.815, 0.012), band(v, 0.905, 0.012)),
    )

    # Linear wool pigments (weathered oatmeal base, faded madder-rust & dark peat-charcoal yarn)
    base_wool = np.array([0.235, 0.185, 0.130], dtype=np.float32)
    rust_wool = np.array([0.195, 0.062, 0.042], dtype=np.float32)
    char_wool = np.array([0.048, 0.044, 0.040], dtype=np.float32)

    albedo_lin = base_wool[None, None, :] * (0.86 + 0.28 * broad[:, :, None])
    # Slightly faded worn dye retention on stripes
    dye_wear = np.clip(0.82 + 0.26 * stain - 0.14 * (1.0 - weave_h), 0.55, 1.0)
    r_m = (rust_stripe * dye_wear)[:, :, None]
    c_m = (charcoal_stripe * dye_wear)[:, :, None]
    albedo_lin = albedo_lin * (1.0 - r_m) + rust_wool[None, None, :] * r_m
    albedo_lin = albedo_lin * (1.0 - c_m) + char_wool[None, None, :] * c_m

    # Add realistic coarse yarn variation, sweat/dust mottling & wool-fuzz contrast
    patina = np.clip((stain - 0.42) * 1.4, 0.0, 1.0)
    albedo_lin *= (0.85 + 0.24 * weave_h[:, :, None] + 0.14 * (fuzz[:, :, None] - 0.5))
    albedo_lin *= (1.0 - 0.22 * patina[:, :, None])
    albedo_lin = np.clip(albedo_lin, 0.018, 0.55)

    height = 0.52 * weave_h + 0.22 * fuzz + 0.16 * broad + 0.10 * stain
    normal_dx, z_mean = height_to_normal_dx(height, strength=2.8, smooth_sigma=1.15)

    ao = np.clip(0.84 + 0.16 * weave_h - 0.12 * patina, 0.45, 1.0)
    rough = np.clip(0.86 + 0.09 * (1.0 - weave_h) + 0.05 * fuzz - 0.05 * patina, 0.76, 0.98)
    metal = np.zeros_like(ao)
    orm = np.stack([ao, rough, metal], axis=2)

    save_png(OUT / 'T_StableBlanket_BaseColor.png', linear_to_srgb(albedo_lin))
    save_png(OUT / 'T_StableBlanket_NormalDX.png', normal_dx)
    save_png(OUT / 'T_StableBlanket_ORM.png', orm)
    return dict(
        name='T_StableBlanket',
        size=n,
        albedo_lin_mean=albedo_lin.mean(axis=(0, 1)).round(4).tolist(),
        normal_z_mean=round(z_mean, 4),
        ao_mean=round(float(ao.mean()), 4),
        rough_mean=round(float(rough.mean()), 4),
    )


def main():
    report = dict(
        rope=author_weathered_rope(2048),
        blanket=author_wool_blanket(2048),
    )
    (OUT / 'textures-manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('R44_TEXTURES_OK', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
