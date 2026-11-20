"""Bake tileable split-hide, fabric, cord and moulded finishes at 4 cm scale."""
import hashlib
import json

import numpy as np
from PIL import Image

from field_pants_textures import noise, yarn
from ridge_boots_materials import ROOT, SURFACES, TILE_CM


def create_tile(kind, seed):
    colour, mean_rough, _, n = SURFACES[kind]
    rng = np.random.default_rng(seed)
    y, x = (np.indices((n, n), dtype=np.float32) + .5) / n
    grain = noise(rng, n, n / 800)
    fibre = noise(rng, n, .65)
    broad = noise(rng, n, n / 40)
    micro = noise(rng, n, n / 255)
    albedo = .012 * broad + .011 * grain
    rough = mean_rough + .014 * grain + .009 * broad
    metal = np.zeros_like(x)
    ao = np.full_like(x, .998)
    tau = 2 * np.pi

    if kind == "Suede":
        # Local changes of nap direction are visible in diffuse and grazing light.
        nap_a = noise(rng, n, (n / 900, n / 310))
        nap_b = noise(rng, n, (n / 380, n / 920))
        tangent = .5 + .43 * np.tanh(broad)
        nap = tangent * nap_a + (1 - tangent) * nap_b
        height = .0028 * nap + .0014 * micro + .00085 * fibre
        albedo += .026 * nap + .016 * micro + .010 * broad
        rough += .022 * np.tanh(nap) + .010 * micro
    elif kind == "Textile":
        # The shaft uses prominent basket-weave bundles, visible at boot scale.
        warp, weft = x * 52 + .023 * micro, y * 48 + .032 * broad
        cloth = .76 * yarn(warp, weft) + .24 * yarn(2 * warp, 2 * weft)
        height = .019 * cloth + .0009 * fibre
        albedo += .25 * (cloth - .5)
        ao = .925 + .074 * cloth
        rough += .021 * (1 - cloth)
    elif kind == "Lining":
        course = y * 72
        wale = x * 86 + .23 * np.sin(tau * course)
        knit = .5 + .29 * np.cos(tau * wale) + .21 * np.cos(tau * course + .6 * np.sin(tau * wale))
        height = .013 * knit + .0009 * grain
        albedo += .13 * (knit - .5)
        rough += .017 * knit
        ao = .948 + .050 * knit
    elif kind in ("Lace", "Thread"):
        # Two crossing bundles over and under along a cord; each contains finer filaments.
        u, v = x * 18 + y * 13, x * 18 - y * 13
        if kind == "Thread":
            twist = .5 + .5 * np.cos(tau * (x * 32 + y * 17) + .10 * grain)
        else:
            twist = .77 * yarn(u, v) + .23 * yarn(3 * u, 3 * v)
        height = .013 * twist + .00085 * fibre
        albedo += .145 * (twist - .5)
        ao = .950 + .049 * twist
        rough += .019 * (1 - twist)
    elif kind == "Frame":
        # Shallow orange peel catches grazing light along the moulded quarter frame.
        pebble = np.tanh(.9 * micro + .45 * grain)
        height = .0032 * pebble + .0008 * fibre
        albedo += .012 * pebble
        rough += .029 * pebble
    elif kind == "Outsole":
        pores = np.maximum(0, grain - .58)
        height = .0023 * micro - .0031 * pores + .0013 * fibre
        albedo += .021 * micro - .027 * pores
        rough += .018 * micro + .016 * pores
        ao = 1 - .018 * pores
    else:
        height = .0007 * grain + .00045 * fibre
        albedo += .006 * micro
        rough += .026 * micro
        metal[:] = .17

    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * n / (2 * TILE_CM)
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * n / (2 * TILE_CM)
    normal = np.stack((-dx, dy, np.ones_like(dx)), axis=2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    rgb = np.asarray(colour, dtype=np.float32) * (1 + albedo[..., None])
    orm = np.stack((ao, np.clip(rough, .1, .99), metal), axis=2)
    return {"BaseColor": rgb, "NormalGL": (normal + 1) * 127.5, "ORM": orm * 255}


def main():
    destination = ROOT / "Textures"
    destination.mkdir(exist_ok=True, parents=True)
    report = {}
    for i, (kind, (colour, rough, sheen, size)) in enumerate(SURFACES.items()):
        checksums = {}
        for channel, values in create_tile(kind, 181180 + i * 37).items():
            path = destination / f"RB_{kind}_{channel}.png"
            Image.fromarray(np.uint8(np.clip(np.rint(values), 0, 255))).save(path, compress_level=4)
            checksums[channel] = hashlib.sha256(path.read_bytes()).hexdigest()
        report[kind] = dict(resolution=size, tile_cm=TILE_CM, roughness=rough, specular=.29,
                            sheen=sheen, base_srgb=colour, sha256=checksums)
    (ROOT / "surfaces.json").write_text(json.dumps(report, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
