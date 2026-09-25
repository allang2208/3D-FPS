"""Author a hunt/work short glove family from the accepted V7 hands.

New family: HuntFieldGlovesV1. Does not write FittedFieldGlovesV1.
Offsets are centimetres on the shared canonical hand surface. No new animations.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hunt_glove_thickness import (
    BACK_CM, CONTACT_CM, CUFF_GROOVE_CM, CUFF_LIP_CM, KNUCKLE_CM, STRAP_CM,
    hunt_thickness, unit,
)

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / "SourceAssets/ModularOutfit20260925/HuntFieldGlovesV1"
BARE = PROJECT / "SourceAssets/ModularOutfit20260925/BarePalmV7"
SOURCES = PROJECT / "SourceAssets/ModularOutfit20260925/BareArmsFamilyV6/Sources"
OUT = ROOT / "Authored"
OUT.mkdir(parents=True, exist_ok=True)


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


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def bind(bone):
    m = np.eye(4)
    m[:3, :3] = np.asarray(bone["axes"]).T
    m[:3, 3] = bone["position"]
    return m


canonical_raw = (BARE / "M4_original.json").read_bytes()
canonical = json.loads(canonical_raw)
anatomy = read(PROJECT / "SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/BareUpperArmsV6/M4_bare_shape.json")["anatomy"]
p = np.asarray(canonical["positions"])
t = np.asarray(canonical["triangles"])
hand_faces = np.flatnonzero(np.asarray(canonical["triangle_materials"]) == 2)
hand_t = t[hand_faces]
hand_ids = np.unique(hand_t)
n = vertex_normals(p, t)

edges = Counter(tuple(sorted((int(f[k]), int(f[(k + 1) % 3]))) ) for f in hand_t for k in range(3))
boundary = np.asarray(sorted({v for e, count in edges.items() if count == 1 for v in e}))
ij = np.asarray(list(edges))
lengths = np.linalg.norm(p[ij[:, 0]] - p[ij[:, 1]], axis=1)
graph = coo_matrix((np.r_[lengths, lengths],
                    (np.r_[ij[:, 0], ij[:, 1]], np.r_[ij[:, 1], ij[:, 0]])), shape=(len(p), len(p))).tocsr()
edge_distance = dijkstra(graph, indices=boundary, min_only=True, directed=False)

dorsal = np.zeros_like(p)
for side, frame in anatomy.items():
    belongs = p[:, 0] < 0 if side == "l" else p[:, 0] > 0
    digit_dorsal = {d["bone"]: np.asarray(d["dorsal"]) for d in frame["digits"]}
    for vi in np.flatnonzero(belongs):
        w = canonical["weights"][vi]
        total = sum(value for name, value in w.items() if name in digit_dorsal)
        dorsal[vi] = np.asarray(frame["dorsal"]) * max(0, 1 - total)
        for name, value in w.items():
            if name in digit_dorsal:
                dorsal[vi] += digit_dorsal[name] * value
dorsal = unit(dorsal)

thickness = np.zeros(len(p))
thickness[hand_ids] = hunt_thickness(n[hand_ids], dorsal[hand_ids], edge_distance[hand_ids],
                                     [canonical["weights"][int(vi)] for vi in hand_ids])
offset = np.zeros_like(p)
offset[hand_ids] = n[hand_ids] * thickness[hand_ids, None]
offset[boundary] = 0
new_p = p + offset
new_n = vertex_normals(new_p, t)

axis = np.cross(n, new_n)[t]
dot = (n * new_n).sum(1)[t, None]
old_n = np.asarray(canonical["normals"])
glove_normals = unit(old_n + np.cross(axis, old_n) + np.cross(axis, np.cross(axis, old_n)) / np.maximum(1 + dot, 1e-8))
canonical_native = read(SOURCES / "M4.json")
inverse = {name: np.linalg.inv(bind(b)) for name, b in canonical_native["bones"].items()}
config = read(PROJECT / "Content/ColdSteelData/modular_outfits.json")
manifest = []

for entry in read(BARE / "manifest.json"):
    name = entry["profile"]
    raw = Path(entry["authored"]).read_bytes()
    bare = json.loads(raw)
    native = read(SOURCES / f"{name}.json")
    profile = config["profiles"][bare["source"]]
    rest = np.asarray(bare["canonical_positions"])
    if len(rest) == len(p):
        mapping = np.arange(len(p))
    else:
        side = -1 if rest[:, 0].mean() < 0 else 1
        mapping = np.flatnonzero(p[:, 0] * side > 0)
    if len(rest) != len(mapping):
        raise RuntimeError("Canonical hand correspondence changed: " + name)
    candidates = p[mapping]
    if float(np.max(np.linalg.norm(rest - candidates, axis=1))) > 1e-7:
        order = []
        used = set()
        for sample in rest:
            d = np.linalg.norm(candidates - sample, axis=1)
            pick = int(np.argmin(d))
            if pick in used or float(d[pick]) > 1e-7:
                raise RuntimeError("Canonical hand correspondence changed: " + name)
            used.add(pick)
            order.append(pick)
        mapping = mapping[order]
    faces = [i for i, mat in enumerate(bare["triangle_materials"]) if mat == 2]
    ids = sorted({v for fi in faces for v in bare["triangles"][fi]})
    remap = {v: i for i, v in enumerate(ids)}
    matrices = {bn: (bind(native["bones"][bn]) @ inverse[bn])[:3, :3]
                for bn in {bn for vi in ids for bn in bare["weights"][vi]}}
    positions = []
    normals_by_vertex = {}
    for vi in ids:
        matrix = sum(matrices[bn] * weight for bn, weight in bare["weights"][vi].items())
        positions.append((np.asarray(bare["positions"][vi]) + matrix @ offset[mapping[vi]]).tolist())
        normals_by_vertex[vi] = np.linalg.inv(matrix).T
    canonical_faces = {tuple(face): fi for fi, face in enumerate(canonical["triangles"])}
    normals = []
    canonical_normals = []
    for fi in faces:
        face = bare["triangles"][fi]
        ci = canonical_faces[tuple(int(mapping[vi]) for vi in face)]
        cn = glove_normals[ci]
        normals.append([unit(normals_by_vertex[vi] @ cn[k]).tolist() for k, vi in enumerate(face)])
        canonical_normals.append(cn.tolist())
    data = {
        "profile": name, "source": bare["source"], "skeleton": bare["skeleton"],
        "binding_source": profile["original_gloved_source"],
        "base_mesh": profile["native_bare_skin"],
        "bare_authored_sha256": hashlib.sha256(raw).hexdigest(),
        "positions": positions, "weights": [bare["weights"][vi] for vi in ids],
        "triangles": [[remap[vi] for vi in bare["triangles"][fi]] for fi in faces],
        "uv": [bare["uv"][fi] for fi in faces], "normals": normals,
        "triangle_materials": [0] * len(faces),
        "canonical_positions": [new_p[mapping[vi]].tolist() for vi in ids],
        "canonical_normals": canonical_normals,
        "bare_vertex_ids": ids, "bare_face_ids": faces,
        "surface_winding": "ue_native",
        "family": "HuntFieldGlovesV1",
        "contract": "V7 hand section 2 hunt short glove; native weights; fixed cuff boundary; dorsal pads only; shared animations",
    }
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    manifest.append({"profile": name, "source": bare["source"], "authored": str(path),
                     "vertices": len(ids), "triangles": len(faces)})
    print("HUNT_GLOVES_AUTHORED", name, len(ids), len(faces), flush=True)

(ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
(ROOT / "fit-policy.json").write_text(json.dumps({
    "canonical": str(BARE / "M4_original.json"),
    "canonical_sha256": hashlib.sha256(canonical_raw).hexdigest(),
    "contact_thickness_mm": CONTACT_CM * 10,
    "dorsal_thickness_mm": BACK_CM * 10,
    "knuckle_pad_mm": KNUCKLE_CM * 10,
    "cuff_lip_extra_mm": CUFF_LIP_CM * 10,
    "cuff_groove_mm": CUFF_GROOVE_CM * 10,
    "wrist_strap_mm": STRAP_CM * 10,
    "cuff_boundary": "Original V7 section 2 boundary, zero displacement and copied weights",
    "new_animations": 0, "runtime_tested": False,
    "items": ["ue_field_gloves"],
    "not_items": ["ue_field_gloves_black"],
    "third_person": "Hunt Body glove authored separately",
}, indent=2) + "\n", encoding="utf-8")
print("HUNT_GLOVES_FAMILY", len(manifest), "max_offset_mm", float(np.linalg.norm(offset, axis=1).max()) * 10, flush=True)
