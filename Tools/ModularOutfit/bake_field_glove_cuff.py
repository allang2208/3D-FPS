"""Bake a local cuff-distance field and DirectX roll normal on the V7 field-glove UV."""
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

PROJECT = Path('D:/FPS3D/FPSGAME')
GLOVE = json.loads((PROJECT/'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored/M4.json').read_text())
OUT = PROJECT/'SourceAssets/ModularOutfit20260925/FieldGlovesLeatherV1'
OUT.mkdir(parents=True, exist_ok=True)
SIZE = 2048
SPAN_M = 0.012
RIDGE_M = 0.0025
RIDGE_W = 0.0012
RIDGE_H = 0.00100
GROOVE_M = 0.0050
GROOVE_W = 0.00055
GROOVE_H = 0.00018


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


p = np.asarray(GLOVE['positions'], dtype=np.float64) * 0.01
t = np.asarray(GLOVE['triangles'], dtype=np.int32)
uv = np.asarray(GLOVE['uv'], dtype=np.float64)
authored_n = np.asarray(GLOVE['normals'], dtype=np.float64)
edges = Counter(tuple(sorted((int(f[k]), int(f[(k + 1) % 3])))) for f in t for k in range(3))
boundary = np.asarray(sorted({v for e, count in edges.items() if count == 1 for v in e}))
ij = np.asarray(list(edges))
lengths = np.linalg.norm(p[ij[:, 0]] - p[ij[:, 1]], axis=1)
graph = coo_matrix((np.r_[lengths, lengths],
                   (np.r_[ij[:, 0], ij[:, 1]], np.r_[ij[:, 1], ij[:, 0]])),
                  shape=(len(p), len(p))).tocsr()
distance = dijkstra(graph, indices=boundary, min_only=True, directed=False)

field = np.zeros((SIZE, SIZE), np.uint8)
normal = np.empty((SIZE, SIZE, 3), np.uint8)
normal[:] = [128, 128, 255]
valid = np.zeros((SIZE, SIZE), bool)
near = np.flatnonzero(distance[t].min(1) < SPAN_M + 0.004)

for fi in near:
    face = t[fi]
    loops = uv[fi]
    pts3 = p[face]
    ds = distance[face]
    pix = loops * np.array([SIZE - 1, -(SIZE - 1)]) + np.array([0, SIZE - 1])
    a, b, c = pix
    den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
    if abs(den) < 1e-7:
        continue
    lo = np.maximum(0, np.floor(pix.min(axis=0)).astype(int))
    hi = np.minimum(SIZE - 1, np.ceil(pix.max(axis=0)).astype(int))
    if np.any(hi < lo):
        continue
    yy, xx = np.mgrid[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
    wa = ((b[1] - c[1]) * (xx - c[0]) + (c[0] - b[0]) * (yy - c[1])) / den
    wb = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / den
    wc = 1 - wa - wb
    inside = (wa >= -0.001) & (wb >= -0.001) & (wc >= -0.001)
    if not np.any(inside):
        continue
    weights = np.stack([wa[inside], wb[inside], wc[inside]], axis=-1)
    d = weights @ ds
    e1 = pts3[1] - pts3[0]
    e2 = pts3[2] - pts3[0]
    face_n = unit(authored_n[fi].mean(0))
    ns = unit(weights @ authored_n[fi])
    du1 = loops[1] - loops[0]
    du2 = loops[2] - loops[0]
    determinant = du1[0] * du2[1] - du1[1] * du2[0]
    if abs(determinant) < 1e-12:
        continue
    dpdu = (e1 * du2[1] - e2 * du1[1]) / determinant
    dpdv = (-e1 * du2[0] + e2 * du1[0]) / determinant
    tangent = unit(dpdu - ns * np.sum(ns * dpdu, axis=-1, keepdims=True))
    bitangent = np.cross(ns, tangent)
    handedness = np.where(np.sum(bitangent * dpdv, axis=-1, keepdims=True) >= 0, 1, -1)
    bitangent *= handedness
    try:
        axis = unit(np.linalg.solve(np.stack([e1, e2, face_n]), np.array([ds[1] - ds[0], ds[2] - ds[0], 0.0])))
    except np.linalg.LinAlgError:
        axis = tangent[0]
    ridge = RIDGE_H * np.exp(-((d - RIDGE_M) / RIDGE_W) ** 2)
    groove = -GROOVE_H * np.exp(-((d - GROOVE_M) / GROOVE_W) ** 2)
    slope = (-2 * (d - RIDGE_M) / (RIDGE_W ** 2) * ridge
             - 2 * (d - GROOVE_M) / (GROOVE_W ** 2) * groove)
    surface_axis = axis - ns * np.sum(ns * axis, axis=-1, keepdims=True)
    bent = unit(ns - slope[:, None] * surface_axis)
    tangent_normal = np.stack([
        np.sum(bent * tangent, axis=-1),
        -np.sum(bent * bitangent, axis=-1),
        np.sum(bent * ns, axis=-1),
    ], axis=-1)
    region = np.s_[lo[1]:hi[1] + 1, lo[0]:hi[0] + 1]
    field[region][inside] = np.uint8(np.rint(np.clip(d / SPAN_M, 0, 1) * 255))
    normal[region][inside] = np.uint8(np.rint(np.clip(tangent_normal * 0.5 + 0.5, 0, 1) * 255))
    valid[region] |= inside

dist, nearest = distance_transform_edt(~valid, return_indices=True)
edge = (~valid) & (dist <= 4)
field[edge] = field[nearest[0][edge], nearest[1][edge]]
normal[edge] = normal[nearest[0][edge], nearest[1][edge]]
Image.fromarray(field).save(OUT/'T_FieldGloves_CuffField.png')
Image.fromarray(normal).save(OUT/'T_FieldGloves_CuffRollNormal.png')
report = {
    'source': str(PROJECT/'SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored/M4.json'),
    'size': SIZE,
    'field_span_mm': SPAN_M * 1000,
    'fold_center_mm': RIDGE_M * 1000,
    'fold_height_mm': RIDGE_H * 1000,
    'groove_center_mm': GROOVE_M * 1000,
    'groove_depth_mm': GROOVE_H * 1000,
    'normal_convention': 'DirectX; do not flip green in UE',
    'mesh_modified': False,
    'near_faces': int(len(near)),
    'valid_texels': int(valid.sum()),
}
(OUT/'cuff_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report), flush=True)
