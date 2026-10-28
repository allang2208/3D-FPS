"""Signed distance field of the whole SM_Kukri (grip frame, cm; negative = inside) and surface samples.

Mesh: DualPistolKukri20261025/kukri_mesh.npz (read_kukri_mesh.py from Kukri_Editable.blend, grip frame like the game
asset).  The field is cached in Work/kukri_sdf.npz (voxel pitch 0.1 cm, 3 cm margin).
KUKRI_SDF_VARIANT=hunter (2026-10-27, the 猎手刀身 blade module, 1.5x exposed blade, tip at 36.1 cm): the union of
SM_Kukri and the hunter blade (Work/hunter_blade_mesh.npz, read_hunter_mesh.py) -- the longest blade any hand can
carry, a conservative envelope of every blade module -- cached in Work/kukri_sdf_hunter.npz.
"""
import os
from pathlib import Path

import numpy as np
from scipy import ndimage

P = Path(__file__).resolve().parent
MESH = P.parent / 'DualPistolKukri20261025' / 'kukri_mesh.npz'
VARIANT = os.environ.get('KUKRI_SDF_VARIANT', 'factory')
EXTRA = [P / 'Work' / 'hunter_blade_mesh.npz'] if VARIANT == 'hunter' else []
CACHE = P / 'Work' / ('kukri_sdf.npz' if VARIANT == 'factory' else 'kukri_sdf_%s.npz' % VARIANT)
PITCH = 0.1


def _build():
    import trimesh
    meshes = []
    for path in [MESH] + EXTRA:
        km = np.load(path)
        meshes.append(trimesh.Trimesh(km['X'], km['T'], process=False))
    lo = np.min([m.vertices.min(0) for m in meshes], axis=0) - 3.0
    hi = np.max([m.vertices.max(0) for m in meshes], axis=0) + 3.0
    shape = np.ceil((hi - lo) / PITCH).astype(int) + 1
    grid = np.zeros(shape, bool)
    for mesh in meshes:                       # the union of the parts
        vox = mesh.voxelized(PITCH).fill()
        occ, origin = vox.matrix, vox.transform[:3, 3]
        off = np.round((origin - lo) / PITCH).astype(int)
        src = [slice(max(0, -o), min(s, g - o)) for o, s, g in zip(off, occ.shape, shape)]
        dst = [slice(max(0, o), max(0, o) + (sl.stop - sl.start)) for o, sl in zip(off, src)]
        grid[tuple(dst)] |= occ[tuple(src)]
    sdf = (ndimage.distance_transform_edt(~grid) - ndimage.distance_transform_edt(grid)) * PITCH
    pts = np.concatenate([trimesh.sample.sample_surface_even(m, 6000, seed=7)[0] for m in meshes])
    if len(meshes) > 1:                       # keep the samples on the union's surface (not inside another part)
        idx = ((pts - lo) / PITCH).T
        pts = pts[ndimage.map_coordinates(sdf, idx, order=1, mode='nearest') > -0.15]
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, sdf=sdf.astype(np.float32), lo=lo, surface=pts.astype(np.float32))


if not CACHE.exists():
    _build()
_D = np.load(CACHE)
SDF, LO, SURFACE = _D['sdf'], _D['lo'], _D['surface'].astype(float)
# Blade-only samples (above the guard, grip z > 6.5 cm) and handle samples.
BLADE = SURFACE[SURFACE[:, 2] > 6.5]
HANDLE = SURFACE[SURFACE[:, 2] <= 6.5]


def sample(points):
    """SDF at grip-frame points (cm); outside the box the value is clamped to the border (>= 3 cm)."""
    idx = ((np.asarray(points, float) - LO) / PITCH).T
    return ndimage.map_coordinates(SDF, idx, order=1, mode='nearest')


def to_local(K, pts_mesh):
    """Mesh-space points -> grip frame of kukri transform K (kmath.T, unit scale)."""
    from kmath import qrot, qconj
    return np.array([qrot(qconj(K.q), p - K.p) for p in pts_mesh])


def kukri_gap(Ka, Kb, pts=None):
    """Min signed distance of kukri a's surface samples to kukri b (cm)."""
    pts = SURFACE if pts is None else pts
    from kmath import qmat
    Ra, Rb = qmat(Ka.q), qmat(Kb.q)
    world = pts @ Ra.T + Ka.p
    local = (world - Kb.p) @ Rb
    return float(sample(local).min())


def points_gap(points_mesh, K):
    """Min signed distance of mesh-space points to kukri K and the index of the deepest point."""
    from kmath import qmat
    local = (np.asarray(points_mesh, float) - K.p) @ qmat(K.q)
    d = sample(local)
    return d, int(np.argmin(d))
