"""Compare native wrist depth to the physical cuff in 16 directions around each arm."""
import hashlib
import json
from pathlib import Path

import numpy as np

PROJECT = Path("D:/FPS3D/FPSGAME")
SET = PROJECT / "SourceAssets/ModernTacticalSet20261113"
ROOT = SET / "BareWrists20261118"


def load(path):
    return json.loads(path.read_bytes().decode("utf-8-sig"))


def extent(points, wrist, axis, radial, tangent, nearest):
    delta = points - wrist
    valid = np.linalg.norm(delta, axis=1) < 15
    delta = delta[valid]
    theta = np.arctan2(delta@tangent, delta@radial)
    sectors = ((theta + np.pi)*16/(2*np.pi)).astype(int) % 16
    depth = delta@axis
    return np.array([((np.min if nearest else np.max)(depth[sectors==i])
                     if (sectors==i).any() else np.nan) for i in range(16)])


def compare(sleeve, skin):
    cloth = np.array(sleeve["positions"])
    cf = np.array(sleeve["triangles"])
    cuff = sleeve["material_slots"].index("CombatCuff")
    cloth = cloth[np.unique(cf[np.array(sleeve["triangle_materials"])==cuff])]
    points = np.array(skin["positions"])
    faces = np.array(skin["triangles"])
    materials = np.array(skin["triangle_materials"])
    slots = skin["material_slots"]
    hand = next(i for i,s in enumerate(slots) if "hand" in s.lower() and "wrist" not in s.lower())
    lower = next(i for i,s in enumerate(slots) if s in ("SkinArms", "BareLowerArms", "Manny_S90_Skin_Forearm"))
    hand_pts = points[np.unique(faces[materials==hand])]
    native_strip = "WristUnderlapSkin" in slots
    strip = slots.index("WristUnderlapSkin") if native_strip else lower
    arm_pts = points[np.unique(faces[materials==strip])]
    bones = {b["name"]: np.array(b["position"]) for b in sleeve["bones"]}
    records = {}
    for side in "lr":
        wrist = bones["hand_"+side]
        axis = bones["lowerarm_"+side] - wrist
        axis /= np.linalg.norm(axis)
        radial = np.cross(axis, np.eye(3)[np.argmin(abs(axis))])
        radial /= np.linalg.norm(radial)
        tangent = np.cross(axis, radial)
        rim = extent(cloth, wrist, axis, radial, tangent, True)
        if not np.isfinite(rim).any():
            continue
        args = wrist, axis, radial, tangent, False
        old = extent(hand_pts, *args)
        band = arm_pts if native_strip else arm_pts[np.linalg.norm(arm_pts-wrist, axis=1)<10.5]
        combined = extent(np.vstack([hand_pts, band]), *args)
        valid = np.isfinite(rim) & np.isfinite(old) & np.isfinite(combined)
        if not np.any(valid):
            continue
        before, after = old[valid]-rim[valid], combined[valid]-rim[valid]
        records[side] = {"sectors": int(valid.sum()), "sectors_open_before": int(sum(before<0)),
                         "sectors_open_after": int(sum(after<0)), "min_overlap_before_cm": round(float(before.min()),3),
                         "min_overlap_after_cm": round(float(after.min()),3), "max_cuff_edge_cm": round(float(rim[valid].max()),3)}
    return records


def main():
    capture = load(SET / "CombatShirtR3/CuffRepairR1/captured.json")
    sources = {r["rig"]: Path(r["file"]) for r in capture["rows"] if r["key"]=="Native_"+r["rig"]}
    rigs = {r["rig"]: Path(r["file"]) for r in load(SET/"CombatShirtR4/fp-authored.json")["rows"]}
    for sex in ["Jason", "Kaitlin"]:
        sources[sex] = SET / ("CombatShirtR3/Inputs/Body_"+sex+".json")
        rigs[sex] = SET / ("CombatShirtR4/Authored/shirt_outer_"+sex+".json")
    records = {}
    for rig, cloth in rigs.items():
        native = load(sources[rig])
        path = native["source"].removeprefix("/Game/").split(".")[0]+".uasset"
        with (PROJECT/"Content"/path).open("rb") as stream:
            current = hashlib.file_digest(stream, "sha256").hexdigest()
        saved_hash = native.get("asset_sha256", native.get("source_sha256"))
        records[rig] = dict(source=native["source"], capture_matches_current=(current==saved_hash),
                            sides=compare(load(cloth),native))
    (ROOT/"cuff-reference-review.json").write_text(json.dumps(dict(
        method="Angular vertex extents in sixteen wrist sectors in the reference pose",
        native_rigs=records, gameplay_tested=False), indent=2))
    print("WRIST_REFERENCE_CUFFS", len(records))


if __name__ == "__main__":
    main()
