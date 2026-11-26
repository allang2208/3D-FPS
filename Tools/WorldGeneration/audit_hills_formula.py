"""Offline replica and audit of the temperate-hills base height formula.

Mirrors Source/FPSGAME/WorldGeneration/TemperateHillsSurface.h exactly:
  32-bit hash -> 24-bit unit -> smoothstep bilinear value noise.
X/Y are centimetres, matching the game code; no engine types are used.

This samples the *base* formula only. It does not include the river carve,
terrain edits, PCG placement or rendering, so the numbers describe the
height field the rest of the system is built on.

Usage:
  python audit_hills_formula.py
  python audit_hills_formula.py --seed 122 --out D:/tmp/hills-audit
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

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
    tx = mix(xa * U32(0x9E3779B9))
    ty = mix(ya * U32(0x85EBCA6B) + U32(0x1B873593))
    ts = mix(U32(seed & 0xFFFFFFFF) + U32(salt))
    return mix(tx ^ ty ^ ts)


def unit(v):
    return (mix(v) & U32(0x00FFFFFF)).astype(np.float64) / 16777216.0


def smooth(t):
    return t * t * (3.0 - 2.0 * t)


def noise(x, y, seed, salt):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    ix = np.floor(x).astype(np.int64)
    iy = np.floor(y).astype(np.int64)
    fx = smooth(x - ix)
    fy = smooth(y - iy)

    def v(a, b):
        return unit(key(a, b, seed, salt)) * 2.0 - 1.0

    top = v(ix, iy) + (v(ix + 1, iy) - v(ix, iy)) * fx
    bot = v(ix, iy + 1) + (v(ix + 1, iy + 1) - v(ix, iy + 1)) * fx
    return top + (bot - top) * fy


def valley_y(x, seed):
    phase = float(unit(np.array([seed & 0xFFFFFFFF], dtype=np.uint32))[0])
    return 1900.0 * np.sin(x * 0.000065 + phase * 3.0) + 850.0 * np.sin(x * 0.00014)


def height_parts(x, y, seed):
    warp = noise(x * 0.000024, y * 0.000024, seed, 14) * 4200.0
    hill = noise((x + warp) * 0.000055, (y - warp * 0.5) * 0.000055, seed, 73)
    large = noise(x * 0.000020 + 1.31, y * 0.000020 - 2.1, seed, 91)
    valley = np.exp(-np.square(np.abs(y - valley_y(x, seed)) / 9000.0))
    d1 = noise(x * 0.00035, y * 0.00035, seed, 26) * 95.0
    d2 = noise(x * 0.0011, y * 0.0011, seed, 88) * 14.0
    h = 5400.0 + large * 3200.0 + hill * 2400.0 - valley * 1200.0 + d1 + d2
    return h, {"warp": warp, "hill": hill, "large": large, "valley": valley, "detail": d1 + d2}


def grid(half_cm, step_cm, offset_cm=None):
    n = int(round(2 * half_cm / step_cm))
    offset = step_cm * 0.5 if offset_cm is None else offset_cm
    c = -half_cm + offset + np.arange(n) * step_cm
    return np.meshgrid(c, c, indexing="xy")


def stats(h):
    return {
        "min_m": float(h.min() / 100),
        "max_m": float(h.max() / 100),
        "mean_m": float(h.mean() / 100),
        "std_m": float(h.std() / 100),
        "p01_m": float(np.percentile(h, 1) / 100),
        "p99_m": float(np.percentile(h, 99) / 100),
        "relief_m": float((h.max() - h.min()) / 100),
    }


def slope_deg(h, step_cm):
    gy, gx = np.gradient(h, step_cm)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def psd(h, step_cm):
    a = h - h.mean()
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    f = np.abs(np.fft.fftshift(np.fft.fft2(a * win))) ** 2
    fy = np.fft.fftshift(np.fft.fftfreq(a.shape[0], d=step_cm))
    fx = np.fft.fftshift(np.fft.fftfreq(a.shape[1], d=step_cm))
    k = np.hypot(*np.meshgrid(fx, fy, indexing="xy"))
    with np.errstate(divide="ignore"):
        wl = np.where(k > 0, 1.0 / k, np.inf)
    edges_m = [0, 6, 12, 25, 50, 100, 200, 400, 800, np.inf]
    total = f.sum()
    out = {}
    for i in range(len(edges_m) - 1):
        lo, hi = edges_m[i] * 100, edges_m[i + 1] * 100
        m = (wl >= lo) & (wl < hi)
        label = f"{edges_m[i]}-{edges_m[i+1]}m" if np.isfinite(edges_m[i + 1]) else f">{edges_m[i]}m"
        out[label] = float(f[m].sum() / total)
    return out


def lattice_bias(h, step_cm, freq_per_cm, offset=0.0, axis="x"):
    """Mean |dH/dx| near value-noise lattice lines vs mid-cell, one octave."""
    n = h.shape[1] if axis == "x" else h.shape[0]
    coord_cm = -(n * step_cm) / 2 + (np.arange(n) + 0.5) * step_cm
    gy, gx = np.gradient(h, step_cm)
    g = np.abs(gx if axis == "x" else gy)
    phase = np.mod(coord_cm * freq_per_cm + offset, 1.0)
    near = np.minimum(phase, 1 - phase) < 0.06
    mid = np.abs(phase - 0.5) < 0.06
    prof = g.mean(axis=0)
    return {
        "near_lattice": float(prof[near].mean()),
        "mid_cell": float(prof[mid].mean()),
        "ratio_near_over_mid": float(prof[near].mean() / max(1e-12, prof[mid].mean())),
    }


def hillshade(h, step_cm):
    gy, gx = np.gradient(h, step_cm)
    nx, ny, nz = -gx, -gy, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    lx, ly, lz = -0.5, -0.5, 0.7071
    ll = np.sqrt(lx * lx + ly * ly + lz * lz)
    return np.clip((nx * lx + ny * ly + nz * lz) / ll, 0, 1)


def colorize(h, shade):
    lo, hi = np.percentile(h, 1), np.percentile(h, 99)
    t = np.clip((h - lo) / max(1e-9, hi - lo), 0, 1)
    stops = np.array([
        [0.00, 74, 104, 78],
        [0.35, 110, 135, 88],
        [0.60, 150, 148, 107],
        [0.82, 168, 158, 148],
        [1.00, 232, 232, 226],
    ])
    rgb = np.zeros(h.shape + (3,))
    for i in range(len(stops) - 1):
        a, b = stops[i], stops[i + 1]
        m = (t >= a[0]) & (t <= b[0] if i == len(stops) - 2 else t < b[0])
        if not m.any():
            continue
        f = (t[m] - a[0]) / (b[0] - a[0])
        rgb[m] = a[1:] + (b[1:] - a[1:]) * f[:, None]
    rgb *= (0.55 + 0.75 * shade)[..., None]
    return np.clip(rgb, 0, 255).astype(np.uint8)


def save_map(h, step_cm, path):
    Image.fromarray(colorize(h, hillshade(h, step_cm))).save(path)


def main():
    default_out = Path(__file__).resolve().parents[2] / "Saved" / "WorldGenerationAudit" / "formula-20261019"
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=122)
    ap.add_argument("--half-m", type=int, default=512, help="sample half extent in metres")
    ap.add_argument("--step-m", type=float, default=2.0, help="sample spacing in metres")
    ap.add_argument("--out", type=Path, default=default_out)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    half_cm, step_cm = args.half_m * 100, args.step_m * 100
    seed = args.seed

    report = {"seed": seed, "sample_half_m": args.half_m, "sample_step_m": args.step_m,
              "formula": "TemperateHillsSurface::Height (base only, no river/edits)"}

    X, Y = grid(half_cm, step_cm)
    h, parts = height_parts(X, Y, seed)
    report["world"] = stats(h)
    s = slope_deg(h, step_cm)
    report["world"].update({
        "slope_mean_deg": float(s.mean()),
        "slope_p95_deg": float(np.percentile(s, 95)),
        "slope_max_deg": float(s.max()),
        "pct_gt_30deg": float((s > 30).mean() * 100),
        "pct_gt_45deg": float((s > 45).mean() * 100),
        "height_hash_cm": hashlib.sha256(h.astype("<i4").tobytes()).hexdigest()[:16],
    })
    report["components_std_m"] = {
        "warp_xy": float(parts["warp"].std() / 100),
        "hill": float(parts["hill"].std() * 2400 / 100),
        "large": float(parts["large"].std() * 3200 / 100),
        "valley": float(parts["valley"].std() * 1200 / 100),
        "detail": float(parts["detail"].std() / 100),
    }
    report["components_p2p_m"] = {
        "hill": float((parts["hill"].max() - parts["hill"].min()) * 2400 / 100),
        "large": float((parts["large"].max() - parts["large"].min()) * 3200 / 100),
        "valley": float((parts["valley"].max() - parts["valley"].min()) * 1200 / 100),
        "detail": float((parts["detail"].max() - parts["detail"].min()) / 100),
    }
    report["psd_energy_fraction"] = psd(h, step_cm)
    report["lattice_bias_large_x"] = lattice_bias(parts["large"] * 3200, step_cm, 0.000020, 1.31, "x")
    report["lattice_bias_large_y"] = lattice_bias(parts["large"] * 3200, step_cm, 0.000020, -2.1, "y")

    # 8 m (far LOD) bilinear mesh error against the continuous height.
    n = h.shape[0]
    if n % 4 == 0:
        hc = h[::4, ::4]
        c8 = -half_cm + 2.5 * step_cm + 4 * step_cm * np.arange(hc.shape[0] - 1)
        Xm, Ym = np.meshgrid(c8, c8, indexing="xy")
        hm, _ = height_parts(Xm, Ym, seed)
        corners = (hc[:-1, :-1] + hc[1:, :-1] + hc[:-1, 1:] + hc[1:, 1:]) / 4.0
        err = hm - corners
        report["lod8_mesh_error_rms_cm"] = float(np.sqrt(np.mean(err ** 2)))
        report["lod8_mesh_error_max_cm"] = float(np.abs(err).max())

    # 9.09 m detail octave vs 8 m sampling: aliasing and reconstructed RMS.
    xline = np.arange(0, 200000, 200.0)
    d_hi = noise(xline * 0.0011, np.zeros_like(xline), seed, 88) * 14
    xc = xline[::4]
    d_lo = noise(xc * 0.0011, np.zeros_like(xc), seed, 88) * 14
    d_recon = np.interp(xline, xc, d_lo)
    report["detail_9m"] = {
        "std_cm": float(d_hi.std()),
        "lod8_recon_rms_cm": float(np.sqrt(np.mean((d_hi - d_recon) ** 2))),
        "lod8_recon_rms_over_std": float(np.sqrt(np.mean((d_hi - d_recon) ** 2)) / max(1e-9, d_hi.std())),
        "alias_wavelength_m": float(1.0 / abs(1.0 / 9.0909 - 1.0 / 8.0)),
    }

    # Seed variation at 4 m sampling.
    Xs, Ys = grid(51200, 400)
    maps = {}
    for sd in (seed, seed + 1, 7, 12345):
        hs, _ = height_parts(Xs, Ys, sd)
        maps[sd] = hs
        report.setdefault("seed_samples", {})[str(sd)] = stats(hs)
    report["seed_correlation"] = float(np.corrcoef(
        maps[seed].ravel(), maps[seed + 1].ravel())[0, 1])

    # 4 km map for the target scale.
    X4, Y4 = grid(204800, 400)
    h4, _ = height_parts(X4, Y4, seed)
    report["world_4096m"] = stats(h4)
    s4 = slope_deg(h4, 400)
    report["world_4096m"].update({
        "slope_p95_deg": float(np.percentile(s4, 95)),
        "slope_max_deg": float(s4.max()),
        "pct_gt_30deg": float((s4 > 30).mean() * 100),
    })
    save_map(h4, 400, args.out / f"hills_seed{seed}_4096m.png")

    # Contact sheet: four seeds, 1 km, 4 m.
    tiles = []
    for sd in (seed, seed + 1, 7, 12345):
        hs, _ = height_parts(*grid(51200, 400), sd)
        tiles.append(Image.fromarray(colorize(hs, hillshade(hs, 400))))
    sheet = Image.new("RGB", (2 * 260 + 6, 2 * 260 + 6), (24, 24, 24))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, (2 + (i % 2) * 260, 2 + (i // 2) * 260))
    sheet.save(args.out / "seeds_contact_sheet.png")

    report["river_priority_flood_nodes"] = {
        f"{km}km": int((2 * km * 1000 / 16 + 1) ** 2) for km in (1, 4, 8, 16)
    }
    report["border_note"] = (
        "height is continuous everywhere; the runtime stops at +-Size/2 and "
        "Wanted() rejects cell indices outside [0,Count)")

    with open(args.out / "report.json", "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()