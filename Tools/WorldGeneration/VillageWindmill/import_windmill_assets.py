"""Import the fitted windmill exchange meshes with the legacy FBX importer."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import unreal as ue


PROJECT = Path(os.environ["WINDMILL_PROJECT"])
WORK = Path(os.environ["WINDMILL_ART"])
SOURCE = PROJECT / "SourceAssets/HillsVillageWindmill/ComponentsR2"
RECEIPT = Path(os.environ.get("WINDMILL_IMPORT_RECEIPT", WORK / "imported.json"))
HILLS = "/Game/WorldGeneration/TemperateHills"
DEST = HILLS + "/VillageWindmill"
CHAPEL = HILLS + "/OldChapel/Materials/M_Chapel"
SMITH = HILLS + "/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_"
CARPENTER = HILLS + "/VillageCarpenter/Props/Surfaces/M_Carpenter"
SURFACES = {
    "oak": SMITH + "Oak",
    "lightwood": CARPENTER + "Sawn",
    "darkwood": CHAPEL + "Timber",
    "endgrain": SMITH + "Endgrain",
    "iron": CARPENTER + "Iron",
    "flax": SMITH + "Linen",
    "rope": "/Game/Dungeons/ArtPass20260922/Materials/MI_Prop_Rope_All",
    "stone": CHAPEL + "Wall",
    "slate": CHAPEL + "Slate",
    "lime": CHAPEL + "Limewash",
}
SOLID = {"A04", "C01", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11",
         "D01", "D02", "D03", "D04", "D05", "D06", "D07"}
ASSETS = ue.EditorAssetLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()
MAT = ue.MaterialEditingLibrary
MESH = ue.get_editor_subsystem(ue.StaticMeshEditorSubsystem) or ue.new_object(ue.StaticMeshEditorSubsystem)
surface_cache = {}
TANGENT_PARTS = {"C03", "D01", "D02", "D03", "D04", "D05", "D06"}
TANGENT_REVISION = 1


def load(path):
    obj = ue.load_asset(path)
    if obj is None:
        raise RuntimeError(f"Missing asset {path}")
    return obj


def save(obj):
    if not ASSETS.save_loaded_asset(obj, False):
        raise RuntimeError(f"Could not save {obj.get_path_name()}")


def receipt_write(data):
    tmp = RECEIPT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(RECEIPT)


def surface(path):
    if path in surface_cache:
        return surface_cache[path]
    original = load(path)
    if isinstance(original, ue.MaterialInstanceConstant):
        parent = original.get_editor_property("parent")
        ready_parent = surface(parent.get_path_name().split(".")[0])
        needs_copy = ready_parent != parent
    else:
        needs_copy = not (original.get_editor_property("used_with_nanite") and
                          original.get_editor_property("used_with_instanced_static_meshes"))
    obj = original
    if needs_copy:
        # Shader usage belongs to the windmill copy when the existing donor lacks it.
        address = DEST + "/Materials/" + original.get_name() + "_Windmill"
        obj = (load(address) if ASSETS.does_asset_exist(address) else
               ASSETS.duplicate_asset(path, address))
        if not obj:
            raise RuntimeError(f"Could not prepare windmill material from {path}")
        if isinstance(original, ue.MaterialInstanceConstant):
            if obj.get_editor_property("parent") == ready_parent:
                surface_cache[path] = obj
                return obj
            MAT.set_material_instance_parent(obj, ready_parent)
            MAT.update_material_instance(obj)
        else:
            if obj.get_editor_property("used_with_nanite") and obj.get_editor_property("used_with_instanced_static_meshes"):
                surface_cache[path] = obj
                return obj
            MAT.set_base_material_usage(obj, ue.MaterialUsage.MATUSAGE_NANITE, True)
            MAT.set_base_material_usage(obj, ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
            MAT.recompile_material(obj)
        save(obj)
    surface_cache[path] = obj
    return obj


def atlas_texture(part, channel, limit):
    src = SOURCE / "Meshy" / part / "downloads" / f"texture_urls_0_{channel}.png"
    folder = DEST + "/Textures"
    name = f"T_Windmill_{part}_{channel}"
    address = folder + "/" + name
    task = ue.AssetImportTask()
    task.filename = str(src)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    tex = load(address)
    tex.set_editor_property("srgb", channel == "base_color")
    if channel == "normal":
        tex.set_editor_property("compression_settings", ue.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property("flip_green_channel", True)
    elif channel != "base_color":
        tex.set_editor_property("compression_settings", ue.TextureCompressionSettings.TC_MASKS)
    if limit < 2048:
        result = ue.TextureAssetActionsBlueprintFns.resize_texture_source(tex, limit)
        if result == ue.TextureAssetActionsBlueprintReturn.ERROR:
            raise RuntimeError(f"Could not resize {address}")
    tex.set_editor_property("max_texture_size", limit)
    save(tex)
    return tex


def atlas(part, size):
    name = "MI_Windmill_" + part
    folder = DEST + "/Materials"
    address = folder + "/" + name
    mat = (load(address) if ASSETS.does_asset_exist(address) else
           TOOLS.create_asset(name, folder, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew()))
    MAT.set_material_instance_parent(mat, surface(CHAPEL + "Artifact"))
    limit = 2048 if max(size) >= 200 else 1024
    for channel in ("base_color", "normal", "roughness", "metallic"):
        MAT.set_material_instance_texture_parameter_value(mat, channel, atlas_texture(part, channel, limit))
    MAT.update_material_instance(mat)
    save(mat)
    return mat


def import_fbx(src, mesh_folder=DEST + "/Meshes"):
    opts = ue.FbxImportUI()
    opts.automated_import_should_detect_type = False
    opts.mesh_type_to_import = ue.FBXImportType.FBXIT_STATIC_MESH
    opts.import_as_skeletal = False
    opts.import_mesh = True
    opts.import_materials = False
    opts.import_textures = False
    opts.set_editor_property("reset_to_fbx_on_material_conflict", True)
    data = opts.static_mesh_import_data
    data.combine_meshes = True
    # Blender exports Y-forward, Z-up numerical coordinates in cm at identity.
    # Legacy FBX conversion already reflects Y when writing UE positions.
    data.convert_scene = False
    data.convert_scene_unit = True
    data.force_front_x_axis = False
    data.transform_vertex_to_absolute = True
    data.bake_pivot_in_vertex = False
    data.generate_lightmap_u_vs = False
    data.auto_generate_collision = False
    data.remove_degenerates = True
    data.build_nanite = False
    data.normal_import_method = ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task = ue.AssetImportTask()
    task.filename = str(src)
    task.destination_name = src.stem
    task.destination_path = mesh_folder
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.options = opts
    task.factory = ue.FbxFactory()
    TOOLS.import_asset_tasks([task])
    imported = task.get_objects()
    if len(imported) != 1 or not isinstance(imported[0], ue.StaticMesh):
        raise RuntimeError(f"Expected one combined static mesh for {src}, got {imported}")
    return imported[0]


def setup_geometry(mesh, solid, triangles):
    # Use the actual open surfaces for floors, stairs and walls. An empty simple
    # shape set keeps moving transmission parts outside all collision queries.
    body = mesh.get_editor_property("body_setup")
    flag = (ue.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE if solid else
            ue.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)
    body.set_editor_property("collision_trace_flag", flag)
    body.set_editor_property("double_sided_geometry", solid)
    if solid:
        for section in range(mesh.get_num_sections(0)):
            if not MESH.is_section_collision_enabled(mesh, 0, section):
                MESH.enable_section_collision(mesh, True, 0, section)
    use_nanite = triangles >= 8000
    if use_nanite:
        settings = mesh.get_editor_property("nanite_settings")
        settings.enabled = True
        settings.explicit_tangents = True
        settings.generate_fallback = ue.NaniteGenerateFallback.ENABLED
        settings.fallback_target = ue.NaniteFallbackTarget.PERCENT_TRIANGLES
        settings.fallback_percent_triangles = 1.0 if solid else .35
        settings.fallback_relative_error = 0.0 if solid else 1.0
        mesh.set_editor_property("nanite_settings", settings)
    elif triangles >= 400:
        lods = ue.StaticMeshReductionOptions()
        lods.auto_compute_lod_screen_size = False
        lods.reduction_settings = [
            ue.StaticMeshReductionSettings(percent_triangles=ratio, screen_size=screen)
            for ratio, screen in ((1.0, 1.0), (.60, .15), (.32, .045))
        ]
        if MESH.set_lods(mesh, lods) < 1:
            raise RuntimeError("Could not build distance LODs for " + mesh.get_name())
    return use_nanite


def tangent_source(src):
    blender = os.environ.get("BLENDER_EXE", "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe")
    helper = Path(__file__).with_name("repair_windmill_tangents.py")
    dest = WORK / "TangentExchange" / src.name
    result = subprocess.run(
        [blender, "-b", "--factory-startup", "--python-exit-code", "1", "--python", str(helper),
         "--", str(src), str(dest)], capture_output=True, text=True, errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(f"Could not prepare tangents for {src.name}: {result.stdout} {result.stderr}")
    ue.log(result.stdout.strip())
    return dest


def author(row, src, digest, retained_materials):
    part = row["id"]
    mesh = import_fbx(tangent_source(src) if part in TANGENT_PARTS else src)
    assignments = {}
    scanned = None
    for index, slot in enumerate(mesh.static_materials):
        name = str(slot.get_editor_property("imported_material_slot_name"))
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        if key.startswith("mill"):
            key = key[4:]
        if name in retained_materials:
            mat = load(retained_materials[name])
        elif key == "meshy":
            if scanned is None:
                scanned = atlas(part, row["target_cm"])
            mat = scanned
        else:
            if key not in SURFACES:
                raise RuntimeError(f"Unknown FBX material {name!r} on {part}")
            mat = surface(SURFACES[key])
        mesh.set_material(index, mat)
        assignments[name] = mat.get_path_name()
    solid = part in SOLID
    triangles = mesh.get_num_triangles(0)
    nanite = setup_geometry(mesh, solid, triangles)
    save(mesh)
    bounds = mesh.get_bounding_box()
    return {"path": mesh.get_path_name(), "source_sha256": digest, "materials": assignments,
            "source_triangles": triangles, "nanite": nanite, "lods": MESH.get_lod_count(mesh),
            "bounds_cm": [[p.x, p.y, p.z] for p in (bounds.min, bounds.max)],
            "collision": "complex_as_simple" if solid else "empty_simple"}


def main():
    for folder in ("Meshes", "Materials", "Textures"):
        ASSETS.make_directory(DEST + "/" + folder)
    rows = json.loads((SOURCE / "catalog.json").read_text(encoding="utf-8-sig"))
    data = json.loads(RECEIPT.read_text(encoding="utf-8")) if RECEIPT.is_file() else {"saved": {}}
    data["complete"] = False
    receipt_write(data)
    for row in rows:
        key = row["id"]
        src = WORK / "Exchange" / f"SM_Windmill_{key}.fbx"
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        old = data["saved"].get(key, {})
        collision = "complex_as_simple" if key in SOLID else "empty_simple"
        same_source = old.get("source_sha256") == digest and ASSETS.does_asset_exist(old["path"])
        revision = TANGENT_REVISION if key in TANGENT_PARTS else 0
        if same_source and old.get("collision") == collision and old.get("tangent_revision", 0) == revision:
            continue
        data["saved"][key] = author(row, src, digest, old.get("materials", {}) if same_source else {})
        if revision:
            data["saved"][key]["tangent_revision"] = revision
        receipt_write(data)
        ue.log("WINDMILL_SAVED " + key)
    data["complete"] = True
    receipt_write(data)
    ue.log(f"WINDMILL_IMPORT_COMPLETE {len(data['saved'])}")


if __name__ == "__main__":
    main()
