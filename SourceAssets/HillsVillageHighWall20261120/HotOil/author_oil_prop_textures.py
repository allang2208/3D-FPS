"""Generate dedicated 1024x1024 tileable PBR texture sets for the Hot Oil props."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

OUT = Path(__file__).resolve().parent / "PropTextures"
SIZE = 1024


def make_maps():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42071)
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

    # 1. OilCastIron: deep charcoal hammered cast iron (#282624-#403C38) with sand-cast pitting & oxide scale.
    hammer = noise(13.0) * 0.65 + noise(5.5) * 0.35
    pits = np.maximum(0.0, noise(1.4) - 1.08)
    micro = noise(2.2)
    oxide = np.clip(0.28 + 0.17 * noise(24.0) + 0.22 * pits, 0.0, 0.80)
    iron_hi = np.array([64.0, 60.0, 56.0])
    iron_lo = np.array([38.0, 36.0, 34.0])
    iron_col = iron_hi * (1.0 - oxide[:, :, None]) + iron_lo * oxide[:, :, None] + hammer[:, :, None] * 6.5 - pits[:, :, None] * 9.0
    iron_h = 0.68 * hammer - 0.92 * pits + 0.12 * micro
    iron_r = np.clip(0.35 + 0.24 * oxide + 0.05 * noise(3.5) + 0.04 * pits, 0.34, 0.62)
    iron_m = np.clip(0.90 - 0.10 * oxide, 0.82, 0.90)
    save("OilCastIron", iron_col, iron_h, iron_r, iron_m, 1.35)

    # 2. OilAgedBrass: burnished antique bronze/brass (#9E7437-#4D381B) with spun/hammered marks.
    tarnish = np.clip((noise(28.0) + 0.45 * noise(6.0) - 0.05) * 0.52, 0.0, 0.85)
    tool = 0.18 * noise((1.2, 11.0)) + 0.19 * noise(3.2)
    brass_hi = np.array([158.0, 116.0, 55.0])
    brass_lo = np.array([77.0, 56.0, 27.0])
    brass_col = brass_hi * (1.0 - tarnish[:, :, None]) + brass_lo * tarnish[:, :, None] + tool[:, :, None] * 7.5
    brass_h = tool - 0.34 * tarnish
    brass_r = np.clip(0.26 + 0.26 * tarnish + 0.03 * noise(2.0), 0.26, 0.52)
    brass_m = np.clip(0.92 - 0.09 * tarnish, 0.85, 0.92)
    save("OilAgedBrass", brass_col, brass_h, brass_r, brass_m, 1.05)

    # 3. OilCharredOak: heat-darkened oiled hardwood (#3B2515-#6B4527) with fibers along UV V.
    fine = noise((9.0, 1.1))
    drift = noise((68.0, 24.0))
    rings = np.sin(2.0 * np.pi * (x * 16.0 + 0.22 * drift + 0.26 * np.sin(2.0 * np.pi * (3.0 * x + y))))
    pores = np.maximum(0.0, fine - 0.58)
    grain = 0.42 * rings + 0.20 * noise((22.0, 2.6)) - 0.58 * pores
    wood_mid = np.array([84.0, 54.0, 31.0])
    oak_col = wood_mid + grain[:, :, None] * np.array([23.0, 15.0, 9.0]) + drift[:, :, None] * 3.0
    oak_col = np.clip(oak_col, [59.0, 37.0, 21.0], [107.0, 69.0, 39.0])
    oak_r = np.clip(0.46 + 0.08 * rings + 0.07 * pores + 0.03 * noise(4.0), 0.38, 0.62)
    save("OilCharredOak", oak_col, grain, oak_r, 0.0, 1.15)

    # 4. OilHearthEmbers: cracked matte ash & charcoal with incandescent crack heat mask.
    chunk = noise(16.0)
    crackle_base = np.abs(noise(8.5) + 0.35 * noise(3.8))
    glow_cracks = np.power(np.clip(1.0 - crackle_base * 1.45, 0.0, 1.0), 2.1)
    ember_core = np.clip(0.65 * glow_cracks + 0.35 * np.maximum(0.0, -chunk * 0.55), 0.0, 1.0)
    ash_col = np.array([20.0, 17.0, 15.0]) + noise(4.0)[:, :, None] * 5.0
    coal_col = ash_col * (1.0 - 0.35 * ember_core[:, :, None]) + np.array([45.0, 14.0, 4.0]) * ember_core[:, :, None]
    coal_h = 0.65 * chunk - 0.85 * glow_cracks + 0.25 * noise(2.2)
    coal_r = np.clip(0.90 - 0.08 * glow_cracks, 0.78, 0.94)
    save("OilHearthEmbers", coal_col, coal_h, coal_r, 0.0, 1.65, emissive=ember_core)


if __name__ == "__main__":
    make_maps()
    print(f"WROTE PropTextures -> {OUT}")
