"""Procedural PBR texture generator for the Cyberpunk Apartment scene.

Runs inside Blender's bundled Python (numpy). Writes albedo / normal / roughness
(and emissive where relevant) PNGs into ../textures.

Every normal map is derived from a real height field via central differences,
encoded as an OpenGL-convention tangent-space normal map.

    blender --background --python gen_textures.py
"""
from __future__ import annotations

import math
import os
import struct
import sys
import zlib

import numpy as np

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "textures")
os.makedirs(OUT, exist_ok=True)

# --------------------------------------------------------------------------
# PNG writer
# --------------------------------------------------------------------------


def write_png(path: str, arr: np.ndarray) -> None:
    arr = np.ascontiguousarray(np.clip(arr, 0, 255).astype(np.uint8))
    if arr.ndim == 2:
        arr = np.stack([arr] * 3, axis=-1)
    h, w, c = arr.shape
    ctype = {1: 0, 3: 2, 4: 6}[c]
    raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


# --------------------------------------------------------------------------
# Noise helpers (all seamless / tileable)
# --------------------------------------------------------------------------


def _smooth(t: np.ndarray) -> np.ndarray:
    return t * t * (3.0 - 2.0 * t)


def vnoise(h: int, w: int, fy: int, fx: int, seed: int) -> np.ndarray:
    """Tileable value noise on a fy x fx lattice."""
    rng = np.random.default_rng(seed)
    g = rng.random((fy, fx)).astype(np.float32)
    ys = np.linspace(0, fy, h, endpoint=False, dtype=np.float32)
    xs = np.linspace(0, fx, w, endpoint=False, dtype=np.float32)
    y0 = np.floor(ys).astype(np.int32) % fy
    x0 = np.floor(xs).astype(np.int32) % fx
    y1 = (y0 + 1) % fy
    x1 = (x0 + 1) % fx
    ty = _smooth(ys - np.floor(ys))[:, None]
    tx = _smooth(xs - np.floor(xs))[None, :]
    a = g[np.ix_(y0, x0)]
    b = g[np.ix_(y0, x1)]
    c = g[np.ix_(y1, x0)]
    d = g[np.ix_(y1, x1)]
    top = a + (b - a) * tx
    bot = c + (d - c) * tx
    return top + (bot - top) * ty


def fbm(h: int, w: int, base: int, octaves: int = 5, seed: int = 0,
        persistence: float = 0.5, lacunarity: int = 2) -> np.ndarray:
    out = np.zeros((h, w), dtype=np.float32)
    amp, norm = 1.0, 0.0
    fy, fx = base, max(2, int(base * w / h))
    for i in range(octaves):
        out += amp * vnoise(h, w, fy, fx, seed + i * 977)
        norm += amp
        amp *= persistence
        fy *= lacunarity
        fx *= lacunarity
    return out / norm


def voronoi(h: int, w: int, cells_y: int, cells_x: int, seed: int,
            jitter: float = 0.85) -> tuple[np.ndarray, np.ndarray]:
    """Tileable F1 distance field + per-cell random id (in cell units)."""
    rng = np.random.default_rng(seed)
    jy = (np.arange(cells_y, dtype=np.float32)[:, None] + 0.5
          + (rng.random((cells_y, cells_x)).astype(np.float32) - 0.5) * jitter)
    jx = (np.arange(cells_x, dtype=np.float32)[None, :] + 0.5
          + (rng.random((cells_y, cells_x)).astype(np.float32) - 0.5) * jitter)
    ids = rng.random((cells_y, cells_x)).astype(np.float32)
    ys = (np.arange(h, dtype=np.float32) + 0.5) / h * cells_y
    xs = (np.arange(w, dtype=np.float32) + 0.5) / w * cells_x
    Y = ys[:, None]
    X = xs[None, :]

    ci = np.broadcast_to(np.minimum(np.floor(Y), cells_y - 1).astype(np.int32), (h, w))
    cj = np.broadcast_to(np.minimum(np.floor(X), cells_x - 1).astype(np.int32), (h, w))

    best = np.full((h, w), 1e9, dtype=np.float32)
    bestid = np.zeros((h, w), dtype=np.float32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            ny = (ci + oy) % cells_y
            nx = (cj + ox) % cells_x
            gy = jy[ny, nx] + oy
            gx = jx[ny, nx] + ox
            dy = Y - gy
            dx = X - gx
            d = dy * dy + dx * dx
            better = d < best
            best = np.where(better, d, best)
            bestid = np.where(better, ids[ny, nx], bestid)
    return np.sqrt(best), bestid


def blur(a: np.ndarray, r: int = 2) -> np.ndarray:
    """Tileable box blur via cumulative sums."""
    out = a.astype(np.float32)
    for _ in range(r):
        out = (out + np.roll(out, 1, 0) + np.roll(out, -1, 0)
               + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 5.0
    return out


def normal_map(height: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """Height field -> OpenGL tangent-space normal map (RGB uint8).

    The gradient is normalised against its own 98th percentile so that every
    map carries visible relief regardless of the absolute height scale.
    `strength` acts as a relative multiplier (1.0 = ~30 deg typical slope).
    """
    h = height.astype(np.float32)
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5
    g = np.sqrt(dx * dx + dy * dy)
    p98 = float(np.percentile(g, 98))
    k = 0.62 * strength / (p98 + 1e-6)
    nx = np.clip(-dx * k, -5.0, 5.0)
    ny = np.clip(dy * k, -5.0, 5.0)
    nz = np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    return np.stack([
        (nx * 0.5 + 0.5) * 255.0,
        (ny * 0.5 + 0.5) * 255.0,
        (nz * 0.5 + 0.5) * 255.0,
    ], axis=-1)


def grad3(a: np.ndarray, c0: np.ndarray, c1: np.ndarray) -> np.ndarray:
    out = np.empty(a.shape + (3,), dtype=np.float32)
    out[..., 0] = c0[0] + (c1[0] - c0[0]) * a
    out[..., 1] = c0[1] + (c1[1] - c0[1]) * a
    out[..., 2] = c0[2] + (c1[2] - c0[2]) * a
    return out


def ramp(t: np.ndarray, stops: list[tuple[float, tuple[float, float, float]]]) -> np.ndarray:
    """Piecewise-linear colour ramp."""
    t = np.clip(t, 0.0, 1.0).astype(np.float32)
    out = np.zeros(t.shape + (3,), dtype=np.float32)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]
        p1, c1 = stops[i + 1]
        m = (t >= p0) & (t <= p1 if i == len(stops) - 2 else t < p1)
        u = np.clip((t - p0) / max(p1 - p0, 1e-6), 0, 1)[..., None]
        seg = np.array(c0, dtype=np.float32) * (1 - u) + np.array(c1, dtype=np.float32) * u
        out = np.where(m[..., None], seg, out)
    return out


def save(name: str, albedo=None, normal=None, rough=None, emis=None) -> None:
    if albedo is not None:
        write_png(os.path.join(OUT, f"{name}_alb.png"), albedo)
    if normal is not None:
        write_png(os.path.join(OUT, f"{name}_nrm.png"), normal)
    if rough is not None:
        write_png(os.path.join(OUT, f"{name}_rgh.png"), rough)
    if emis is not None:
        write_png(os.path.join(OUT, f"{name}_emi.png"), emis)
    print(f"  wrote {name}", flush=True)


def to8(x: np.ndarray) -> np.ndarray:
    return np.clip(x * 255.0 + 0.5, 0, 255)


# ==========================================================================
# Individual textures
# ==========================================================================


def tex_concrete_floor(sz: int = 1024) -> None:
    n1 = fbm(sz, sz, 8, 6, seed=11)
    n2 = fbm(sz, sz, 32, 4, seed=23)
    vor, vid = voronoi(sz, sz, 48, 48, seed=31)
    agg = (1.0 - np.clip(vor * 2.4, 0, 1)) ** 3         # aggregate pebbles
    pits = np.clip(1.0 - vor * 5.0, 0, 1) ** 2
    polish = blur(fbm(sz, sz, 4, 4, seed=41), 3)

    h = 0.55 * n2 + 0.25 * agg + 0.12 * pits + 0.08 * n1
    h = h + 0.10 * polish

    base = ramp(np.clip(0.45 + 0.55 * h, 0, 1), [
        (0.0, (0.055, 0.056, 0.060)),
        (0.35, (0.135, 0.133, 0.130)),
        (0.62, (0.205, 0.200, 0.195)),
        (1.0, (0.300, 0.292, 0.280)),
    ])
    # stains / traffic wear
    stain = fbm(sz, sz, 3, 4, seed=57)
    base *= (0.80 + 0.45 * stain)[..., None]
    # hairline cracks
    crack = np.abs(fbm(sz, sz, 6, 5, seed=63) - 0.5)
    crack = np.clip(1.0 - crack * 60.0, 0, 1) * (fbm(sz, sz, 2, 3, seed=71) > 0.52)
    base *= (1.0 - 0.55 * crack)[..., None]
    h = h - 0.35 * crack

    rgh = 0.30 + 0.42 * (1.0 - blur(agg, 1)) + 0.18 * (1.0 - stain) - 0.18 * polish
    rgh = np.clip(rgh, 0.06, 0.95)
    save("concrete_floor", to8(base), normal_map(h, 2.2), to8(rgh))


def tex_concrete_wall(sz: int = 1024) -> None:
    n1 = fbm(sz, sz, 6, 6, seed=101)
    n2 = fbm(sz, sz, 24, 4, seed=113)
    # board-formed horizontal seams
    rows = 8
    yy = np.arange(sz, dtype=np.float32) / sz * rows
    seam = np.clip(np.abs((yy % 1.0) - 0.5) * 2.0, 0.0, 1.0)
    seam = np.clip((1.0 - seam) * 14.0, 0, 1)            # 1 at seam centre
    seam = seam[:, None].repeat(sz, 1)
    # form tie holes
    holes = np.zeros((sz, sz), dtype=np.float32)
    step = sz // 8
    cx = np.arange(step // 2, sz, step)
    cy = np.arange(step, sz, step * 2)
    Y, X = np.mgrid[0:sz, 0:sz].astype(np.float32)
    for y in cy:
        for x in cx:
            d = np.sqrt((Y - y) ** 2 + (X - x) ** 2)
            holes = np.maximum(holes, np.clip(1.0 - d / (sz * 0.006), 0, 1))
    h = 0.5 * n2 + 0.3 * n1 - 0.55 * seam - 0.65 * holes
    h = blur(h, 1)

    base = ramp(np.clip(0.35 + 0.65 * n1, 0, 1), [
        (0.0, (0.088, 0.086, 0.082)),
        (0.4, (0.180, 0.176, 0.168)),
        (0.75, (0.260, 0.254, 0.242)),
        (1.0, (0.330, 0.322, 0.306)),
    ])
    base *= (1.0 - 0.45 * seam)[..., None]
    base *= (1.0 - 0.6 * holes)[..., None]
    # very faint damp streaking - enough to break flatness, not to blotch
    streak = fbm(sz, sz, 3, 5, seed=127)
    streak = np.clip(streak * 1.4 - 0.30, 0, 1)
    base *= (1.0 - 0.10 * streak)[..., None]
    # a few small spalls only, sparse and low contrast
    paint = fbm(sz, sz, 7, 5, seed=131)
    pmask = np.clip((paint - 0.72) * 9.0, 0, 1)
    base = base * (1 - 0.16 * pmask[..., None]) + pmask[..., None] * np.array([0.22, 0.22, 0.23])
    h = h + 0.10 * pmask

    rgh = np.clip(0.66 + 0.16 * n2 - 0.08 * pmask, 0.3, 0.95)
    save("concrete_wall", to8(base), normal_map(h, 1.3), to8(rgh))


def tex_plaster(sz: int = 1024) -> None:
    n1 = fbm(sz, sz, 12, 6, seed=201)
    n2 = fbm(sz, sz, 64, 3, seed=211)
    h = 0.55 * n1 + 0.45 * n2
    base = ramp(n1, [(0.0, (0.40, 0.395, 0.385)), (0.5, (0.50, 0.492, 0.478)),
                     (1.0, (0.58, 0.572, 0.556))])
    stain = fbm(sz, sz, 3, 4, seed=223)
    base *= (0.88 + 0.18 * stain)[..., None]
    rgh = np.clip(0.72 + 0.2 * n2, 0.3, 1.0)
    save("plaster", to8(base), normal_map(h, 0.7), to8(rgh))


def tex_concrete_ceiling(sz: int = 1024) -> None:
    n1 = fbm(sz, sz, 5, 5, seed=301)
    boards = 6
    yy = np.arange(sz, dtype=np.float32) / sz * boards
    seam = np.clip((1.0 - np.abs((yy % 1.0) - 0.5) * 2.0) * 12.0, 0, 1)[:, None].repeat(sz, 1)
    h = 0.5 * n1 + 0.35 * blur(fbm(sz, sz, 40, 3, seed=311), 1) - 0.5 * seam
    base = ramp(n1, [(0.0, (0.070, 0.070, 0.072)), (0.6, (0.130, 0.129, 0.128)),
                     (1.0, (0.180, 0.178, 0.174))])
    base *= (1.0 - 0.5 * seam)[..., None]
    soot = fbm(sz, sz, 2, 4, seed=317)
    base *= (0.85 + 0.25 * soot)[..., None]
    rgh = np.clip(0.80 + 0.15 * n1, 0.4, 1.0)
    save("concrete_ceiling", to8(base), normal_map(h, 1.6), to8(rgh))


def tex_wood(name: str, sz: int, plank_w: int, seed: int,
             cols=(0.30, 0.19, 0.11), light=(0.52, 0.35, 0.20)) -> None:
    """Planks running along U."""
    h, w = sz, sz * 2
    npl = 10
    ph = h // npl
    rng = np.random.default_rng(seed)
    grain = fbm(h, w, 3, 6, seed=seed + 5)
    fine = fbm(h, w, 40, 4, seed=seed + 9)
    hgt = np.zeros((h, w), dtype=np.float32)
    base = np.zeros((h, w, 3), dtype=np.float32)
    Y = np.arange(h, dtype=np.float32)[:, None]
    for i in range(npl):
        y0 = i * ph
        warp = rng.random()
        g = np.roll(grain, int(warp * w), axis=1)
        tone = 0.75 + 0.45 * rng.random()
        c = np.array(cols) * tone
        l = np.array(light) * tone
        gg = np.clip(g * 0.6 + fine * 0.4 + 0.15 * np.sin((Y - y0) / ph * math.pi * 6), 0, 1)
        seg = c[None, None, :] * (1 - gg[..., None] * 0.75) + l[None, None, :] * (gg[..., None] * 0.55)
        m = ((Y >= y0) & (Y < y0 + ph)).astype(np.float32)
        base = base * (1 - m[..., None]) + seg * m[..., None]
        hgt = np.maximum(hgt, (0.30 + 0.55 * gg) * m)
    # plank grooves
    groove = np.zeros((h, w), dtype=np.float32)
    for i in range(npl + 1):
        y = i * ph
        d = np.abs(((Y - y) + h / 2) % h - h / 2)
        groove = np.maximum(groove, np.clip(1.0 - d / 3.0, 0, 1))
    hgt = hgt - 0.9 * groove
    base *= (1.0 - 0.6 * groove)[..., None]
    # varnish wear
    wear = fbm(h, w, 6, 4, seed=seed + 17)
    base *= (0.85 + 0.28 * wear)[..., None]
    rgh = np.clip(0.34 + 0.30 * (1 - wear) + 0.25 * groove, 0.10, 0.95)
    save(name, to8(base), normal_map(hgt, 2.0), to8(rgh))


def tex_wood_solid(name: str, sz: int, seed: int,
                   cols=(0.10, 0.055, 0.034), light=(0.20, 0.115, 0.068)) -> None:
    """Solid timber panel: continuous vertical grain, cathedral figure, no joints.

    Grain runs along the image Y axis (vertical on a door/wall panel after the
    box-projected UV), so the stripes are functions of X only.
    """
    h, w = sz, sz
    rng = np.random.default_rng(seed)
    X = np.arange(w, dtype=np.float32)[None, :] / w
    Y = np.arange(h, dtype=np.float32)[:, None] / h

    # slow wander of the whole grain field, then fine per-line variation
    warp = fbm(h, w, 3, 4, seed=seed + 3) * 0.55
    lines = 22.0
    phase = (X * lines + warp * 2.2 + 0.06 * np.sin(Y * math.pi * 2.0)) * math.pi * 2.0
    # asymmetric profile: wide pale ring, narrow dark line
    g = 0.5 + 0.5 * np.sin(phase)
    g = g ** 2.4
    # cathedral figure: elliptical offsets where the grain bends around a knot
    cat = np.exp(-(((X - 0.62) * 2.6) ** 2 + ((Y - 0.30) * 1.5) ** 2) * 5.0)
    cat2 = np.exp(-(((X - 0.24) * 3.4) ** 2 + ((Y - 0.72) * 1.9) ** 2) * 6.0)
    figure = 0.55 * cat + 0.35 * cat2

    fine = fbm(h, w, 64, 3, seed=seed + 11)
    broad = fbm(h, w, 5, 4, seed=seed + 17)
    tone = np.clip(0.62 * g + 0.20 * fine + 0.18 * broad + 0.34 * figure, 0, 1)

    c = np.array(cols)
    l = np.array(light)
    base = c[None, None, :] * (1.0 - tone[..., None] * 0.86) + l[None, None, :] * (tone[..., None] * 0.74)
    # a little pore speckle so it is not perfectly smooth
    pore = np.clip(fbm(h, w, 120, 2, seed=seed + 23) * 1.4 - 0.55, 0, 1)
    base *= (1.0 - 0.16 * pore)[..., None]

    hgt = 0.35 * g + 0.30 * fine + 0.35 * broad
    save(name, to8(base), normal_map(hgt, 0.65),
         to8(np.clip(0.30 + 0.26 * (1.0 - tone) + 0.10 * pore, 0.12, 0.85)))


def tex_fabric(sz: int = 1024) -> None:
    """Woven upholstery: two crossing thread systems, irregularised, low amplitude.

    The v2 version was a perfect 96-cycle sine grid at normal strength 1.4,
    which tiled into a bright dot lattice and read as perforated metal.
    Real cloth is a *soft* weave: threads wander, slubs break the rhythm, and
    the height field is dominated by fibre fuzz rather than geometry.
    """
    u = np.arange(sz, dtype=np.float32)[None, :] / sz * math.pi * 2
    v = np.arange(sz, dtype=np.float32)[:, None] / sz * math.pi * 2
    # thread count per tile: 132 ends is ~ linen at a 0.35 m tile
    warp = np.sin(u * 300 + 0.6 * np.sin(v * 11.0)) * 0.5 + 0.5
    weft = np.sin(v * 300 + 0.6 * np.sin(u * 10.0)) * 0.5 + 0.5
    # slubs: local thread thickness variation, the thing that kills tiling
    slub = fbm(sz, sz, 26, 4, seed=403)
    sel = fbm(sz, sz, 11, 4, seed=405)
    weave = 0.5 * (warp * weft) + 0.5 * (0.5 * warp + 0.5 * weft)
    weave = weave * (0.90 + 0.20 * slub)
    # fibre fuzz on top: fine, isotropic, and the main source of highlight break-up
    fuzz = fbm(sz, sz, 68, 3, seed=407)
    broad = fbm(sz, sz, 5, 5, seed=409)
    # keep the height field shallow so the normals stay soft
    h = 0.34 * weave + 0.30 * fuzz + 0.36 * broad
    base = ramp(0.55 * broad + 0.30 * weave + 0.15 * sel, [
        (0.0, (0.068, 0.070, 0.094)), (0.45, (0.104, 0.107, 0.138)),
        (0.78, (0.139, 0.142, 0.174)), (1.0, (0.166, 0.168, 0.198))])
    rough = np.clip(0.80 + 0.10 * slub - 0.10 * fuzz, 0.55, 0.98)
    save("fabric", to8(base), normal_map(h, 0.55), to8(rough))


def tex_leather(sz: int = 1024) -> None:
    """Aniline leather: broad creases and a fine random grain.

    v2 used a 90x90 voronoi pebble array, which tiled into a regular studded
    pattern - the armchair read as quilted metal. Real leather grain is
    irregular in both position and size, and its *large* features are the
    creases, not the pores.
    """
    # large soft creases from a warped low frequency field
    warp = fbm(sz, sz, 3, 4, seed=453)
    yy = np.linspace(0, 1, sz, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, sz, dtype=np.float32)[None, :]
    crease = np.sin((xx * 2.3 + yy * 2.9 + warp * 3.1) * math.pi * 2.0)
    crease = np.clip(1.0 - np.abs(crease) * 9.0, 0, 1) ** 2.6
    crease *= 0.35 + 0.65 * fbm(sz, sz, 6, 3, seed=455)   # break it up, keep it thin
    # grain: many small cells but at random density, then heavily blurred so
    # it never forms a lattice
    vor, _ = voronoi(sz, sz, 150, 150, seed=451)
    grain = np.clip(vor * 2.4, 0, 1.6)
    grain = blur(grain, 1) * blur(fbm(sz, sz, 9, 4, seed=459), 0)
    n = fbm(sz, sz, 22, 5, seed=457)
    h = 0.34 * (1.0 - crease) + 0.40 * grain + 0.26 * n
    # tight albedo range: hides tiling, lets the normal map do the work
    base = ramp(0.6 * n + 0.4 * grain, [
        (0.0, (0.052, 0.044, 0.045)), (0.55, (0.068, 0.057, 0.056)),
        (1.0, (0.086, 0.072, 0.069))])
    rough = np.clip(0.46 + 0.14 * n - 0.06 * crease, 0.22, 0.80)
    save("leather", to8(base), normal_map(h, 0.75), to8(rough))


def tex_metal_brushed(sz: int = 1024) -> None:
    streak = fbm(sz, sz, 128, 5, seed=501)
    streak = blur(streak, 0)
    n = fbm(sz, sz, 8, 4, seed=511)
    h = 0.7 * (streak * 0.6 + n * 0.4)
    base = np.zeros((sz, sz, 3), dtype=np.float32)
    base[:] = np.array([0.42, 0.43, 0.45])
    base *= (0.80 + 0.30 * streak)[..., None]
    save("metal_brushed", to8(base), normal_map(h, 0.7),
         to8(np.clip(0.18 + 0.25 * streak, 0.05, 0.7)))


def tex_metal_rust(sz: int = 1024) -> None:
    n1 = fbm(sz, sz, 6, 6, seed=601)
    vor, vid = voronoi(sz, sz, 26, 26, seed=607)
    rust = np.clip((n1 - 0.42) * 3.0, 0, 1) * np.clip(1.0 - vor * 0.8, 0, 1)
    grit = fbm(sz, sz, 60, 4, seed=613)
    h = 0.4 * grit + 0.6 * rust
    base = np.where(rust[..., None] > 0.35,
                    ramp(rust, [(0.0, (0.20, 0.085, 0.035)), (1.0, (0.42, 0.19, 0.07))]),
                    np.array([0.24, 0.245, 0.25])[None, None, :] * (0.8 + 0.4 * grit[..., None]))
    save("metal_rust", to8(base), normal_map(h, 2.2),
         to8(np.clip(0.45 + 0.45 * rust, 0.25, 1.0)))


def tex_tile_bath(sz: int = 1024) -> None:
    tiles = 4
    gap = 0.035
    t = np.arange(sz, dtype=np.float32) / sz * tiles
    gx = np.abs((t % 1.0) - 0.5) * 2
    gy = np.abs((t[:, None] % 1.0) - 0.5) * 2
    gt = np.maximum(gx[None, :], gy)
    grout = np.clip((gt - (1 - gap * 2)) / (gap * 1.2), 0, 1)
    # glaze: very slight mottling only - no veining, no clouds
    n = fbm(sz, sz, 22, 5, seed=701)
    spot = fbm(sz, sz, 60, 3, seed=709)
    h = 0.34 * n + 0.16 * spot - 0.80 * grout
    tone = np.clip(0.55 + 0.30 * (n - 0.5) + 0.14 * (spot - 0.5), 0, 1)
    base = ramp(tone, [
        (0.0, (0.395, 0.405, 0.420)), (0.55, (0.452, 0.460, 0.470)),
        (1.0, (0.500, 0.505, 0.512))])
    base = base * (1 - grout[..., None]) + grout[..., None] * np.array([0.11, 0.11, 0.115])
    save("tile_bath", to8(base), normal_map(h, 1.1),
         to8(np.clip(0.18 + 0.32 * grout + 0.08 * n, 0.08, 0.88)))


def tex_carpet(sz: int = 512) -> None:
    n = fbm(sz, sz, 64, 4, seed=801)
    fib = fbm(sz, sz, 200, 3, seed=807)
    h = 0.5 * n + 0.5 * fib
    base = ramp(n, [(0.0, (0.035, 0.038, 0.048)), (1.0, (0.10, 0.105, 0.125))])
    save("carpet", to8(base), normal_map(h, 1.1),
         to8(np.clip(0.85 + 0.1 * fib, 0.6, 1.0)))


def tex_marble(sz: int = 1024) -> None:
    """Veined marble: a few large sweeping veins, not dense speckle.

    v2 used |fbm - 0.5| thresholded hard, which produced thousands of tiny
    bright specks - at 1.6 m tiling that is indistinguishable from noise.
    Marble reads by *long continuous veins* with soft clouding between them.
    """
    # domain-warp a low frequency field to get the sweeping vein direction
    warp = fbm(sz, sz, 2, 4, seed=903)
    yy = np.linspace(0, 1, sz, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, sz, dtype=np.float32)[None, :]
    field = np.sin((xx * 2.2 + yy * 3.1 + warp * 2.4) * math.pi * 2.0)
    # primary veins: two families at different scales
    v1 = np.clip(1.0 - np.abs(field) * 5.5, 0, 1) ** 2.0
    field2 = np.sin((xx * 5.4 - yy * 1.9 + warp * 3.6) * math.pi * 2.0)
    v2 = np.clip(1.0 - np.abs(field2) * 7.0, 0, 1) ** 3.0
    vein = np.clip(v1 * 0.85 + v2 * 0.45, 0, 1)
    # body clouding
    cloud = fbm(sz, sz, 4, 6, seed=907)
    fine = fbm(sz, sz, 30, 3, seed=911)
    base = ramp(cloud, [(0.0, (0.058, 0.058, 0.064)), (0.42, (0.104, 0.102, 0.107)),
                        (0.75, (0.152, 0.150, 0.154)), (1.0, (0.196, 0.194, 0.198))])
    base = base * (1 - 0.80 * vein[..., None]) + vein[..., None] * np.array([0.66, 0.64, 0.62])
    base = base * (0.94 + 0.12 * fine[..., None])
    h = 0.20 * cloud + 0.12 * fine + 0.30 * vein
    rough = np.clip(0.10 + 0.10 * cloud - 0.04 * vein, 0.04, 0.30)
    save("marble", to8(base), normal_map(h, 0.35), to8(rough))


def tex_rug(sz: int = 1024) -> None:
    n = fbm(sz, sz, 24, 5, seed=1001)
    # geometric cyber pattern
    x = np.arange(sz, dtype=np.float32)[None, :] / sz
    y = np.arange(sz, dtype=np.float32)[:, None] / sz
    px = ((x * 10) % 1.0 - 0.5)
    py = ((y * 14) % 1.0 - 0.5)
    pat = np.clip(1.0 - (np.abs(px) + np.abs(py)) * 2.4, 0, 1)
    ring = np.clip(1.0 - np.abs(np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2) - 0.42) * 90, 0, 1)
    h = 0.45 * n + 0.25 * pat + 0.3 * ring
    base = np.zeros((sz, sz, 3), dtype=np.float32)
    base[:] = np.array([0.045, 0.05, 0.075])
    base += pat[..., None] * np.array([0.16, 0.03, 0.12])
    base += ring[..., None] * np.array([0.02, 0.14, 0.16])
    base *= (0.8 + 0.4 * n)[..., None]
    save("rug", to8(base), normal_map(h, 1.5),
         to8(np.clip(0.88 + 0.1 * n, 0.6, 1.0)))


def tex_curtain(sz: int = 512) -> None:
    x = np.arange(sz, dtype=np.float32)[None, :] / sz
    folds = np.sin(x * math.pi * 2 * 7) * 0.5 + 0.5
    n = fbm(sz, sz, 30, 4, seed=1101)
    h = 0.75 * folds + 0.25 * n
    base = ramp(folds, [(0.0, (0.045, 0.048, 0.06)), (1.0, (0.11, 0.112, 0.13))])
    save("curtain", to8(base), normal_map(h, 1.2),
         to8(np.clip(0.8 + 0.15 * n, 0.5, 1.0)))


def tex_brick(sz: int = 1024) -> None:
    rows, cols = 12, 6
    y = np.arange(sz, dtype=np.float32)[:, None] / sz * rows
    x = np.arange(sz, dtype=np.float32)[None, :] / sz * cols
    x = x + (np.floor(y) % 2) * 0.5
    fx, fy = x % 1.0, y % 1.0
    mortar = np.clip((np.maximum(np.abs(fx - 0.5), np.abs(fy - 0.5)) - 0.42) * 22, 0, 1)
    bs = fbm(sz, sz, 30, 4, seed=1201)
    tone = (np.floor(x) * 0.31 + np.floor(y) * 0.77) % 1.0
    h = 0.5 * bs + 0.2 * tone - 0.9 * mortar
    base = ramp(bs * 0.6 + tone * 0.4, [
        (0.0, (0.075, 0.032, 0.028)), (0.5, (0.155, 0.072, 0.055)),
        (1.0, (0.225, 0.115, 0.085))])
    base = base * (1 - mortar[..., None]) + mortar[..., None] * np.array([0.19, 0.185, 0.175])
    save("brick", to8(base), normal_map(h, 2.4),
         to8(np.clip(0.75 + 0.2 * bs, 0.4, 1.0)))


def tex_facade(name: str, sz: int, cols: int, rows: int, seed: int,
               lit: float = 0.55, tint=(1.0, 0.72, 0.42)) -> None:
    """Night office/hab tower facade: albedo + emissive window grid + normal."""
    rng = np.random.default_rng(seed)
    x = np.arange(sz, dtype=np.float32)[None, :] / sz * cols
    y = np.arange(sz, dtype=np.float32)[:, None] / sz * rows
    fx, fy = x % 1.0, y % 1.0
    # window aperture 0.10..0.90
    inx = (fx > 0.10) & (fx < 0.90)
    iny = (fy > 0.12) & (fy < 0.88)
    win = (inx & iny).astype(np.float32)
    frame = (1 - win)
    # emissive
    cell = np.floor(x).astype(np.int32) * 7919 + np.floor(y).astype(np.int32) * 104729
    rr = (np.sin(cell * 12.9898) * 43758.5453) % 1.0
    on = (rr < lit).astype(np.float32)
    # blinds: horizontal slats on some windows
    slat = (np.sin(fy * math.pi * 22) * 0.5 + 0.5)
    blind = (np.sin(cell * 0.7) * 0.5 + 0.5) > 0.62
    vl = 0.55 + 0.45 * ((np.sin(cell * 3.3) * 0.5 + 0.5))
    em = np.zeros((sz, sz, 3), dtype=np.float32)
    palette = np.array([[1.0, 0.74, 0.42], [0.42, 0.86, 1.0], [1.0, 0.30, 0.62],
                        [0.62, 1.0, 0.78], [1.0, 0.95, 0.85]])
    pidx = (np.floor(rr * 97) % len(palette)).astype(np.int32)
    col = palette[pidx]
    inten = (vl * on)[..., None] * col * (0.55 + 0.45 * np.sin(cell * 1.7)[..., None])
    inten = inten * blind[..., None] * (0.35 + 0.65 * slat[..., None]) + inten * (~blind)[..., None]
    em = inten * win[..., None]
    # albedo
    conc = fbm(sz, sz, 10, 5, seed=seed + 3)
    base = ramp(conc, [(0.0, (0.030, 0.031, 0.034)), (1.0, (0.085, 0.086, 0.092))])
    glass = np.array([0.012, 0.014, 0.020])[None, None, :] * (0.6 + 0.8 * conc[..., None])
    base = base * frame[..., None] + glass * win[..., None]
    base += em * 0.25
    # height: mullions raised, glass recessed
    hgt = frame * 0.35 - win * 0.55
    hgt += 0.25 * (1 - np.clip(np.abs(fy - 0.94) * 30, 0, 1))  # sill ledge
    n = fbm(sz, sz, 40, 3, seed=seed + 11)
    hgt += 0.12 * n
    rgh = (0.13 + 0.5 * frame + 0.3 * n)
    save(name, to8(base), normal_map(hgt, 2.2), to8(np.clip(rgh, 0.05, 1.0)), to8(em))


def tex_holo_panel(sz: int = 1024) -> None:
    y = np.arange(sz, dtype=np.float32)[:, None] / sz
    x = np.arange(sz, dtype=np.float32)[None, :] / sz
    # hex grid
    gx, gy = x * 12, y * 20
    hexl = np.abs(np.sin(gx * math.pi) * np.sin(gy * math.pi)) ** 0.5
    lines = np.clip(1.0 - np.abs(np.sin(gx * math.pi * 2)) * 8, 0, 1)
    # circuit traces
    n = fbm(sz, sz, 8, 4, seed=1301)
    tr = np.clip(1.0 - np.abs(np.sin(x * 40 + n * 6)) * 12, 0, 1)
    tr += np.clip(1.0 - np.abs(np.sin(y * 55 + n * 5)) * 14, 0, 1)
    tr = np.clip(tr, 0, 1)
    # UI bars
    bars = np.zeros((sz, sz), dtype=np.float32)
    rng = np.random.default_rng(1307)
    for _ in range(24):
        bx, by = rng.random(), rng.random()
        bw, bh = 0.05 + 0.25 * rng.random(), 0.004 + 0.012 * rng.random()
        bars[(np.abs(y - by) < bh) & (np.abs(x - bx) < bw)] = 1.0
    em = np.clip(0.35 * lines + 0.5 * tr + 0.9 * bars, 0, 1)
    emis = np.stack([em * 0.15, em * 0.95, em * 1.0], axis=-1)
    base = np.zeros((sz, sz, 3), dtype=np.float32)
    base[:] = np.array([0.015, 0.03, 0.035])
    base += emis * 0.6
    save("holo_panel", to8(base), normal_map(em * 0.15, 0.5),
         to8(np.full((sz, sz), 0.25)), to8(emis))


def tex_tech_panel(sz: int = 1024) -> None:
    rng = np.random.default_rng(1401)
    base = np.zeros((sz, sz, 3), dtype=np.float32)
    hgt = np.zeros((sz, sz), dtype=np.float32)
    base[:] = np.array([0.055, 0.058, 0.065])
    # plates
    for _ in range(60):
        x0, y0 = rng.integers(0, sz - 40, 2)
        w, h = rng.integers(40, 260, 2)
        v = 0.05 + 0.05 * rng.random()
        base[y0:y0 + h, x0:x0 + w] = v
        hgt[y0:y0 + h, x0:x0 + w] += 0.15
    # vents
    for _ in range(10):
        x0, y0 = rng.integers(0, sz - 100, 2)
        for k in range(8):
            yy = y0 + k * 10
            base[yy:yy + 4, x0:x0 + 200] = 0.012
            hgt[yy:yy + 4, x0:x0 + 200] -= 0.5
    # LEDs
    em = np.zeros((sz, sz, 3), dtype=np.float32)
    for _ in range(28):
        x0, y0 = rng.integers(0, sz - 8, 2)
        c = np.array([[0.1, 0.9, 1.0], [1.0, 0.25, 0.6], [1.0, 0.85, 0.2],
                      [0.3, 1.0, 0.45]][rng.integers(0, 4)])
        em[y0:y0 + 5, x0:x0 + 5] = c
    n = fbm(sz, sz, 50, 3, seed=1407)
    hgt += 0.1 * n
    base += em * 0.3
    save("tech_panel", to8(base), normal_map(hgt, 1.8),
         to8(np.clip(0.35 + 0.3 * n, 0.1, 0.9)), to8(em))


def tex_circuit(sz: int = 1024) -> None:
    n = fbm(sz, sz, 6, 4, seed=1501)
    x = np.arange(sz, dtype=np.float32)[None, :] / sz
    y = np.arange(sz, dtype=np.float32)[:, None] / sz
    tr = np.zeros((sz, sz), dtype=np.float32)
    rng = np.random.default_rng(1507)
    for _ in range(90):
        ax = rng.random()
        ay = rng.random()
        ln = 0.04 + 0.22 * rng.random()
        if rng.random() > 0.5:
            tr[(np.abs(y - ay) < 0.0022) & (np.abs(x - ax - ln / 2) < ln / 2)] = 1
        else:
            tr[(np.abs(x - ax) < 0.0022) & (np.abs(y - ay - ln / 2) < ln / 2)] = 1
    pads = np.zeros((sz, sz), dtype=np.float32)
    for _ in range(70):
        cx, cy = rng.random(), rng.random()
        d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        pads = np.maximum(pads, np.clip(1 - d / 0.008, 0, 1))
    h = np.clip(tr * 0.8 + pads * 0.9 + 0.1 * n, 0, 1.5)
    base = np.zeros((sz, sz, 3), dtype=np.float32)
    base[:] = np.array([0.025, 0.055, 0.035])
    base = base * (1 - tr[..., None] * 0.6) + tr[..., None] * np.array([0.16, 0.34, 0.22])
    base = base * (1 - pads[..., None] * 0.7) + pads[..., None] * np.array([0.55, 0.45, 0.18])
    save("circuit", to8(base), normal_map(h, 1.4),
         to8(np.clip(0.45 + 0.2 * n, 0.2, 0.8)))


def tex_screen_ui(name: str = "screen_ui", sz: int = 1024) -> None:
    rng = np.random.default_rng(1601)
    x = np.arange(sz, dtype=np.float32)[None, :] / sz
    y = np.arange(sz, dtype=np.float32)[:, None] / sz
    em = np.zeros((sz, sz, 3), dtype=np.float32)
    em[:] = np.array([0.02, 0.05, 0.09])
    # window frames
    for _ in range(9):
        x0, y0 = rng.random() * 0.8, rng.random() * 0.8
        w, h = 0.08 + 0.3 * rng.random(), 0.10 + 0.3 * rng.random()
        m = (x > x0) & (x < x0 + w) & (y > y0) & (y < y0 + h)
        border = m & ~((x > x0 + 0.004) & (x < x0 + w - 0.004) & (y > y0 + 0.004) & (y < y0 + h - 0.004))
        em[border] = np.array([0.12, 0.8, 1.0]) * 0.75
        em[m & ~border] = np.array([0.02, 0.06, 0.10])
        # content lines
        for k in range(int(6 + rng.random() * 12)):
            ly = y0 + 0.02 + k * (h - 0.03) / 14
            lw = 0.2 + 0.7 * rng.random()
            lm = m & (np.abs(y - ly) < 0.0025) & (x > x0 + 0.012) & (x < x0 + 0.012 + w * lw * 0.8)
            em[lm] = np.array([0.25, 0.95, 1.0]) * (0.5 + 0.5 * rng.random())
    # waveform
    wv = np.abs(np.sin(x * 60 + rng.random() * 6)) * 0.03
    em[(np.abs(y - (0.15 + wv)) < 0.003)] = np.array([1.0, 0.25, 0.65])
    # scanlines
    em *= (0.72 + 0.28 * (np.sin(y * math.pi * sz / 2) * 0.5 + 0.5))[..., None]
    base = np.clip(em * 0.35, 0, 1)
    save(name, to8(base), np.full((sz, sz, 3), 128), to8(np.full((sz, sz), 0.12)), to8(em * 1.35))


def tex_asphalt_wet(sz: int = 1024) -> None:
    n = fbm(sz, sz, 10, 6, seed=1701)
    vor, vid = voronoi(sz, sz, 60, 60, seed=1707)
    grit = np.clip(1 - vor * 3.0, 0, 1)
    h = 0.4 * n + 0.45 * grit
    puddle = np.clip((fbm(sz, sz, 3, 5, seed=1711) - 0.55) * 6, 0, 1)
    h = h * (1 - puddle) - 0.15 * puddle
    base = ramp(n, [(0.0, (0.022, 0.022, 0.025)), (1.0, (0.075, 0.073, 0.072))])
    base = base * (1 - puddle[..., None]) + puddle[..., None] * np.array([0.02, 0.025, 0.035])
    rgh = np.clip(0.55 + 0.3 * (1 - puddle) - 0.5 * puddle, 0.02, 0.95)
    save("asphalt_wet", to8(base), normal_map(h, 1.4), to8(rgh))


def tex_deck_wet(sz: int = 1024) -> None:
    n = fbm(sz, sz, 12, 5, seed=1801)
    planks = 8
    yy = np.arange(sz, dtype=np.float32)[:, None] / sz * planks
    seam = np.clip((1 - np.abs((yy % 1.0) - 0.5) * 2) * 16, 0, 1)
    h = 0.5 * n - 0.7 * seam
    puddle = np.clip((fbm(sz, sz, 4, 4, seed=1807) - 0.5) * 5, 0, 1)
    base = ramp(n, [(0.0, (0.045, 0.045, 0.048)), (1.0, (0.115, 0.112, 0.108))])
    base *= (1 - 0.45 * seam)[..., None]
    base = base * (1 - puddle[..., None] * 0.7)
    rgh = np.clip(0.42 + 0.3 * n - 0.35 * puddle, 0.03, 0.9)
    save("deck_wet", to8(base), normal_map(h, 1.8), to8(rgh))


def tex_diamond_plate(sz: int = 512) -> None:
    x = np.arange(sz, dtype=np.float32)[None, :] / sz * 16
    y = np.arange(sz, dtype=np.float32)[:, None] / sz * 16
    a = np.abs(((x + y) % 2) - 1)
    b = np.abs(((x - y) % 2) - 1)
    pat = np.clip((1 - a * 3), 0, 1) + np.clip((1 - b * 3), 0, 1)
    pat = np.clip(pat, 0, 1)
    n = fbm(sz, sz, 40, 3, seed=1901)
    h = 0.8 * pat + 0.2 * n
    base = np.zeros((sz, sz, 3), dtype=np.float32)
    base[:] = np.array([0.20, 0.205, 0.215])
    base *= (0.75 + 0.45 * pat)[..., None]
    save("diamond_plate", to8(base), normal_map(h, 2.0),
         to8(np.clip(0.35 + 0.2 * n, 0.1, 0.8)))


def tex_neon_grille(sz: int = 512) -> None:
    x = np.arange(sz, dtype=np.float32)[None, :] / sz
    y = np.arange(sz, dtype=np.float32)[:, None] / sz
    seg = np.clip(1 - np.abs(((x * 24) % 1) - 0.5) * 6, 0, 1)
    bars = np.clip(1 - np.abs(((y * 3) % 1) - 0.5) * 8, 0, 1)
    em = np.clip(seg * 0.8 + bars * 0.6, 0, 1)
    emis = np.stack([em * 1.0, em * 0.25, em * 0.75], axis=-1)
    base = np.clip(emis * 0.4, 0, 1)
    save("neon_grille", to8(base), np.full((sz, sz, 3), 128),
         to8(np.full((sz, sz), 0.3)), to8(emis))


def tex_glass_smudge(sz: int = 1024) -> None:
    n = fbm(sz, sz, 5, 5, seed=2001)
    drops = np.clip((fbm(sz, sz, 90, 3, seed=2007) - 0.62) * 8, 0, 1)
    h = 0.3 * n + 0.7 * drops
    rgh = np.clip(0.03 + 0.22 * drops + 0.06 * n, 0.02, 0.6)
    base = np.zeros((sz, sz, 3), dtype=np.float32)
    base[:] = np.array([0.02, 0.022, 0.026])
    save("glass_smudge", to8(base), normal_map(h, 1.0), to8(rgh))


def tex_wall_graffiti(sz: int = 1024) -> None:
    rng = np.random.default_rng(2101)
    base = np.zeros((sz, sz, 3), dtype=np.float32)
    base[:] = np.array([0.32, 0.31, 0.30])
    n = fbm(sz, sz, 6, 5, seed=2107)
    base *= (0.85 + 0.25 * n)[..., None]
    # spray strokes
    for _ in range(26):
        x0, y0 = rng.random(2)
        ang = rng.random() * math.pi
        ln = 0.06 + 0.3 * rng.random()
        w = 0.004 + 0.012 * rng.random()
        x = np.arange(sz, dtype=np.float32)[None, :] / sz
        y = np.arange(sz, dtype=np.float32)[:, None] / sz
        d = np.abs((x - x0) * math.sin(ang) - (y - y0) * math.cos(ang))
        along = (x - x0) * math.cos(ang) + (y - y0) * math.sin(ang)
        m = (d < w) & (along > 0) & (along < ln)
        c = np.array([[0.9, 0.15, 0.45], [0.1, 0.9, 0.95], [0.95, 0.85, 0.1],
                      [0.55, 0.2, 0.95]][rng.integers(0, 4)])
        base[m] = c * (0.6 + 0.4 * rng.random())
    save("wall_graffiti", to8(base), normal_map(0.2 * n, 0.8),
         to8(np.clip(0.7 + 0.2 * n, 0.4, 1.0)))


def main() -> int:
    print(f"[tex] writing into {OUT}", flush=True)
    tex_concrete_floor()
    tex_concrete_wall()
    tex_plaster()
    tex_concrete_ceiling()
    tex_wood("wood_floor", 1024, 10, 150)
    tex_wood_solid("wood_dark", 1024, 250,
               cols=(0.115, 0.062, 0.036), light=(0.255, 0.140, 0.082))
    tex_wood_solid("wood_walnut_t", 1024, 271,
                   cols=(0.070, 0.042, 0.028), light=(0.180, 0.108, 0.066))
    tex_fabric()
    tex_leather()
    tex_metal_brushed()
    tex_metal_rust()
    tex_tile_bath()
    tex_carpet()
    tex_marble()
    tex_rug()
    tex_curtain()
    tex_brick()
    tex_holo_panel()
    tex_tech_panel()
    tex_circuit()
    tex_screen_ui()
    tex_asphalt_wet()
    tex_deck_wet()
    tex_diamond_plate()
    tex_neon_grille()
    tex_glass_smudge()
    tex_wall_graffiti()
    tex_facade("facade_office", 1024, 14, 20, seed=3001, lit=0.5, tint=(1.0, 0.8, 0.55))
    tex_facade("facade_hab", 1024, 10, 26, seed=3101, lit=0.62)
    tex_facade("facade_mega", 2048, 26, 44, seed=3201, lit=0.58)
    print("[tex] done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
