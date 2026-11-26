"""Offline audit for the V2 hills height field.

Mirrors TemperateHillsSurface::HeightV2 in Python so the shape can be checked
without launching the game. Units are centimetres, matching the C++ code.

Examples:
  python audit_hills_v2.py --seed 122 --half-m 512 --step-m 2
  python audit_hills_v2.py --seed 122 --half-m 2048 --step-m 4 --image v2.png
"""
import argparse
import numpy as np

U32 = np.uint32
np.seterr(over="ignore")


def mix(v):
    v = v ^ (v >> U32(16))
    v = v * U32(0x7FEB352D)
    v = v ^ (v >> U32(15))
    v = v * U32(0x846CA68B)
    return v ^ (v >> U32(16))


def key(x, y, seed, salt):
    xa = (np.asarray(x, dtype=np.int64) & 0xFFFFFFFF).astype(np.uint32)
    ya = (np.asarray(y, dtype=np.int64) & 0xFFFFFFFF).astype(np.uint32)
    return mix(mix(xa * U32(0x9E3779B9)) ^ mix(ya * U32(0x85EBCA6B) + U32(0x1B873593)) ^ mix(U32(seed & 0xFFFFFFFF) + U32(salt)))


def unit(v):
    return (mix(v) & U32(0x00FFFFFF)).astype(np.float64) / 16777216.0


def quintic(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def noise5(x, y, seed, salt):
    # Fixed 36.87-degree rotation breaks the axis-aligned value-noise lattice.
    rx = x * 0.8 - y * 0.6
    ry = x * 0.6 + y * 0.8
    ix = np.floor(rx).astype(np.int64)
    iy = np.floor(ry).astype(np.int64)
    fx = quintic(rx - ix)
    fy = quintic(ry - iy)

    def v(a, b):
        return unit(key(a, b, seed, salt)) * 2.0 - 1.0

    top = v(ix, iy) + (v(ix + 1, iy) - v(ix, iy)) * fx
    bot = v(ix, iy + 1) + (v(ix + 1, iy + 1) - v(ix, iy + 1)) * fx
    return top + (bot - top) * fy


def fbm(x, y, seed, salt, octaves):
    total = 0.0
    norm = 0.0
    amp = 1.0
    freq = 1.0
    for i in range(octaves):
        total = total + amp * noise5(x * freq + i * 13.7, y * freq - i * 7.3, seed, salt + i * 131)
        norm += amp
        amp *= 0.5
        freq *= 2.03
    return total / norm


def ridged(x, y, seed, salt, octaves):
    total = 0.0
    norm = 0.0
    amp = 1.0
    freq = 1.0
    for i in range(octaves):
        n = 1.0 - np.abs(noise5(x * freq + i * 17.3, y * freq + i * 5.9, seed, salt + i * 197))
        total = total + amp * n * n
        norm += amp
        amp *= 0.5
        freq *= 2.03
    return total / norm


def valley_y(x, seed):
    phase = float(unit(np.array([seed & 0xFFFFFFFF], dtype=np.uint32))[0])
    return 1900.0 * np.sin(x * 0.000065 + phase * 3.0) + 850.0 * np.sin(x * 0.00014)


def smoothstep(a, b, v):
    t = np.clip((v - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def height_v2(x, y, seed):
    c = fbm(x / 140000.0, y / 140000.0, seed, 2101, 4)
    e = fbm(x / 90000.0, y / 90000.0, seed, 2102, 4) * 0.5 + 0.5
    wx = fbm(x / 220000.0, y / 220000.0, seed, 2103, 2) * 12000.0
    wy = fbm(x / 220000.0, y / 220000.0, seed, 2104, 2) * 12000.0
    r = ridged((x + wx) / 52000.0, (y + wy) / 52000.0, seed, 2105, 4)
    d = fbm(x / 6500.0, y / 6500.0, seed, 2106, 3) * 350.0 + fbm(x / 2400.0, y / 2400.0, seed, 2107, 2) * 90.0
    base = 7000.0 + 3500.0 * c
    amp = np.clip(14000.0 + 14000.0 * c, 5000.0, 28000.0) * (1.0 + (0.3 - 1.0) * smoothstep(0.2, 0.8, e))
    valley = 1500.0 * np.exp(-np.square(np.abs(y - valley_y(x, seed)) / 9000.0))
    return np.maximum(150.0, base + amp * (r - 0.35) + d - valley)


def grid(half_cm, step_cm):
    n = int(round(2 * half_cm / step_cm))
    c = -half_cm + step_cm * 0.5 + np.arange(n) * step_cm
    return np.meshgrid(c, c, indexing="xy")


def slope_degrees(h, step_cm):
    gy, gx = np.gradient(h, step_cm)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def summarize(h, step_cm):
    s = slope_degrees(h, step_cm)
    return {
        "min_m": float(h.min() / 100),
        "max_m": float(h.max() / 100),
        "mean_m": float(h.mean() / 100),
        "std_m": float(h.std() / 100),
        "relief_m": float((h.max() - h.min()) / 100),
        "slope_mean_deg": float(s.mean()),
        "slope_p95_deg": float(np.percentile(s, 95)),
        "slope_max_deg": float(s.max()),
        "pct_gt30": float((s > 30).mean() * 100),
        "pct_gt45": float((s > 45).mean() * 100),
    }


def write_image(path, h, step_cm):
    from PIL import Image
    gy, gx = np.gradient(h, step_cm)
    nx, ny, nz = -gx, -gy, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    shade = np.clip((nx / ln * -0.5 + ny / ln * -0.5 + nz / ln * 0.7071) / np.sqrt(0.75), 0, 1)
    lo, hi = np.percentile(h, 1), np.percentile(h, 99)
    t = np.clip((h - lo) / max(1e-9, hi - lo), 0, 1)
    stops = np.array([[0.0, 74, 104, 78], [0.35, 110, 135, 88], [0.6, 150, 148, 107], [0.82, 168, 158, 148], [1.0, 232, 232, 226]])
    rgb = np.zeros(h.shape + (3,))
    for i in range(len(stops) - 1):
        a, b = stops[i], stops[i + 1]
        m = (t >= a[0]) & (t <= b[0] if i == len(stops) - 2 else t < b[0])
        if m.any():
            f = (t[m] - a[0]) / (b[0] - a[0])
            rgb[m] = a[1:] + (b[1:] - a[1:]) * f[:, None]
    rgb *= (0.55 + 0.75 * shade)[..., None]
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(path)


def main():
    parser = argparse.ArgumentParser(description="Audit the Temperate Hills V2 height field offline.")
    parser.add_argument("--seed", type=int, default=122)
    parser.add_argument("--half-m", type=float, default=512.0, help="half extent in metres")
    parser.add_argument("--step-m", type=float, default=2.0, help="sample spacing in metres")
    parser.add_argument("--image", default="", help="optional PNG output path")
    args = parser.parse_args()
    x, y = grid(args.half_m * 100.0, args.step_m * 100.0)
    h = height_v2(x, y, args.seed)
    stats = summarize(h, args.step_m * 100.0)
    print(f"seed={args.seed} size={2 * args.half_m:.1f}m step={args.step_m:g}m")
    for k, v in stats.items():
        print(f"  {k}: {v:.4f}")
    if args.image:
        write_image(args.image, h, args.step_m * 100.0)
        print(f"image: {args.image}")


if __name__ == "__main__":
    main()