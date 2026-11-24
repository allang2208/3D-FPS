"""Import the catalog render in the authoring host. Keep the R2 package for old references."""
import json
import os
from pathlib import Path
import shutil

import unreal

batch = Path(os.environ["FRONTIER_INVENTORY_BATCH"])
folder = "/Game/ColdSteelData/Icons"
primary = "bow_frontier_compound"
names = (primary, primary + "_r2")
export = batch / "Export"
shutil.copyfile(export / (primary + ".png"), export / (names[1] + ".png"))
saved = {}
for name in names:
    task = unreal.AssetImportTask()
    task.filename = str(export / (name + ".png"))
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset_path = f"{folder}/{name}.{name}"
    if asset_path not in task.imported_object_paths:
        raise RuntimeError(f"Import did not produce {asset_path}")
    texture = unreal.load_asset(asset_path)
    texture.lod_group = unreal.TextureGroup.TEXTUREGROUP_UI
    texture.compression_settings = unreal.TextureCompressionSettings.TC_EDITOR_ICON
    texture.mip_gen_settings = unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS
    texture.srgb = True
    if not unreal.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
        raise RuntimeError(f"Could not save {asset_path}")
    saved[name] = asset_path
(batch / "saved-textures.json").write_text(json.dumps(saved, indent=2), encoding="utf-8")
