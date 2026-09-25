"""Fit thin field gloves to the third-person Body native-skin hands."""
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

PROJECT = Path("D:/FPS3D/FPSGAME")
BODY = json.loads((PROJECT / "SourceAssets/ModularOutfit20260924/NativeSkin/Body_skin.json").read_text(encoding="utf-8-sig"))
OUT = PROJECT / "SourceAssets/ModularOutfit20260925/FittedFieldGlovesV1/Authored"
OUT.mkdir(parents=True, exist_ok=True)
SAFE_UV = [0.004, 0.004]


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def smooth(a, b, v):
    t = np.clip((v - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def vertex_normals(p, t):
    corners = p[t]
    face = -unit(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]))
    result = np.zeros_like(p)
    for k in range(3):
        a = unit(corners[:, (k + 1) % 3] - corners[:, k])
        b = unit(corners[:, (k + 2) % 3] - corners[:, k])
        angle = np.arccos(np.clip((a * b).sum(1), -1, 1))
        np.add.at(result, t[:, k], face * angle[:, None])
    return unit(result)


p = np.asarray(BODY["vertices"], dtype=np.float64)
all_t = np.asarray(BODY["triangles"], dtype=np.int32)
mats = np.asarray(BODY["materials"])
faces = np.flatnonzero(mats == 2)
hand_t = all_t[faces]
ids = np.array(sorted({int(v) for f in hand_t for v in f}))
remap = {int(v): i for i, v in enumerate(ids)}
local_t = np.array([[remap[int(v)] for v in f] for f in hand_t], dtype=np.int32)
local_p = p[ids]
n = vertex_normals(p, all_t)[ids]
edges = Counter(tuple(sorted((int(f[k]), int(f[(k + 1) % 3])))) for f in local_t for k in range(3))
boundary = np.asarray(sorted({v for e, count in edges.items() if count == 1 for v in e}))
ij = np.asarray(list(edges))
lengths = np.linalg.norm(local_p[ij[:, 0]] - local_p[ij[:, 1]], axis=1)
graph = coo_matrix((np.r_[lengths, lengths], (np.r_[ij[:, 0], ij[:, 1]], np.r_[ij[:, 1], ij[:, 0]])),
                   shape=(len(ids), len(ids))).tocsr()
edge_distance = dijkstra(graph, indices=boundary, min_only=True, directed=False)
# Body T-pose: offset along outward normals. Palm stays thinner.
center = local_p.mean(0)
outward = unit(local_p - center)
back = smooth(-0.10, 0.55, (n * outward).sum(1))
thickness = 0.015 + 0.055 * back
thickness *= smooth(0, 0.60, edge_distance)
thickness += 0.100 * np.exp(-((edge_distance - 0.25) / 0.12) ** 2) * smooth(0, 0.16, edge_distance)
thickness -= 0.018 * np.exp(-((edge_distance - 0.50) / 0.055) ** 2) * smooth(0.10, 0.22, edge_distance)
thickness = np.maximum(thickness, 0)
offset = n * thickness[:, None]
offset[boundary] = 0
new_p = local_p + offset
weights = [BODY["weights"][int(v)] for v in ids]
uv_faces = [[SAFE_UV, SAFE_UV, SAFE_UV] for _ in local_t]
new_n = vertex_normals(new_p, local_t)
data = {
    "profile": "Body",
    "source": BODY["source"] if BODY["source"].endswith(BODY["source"]) else BODY["source"],
    "skeleton": "/Game/Characters/ModularOutfit20260924/NativeSkin/SK_Body_NativeBareSkin.SK_Body_NativeBareSkin",
    "binding_source": "/Game/Characters/ModularOutfit20260924/NativeSkin/SK_Body_NativeBareSkin.SK_Body_NativeBareSkin",
    "base_mesh": "/Game/Characters/ModularOutfit20260924/NativeSkin/SK_Body_NativeBareSkin.SK_Body_NativeBareSkin",
    "positions": new_p.tolist(),
    "weights": weights,
    "triangles": local_t.tolist(),
    "uv": uv_faces,
    "normals": [[new_n[i].tolist() for i in face] for face in local_t],
    "triangle_materials": [0] * len(local_t),
    "surface_winding": "ue_native",
    "safe_uv": SAFE_UV,
    "contract": "Body mat 2 field gloves; native weights; safe UV island; shared leather material",
}
path = OUT / "Body.json"
path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
print("BODY_FIELD_GLOVES_AUTHORED", len(ids), len(local_t), flush=True)
