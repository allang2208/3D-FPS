"""Import the tutorial's scanned rocks and plants, and build its road decal materials."""
import json
import os
from pathlib import Path
import unreal as u

SRC = Path(os.environ["FOREST_PATH_SOURCE"]) / "Fab"
ROOT = "/Game/ForestPathStudy/Scans"
lib = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
edit = u.MaterialEditingLibrary

def import_asset(file, folder, name=None):
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = folder
    if name:
        task.destination_name = name
    task.automated = True
    task.save = True
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError(f"Import returned no packages for {file}")
    return task.imported_object_paths

def texture(folder, key, suffix):
    name = f"T_{key}_{suffix.replace('-', '_')}"
    out = f"{folder}/{name}"
    if not lib.does_asset_exist(out):
        import_asset(next((SRC/key).rglob(f"*_{suffix}.png")), folder, name)
    asset = u.load_asset(out)
    if suffix in ("N", "ORM"):
        asset.set_editor_property("srgb", False)
        asset.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_NORMALMAP if suffix == "N" else u.TextureCompressionSettings.TC_MASKS)
        lib.save_loaded_asset(asset, False)
    return asset

def decal(key):
    folder = ROOT + "/" + key
    name = "M_" + key + "_Decal"
    path = f"{folder}/{name}"
    if lib.does_asset_exist(path):
        return path
    lib.make_directory(folder)
    mat = tools.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    mat.set_editor_property("material_domain", u.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property("blend_mode", u.BlendMode.BLEND_TRANSLUCENT)
    for index,(suffix,typ,pins) in enumerate([
        ("B-O", u.MaterialSamplerType.SAMPLERTYPE_COLOR, [("RGB",u.MaterialProperty.MP_BASE_COLOR),("A",u.MaterialProperty.MP_OPACITY)]),
        ("N", u.MaterialSamplerType.SAMPLERTYPE_NORMAL, [("RGB",u.MaterialProperty.MP_NORMAL)]),
        ("ORM", u.MaterialSamplerType.SAMPLERTYPE_MASKS, [("G",u.MaterialProperty.MP_ROUGHNESS)])]):
        sampler = edit.create_material_expression(mat, u.MaterialExpressionTextureSample, -500, index*220)
        sampler.set_editor_property("texture", texture(folder, key, suffix))
        sampler.set_editor_property("sampler_type", typ)
        for channel,prop in pins:
            edit.connect_material_property(sampler, channel, prop)
    edit.recompile_material(mat)
    if not lib.save_loaded_asset(mat, False):
        raise RuntimeError(path)
    return path

def meshes(key):
    folder = ROOT + "/" + key
    registry = u.AssetRegistryHelpers.get_asset_registry()
    files = sorted((SRC / key).glob("*.gltf"))
    if not files:
        raise RuntimeError(f"Missing official glTF for {key}")
    lib.make_directory(folder)
    existing = [a for a in registry.get_assets_by_path(folder,recursive=True) if str(a.asset_class_path.asset_name)=="StaticMesh"]
    if not existing:
        for path in files:
            import_asset(path, folder)
    found = [a for a in registry.get_assets_by_path(folder,recursive=True) if str(a.asset_class_path.asset_name)=="StaticMesh"]
    if not found:
        raise RuntimeError(f"No mesh packages created for {key}")
    return sorted(str(x.package_name) for x in found)

receipt_path = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir())) / "forest-scan-assets.json"
receipt = json.loads(receipt_path.read_text("utf8")) if receipt_path.exists() else {}
for key in os.environ["FOREST_PATH_SCANS"].split(","):
    receipt[key] = decal(key) if key in ("tdipmjh", "slqlwtd", "tjxpg3h", "tjxpndh") else meshes(key)
    receipt_path.write_text(json.dumps(receipt, indent=2),"utf8")
