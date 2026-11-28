"""Generate 6 dedicated 1024x1024 tileable PBR texture sets for SM_LightningSpire."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

OUT = Path(__file__).resolve().parent / "PropTextures"
SIZE = 1024


def make_maps():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(73197)
    y, x = np.mgrid[:SIZE, :SIZE] / SIZE

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

    # 1. SpireStone: cool dark fortress basalt (#343942 - #505866) with carved grain & hairline fissures.
    strata = noise((18.0, 6.0)) * 0.55 + noise(5.0) * 0.30 + noise(2.0) * 0.15
    fissure = np.clip(1.0 - np.abs(noise(11.0) + 0.25 * noise(3.5)) * 4.2, 0.0, 1.0)
    speck = noise(1.3)
    stone_hi = np.array([82.0, 90.0, 102.0])
    stone_lo = np.array([50.0, 56.0, 66.0])
    stone_t = np.clip(0.5 + 0.22 * strata, 0.0, 1.0)
    stone_col = (
        stone_lo * (1.0 - stone_t[:, :, None])
        + stone_hi * stone_t[:, :, None]
        - fissure[:, :, None] * 16.0
        + speck[:, :, None] * 2.5
    )
    stone_h = 0.55 * strata - 1.15 * fissure + 0.14 * speck
    stone_r = np.clip(0.74 + 0.07 * strata + 0.10 * fissure + 0.03 * speck, 0.66, 0.88)
    save("SpireStone", stone_col, stone_h, stone_r, 0.0, 1.45)

    # 2. SpireCastIron: blackened hammered wrought iron (#22262C - #3D434C) with forge scale.
    hammer = noise(12.0) * 0.62 + noise(4.8) * 0.38
    pits = np.maximum(0.0, noise(1.4) - 1.05)
    oxide = np.clip(0.26 + 0.18 * noise(22.0) + 0.24 * pits, 0.0, 0.78)
    iron_hi = np.array([61.0, 67.0, 76.0])
    iron_lo = np.array([34.0, 38.0, 44.0])
    iron_col = iron_hi * (1.0 - oxide[:, :, None]) + iron_lo * oxide[:, :, None] + hammer[:, :, None] * 6.0 - pits[:, :, None] * 8.0
    iron_h = 0.65 * hammer - 0.90 * pits + 0.12 * noise(2.0)
    iron_r = np.clip(0.33 + 0.20 * oxide + 0.04 * noise(3.5) + 0.04 * pits, 0.32, 0.56)
    iron_m = np.clip(0.89 - 0.07 * oxide, 0.82, 0.90)
    save("SpireCastIron", iron_col, iron_h, iron_r, iron_m, 1.35)

    # 3. SpireCopperBrass: antique coiled copper-brass (#BA803E - #5B3E1B) with fine windings & verdigris.
    windings = np.sin(2.0 * np.pi * (y * 26.0 + 0.06 * noise(18.0))) * 0.5 + np.sin(2.0 * np.pi * y * 52.0) * 0.18
    tarnish = np.clip((noise(24.0) + 0.45 * noise(6.0) - 0.12) * 0.48, 0.0, 0.78)
    verdigris = np.clip((noise(19.0) - 0.95) * 0.9, 0.0, 0.42) * np.clip(0.5 - 0.5 * windings, 0.15, 1.0)
    copper_hi = np.array([186.0, 128.0, 62.0])
    copper_lo = np.array([91.0, 62.0, 27.0])
    patina = np.array([56.0, 108.0, 96.0])
    cu_col = copper_hi * (1.0 - tarnish[:, :, None]) + copper_lo * tarnish[:, :, None] + windings[:, :, None] * 9.0
    cu_col = cu_col * (1.0 - verdigris[:, :, None]) + patina * verdigris[:, :, None]
    cu_h = 0.42 * windings + 0.16 * noise(3.0) - 0.30 * tarnish
    cu_r = np.clip(0.24 + 0.18 * tarnish + 0.24 * verdigris - 0.04 * windings, 0.22, 0.52)
    cu_m = np.clip(0.94 - 0.08 * tarnish - 0.45 * verdigris, 0.48, 0.94)
    save("SpireCopperBrass", cu_col, cu_h, cu_r, cu_m, 1.25)

    # 4. SpireInsulator: dark glazed porcelain ceramic (#1B222C - #2F3B4A) with faint kiln ripples.
    glaze = noise(28.0) * 0.55 + noise(8.0) * 0.45
    micro_g = noise(2.5)
    ins_hi = np.array([47.0, 59.0, 74.0])
    ins_lo = np.array([27.0, 34.0, 44.0])
    ins_t = np.clip(0.5 + 0.25 * glaze, 0.0, 1.0)
    ins_col = ins_lo * (1.0 - ins_t[:, :, None]) + ins_hi * ins_t[:, :, None]
    ins_h = 0.25 * glaze + 0.06 * micro_g
    ins_r = np.clip(0.18 + 0.04 * glaze + 0.015 * micro_g, 0.15, 0.26)
    save("SpireInsulator", ins_col, ins_h, ins_r, 0.05, 0.55)

    # 5. SpireRuneGlow: dark etched obsidian-iron (#181E28) with crisp arcane lightning rune glyphs & circuits.
    u = np.mod(x * 2.0, 1.0)
    v = np.mod(y * 2.0, 1.0)
    du = np.abs(u - 0.5)
    dv = np.abs(v - 0.5)
    frame = np.clip(1.0 - np.abs(np.maximum(du, dv) - 0.42) * 58.0, 0.0, 1.0)
    diamond = np.clip(1.0 - np.abs((du + dv) - 0.28) * 65.0, 0.0, 1.0)
    inner_hex = np.clip(1.0 - np.abs(np.maximum(du * 0.95, (du + dv * 0.58) * 0.72) - 0.14) * 72.0, 0.0, 1.0)
    bolt_line = np.clip(
        1.0 - np.abs((u - 0.5) - 0.08 * np.sign(np.sin(2.0 * np.pi * v * 3.0)) * (1.0 - 2.0 * np.abs(v - 0.5))) * 75.0,
        0.0,
        1.0,
    ) * ((dv < 0.34).astype(float))
    bus_h = np.clip(1.0 - np.abs(v - 0.5) * 90.0, 0.0, 1.0) * ((du > 0.22) & (du < 0.42)).astype(float)
    rune_mask = np.clip(np.maximum.reduce([frame * 0.82, diamond, inner_hex, bolt_line, bus_h * 0.85]), 0.0, 1.0)
    plate_col = np.array([24.0, 30.0, 40.0]) + noise(4.5)[:, :, None] * 4.5
    rune_tint = np.array([48.0, 192.0, 255.0])
    rg_col = plate_col * (1.0 - rune_mask[:, :, None]) + rune_tint * rune_mask[:, :, None]
    rg_h = 0.22 * noise(6.0) - 0.95 * rune_mask
    rg_r = np.clip(0.40 - 0.22 * rune_mask + 0.04 * noise(3.0), 0.16, 0.48)
    rg_m = np.clip(0.76 - 0.70 * rune_mask, 0.06, 0.80)
    save("SpireRuneGlow", rg_col, rg_h, rg_r, rg_m, 1.65, emissive=rune_mask)

    # 6. SpireCrystal: deep faceted sapphire-indigo crystal (#112A52 - #2E74C4) + crisp glowing veins.
    facet = np.abs(np.sin(2.0 * np.pi * (x * 4.0 + 0.45 * y + 0.08 * noise(24.0))))
    veins = np.power(np.clip(1.0 - np.abs(noise(7.5) + 0.35 * noise(3.0)) * 2.2, 0.0, 1.0), 2.3)
    crys_lo = np.array([17.0, 42.0, 82.0])
    crys_hi = np.array([46.0, 116.0, 196.0])
    crys_col = crys_lo * (1.0 - facet[:, :, None]) + crys_hi * facet[:, :, None] + veins[:, :, None] * np.array([75.0, 145.0, 190.0])
    crys_h = 0.50 * facet + 0.20 * noise(3.5) - 0.45 * veins
    crys_r = np.clip(0.11 + 0.05 * (1.0 - facet) + 0.02 * noise(2.5), 0.08, 0.18)
    crys_em = np.clip(0.28 + 0.72 * veins, 0.0, 1.0)
    save("SpireCrystal", crys_col, crys_h, crys_r, 0.08, 0.95, emissive=crys_em)


if __name__ == "__main__":
    make_maps()
    print(f"WROTE PropTextures -> {OUT}")
