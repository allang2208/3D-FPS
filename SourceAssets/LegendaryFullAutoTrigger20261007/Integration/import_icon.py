"""Save the shared full-auto trigger icon as an Unreal UI texture."""
import json
from pathlib import Path
import unreal as u

output = Path(__file__).resolve().parent
project = output.parents[2]
name = "trigger_legendary_full_auto_trigger"
folder = "ColdSteelData/AttachmentIcons20260913/FramedFirearms"
source = project / "Content" / folder / (name + ".png")
package = "/Game/" + folder + "/" + name
if package in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError("The full-auto trigger texture has unsaved edits")
task = u.AssetImportTask()
task.filename = str(source)
task.destination_path = "/Game/" + folder
task.destination_name = name
task.automated = True
task.replace_existing = False
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = u.load_asset(package)
if not texture:
    raise RuntimeError("Full-auto trigger texture import failed")
texture.srgb = True
texture.lod_group = u.TextureGroup.TEXTUREGROUP_UI
texture.compression_settings = u.TextureCompressionSettings.TC_EDITOR_ICON
texture.never_stream = True
texture.mip_gen_settings = u.TextureMipGenSettings.TMGS_NO_MIPMAPS
if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
    raise RuntimeError("Full-auto trigger texture save failed")
(output / "import_receipt.json").write_text(json.dumps({
    "complete": True, "texture": texture.get_path_name(), "png": str(source),
    "runtime_tested": False, "models_created": False
}, indent=2), encoding="utf-8")
print("FULL_AUTO_TRIGGER_ICON_SAVED", texture.get_path_name(), flush=True)
