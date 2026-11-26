"""Make the terrain instance using the two 2K Quixel surfaces named in the film."""
from pathlib import Path
import os
import unreal as ue

root = Path(os.environ["FOREST_PATH_SOURCE"])
dest = "/Game/ForestPathStudy/Materials"
assets = ue.EditorAssetLibrary
tools = ue.AssetToolsHelpers.get_asset_tools()
edit = ue.MaterialEditingLibrary
assets.make_directory(dest)
base = ue.load_asset("/Game/Example/Materials/M_Landscape_NaniteEx")
if not base:
    raise RuntimeError("Unreal Sensei's M_Landscape_NaniteEx is required")
material_path = dest + "/MI_ForestPathLandscape"
material = ue.load_asset(material_path) if assets.does_asset_exist(material_path) else assets.duplicate_asset(base.get_path_name(), material_path)
for group, layer in [("NordicMoss", "A"), ("NordicForestGroundRootsCoarse", "C")]:
    files = root / "Fab" / group
    for parameter, suffix in [("Color", "BaseColor"), ("Normal", "Normal"), ("Roughness", "ORM")]:
        filename = next(files.glob("*_2K_" + suffix + ".*"))
        name = "T_" + group + "_" + suffix
        path = dest + "/" + name
        texture = ue.load_asset(path) if assets.does_asset_exist(path) else None
        if texture is None:
            task = ue.AssetImportTask()
            task.filename = str(filename)
            task.destination_path = dest
            task.destination_name = name
            task.automated = True
            task.save = False
            tools.import_asset_tasks([task])
            texture = ue.load_asset(path)
        if not texture:
            raise RuntimeError(path)
        if suffix in ("Normal", "ORM"):
            texture.set_editor_property("srgb", False)
            texture.set_editor_property("compression_settings", ue.TextureCompressionSettings.TC_NORMALMAP if suffix == "Normal" else ue.TextureCompressionSettings.TC_MASKS)
        if not assets.save_loaded_asset(texture, False):
            raise RuntimeError(path)
        edit.set_material_instance_texture_parameter_value(material, f"{parameter} {layer}", texture)
for key, value in [("Size A", 0.075), ("Size C", 0.498)]:
    edit.set_material_instance_scalar_parameter_value(material, key, value)
edit.update_material_instance(material)
if not assets.save_loaded_asset(material, False):
    raise RuntimeError(material.get_path_name())
