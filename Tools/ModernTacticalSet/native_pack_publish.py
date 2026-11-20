"""Publish only the native-volume backpack pairs for the TS01 upper garment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile

import numpy as np
from scipy.spatial import cKDTree

P = Path(__file__).resolve().parents[2]
R = P / "SourceAssets/BackpackFit20261024/ModernTacticalNativePacks20261118"
CONFIG = P / "Content/ColdSteelData/player_body.json"
SHIRT = "ue_modern_kevlar_vest"
TOOLS = P / "Tools/BackpackFit"


def read(path):
    return json.loads(path.read_bytes())


def record(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def obj(path):
    return path if "." in path else path + "." + path.rsplit("/", 1)[-1]


def pairs():
    routes = read(R / "Rigid/routes.json") + read(R / "Soft/routes.json")
    seated = {q["asset"]: q for q in read(R / "Contact/author.json")["rows"]}
    for row in routes:
        points = np.fromfile(seated[row["mesh"]]["positions"], "<f4").reshape(-1, 3)
        row["bounds_min"] = np.minimum(row["bounds_min"], points.min(0)).tolist()
        row["bounds_max"] = np.maximum(row["bounds_max"], points.max(0)).tolist()
    return routes


def key(row):
    return row["rig"] + "/" + row["item"]


def root(row):
    rig = () if row["rig"] == "Jason" else ("body_variants", "kaitlin")
    return rig + ("outfits", row["item"])


def get(node, path):
    for part in path:
        node = node[part]
    return node


def fields(row):
    updates = {("world_mesh_by_shirt", SHIRT): obj(row["mesh"]),
               ("backpack_motion", "support_by_shirt", SHIRT): row["support"]}
    if row.get("rigid"):
        updates[("rigid_pack", "mesh_by_shirt", SHIRT)] = obj(row["rigid"])
        updates[("rigid_pack", "location_by_shirt", SHIRT)] = row["rigid_location"]
    return updates


def prepare():
    manifests = [read(R / family / "author.json") for family in ("Rigid", "Soft")]
    combined = {kind: [entry for family in manifests for entry in family[kind]] for kind in ("rows", "statics")}
    refined = read(R / "Contact/author.json")
    if {r["asset"] for r in refined["rows"]} != {r["asset"] for r in combined["rows"]}:
        raise RuntimeError("Wrong or incomplete strap seating")
    old_contacts = read(R / "strap-contacts.json")
    new_contacts = read(R / "Contact/strap-contacts.json")
    head_contacts = read(R / "Contact/helmet-strap-contacts.json")
    for name, groups in new_contacts.items():
        if max(head_contacts[name].values()) or sum(g["triangle_pairs"] for g in groups.values()) >= sum(g["triangle_pairs"] for g in old_contacts[name].values()):
            raise RuntimeError("Refit did not improve strap contact for " + name)
    combined["rows"] = refined["rows"]
    rows = pairs()
    if len({key(row) for row in rows}) != 12 or len(combined["rows"]) != 12 or len(combined["statics"]) != 6:
        raise RuntimeError("Incomplete modern garment routes")
    old = {key(q): q for q in read(R.with_name("ModernTacticalShoulders20261118") / "authored.json")["rows"]}
    nape = {key(q): q for q in read(R.with_name("ModernTacticalHelmetPacks20261118") / "routes.json")}
    before = {}
    cfg = read(CONFIG)
    for row in rows:
        pair = key(row)
        outfit = get(cfg, root(row))
        prior = nape.get(pair, {})
        expected = obj(prior.get("mesh", old[pair]["asset"]))
        if outfit["world_mesh_by_shirt"][SHIRT] != expected:
            raise RuntimeError("Unexpected current harness " + pair)
        if row.get("rigid") and outfit["rigid_pack"]["mesh_by_shirt"][SHIRT] != obj(prior["rigid"]):
            raise RuntimeError("Unexpected current shell " + pair)
        before[pair] = {"/".join(path): get(outfit, path) for path in fields(row)}
    geometry = {}
    for family in ("Soft", "Rigid"):
        src = read(R / family / ("sources.json" if family == "Soft" else "original-sources.json"))
        for base, info in zip(read(R / family / "author.json")["rows"], src):
            entry = next(a for a in combined["rows"] if a["asset"] == base["asset"])
            previous = np.fromfile(base["positions"], "<f4").reshape(-1, 3)
            fitted = np.fromfile(entry["positions"], "<f4").reshape(-1, 3)
            cap = Path(info.get("source_directory") or info["source_harness_directory"])
            weights = np.fromfile(cap / "mask.bin", "<f4")
            free = np.ones(len(weights), bool) if family == "Rigid" else ~np.fromfile(info["cargo_vertices"], "u1").astype(bool)
            faces = np.fromfile(cap / "triangles.bin", "<i4").reshape(-1, 3)
            faces = faces[free[faces].all(1)]
            triangles = fitted[faces]
            differences = np.linalg.norm(fitted - previous, axis=1)
            name = key(info)
            anchor = float(differences[weights > .97].max())
            if anchor > 1.e-4 or np.any(differences[~free] > 1.e-4):
                raise RuntimeError("Strap clearance changed the cargo or attached seam " + name)
            geometry[name] = dict(before_triangle_pairs=sum(g["triangle_pairs"] for g in old_contacts[name].values()),
                                  final_triangle_pairs=sum(g["triangle_pairs"] for g in new_contacts[name].values()),
                                  max_helmet_pairs_in_12_poses=max(head_contacts[name].values()),
                                  anchor_displacement_cm=anchor, median_strap_displacement_cm=float(np.median(differences[free])),
                                  max_strap_displacement_cm=float(differences.max()),
                                  longest_strap_edge_cm=float(np.linalg.norm(triangles-np.roll(triangles,1,axis=1),axis=2).max()))
    record(R / "contact-summary.json", geometry)
    record(R / "before-routes.json", before)
    record(R / "authored.json", combined)


def mesh_distance(vertices, other, faces):
    # A reduced Nanite fallback has fewer vertices even on an identical flat
    # panel. Measure the actual triangles before classifying that as a gap.
    from trimesh.triangles import closest_point
    tri = other[faces]
    index = cKDTree(tri.mean(1))
    peak = 0.
    for chunk in np.array_split(vertices, max(1, len(vertices)//1000 + 1)):
        neighbors = index.query(chunk, k=min(32, len(tri)))[1]
        candidates = tri[neighbors].reshape(-1, 3, 3)
        query = np.repeat(chunk, neighbors.shape[1], 0)
        distances = np.linalg.norm(closest_point(candidates, query)-query, axis=1)
        peak = max(peak, float(distances.reshape(len(chunk),-1).min(1).max()))
    return peak


def saved_shapes():
    saved = read(R / "saved_assets.json")
    levels = read(R / "lod-read.json")
    manifest = read(R / "authored.json")
    if not saved.get("completed"):
        raise RuntimeError("UE save is incomplete")
    hashes, report = {}, {}
    for kind, group in (("meshes", "rows"), ("statics", "statics")):
        for entry in manifest[group]:
            path = entry["asset"]
            positions = Path(entry["positions"])
            asset = P / "Content" / (path.removeprefix("/Game/") + ".uasset")
            digest = sha(asset)
            if saved[kind][path]["geometry_sha256"] != sha(positions) or digest != levels[path]["package_sha256"]:
                raise RuntimeError("Saved geometry or package changed " + path)
            expected = np.fromfile(positions, "<f4").reshape(-1, 3)
            original = cKDTree(expected)
            output = {}
            source_details = levels[path]["levels"]["source0"]
            source_folder = Path(source_details["folder"])
            source_points = np.fromfile(source_folder/"positions.bin", "<f4").reshape(-1,3)
            source_faces = np.fromfile(source_folder/"faces.bin", "<i4").reshape(-1,3)
            for level, details in levels[path]["levels"].items():
                folder = Path(details["folder"])
                received = np.fromfile(folder / "positions.bin", "<f4").reshape(-1, 3)
                faces = np.fromfile(folder / "faces.bin", "<i4").reshape(-1, 3)
                distance = float(max(cKDTree(received).query(expected)[0].max(),
                                     original.query(received)[0].max()))
                surface_distance = None
                if level == "source0" and distance > .12:
                    raise RuntimeError(f"{path} {level} differs from authored mesh by {distance:.3f} cm")
                if level == "render0" and distance > .12:
                    surface_distance = max(mesh_distance(source_points,received,faces),
                                           mesh_distance(received,source_points,source_faces))
                    if surface_distance > .30:
                        raise RuntimeError(f"{path} renderer differs from saved surface by {surface_distance:.3f} cm")
                triangles = received[faces]
                edge = np.linalg.norm(triangles - np.roll(triangles, 1, axis=1), axis=2)
                output[level] = dict(vertices=len(received), triangles=len(faces),
                                     maximum_point_set_distance_cm=distance, surface_distance_if_reduced_cm=surface_distance,
                                     longest_mesh_edge_cm=float(edge.max()))
            report[path] = output
            hashes[path] = digest
    record(R / "saved-shapes.json", report)
    return hashes


def register(selected):
    os.environ["BACKPACK_FIT_RUN_DIR"] = str(R)
    sys.path.insert(0, str(TOOLS))
    from pending import signatures, REG
    runpy.run_path(str(TOOLS / "prepare.py"), run_name="__main__")
    plan = read(R / "plan.json")
    live = [row for row in plan["rows"] if row["shirt"] == SHIRT]
    plan["rows"] = [row for row in live if key(row) in selected]
    for row in plan["rows"]:
        expected = selected[key(row)]
        if row["mesh"] != obj(expected["mesh"]) or row.get("rigid_mesh") != (obj(expected["rigid"]) if expected.get("rigid") else None):
            raise RuntimeError("Unexpected live selection " + key(row))
    updates = signatures(plan)
    if len(updates) != len(selected):
        raise RuntimeError("Runtime route coverage changed")
    for attempt in range(3):
        before = REG.read_bytes()
        registry = json.loads(before)
        registry["routes"].update(updates)
        registry["revision"] = R.name
        with tempfile.NamedTemporaryFile(dir=REG.parent, delete=False) as handle:
            handle.write((json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode("utf8"))
        tmp = Path(handle.name)
        try:
            if REG.read_bytes() != before:
                continue
            os.replace(tmp, REG)
            break
        finally:
            tmp.unlink(missing_ok=True)
    else:
        raise RuntimeError("Concurrent registry edit")
    result = {}
    for row in live:
        result[key(row)] = {k: row[k] for k in ("mesh", "rigid_mesh", "explicit_mapping", "rigid_location", "hanging_pack") if k in row}
    plan["rows"] = live
    registry = read(REG)["routes"]
    matches = {key: registry.get(key, {}).get("signature") == value["signature"]
               for key,value in signatures(plan).items()}
    if not all(matches.values()):
        raise RuntimeError("Unequal live garment fingerprints " + str([key for key,valid in matches.items() if not valid]))
    return result, updates, matches


def publish():
    hashes = saved_shapes()
    before = read(R / "before-routes.json")
    rows = pairs()
    raw = CONFIG.read_bytes()
    cfg = json.loads(raw)
    owned = []
    for row in rows:
        outfit = get(cfg, root(row))
        if row.get("rigid") and outfit["rigid_pack"]["rotation_quat"] != row["rigid_rotation_quat"]:
            raise RuntimeError("Mount rotation changed for " + key(row))
        for path, value in fields(row).items():
            if get(outfit, path) not in (before[key(row)]["/".join(path)], value):
                raise RuntimeError("Concurrent update " + key(row) + "/" + "/".join(path))
            get(outfit, path[:-1])[path[-1]] = value
            owned.append(root(row) + path)
        motion = outfit["backpack_motion"]
        for name, combine in (("bounds_min", min), ("bounds_max", max)):
            merged = [combine(a, b) for a, b in zip(motion[name], row[name])]
            if merged != motion[name]:
                motion[name] = merged
                owned.append(root(row) + ("backpack_motion", name))
    commit = runpy.run_path(str(P / "Tools/PlayerBody/config_transaction.py"))["commit"]
    receipt = commit(CONFIG, raw, cfg, owned_paths=owned, producer=__file__)
    record(R / "config-receipt.json", receipt)
    selected = {key(q): q for q in rows}
    live, updates, matches = register(selected)
    lods = read(R / "lod-read.json")
    level_count = sum(len(record["levels"]) for record in lods.values())
    record(R / "published.json", dict(status="saved_and_integrated", revision=R.name, changed_combinations=len(rows),
           packages_sha256=hashes, registered_routes=sorted(updates), actual_routes=live,
           equipment_resolution="Source/FPSGAME/Characters/FPSPlayerBodyEquipment.cpp, FittedShirt and StringForShirt",
           garment_dependencies={key: value["signature"] for key,value in updates.items()},
           all_live_route_fingerprints=matches, source_and_render_lod_count=level_count,
           render_lod_count=level_count-len(lods), runtime_tested=False))
    print("NATIVE_PACKS_PUBLISHED", len(rows), len(hashes), len(live), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("prepare", "publish"))
    {"prepare": prepare, "publish": publish}[parser.parse_args().operation]()
