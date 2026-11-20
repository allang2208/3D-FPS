"""Choose installed trouser cuts against the actual boot shaft and native skin insert."""
import gzip
import json

import numpy as np

from ridge_boots_wear import ROOT, WEAR, package_path, plan, read, sha, write


DIRECTIONS = np.stack((np.cos(np.arange(36) * np.pi / 18), np.sin(np.arange(36) * np.pi / 18)), axis=1)


def cross(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def section(vertices, triangles, side, z, origin):
    if not len(triangles):
        return np.full(len(DIRECTIONS), np.nan)
    xyz = vertices[triangles]
    select = ((side * xyz[:, :, 0]).mean(axis=1) > 0) & (xyz[:, :, 2].min(1) <= z) & (xyz[:, :, 2].max(1) > z)
    xyz = xyz[select]
    other = np.roll(xyz, -1, axis=1)
    cuts = (xyz[:, :, 2] > z) != (other[:, :, 2] > z)
    a, b = xyz[cuts], other[cuts]
    xy = a[:, :2] + (b[:, :2] - a[:, :2]) * ((z - a[:, 2]) / (b[:, 2] - a[:, 2]))[:, None]
    segments = xy.reshape(-1, 2, 2)
    outer = np.full(len(DIRECTIONS), np.nan)
    if len(segments):
        a = segments[:, 0, :] - origin
        delta = segments[:, 1, :] - segments[:, 0, :]
        denom = cross(DIRECTIONS[:, None, :], delta)
        with np.errstate(invalid="ignore", divide="ignore"):
            distances = cross(a, delta) / denom
            along = cross(a, DIRECTIONS[:, None, :]) / denom
        hits = (np.abs(denom) > 1e-9) & (distances > 0.) & (along >= 0) & (along <= 1)
        for i, valid in enumerate(hits):
            if np.any(valid):
                outer[i] = np.max(distances[i, valid])
    return outer


def match(body, row):
    with gzip.open(WEAR / (body + "-cuffs.json.gz"), "rt", encoding="utf8") as stream:
        cuffs = json.load(stream)
    boot = read(ROOT / row["source"])
    bones = {b["name"]: np.array(b["position"]) for b in boot["bones"]}
    vertices, faces, ids = map(np.array, (boot["positions"], boot["triangles"], boot["triangle_materials"]))
    skin_slots = [i for i, s in enumerate(boot["material_slots"]) if s.startswith("NATIVE:")]
    cover_slots = [boot["material_slots"].index(s) for s in ("RB_Textile", "RB_Suede")]
    shaft, skin = faces[np.isin(ids, cover_slots)], faces[np.isin(ids, skin_slots)]
    # The tongue crown rises above the opening. Measure the actual
    # turned lip to use the same shaft transition on each native rig.
    lip = [faces[lo:hi] for name, (lo, hi) in boot["parts"].items() if name.endswith("_turned_collar_lip")]
    cutoff = float(np.median(vertices[np.unique(np.vstack(lip)), 2]))
    slices = []
    for sign, side in ((1, "l"), (-1, "r")):
        foot, calf = bones["foot_" + side], bones["calf_" + side]
        for offset in (-12.15, -9.65, -7.15, -4.65, 1.05, 2.85, 4.55):
            z = cutoff + offset
            center = (foot + (calf - foot) * ((z - foot[2]) / (calf[2] - foot[2])))[:2]
            tuck = offset < 0
            radius = section(vertices, shaft if tuck else skin, sign, z, center)
            slices.append((tuck, sign, z, center, radius))
    result = {}
    for item, choices in row["pants"].items():
        ranked = []
        for key, path in choices.items():
            sample = cuffs[path]
            if sample["asset_sha256"] != sha(package_path(path)):
                raise ValueError("Recapture the changed trouser cuff " + path)
            v, tri = np.array(sample["positions"]), np.array(sample["triangles"], dtype=int)
            inner, outer = [], []
            for tuck, sign, z, center, radius in slices:
                cloth = section(v, tri, sign, z, center)
                overlap = cloth - radius if tuck else radius - cloth
                finite = overlap[np.isfinite(overlap)]
                (inner if tuck else outer).extend(np.maximum(0., finite))
            def loss(values):
                return round(float(np.sqrt(np.mean(np.square(values)))), 4) if values else 0.
            under, above = loss(inner), loss(outer)
            ranked.append(dict(cut=key, asset=path, shaft_intrusion_rms_cm=under,
                shin_intrusion_rms_cm=above, shaft_samples=len(inner), shin_samples=len(outer),
                cost=round(under + above, 4)))
        # A configured cut is retained as-is. Otherwise use the lowest
        # intrusion among the actual normal, short-boot and high-boot garments.
        decision = min(ranked, key=lambda entry: entry["cost"])
        result[item] = dict(asset=decision["asset"], cut=decision["cut"], options=ranked)
    return dict(boot_source_sha256=sha(ROOT / row["source"]), cuff_top_cm=round(float(cutoff), 3), pants=result)


if __name__ == "__main__":
    write(WEAR / "cuff-pairings.json", {body: match(body, row) for body, row in plan().items()})
