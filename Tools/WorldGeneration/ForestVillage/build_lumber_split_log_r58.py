"""Blender 5.1 procedural AAA builder for interactive splitting firewood halves (LumberMillOps-R58).

Produces 2 interlocking watertight FBX meshes (100% resident PBR materials, +0.00 MB VRAM):
  1. SM_LM_SplitLog_HalfL  (left half of upright 30 cm x 18.4 cm oak billet, X <= split_seam, pivot at bottom center Z=0)
  2. SM_LM_SplitLog_HalfR  (right half of upright 30 cm x 18.4 cm oak billet, X >= split_seam, pivot at bottom center Z=0)

When seated together at the same transform on Stump A/B, they form one seamless bark-wrapped oak round.
At the axe cleave frame, HalfL & HalfR separate along -X / +X exposing bright cleft heartwood (Sawn),
tumble off the chopping stump, and come to rest on the ground!
"""
import json
import math
import sys
from pathlib import Path

import bpy

PROPS_LIB = Path("D:/FPS3D/FPSGAME/Tools/WorldGeneration/VillageStable/PropsR43")
sys.path.insert(0, str(PROPS_LIB))
import props_geom as pg

pg.UV_SCALES_M.update({"Bark": 0.90, "Sawn": 0.65, "Endgrain": 0.45})
pg.PREVIEW_COLORS.update({"Bark": (0.22, 0.16, 0.11), "Sawn": (0.68, 0.56, 0.40), "Endgrain": (0.58, 0.46, 0.32)})

OUT_DIR = Path("F:/FPSGAMEData/ArtProduction/SourceAssets/WorldGeneration/HillsForestPath/LumberMill-R49/TransportFBX")

HEIGHT_CM = 30.0
RADIUS_CM = 9.2
N_Z = 7
N_ARC = 10
N_SPLIT = 5


def bark_radius(ang: float, tz: float) -> float:
    taper = 1.0 + 0.05 * math.cos(tz * math.pi)
    ridge = (
        0.48 * math.sin(ang * 7.0 + tz * 1.4 + 0.5)
        + 0.26 * math.cos(ang * 13.0 - tz * 2.1)
        + 0.14 * math.sin(ang * 19.0 + 1.2)
    )
    return RADIUS_CM * taper + ridge


def split_seam_x(ty: float, tz: float) -> float:
    """Shared organic cleft wood-fiber plane X(ty, tz) for ty in [-1, 1], tz in [0, 1]."""
    return (
        0.55 * math.sin(tz * math.pi * 1.6 + 0.4) * (1.0 - 0.3 * abs(ty))
        + 0.38 * math.cos(ty * 2.4 - tz * 2.2)
        + 0.16 * math.sin(ty * 5.2 + tz * 4.0)
    )


def build_split_half(out_dir: Path, name: str, is_right: bool):
    b = pg.AssetBuilder(name, seed=5801 if is_right else 5802, ground_mud_cm=0.0)
    # Cross-section loop at each Z ring:
    #   0 .. N_ARC: outer curved bark rim
    #     - Right half (X >= seam): ang from -pi/2 (Y=-R) to +pi/2 (Y=+R)
    #     - Left  half (X <= seam): ang from +pi/2 (Y=+R) to 3*pi/2 (Y=-R)
    #   N_ARC+1 .. N_ARC+N_SPLIT-1: interior jagged split plane returning from end back to start!
    a0 = -0.5 * math.pi if is_right else 0.5 * math.pi
    a1 = 0.5 * math.pi if is_right else 1.5 * math.pi
    n_sec = (N_ARC + 1) + (N_SPLIT - 1)  # closed ring vertex count

    verts = []
    for iz in range(N_Z + 1):
        tz = iz / N_Z
        z = HEIGHT_CM * tz
        # Slight organic lean/bulge along height
        row = []
        y_start = 0.0
        y_end = 0.0
        for ia in range(N_ARC + 1):
            ua = ia / N_ARC
            ang = a0 + (a1 - a0) * ua
            r = bark_radius(ang, tz)
            x = r * math.cos(ang)
            y = r * math.sin(ang)
            if ia == 0:
                y_start = y
                x = split_seam_x(-1.0 if is_right else 1.0, tz)
            elif ia == N_ARC:
                y_end = y
                x = split_seam_x(1.0 if is_right else -1.0, tz)
            row.append((x, y, z))
        # Return along split cleft plane from y_end -> y_start
        for ks in range(1, N_SPLIT):
            us = ks / N_SPLIT
            y = y_end + (y_start - y_end) * us
            ty = max(-1.0, min(1.0, y / RADIUS_CM))
            x = split_seam_x(ty, tz)
            row.append((x, y, z))
        verts.extend(row)

    faces = []
    face_mats = []
    for iz in range(N_Z):
        for k in range(n_sec):
            k2 = (k + 1) % n_sec
            v00 = iz * n_sec + k
            v01 = iz * n_sec + k2
            v11 = (iz + 1) * n_sec + k2
            v10 = (iz + 1) * n_sec + k
            faces.append((v00, v01, v11, v10))
            is_bark = (k < N_ARC)
            face_mats.append("Bark" if is_bark else "Sawn")

    # Bottom cap (Z = 0, normal -Z) & Top cap (Z = HEIGHT_CM, normal +Z)
    faces.append(tuple(reversed(range(n_sec))))
    face_mats.append("Endgrain")
    faces.append(tuple(N_Z * n_sec + k for k in range(n_sec)))
    face_mats.append("Endgrain")

    obj = b._new_mesh_obj(name + "_Body", verts, faces, "Bark", face_mats=face_mats)
    b._bake_smooth(obj, 36.0)
    b._uv_box(obj, long_axis=2)
    b.add_collider((4.6 if is_right else -4.6, 0.0, 15.0), (9.6, 18.4, 30.0))
    return b.finish(out_dir, lod_ratios=(1.0,))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = [
        build_split_half(OUT_DIR, "SM_LM_SplitLog_HalfL", is_right=False),
        build_split_half(OUT_DIR, "SM_LM_SplitLog_HalfR", is_right=True),
    ]
    mpath = OUT_DIR / "splitlog-manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"SPLIT_LOG_FBX_OK: {len(manifest)} meshes -> {mpath}")


if __name__ == "__main__":
    main()
