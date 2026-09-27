"""Read-only structure report for the Fab split riser."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "ArmsV2" / "bow_surface.json"
OUT = HERE / "structure_inspect.json"
STRING = dict(xmin=-21.79, xmax=-21.13, ymin=-1.26, ymax=-0.61, zmin=-64.05, zmax=64.12)
NOCKS = ((-21.46, -0.935, 64.11), (-21.46, -0.935, -64.04))
SLOT_NAMES = {0: "Body", 1: "Limb", 2: "Inlay"}


def slot_stats(source):
    keep = []
    removed = 0
    for i, face in enumerate(source["triangles"]):
        pts = [source["positions"][v] for v in face]
        if all(
            STRING["xmin"] <= v[0] <= STRING["xmax"]
            and STRING["ymin"] <= v[1] <= STRING["ymax"]
            and STRING["zmin"] <= v[2] <= STRING["zmax"]
            for v in pts
        ):
            removed += 1
            continue
        keep.append(i)
    by_slot = defaultdict(lambda: {"tris": 0, "xs": [], "ys": [], "zs": []})
    for i in keep:
        slot = int(source["materials"][i])
        row = by_slot[slot]
        row["tris"] += 1
        for v in source["triangles"][i]:
            x, y, z = source["positions"][v]
            row["xs"].append(x)
            row["ys"].append(y)
            row["zs"].append(z)
    slots = {}
    for slot, row in sorted(by_slot.items()):
        slots[SLOT_NAMES.get(slot, str(slot))] = {
            "index": slot,
            "tris": row["tris"],
            "bbox_cm": {
                "x": [round(min(row["xs"]), 3), round(max(row["xs"]), 3)],
                "y": [round(min(row["ys"]), 3), round(max(row["ys"]), 3)],
                "z": [round(min(row["zs"]), 3), round(max(row["zs"]), 3)],
                "size": [
                    round(max(row["xs"]) - min(row["xs"]), 3),
                    round(max(row["ys"]) - min(row["ys"]), 3),
                    round(max(row["zs"]) - min(row["zs"]), 3),
                ],
            },
        }
    return removed, slots, keep


def bands(source, keep):
    used = {}
    for i in keep:
        for v in source["triangles"][i]:
            if v not in used:
                used[v] = source["positions"][v]
    rows = []
    for lo, hi, name in (
        (-4, 4, "grip"),
        (8, 20, "fade_low"),
        (20, 45, "limb_mid"),
        (55, 62, "tip"),
        (62, 66, "nock"),
    ):
        pts = [p for p in used.values() if lo <= abs(p[2]) <= hi]
        if not pts:
            rows.append({"name": name, "count": 0})
            continue
        xs, ys, zs = zip(*pts)
        rows.append(
            {
                "name": name,
                "count": len(pts),
                "x_span_cm": round(max(xs) - min(xs), 3),
                "y_span_cm": round(max(ys) - min(ys), 3),
                "x_min": round(min(xs), 3),
            }
        )
    return rows


def nock_gap(source):
    out = []
    for target in NOCKS:
        best = 1e9
        nearest = None
        for p in source["positions"]:
            d = math.dist(p, target)
            if d < best:
                best = d
                nearest = [round(c, 3) for c in p]
        out.append({"key_cm": list(target), "nearest_cm": nearest, "gap_cm": round(best, 3)})
    return out


def main():
    source = json.loads(SRC.read_text(encoding="utf-8"))
    removed, slots, keep = slot_stats(source)
    receipt = {
        "source": str(SRC),
        "verts": len(source["positions"]),
        "tris_with_string": len(source["triangles"]),
        "removed_string_tris": removed,
        "kept_tris": len(keep),
        "slots": slots,
        "thickness_bands_cm": bands(source, keep),
        "nock_keys": nock_gap(source),
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "RISER_STRUCTURE_INSPECT",
        json.dumps(
            {
                "removed": removed,
                "slots": {k: v["tris"] for k, v in slots.items()},
                "bands": receipt["thickness_bands_cm"],
                "nocks": receipt["nock_keys"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
