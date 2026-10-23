import json
import os
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(r"D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019")
TEX = ROOT / "Textures"
GEO = TEX / "GeoNormal"
DETAIL = TEX / "detail_v2"
CLEAN = TEX / "Base_4k_clean"
CLEAN.mkdir(exist_ok=True)

MATS = ["Canvas", "Webbing", "Leather", "Metal"]
THREAD = {
    "Canvas": np.array([151.0, 143.0, 113.0], np.float32),
    "Webbing": np.array([122.0, 114.0, 90.0], np.float32),
    "Leather": np.array([137.0, 104.0, 67.0], np.float32),
}
SEAM_DARK = {"Canvas": 0.26, "Webbing": 0.28, "Leather": 0.24}
STITCH_ALPHA = {"Canvas": 0.34, "Webbing": 0.32, "Leather": 0.36}
ROUGH_TARGET = {"Canvas": 0.79, "Webbing": 0.73, "Leather": 0.66}
ROUGH_BLEND = {"Canvas": 0.18, "Webbing": 0.18, "Leather": 0.20}
GEO_WEIGHT = {"Canvas": 0.90, "Webbing": 0.90, "Leather": 0.82, "Metal": 0.0}


def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def load_l(path):
    return np.asarray(Image.open(path).convert("L")).astype(np.float32)


def save_rgb(path, arr):
    Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8)).save(path)


def save_l(path, arr):
    Image.fromarray(np.clip(arr + 0.5, 0, 255).astype(np.uint8)).save(path)


def decode_gl(rgb):
    n = rgb / 127.5 - 1.0
    n[..., 2] = np.maximum(n[..., 2], 0.05)
    l = np.sqrt((n * n).sum(axis=-1, keepdims=True))
    return n / np.maximum(l, 1e-6)


def encode_gl(n):
    n = n / np.maximum(np.sqrt((n * n).sum(axis=-1, keepdims=True)), 1e-6)
    return np.clip(n * 127.5 + 127.5, 0, 255)


def to_dx(gl):
    out = np.array(gl, copy=True)
    out[..., 1] = 255.0 - out[..., 1]
    return out


stats = {}
for mat in MATS:
    base_bc_path = TEX / ("T_Alice_%s_BaseColor.png" % mat)
    base_n_path = TEX / ("T_Alice_%s_Normal.png" % mat)
    rough_path = TEX / ("T_Alice_%s_Roughness.png" % mat)
    ao_path = TEX / ("T_Alice_%s_AO.png" % mat)
    for p in (base_bc_path, base_n_path, rough_path, ao_path):
        dst = CLEAN / p.name
        if not dst.exists():
            shutil.copy2(p, dst)

    def clean_source(p):
        dst = CLEAN / p.name
        if dst.exists():
            return dst
        if p.exists():
            shutil.copy2(p, dst)
        return p

    base = load_rgb(clean_source(base_bc_path))
    base_n_gl = load_rgb(clean_source(base_n_path))
    rough = load_l(clean_source(rough_path)) / 255.0
    ao = load_l(clean_source(ao_path)) / 255.0
    h, w = rough.shape

    mask = load_l(TEX / ("mask_%s.png" % mat))
    if mask.shape != (h, w):
        mask = np.asarray(Image.fromarray(mask.astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(np.float32)
    mask = np.clip(mask / 255.0, 0.0, 1.0)
    valid = mask > 0.35

    if mat == "Metal":
        seam = np.zeros((h, w), np.float32)
        stitch = np.zeros((h, w), np.float32)
    else:
        seam = load_l(DETAIL / ("seam_%s.png" % mat)) / 255.0
        stitch = load_l(DETAIL / ("stitch_%s.png" % mat)) / 255.0
        if seam.shape != (h, w):
            seam = np.asarray(Image.fromarray((seam * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0
            stitch = np.asarray(Image.fromarray((stitch * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(np.float32) / 255.0

    # Combine the baked procedural normal (weave/grain) with the high-poly
    # stitch geometry normal.  Both are OpenGL; convert once at the end.
    n_gl = decode_gl(base_n_gl)
    geo_path = GEO / ("T_Alice_%s_GeoNormal.png" % mat)
    if mat != "Metal" and geo_path.exists():
        geo_gl = load_rgb(geo_path)
        if geo_gl.shape[:2] != (h, w):
            geo_gl = np.asarray(Image.fromarray(geo_gl.astype(np.uint8)).resize((w, h), Image.LANCZOS)).astype(np.float32)
        g = decode_gl(geo_gl)
        wgt = GEO_WEIGHT[mat] * valid[..., None]
        n_gl[..., 0:2] += g[..., 0:2] * wgt
        n_gl = n_gl / np.maximum(np.sqrt((n_gl * n_gl).sum(axis=-1, keepdims=True)), 1e-6)

    normal_gl = encode_gl(n_gl)
    normal_dx = to_dx(normal_gl)
    save_rgb(TEX / ("T_Alice_%s_Normal_GL.png" % mat), normal_gl)
    save_rgb(TEX / ("T_Alice_%s_Normal.png" % mat), normal_dx)

    out_base = base * (1.0 - SEAM_DARK.get(mat, 0.0) * seam[..., None])
    if mat != "Metal":
        a = (STITCH_ALPHA[mat] * stitch)[..., None]
        out_base = out_base * (1.0 - a) + THREAD[mat][None, None, :] * a

    out_rough = rough * (1.0 - 0.12 * seam)
    if mat != "Metal":
        out_rough = out_rough * (1.0 - ROUGH_BLEND[mat] * stitch) + ROUGH_TARGET[mat] * ROUGH_BLEND[mat] * stitch
    out_ao = np.clip(ao * (1.0 - 0.48 * seam), 0.25, 1.0)
    metallic = 1.0 if mat == "Metal" else 0.0
    out_orm = np.stack([out_ao * 255.0, out_rough * 255.0, np.full_like(out_rough, metallic * 255.0)], axis=-1)

    save_rgb(base_bc_path, out_base)
    save_l(rough_path, out_rough * 255.0)
    save_l(ao_path, out_ao * 255.0)
    save_rgb(TEX / ("T_Alice_%s_ORM.png" % mat), out_orm)

    stats[mat] = {
        "resolution": [w, h],
        "geo_weight": GEO_WEIGHT[mat],
        "seam_coverage": float((seam > 0.25).mean()),
        "stitch_coverage": float((stitch > 0.25).mean()),
        "basecolor_mean": [float(v) for v in out_base.reshape(-1, 3).mean(axis=0)],
        "roughness_mean": float(out_rough.mean()),
        "ao_mean": float(out_ao.mean()),
    }
    print("ALICE_4K_APPLY", mat, stats[mat])

(TEX / "surface_4k_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
print("ALICE_4K_APPLY done")
