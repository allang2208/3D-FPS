"""Generate 6 dedicated 1024x1024 tileable & optic PBR texture sets for SM_SmartTurret (Scheme B)."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

OUT = Path(__file__).resolve().parent / "PropTextures"
SIZE = 1024


def make_maps():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(20261127)
    y, x = np.mgrid[:SIZE, :SIZE] / float(SIZE)

    def noise(sigma):
        n = gaussian_filter(rng.normal(size=(SIZE, SIZE)), sigma, mode="wrap")
        return n / max(n.std(), 1e-8)

    def save(slot, color, height, rough, metal, strength, emissive=None):
        def image(name, values):
            pixels = np.rint(np.clip(values, 0.0, 1.0) * 255.0).astype(np.uint8)
            Image.fromarray(pixels).save(OUT / f"{slot}_{name}.png")

        dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * 0.5 * strength
        dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * 0.5 * strength
        length = np.sqrt(1.0 + dx * dx + dy * dy)
        image("base_color", color / 255.0)
        image("normal", np.stack((-dx / length, dy / length, 1.0 / length), axis=-1) * 0.5 + 0.5)
        image("roughness", rough)
        image("metallic", np.broadcast_to(metal, (SIZE, SIZE)))
        if emissive is not None:
            image("emissive", emissive)

    # 1. TurretStone: weathered dark fortress basalt masonry (#363B42 - #5E6570)
    strata = noise((20.0, 7.0)) * 0.52 + noise(6.0) * 0.30 + noise(2.2) * 0.18
    fissure = np.clip(1.0 - np.abs(noise(13.0) + 0.28 * noise(4.0)) * 4.4, 0.0, 1.0)
    chisel = np.maximum(0.0, noise(2.4) - 0.85)
    speck = noise(1.2)
    stone_hi = np.array([94.0, 100.0, 108.0])
    stone_lo = np.array([54.0, 58.0, 66.0])
    stone_t = np.clip(0.5 + 0.24 * strata, 0.0, 1.0)
    stone_col = (
        stone_lo * (1.0 - stone_t[:, :, None])
        + stone_hi * stone_t[:, :, None]
        - fissure[:, :, None] * 18.0
        - chisel[:, :, None] * 7.0
        + speck[:, :, None] * 2.8
    )
    stone_h = 0.52 * strata - 1.25 * fissure - 0.35 * chisel + 0.16 * speck
    stone_r = np.clip(0.76 + 0.07 * strata + 0.10 * fissure + 0.03 * speck, 0.68, 0.91)
    save("TurretStone", stone_col, stone_h, stone_r, 0.0, 1.55)

    # 2. TurretCastIron: blackened forged wrought iron (#20242A - #3C424B) with forge scale & hammer dimples
    hammer = noise(11.0) * 0.60 + noise(4.5) * 0.40
    pits = np.maximum(0.0, noise(1.5) - 1.0)
    oxide = np.clip(0.28 + 0.20 * noise(24.0) + 0.22 * pits, 0.0, 0.80)
    iron_hi = np.array([62.0, 68.0, 77.0])
    iron_lo = np.array([31.0, 35.0, 41.0])
    iron_col = (
        iron_hi * (1.0 - oxide[:, :, None])
        + iron_lo * oxide[:, :, None]
        + hammer[:, :, None] * 6.5
        - pits[:, :, None] * 9.0
    )
    iron_h = 0.62 * hammer - 0.95 * pits + 0.14 * noise(1.8)
    iron_r = np.clip(0.35 + 0.18 * oxide + 0.04 * noise(3.5) + 0.04 * pits, 0.32, 0.56)
    iron_m = np.clip(0.89 - 0.07 * oxide, 0.82, 0.90)
    save("TurretCastIron", iron_col, iron_h, iron_r, iron_m, 1.40)

    # 3. TurretBrass: antique brushed copper-brass (#78592C - #C8994C) with crisp machined grain & subtle tarnish
    brush = noise((2.0, 26.0)) * 0.62 + np.sin(2.0 * np.pi * y * 48.0) * 0.18
    tarnish = np.clip((noise(28.0) + 0.35 * noise(8.0) - 0.15) * 0.26, 0.0, 0.48)
    patina = np.clip((noise(24.0) - 1.35) * 0.65, 0.0, 0.20)
    brass_hi = np.array([200.0, 153.0, 76.0])
    brass_lo = np.array([118.0, 88.0, 44.0])
    verde = np.array([68.0, 112.0, 96.0])
    br_col = brass_hi * (1.0 - tarnish[:, :, None]) + brass_lo * tarnish[:, :, None] + brush[:, :, None] * 6.5
    br_col = br_col * (1.0 - patina[:, :, None]) + verde * patina[:, :, None]
    br_h = 0.26 * brush + 0.12 * noise(3.0) - 0.18 * tarnish
    br_r = np.clip(0.24 + 0.13 * tarnish + 0.18 * patina - 0.03 * brush, 0.21, 0.44)
    br_m = np.clip(0.94 - 0.06 * tarnish - 0.35 * patina, 0.60, 0.94)
    save("TurretBrass", br_col, br_h, br_r, br_m, 1.05)

    # 4. TurretGunmetal: precision cold-steel dark parkerized gunmetal (#303741 - #525C6B)
    milled = noise((28.0, 2.2)) * 0.55 + noise(3.5) * 0.25 + np.sin(2.0 * np.pi * x * 64.0) * 0.10
    wear = np.clip((noise(16.0) - 0.35) * 0.42, 0.0, 0.55)
    gm_lo = np.array([48.0, 55.0, 65.0])
    gm_hi = np.array([82.0, 92.0, 107.0])
    gm_col = gm_lo * (1.0 - wear[:, :, None]) + gm_hi * wear[:, :, None] + milled[:, :, None] * 6.0
    gm_h = 0.24 * milled + 0.10 * noise(1.6)
    gm_r = np.clip(0.30 + 0.10 * (1.0 - wear) + 0.03 * milled, 0.26, 0.44)
    gm_m = np.clip(0.88 + 0.04 * wear, 0.84, 0.92)
    save("TurretGunmetal", gm_col, gm_h, gm_r, gm_m, 0.85)

    # 5. TurretSteelChrome: honed bright stainless steel (#9FA8B4 - #D6DEE8) for springs, pistons, rails
    polish = noise((32.0, 1.8)) * 0.65 + noise(4.0) * 0.20
    st_lo = np.array([159.0, 168.0, 180.0])
    st_hi = np.array([214.0, 222.0, 232.0])
    st_t = np.clip(0.5 + 0.25 * polish, 0.0, 1.0)
    st_col = st_lo * (1.0 - st_t[:, :, None]) + st_hi * st_t[:, :, None]
    st_h = 0.16 * polish + 0.05 * noise(1.4)
    st_r = np.clip(0.18 + 0.05 * (1.0 - st_t) + 0.02 * noise(2.5), 0.14, 0.28)
    save("TurretSteelChrome", st_col, st_h, st_r, 0.96, 0.55)

    # 6. TurretOpticGlow: UV [0,1]x[0,1] sapphire targeting optic with obsidian bezel & concentric reticle
    dx_c = x - 0.5
    dy_c = y - 0.5
    rad = np.sqrt(dx_c * dx_c + dy_c * dy_c)
    ang = np.arctan2(dy_c, dx_c)

    in_lens = rad < 0.42
    bezel = np.clip((rad - 0.415) / 0.015, 0.0, 1.0)
    chamfer = np.exp(-((rad - 0.425) / 0.022) ** 2)

    # Radial glow peaking in center & subtle Fresnel inner ring + faint 4-tick reticle
    core_grad = np.clip(1.0 - (rad / 0.42) ** 1.75, 0.0, 1.0)
    inner_ring = np.exp(-((rad - 0.27) / 0.012) ** 2) * 0.55
    reticle_cross = (
        np.exp(-(np.abs(dx_c) / 0.006) ** 2) + np.exp(-(np.abs(dy_c) / 0.006) ** 2)
    ) * ((rad > 0.11) & (rad < 0.36)).astype(float) * 0.42
    caustic = 0.08 * np.sin(8.0 * ang + 18.0 * rad) * np.clip(1.0 - rad / 0.40, 0.0, 1.0)

    em_mask = np.where(
        in_lens,
        np.clip(0.32 + 0.68 * core_grad + inner_ring + reticle_cross + caustic, 0.0, 1.0),
        0.0,
    )
    # Softly fade outer rim inside bezel
    em_mask *= np.clip((0.42 - rad) / 0.025, 0.0, 1.0)

    bezel_col = np.array([26.0, 31.0, 38.0]) + noise(3.5)[:, :, None] * 4.0
    sapphire_edge = np.array([18.0, 86.0, 138.0])
    sapphire_core = np.array([68.0, 232.0, 255.0])
    lens_col = sapphire_edge * (1.0 - core_grad[:, :, None]) + sapphire_core * core_grad[:, :, None]
    opt_col = lens_col * (1.0 - bezel[:, :, None]) + bezel_col * bezel[:, :, None]

    opt_h = np.where(in_lens, -0.30 * (1.0 - (rad / 0.42) ** 2), 0.35 - 0.45 * chamfer) + 0.05 * noise(4.0)
    opt_r = np.where(in_lens, 0.07 + 0.03 * (rad / 0.42), 0.34)
    opt_m = np.where(in_lens, 0.05, 0.86)
    save("TurretOpticGlow", opt_col, opt_h, opt_r, opt_m, 1.10, emissive=em_mask)


if __name__ == "__main__":
    make_maps()
    print(f"WROTE SmartTurret PropTextures -> {OUT}")
