"""Offline health check of the apartment against the authored geometry.

Every query works on the real triangles from the glTF export (UE cm). It
answers the three gameplay questions directly, with no editor and no physics
scene:

  * is there a walkable floor under a given point
  * can an 84 cm wide, 192 cm tall body pass through a doorway
  * what does the balcony railing look like for the traversal rules

Usage:
    py -3.11 Tools/AssetPipeline/cyberpunk_apartment/18_structure_audit.py
"""
import json
import sys

import numpy as np

GEOM = r"D:\FPS3D\FPSGAME\Saved\_gltf_geometry.json"
OUT = r"D:\FPS3D\FPSGAME\Saved\_structure_audit.json"

FLOOR_Z = 0.2          # S_floors room quads
DECK_Z = -3.0          # S_floors balcony deck
CAP_R, CAP_H = 42.0, 96.0          # ACharacter capsule (radius / half height)
BODY_R = CAP_R         # clearance a walking body needs

DECOR = {"LIV_sign_01", "LIV_sign_24H", "LIV_sign_NOODLE//", "MST_sign",
         "B2_sign", "B3_sign", "FOY_sign", "BAL_sign", "BAL_holo",
         "DET_graffiti", "DET_wires", "LIV_cables", "LIV_curtains",
         "S_doors"}     # baked leaves: visual only after the rebuild

# Doorways, read from the wall geometry above (UE cm).
# (label, axis, wall_plane, start, end, head_height)
DOORWAYS = [
    ("entry",     "x", -1100.0,  940.0, 1044.0, 218.0),
    ("kitchen",   "x",  -678.0,  530.0,  790.0, 242.0),
    ("living",    "x",  -546.0,  660.0,  960.0, 242.0),
    ("master",    "x",  -546.0,  152.0,  242.0, 208.0),
    ("bath2",     "x",  -814.0,  122.0,  202.0, 206.0),
    ("bath1",     "x",  -814.0,  330.0,  410.0, 206.0),
    ("bed2",      "y",  1134.0, -500.0, -410.0, 208.0),
    ("bed3",      "y",  1134.0, -848.0, -758.0, 208.0),
    ("balcony",   "x",     0.0,  705.0,  805.0, 244.0),
]

ROOMS = [
    ("living",   396, 1128,  -540,   -12), ("master",  12,  384,  -540,  -12),
    ("bed2",    1140, 1588,  -540,   -12), ("bed3",  1140, 1588, -1088, -552),
    ("corridor",  12, 1128,  -672,  -552), ("utility", 12,  272,  -808, -672),
    ("bath2",     12,  272, -1088,  -820), ("bath1",  284,  468, -1088, -820),
    ("utility2", 284,  468,  -808,  -684), ("kitchen",480,  864, -1088, -684),
    ("foyer",    876, 1128, -1088,  -684),
]


def load():
    with open(GEOM, "r", encoding="utf-8") as fh:
        raw = json.load(fh)["meshes"]
    return {n: (np.asarray(m["positions"], dtype=np.float64),
                np.asarray(m["indices"], dtype=np.int64).reshape(-1, 3))
            for n, m in raw.items()}


def tris_in_band(meshes, axis, plane, half=20.0, zlo=25.0, zhi=200.0,
                 skip=DECOR, with_span=False):
    """Triangles crossing a wall plane, in the walking band."""
    for name, (pos, idx) in meshes.items():
        if name.startswith("CITY_") or name in skip:
            continue
        t = pos[idx]
        if axis == "x":
            across, along = t[:, :, 1], t[:, :, 0]
        else:
            across, along = t[:, :, 0], t[:, :, 1]
        z = t[:, :, 2]
        ok = ((across.max(1) > plane - half) & (across.min(1) < plane + half)
              & (z.max(1) > zlo) & (z.min(1) < zhi))
        if ok.any():
            if with_span:
                span = np.stack([across[ok].min(1), across[ok].max(1)], axis=1)
                yield name, along[ok], span
            else:
                yield name, along[ok]


def doorway_report(meshes, label, axis, plane, a0, a1, head):
    """Widest free run inside an opening on the walking line.

    Only surfaces that can actually stop a body count. Hinges, roses and
    screws are sub-centimetre boxes that inflate to full width when the
    capsule radius is added, which is how a doorway full of hardware looked
    "blocked" in earlier audits. A face has to be at least MIN_BLOCK_CM wide
    and deep to be treated as an obstruction.
    """
    MIN_BLOCK = 3.0
    occ = np.zeros(int(a1 - a0) + 1, dtype=bool)
    who = {}
    for name, along, spans in tris_in_band(meshes, axis, plane,
                                          zlo=25.0, zhi=head - 8.0,
                                          with_span=True):
        for lo, hi, across in zip(along.min(1), along.max(1), spans):
            l = max(a0, float(lo))
            r = min(a1, float(hi))
            if r - l < MIN_BLOCK or (across[1] - across[0]) < MIN_BLOCK:
                continue
            s = int(np.floor(l - a0))
            e = int(np.ceil(r - a0))
            occ[max(0, s):min(len(occ), e + 1)] = True
            who[name] = who.get(name, 0) + 1
    best = (0.0, 0.0)
    start = None
    for k, b in enumerate(occ):
        if not b:
            if start is None:
                start = k
        else:
            if start is not None and k - start > best[1]:
                best = (start, k - start)
            start = None
    if start is not None and len(occ) - start > best[1]:
        best = (start, len(occ) - start)
    return {"door": label, "opening_cm": a1 - a0, "head_cm": head,
            "clear_cm": round(float(best[1]), 1),
            "clear_at": round(float(a0 + best[0]), 1),
            "passable": best[1] >= 2 * BODY_R,
            "blockers": sorted(((v, k) for k, v in who.items()), reverse=True)}


def floor_report(meshes):
    """Highest walkable surface under the middle of each room."""
    rows = []
    for (name, x0, x1, y0, y1) in ROOMS:
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        hits = []
        for mesh in ("S_floors", "S_plate"):
            pos, idx = meshes[mesh]
            t = pos[idx]
            for k in range(len(t)):
                tri = t[k]
                if tri[:, 2].max() > 5.0 or tri[:, 2].min() < -40:
                    continue
                (x1_, y1_), (x2_, y2_), (x3_, y3_) = tri[0, :2], tri[1, :2], tri[2, :2]
                den = (y2_ - y3_) * (x1_ - x3_) + (x3_ - x2_) * (y1_ - y3_)
                if abs(den) < 1e-9:
                    continue
                l1 = ((y2_ - y3_) * (cx - x3_) + (x3_ - x2_) * (cy - y3_)) / den
                l2 = ((y3_ - y1_) * (cx - x3_) + (x1_ - x3_) * (cy - y3_)) / den
                if min(l1, l2, 1 - l1 - l2) >= 0:
                    hits.append((mesh, round(float(tri[:, 2].mean()), 2)))
        rows.append({"room": name, "at": [cx, cy], "surfaces": hits})
    # balcony deck
    rows.append({"room": "balcony", "at": [764, 141],
                 "surfaces": [("S_floors", DECK_Z)]})
    return rows


def railing_report(meshes):
    pos, idx = meshes["S_balcony_glass"]
    t = pos[idx]
    top = float(t[:, :, 2].max())
    xs = (float(t[:, :, 0].min()), float(t[:, :, 0].max()))
    # handrail from S_balcony near the same line
    pos2, idx2 = meshes["S_balcony"]
    t2 = pos2[idx2]
    band = t2[(t2[:, :, 1].max() > 270) & (t2[:, :, 1].min() < 286)
              & (t2[:, :, 2].min() > 90)]
    rail_top = float(band[:, :, 2].max()) if len(band) else None
    return {"glass_tris": int(len(t)), "glass_top_z": round(top, 1),
            "glass_span_x": [round(xs[0], 1), round(xs[1], 1)],
            "glass_y": round(float(t[:, :, 1].mean()), 1),
            "handrail_top_z": round(rail_top, 1) if rail_top else None,
            "vault_max_height_cm": 120.0,
            "vaultable_by_height": bool(rail_top and rail_top <= 120.0)}


def main():
    meshes = load()
    audit = {
        "doors": [doorway_report(meshes, *d) for d in DOORWAYS],
        "floors": floor_report(meshes),
        "railing": railing_report(meshes),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(audit, fh, indent=1)

    print("== doorways: can an 84 cm wide body pass? ==")
    for d in audit["doors"]:
        verdict = "PASS" if d["passable"] else "BLOCKED"
        print("  %-9s opening %4.0f cm, head %3.0f cm -> clear %5.1f cm at %.0f  %s" % (
            d["door"], d["opening_cm"], d["head_cm"], d["clear_cm"],
            d["clear_at"], verdict))
        if not d["passable"]:
            print("           blocks:", ", ".join("%s(%d)" % (k, v)
                                                   for v, k in d["blockers"][:6]))
    print("\n== walkable surface per room ==")
    for f in audit["floors"]:
        print("  %-9s %s" % (f["room"], f["surfaces"]))
    print("\n== balcony railing ==")
    r = audit["railing"]
    for k in ("glass_tris", "glass_top_z", "glass_span_x", "glass_y",
              "handrail_top_z", "vaultable_by_height"):
        print("  %-20s %s" % (k, r[k]))
    print("\nwrote", OUT)


if __name__ == "__main__":
    sys.exit(main())
