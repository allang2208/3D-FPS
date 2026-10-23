import os
import numpy as np
from PIL import Image

ROOT = r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019"
OUT = os.path.join(ROOT, "Textures", "detail_v2")
os.makedirs(OUT, exist_ok=True)
N = 1024
rng = np.random.default_rng(20261019)
yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N * (2.0 * np.pi)


def periodic_noise(count, fmin, fmax, amp):
    h = np.zeros((N, N), np.float32)
    for _ in range(count):
        kx = int(rng.integers(fmin, fmax + 1))
        ky = int(rng.integers(fmin, fmax + 1))
        px, py = rng.uniform(0, 2 * np.pi, 2)
        h += amp * np.sin(kx * xx + px) * np.sin(ky * yy + py)
    return h


def normal_from_height(h, strength):
    dx, dy = np.gradient(h)
    nx = -dx * strength
    ny = -dy * strength
    nz = np.ones_like(h)
    length = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / length, ny / length, nz / length
    # UE/DirectX tangent normal: green channel points down.
    ny = -ny
    rgb = np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], axis=-1)
    return np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)


def save(mat, h, strength, rough):
    Image.fromarray(normal_from_height(h, strength)).save(os.path.join(OUT, "detail_%s_Normal.png" % mat))
    r = np.clip(rough * 255.0 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(r).save(os.path.join(OUT, "detail_%s_Roughness.png" % mat))
    print("ALICE_DETAIL_TEX", mat, "normal", "rough_mean", round(float(rough.mean()), 3))


# Canvas: plain weave at ~48 threads per tile, bundle variation and fuzz.
h = 0.62 * np.sin(48 * xx) * np.sin(48 * yy)
h += 0.18 * np.sin(9 * xx + 0.7) * np.sin(9 * yy + 1.9)
h += periodic_noise(22, 3, 30, 0.035)
r = 0.79 + 0.045 * np.sin(9 * xx + 0.7) * np.sin(9 * yy + 1.9) + periodic_noise(18, 4, 26, 0.022)
save("Canvas", h, 2.2, r)

# Webbing: dense warp/weft ribs plus small fuzz.
h = 0.70 * np.sin(64 * xx) * np.sin(64 * yy)
h += 0.22 * np.sin(16 * xx) * np.sin(16 * yy + 0.4)
h += periodic_noise(18, 5, 34, 0.03)
r = 0.72 + 0.06 * np.sin(16 * xx) * np.sin(16 * yy + 0.4) + periodic_noise(16, 4, 28, 0.025)
save("Webbing", h, 1.2, r)

# Leather: periodic pebble grain + broad creases.
h = np.zeros((N, N), np.float32)
for _ in range(240):
    cx, cy = rng.uniform(0, 1, 2)
    sigma = rng.uniform(0.004, 0.018)
    amp = rng.uniform(0.25, 1.0)
    dx = np.minimum(np.abs(xx / (2 * np.pi) - cx), 1 - np.abs(xx / (2 * np.pi) - cx))
    dy = np.minimum(np.abs(yy / (2 * np.pi) - cy), 1 - np.abs(yy / (2 * np.pi) - cy))
    h += amp * np.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))
h += 0.22 * np.sin(7 * xx + 0.3) * np.sin(5 * yy + 1.2)
h += periodic_noise(24, 3, 40, 0.025)
r = 0.56 + 0.06 * np.sin(7 * xx + 0.3) * np.sin(5 * yy + 1.2) + periodic_noise(20, 4, 30, 0.03)
save("Leather", h, 4.5, r)

# Metal: horizontal brushing plus sparse scratches.
h = 0.08 * np.sin(220 * yy + 0.4 * np.sin(11 * xx))
h += periodic_noise(30, 2, 60, 0.035)
for _ in range(40):
    # A scratch is a short slanted line; keep low amplitude.
    cx, cy = rng.uniform(0, N, 2)
    length = rng.uniform(20, 120)
    angle = rng.uniform(-0.35, 0.35)
    xline = np.arange(N)[None, :]
    yline = cy + (xline - cx) * np.tan(angle)
    mask = (xline > cx - length / 2) & (xline < cx + length / 2)
    h += 0.03 * np.exp(-((yy - yline) / 1.2) ** 2) * mask
r = 0.34 + 0.05 * np.sin(220 * yy) + periodic_noise(18, 3, 40, 0.035)
save("Metal", h, 2.2, np.clip(r, 0.22, 0.52))
