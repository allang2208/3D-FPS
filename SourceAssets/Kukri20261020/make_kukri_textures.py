"""Kukri V2 surface (2026-10-20): turn the Fab blade into readable steel.

User report: the blade rendered as "white mosaic".  The Fab Unreal pack paints the blade faces as a
non-metal mid-grey (base ~0.57, metallic 0, roughness ~0.55) with a strong hammered normal; under the
game's bright Lumen lighting that reads as chalky white noise.  Only the bevel and spine are metallic.

This keeps the Fab layout and hammered character but re-authors the blade islands as forged steel:
  - blade mask = low-saturation, non-black, non-padding texels in the blade UV islands (top rows and the
    right-hand edge strips), slightly dilated so mips do not bleed padding grey into the blade;
  - metallic 0.92 on the faces, 1.0 on the original metallic bevel; roughness 0.24-0.40 (faces) and
    0.14-0.22 (bevel), modulated by the original roughness so the hammer marks still break highlights;
  - base colour = iron/steel specular (sRGB ~0.66) modulated +-18 % by the original luminance pattern;
  - V5: steel-island normals flat (mesh normals rebuilt in Blender), pattern +-8 %, roughness 0.26-0.36;
    handle/wood/brass/cord texels untouched.
Writes Textures/T_Kukri_{BaseColor,ORM,Normal}.png (2048, same UVs) for import_kukri.py.
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

P = Path(__file__).resolve().parent
SRC = Path(r"D:\FPS3D\VaultCache\FabLibrary\Kukri-0a08e297\fbx\kukri_extracted\Textures\Unreal")
OUT = P / 'Textures'


def load(name):
    return np.asarray(Image.open(SRC / name).convert('RGB')).astype(np.float32) / 255.0


def main():
    OUT.mkdir(exist_ok=True)
    bc, orm, nrm = load('kukri_BaseColor.png'), load('kukri_OcclusionRoughnessMetallic.png'), load('kukri_Normal.png')
    H, W = bc.shape[:2]
    hsv = cv2.cvtColor((bc * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32) / 255.0
    sat, val = hsv[..., 1], hsv[..., 2]
    padding = np.abs(bc - bc[H - 8, W - 8]).max(-1) < 0.015
    yy, xx = np.mgrid[0:H, 0:W]
    islands = (yy < 0.445 * H) | ((xx > 0.77 * W) & (yy > 0.42 * H))
    steel = islands & (sat < 0.12) & (val > 0.2) & ~padding
    steel = cv2.morphologyEx(steel.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)
    bevel = steel & (orm[..., 2] > 0.35)
    face = steel & ~bevel
    # Dilate into the padding only (never over other islands) so mip levels keep steel at the borders.
    grow = cv2.dilate(steel.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & padding

    lum = bc.mean(-1)
    ref = float(np.median(lum[face])) if face.any() else 0.57
    pattern = np.clip(1.0 + 0.16 * (lum - ref) / max(ref, 1e-3), 0.92, 1.08)
    steel_rgb = np.array([0.655, 0.66, 0.67], np.float32)

    out_bc = bc.copy()
    out_orm = orm.copy()
    rough0 = orm[..., 1]
    out_bc[face] = steel_rgb * pattern[face, None]
    out_bc[bevel] = np.clip(steel_rgb * 1.12 * pattern[bevel, None], 0, 1)
    out_bc[grow] = steel_rgb
    out_orm[face, 1] = np.clip(0.26 + 0.15 * (rough0[face] - 0.30), 0.26, 0.36)
    out_orm[bevel, 1] = np.clip(0.14 + 0.15 * rough0[bevel], 0.14, 0.22)
    out_orm[grow, 1] = 0.32
    out_orm[face, 2] = 0.92
    out_orm[bevel, 2] = 1.0
    out_orm[grow, 2] = 0.92

    n = nrm * 2.0 - 1.0
    soft = steel | grow
    # V5: the hammer bake only matched the Fab smoothing; the steel islands now get rebuilt mesh normals
    # (author_kukri_model.fix_blade_normals), so their tangent-space detail is flat.
    n[soft] = (0.0, 0.0, 1.0)
    out_n = (n * 0.5 + 0.5)

    Image.fromarray((np.clip(out_bc, 0, 1) * 255 + .5).astype(np.uint8)).save(OUT / 'T_Kukri_BaseColor.png')
    Image.fromarray((np.clip(out_orm, 0, 1) * 255 + .5).astype(np.uint8)).save(OUT / 'T_Kukri_ORM.png')
    Image.fromarray((np.clip(out_n, 0, 1) * 255 + .5).astype(np.uint8)).save(OUT / 'T_Kukri_Normal.png')
    print('KUKRI_TEXTURES steel %.3f bevel %.3f face %.3f grow %.3f ref_lum %.3f' % (
        steel.mean(), bevel.mean(), face.mean(), grow.mean(), ref))


if __name__ == '__main__':
    main()
