"""Import quarry-only packages without resaving any shared material or world data asset."""
import json
from pathlib import Path

import unreal as ue

PROJECT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT / "SourceAssets/HillsQuarryRockLayout20261119"
QUARRY = "/Game/WorldGeneration/TemperateHills/WhiteCliffs"
DEST = QUARRY + "/Meshes/Fractures"
tools = ue.AssetToolsHelpers.get_asset_tools()
saved = []

for row in json.loads((SOURCE / "manifest.json").read_text(encoding="utf8")):
    name = row["name"]
    path = DEST + "/" + name
    chip = row["material"] == "LimestoneSpoil"
    options = ue.FbxImportUI()
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    static = options.static_mesh_import_data
    static.combine_meshes = True
    static.auto_generate_collision = False
    static.generate_lightmap_u_vs = False
    static.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task = ue.AssetImportTask()
    task.filename = str(SOURCE / (name + ".fbx"))
    task.destination_name = name
    task.destination_path = DEST
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    task.save = False
    tools.import_asset_tasks([task])
    mesh = ue.load_asset(path)
    if not mesh or not task.imported_object_paths:
        raise RuntimeError("Mesh import failed: " + path)
    bindings = []
    for index, slot in enumerate(mesh.static_materials):
        material = "LimestoneCut" if "LimestoneCut" in str(slot.material_slot_name) else row["material"]
        asset = ue.load_asset(QUARRY + "/Materials/M_" + material)
        if not asset:
            raise RuntimeError("Missing quarry material " + material)
        mesh.set_material(index, asset)
        bindings.append(material)
    expected = {row["material"]} if chip else {row["material"], "LimestoneCut"}
    if set(bindings) != expected:
        raise RuntimeError(f"Unexpected fracture material slots on {name}: {bindings}")
    nanite = mesh.get_editor_property("nanite_settings")
    nanite.enabled = True
    if not chip:
        nanite.fallback_percent_triangles = .5
        nanite.fallback_relative_error = .1
        mesh.get_editor_property("body_setup").set_editor_property(
            "collision_trace_flag", ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh.set_editor_property("nanite_settings", nanite)
    size = mesh.get_bounding_box().max - mesh.get_bounding_box().min
    dimensions = [round(v, 2) for v in (size.x, size.y, size.z)]
    if any(abs(a - b) > 1 for a, b in zip(dimensions, row["size_cm"])):
        raise RuntimeError(f"Scan size mismatch on {name}: {dimensions} vs {row['size_cm']}")
    if not ue.EditorAssetLibrary.save_loaded_asset(mesh, False):
        raise RuntimeError("Mesh save failed: " + path)
    saved.append(dict(path=path, size_cm=dimensions, materials=bindings))

(SOURCE / "saved.json").write_text(json.dumps(saved, indent=2), encoding="utf8")
