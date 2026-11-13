"""Longitudinal crimson ribbon, with matched color and material regions."""
import numpy as np


def smooth(a, b, x):
    s = np.clip((x - a) / (b - a), 0, 1)
    return s * s * (3 - 2 * s)


def build_maps(nx=1024, ny=4096):
    u = np.linspace(0, 1, nx, dtype=np.float32)[None, :]
    t = np.linspace(0, 1, ny, dtype=np.float32)[:, None]
    rng = np.random.default_rng(181018)
    grain = (np.sin(u * 2950 + np.sin(t * 13) * 1.1) + .45 * np.sin(u * 7411 + t * 9)) * .007
    noise = rng.normal(0, .004, (ny, nx)).astype(np.float32)
    cloud = (np.sin(u * 51 + t * 37) + np.sin(u * 17 - t * 58)) * .008
    variation = grain + noise + cloud
    color = np.empty((ny, nx, 3), dtype=np.float32)
    color[:] = [.20, .22, .235]
    color += variation[:, :, None]
    silver = smooth(.755, .773, u) + (1 - smooth(.025, .045, u))
    color = color * (1 - silver[:, :, None]) + np.clip(
        np.array([.59, .61, .63]) + variation[:, :, None] * 1.5, 0, 1) * silver[:, :, None]
    # The old ribbon occupied u=.052..128. Widen toward the broad face, while
    # easing its shoulder and tapering before the narrow tip. Keep the edge free.
    outer = .095 + .170 * smooth(.06, .24, t) * (1 - smooth(.74, .97, t))
    gate = smooth(.065, .105, t) * (1 - smooth(.91, .97, t))
    band = smooth(.048, .054, u) * (1 - smooth(outer - .005, outer + .005, u)) * gate
    red = np.clip(np.array([.25, .038, .033]) + variation[:, :, None] * np.array([2, .4, .4]), .006, 1)
    color = color * (1 - band[:, :, None]) + red * band[:, :, None]
    rail = (np.exp(-((u - .043) / .0018) ** 2) + np.exp(-((u - outer - .008) / .0018) ** 2)) * gate
    color = color * (1 - rail[:, :, None]) + np.array([.51, .34, .135]) * rail[:, :, None]
    rough = np.clip(.40 + noise * 2 + cloud * .8 - silver * .12 - band * .13, .18, .6)
    metal = np.clip(np.ones((ny, nx), dtype=np.float32) * .98 - band * .25, 0, 1)
    alpha = np.ones((ny, nx, 1), dtype=np.float32)
    return {'BaseColor': np.concatenate([np.clip(color, 0, 1), alpha], axis=2),
            'ORM': np.stack([alpha[:, :, 0], rough, metal, alpha[:, :, 0]], axis=2)}
