"""Import only the selected Chain Slash skill texture."""
from pathlib import Path
import unreal

project = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
name = "chain_slash_cold_steel"
task = unreal.AssetImportTask()
task.filename = str(project / "ColdSteelData" / "Skills" / (name + ".png"))
task.destination_path = "/Game/ColdSteelData/Skills"
task.destination_name = name
task.automated = True
task.replace_existing = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = unreal.load_asset(task.destination_path + "/" + name)
if not task.imported_object_paths or not isinstance(texture, unreal.Texture2D):
    raise RuntimeError("Chain Slash icon import failed")
texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property("never_stream", True)
texture.set_editor_property("srgb", True)
texture.set_editor_property("max_texture_size", 512)
if not unreal.EditorAssetLibrary.save_loaded_asset(texture, False):
    raise RuntimeError("Chain Slash icon save failed")
