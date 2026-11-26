"""Build just the village wall-access stair in an unattended content authoring host."""
import json
import os
import runpy
import sys
from pathlib import Path

import unreal as u


PROJECT = Path(os.environ["HIGH_VILLAGE_PROJECT"])
SOURCE = PROJECT / "SourceAssets/HillsVillageHighWall20261120/Stairs"
PATH = "/Game/WorldGeneration/TemperateHills/HighVillageDefense/SM_WallAccessStairs"
OWNER = "HillsVillageHighWall20261120/Stairs"


def material_bindings():
    # Use the same named stone instances selected for the high wall's hand-built parts.
    catalog = PROJECT / "SourceAssets/HillsVillagePerimeter20261117/asset-production.json"
    perimeter = json.loads(catalog.read_text(encoding="utf-8-sig"))["saved"]
    bindings = next(entry["materials"] for entry in perimeter if "Mortar" in entry["materials"])
    return {name: u.load_asset(bindings[name]) for name in ("Mortar", "YardField", "YardSlate", "YardCap")}


def make_mesh(source, slots):
    result = u.DynamicMesh()
    for index, slot in enumerate(slots):
        data = source.groups[slot]
        if not data["triangles"]:
            continue
        buf = u.GeometryScriptSimpleMeshBuffers()
        buf.vertices = [u.Vector(*p) for p in data["vertices"]]
        buf.normals = [u.Vector(*p) for p in data["normals"]]
        buf.uv0 = [u.Vector2D(*p) for p in data["uv0"]]
        buf.uv1 = [u.Vector2D(*p) for p in data["uv1"]]
        buf.triangles = [u.IntVector(*p) for p in data["triangles"]]
        u.GeometryScript_MeshEdits.append_buffers_to_mesh(result, buf, material_id=index)
    return result


def stair_collision(asset, boxes):
    body = asset.get_editor_property("body_setup")
    geometry = body.get_editor_property("agg_geom")
    steps = []
    for data in boxes:
        box = u.KBoxElem()
        box.set_editor_property("center", u.Vector(*data["center"]))
        for axis, extent in zip(("x", "y", "z"), data["size"]):
            box.set_editor_property(axis, extent)
        steps.append(box)
    for key in ("convex_elems", "sphere_elems", "sphyl_elems"):
        geometry.set_editor_property(key, [])
    geometry.set_editor_property("box_elems", steps)
    body.set_editor_property("agg_geom", geometry)
    body.set_editor_property("collision_trace_flag", u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)


def save_mesh(source, materials, path, owner, pivot=None):
    library = u.EditorAssetLibrary
    asset = library.load_asset(path) if library.does_asset_exist(path) else None
    if asset and str(library.get_metadata_tag(asset, "VillageHighWallOwner")) != owner:
        raise RuntimeError("Package already belongs to another asset: " + path)
    slots = list(materials)
    mesh = make_mesh(source, slots)
    if not asset:
        asset, outcome = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh, path,
            u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=True, enable_collision=True, enable_nanite=False))
        if not asset or outcome != u.GeometryScriptOutcomePins.SUCCESS:
            raise RuntimeError("Could not create " + path)
    nanite = asset.get_editor_property("nanite_settings")
    nanite.enabled = True
    nanite.fallback_percent_triangles = 1.
    nanite.fallback_relative_error = .35
    options = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,
        enable_recompute_tangents=True, replace_materials=True, new_materials=list(materials.values()),
        new_material_slot_names=slots, apply_nanite_settings=True, new_nanite_settings=nanite)
    _, outcome = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(mesh, asset, options, u.GeometryScriptMeshWriteLOD())
    if outcome != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError("Could not build stair mesh")
    stair_collision(asset, source.boxes)
    if pivot is not None:
        socket = asset.find_socket("StairOrigin")
        if not socket:
            socket = u.StaticMeshSocket(outer=asset)
            socket.set_editor_property("socket_name", "StairOrigin")
            asset.add_socket(socket)
        socket.set_editor_property("relative_location", u.Vector(*[-v for v in pivot]))
    library.set_metadata_tag(asset, "VillageHighWallOwner", owner)
    if not library.save_loaded_asset(asset, False):
        raise RuntimeError("Could not save " + path)
    return asset


def main():
    materials = material_bindings()
    if not all(materials.values()):
        raise RuntimeError("Could not load the village fieldstone material set")
    if os.environ.get("HIGH_VILLAGE_STAIR_FRACTURE") == "1":
        sys.path.insert(0, str(SOURCE))
        import fracture_stairs
        saved = []
        for index, (role, part, pivot) in enumerate(fracture_stairs.build()):
            path = PATH.rsplit("/", 1)[0] + f"/Fracture/SM_StairShard_{index:02d}"
            asset = save_mesh(part, materials, path, OWNER+"/Fracture", pivot)
            saved.append({"role": role, "mesh": asset.get_path_name(), "pivot_cm": pivot, "stones": part.stones,
                          "triangles": sum(len(group["triangles"]) for group in part.groups.values()),
                          "collision_boxes": len(part.boxes)})
        receipt = {"intact_mesh": PATH, "materials": {k:v.get_path_name() for k,v in materials.items()}, "saved": saved}
        (SOURCE / "fracture_imported.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        u.log(f"WALL_ACCESS_STAIR_FRACTURE_SAVED {len(saved)}")
        return
    stair = runpy.run_path(str(SOURCE / "access_stairs.py"))
    source = stair["build"]()
    asset = save_mesh(source, materials, PATH, OWNER)
    receipt = {"path": asset.get_path_name(), "dimensions_cm": [320, 560, 360],
               "wall_exit_center_cm": [80, -280, 360], "first_riser_cm": [-80, -120, 18],
               "turn_height_cm": 180, "step_rise_run_cm": [18, 28], "flight_width_cm": 160,
               "stones": source.stones, "triangles": sum(len(group["triangles"]) for group in source.groups.values()),
               "collision_boxes": len(source.boxes), "materials": {s: m.get_path_name() for s, m in materials.items()}}
    (SOURCE / "imported.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    u.log("WALL_ACCESS_STAIRS_SAVED " + asset.get_path_name())


main()
