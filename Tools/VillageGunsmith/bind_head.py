"""Retarget the delivered Meshy vertex skin to the resident skeleton at the R4 neck seam."""
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
import trimesh

SRC = Path(__file__).resolve().parents[2] / "SourceAssets/VillageGunsmith"
OUT = SRC / "Assembly"


def main():
    setup = json.loads((OUT / "setup.json").read_text())
    names = setup["bones"]
    head = np.load(OUT / "head.npz")
    skin = np.load(SRC / "Rig/skin.npz")
    p = head["p"]
    joints, weights = skin["joints"], skin["weights"]
    delivered = skin["points"]
    bounds = trimesh.load_scene(SRC / "Rig/assembled.glb").bounds
    original = np.sort(bounds[:, [0, 2, 1]] * [-1, 1, 1], axis=0)
    returned = np.array([delivered.min(0), delivered.max(0)])
    scale = np.ptp(original[:, 2]) / np.ptp(returned[:, 2])
    aligned = (delivered - returned.mean(0)) * scale + original.mean(0)
    distance, match = cKDTree(aligned).query(p)
    if np.percentile(distance, 99) > .005:
        raise ValueError("Returned bind pose does not register with the uploaded head")
    source_names = skin["bones"].tolist()
    aliases = {"head_end": "head", "headfront": "head", "spine_02": "spine_03", "spine_03": "spine_05"}
    lower, cut, upper = setup["fit"]["neck_transition_cm"]
    mix = np.clip((p[:, 2] * 100 - cut) / (upper - cut), 0, 1)
    mix = mix * mix * (3 - 2 * mix)
    native_ids, native_weights = head["joints"], head["weights"]
    skin_rows = []
    for v, (i, t) in enumerate(zip(match, mix)):
        row = {}
        for j, w in zip(native_ids[v], native_weights[v]):
            if w > 0:
                row[int(j)] = w * (1 - t)
        for j, w in zip(joints[i], weights[i]):
            if w <= 0 or t == 0:
                continue
            name = source_names[j]
            bone = names.index(aliases.get(name, name))
            # Meshy uses one neck link here. Distribute that influence over the
            # two native neck links so the resident animation keeps its bend.
            if name == "neck_01":
                portion = np.clip((p[v, 2] * 100 - lower) / 5.5, 0, 1)
                second = names.index("neck_02")
                row[second] = row.get(second, 0.) + t * w * portion
                w = w * (1 - portion)
            row[bone] = row.get(bone, 0.) + w * t
        pairs = sorted(((j, w) for j, w in row.items() if w > 1e-5), key=lambda item: -item[1])[:8]
        total = sum(w for _, w in pairs)
        if not total:
            raise ValueError("Unbound head vertex")
        skin_rows.append([[j, round(float(w / total), 8)] for j, w in pairs])
    # GeometryScript accepts per-vertex UVs. Split actual UV seams while retaining
    # shared positions, weights and authored per-corner maps on the stitched neck.
    tri = head["tri"][:, ::-1]
    uv = head["uv"][:, ::-1].copy()
    uv[:, :, 1] = 1 - uv[:, :, 1]
    corners, inv = np.unique(np.column_stack((tri.ravel(), uv.reshape(-1, 2))), axis=0, return_inverse=True)
    v = corners[:, 0].astype(int)
    data = {"p": (p[v] * 100).round(6).tolist(), "n": head["n"][v].round(7).tolist(),
            "tri": inv.reshape(-1, 3).tolist(), "uv": corners[:, 1:].round(7).tolist(),
            "w": [skin_rows[j] for j in v], "m": head["m"].tolist()}
    with gzip.open(OUT / "bound_head.json.gz", "wt", compresslevel=3) as out:
        json.dump(data, out, separators=(",", ":"))
    rig = json.loads((SRC / "Rig/delivery.json").read_text())
    (OUT / "binding.json").write_text(json.dumps({"meshy_rig_task": rig["id"], "skeleton": setup["fit"]["native_skeleton"],
        "source_bones": source_names, "vertices": len(v), "triangles": len(tri),
        "seam_cm": [lower, cut, upper], "native_body": setup["fit"]["native_body"]}, indent=2))


if __name__ == "__main__":
    main()
