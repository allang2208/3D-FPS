"""Import only the two rune masks and their workbench icons."""
from pathlib import Path
import unreal as u

source = Path(__file__).resolve().parent
project = source.parents[2]
icons = "ColdSteelData/AttachmentIcons20260913"
mask_folder = "Weapons/MeleeRunes20260915/SurfaceV2"

def import_texture(png, folder, icon):
    name = png.stem
    path = f"/Game/{folder}/{name}"
    task = u.AssetImportTask()
    task.filename = str(png)
    task.destination_path = "/Game/" + folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.factory = u.TextureFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError(f"Import failed for {png}")
    texture = u.load_asset(path)
    texture.set_editor_property("srgb", icon)
    texture.set_editor_property("address_x", u.TextureAddress.TA_CLAMP)
    texture.set_editor_property("address_y", u.TextureAddress.TA_CLAMP)
    texture.set_editor_property("compression_settings", u.TextureCompressionSettings.TC_EDITOR_ICON
                                if icon else u.TextureCompressionSettings.TC_GRAYSCALE)
    if icon:
        texture.set_editor_property("lod_group", u.TextureGroup.TEXTUREGROUP_UI)
        texture.set_editor_property("mip_gen_settings", u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        texture.set_editor_property("never_stream", True)
    if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
        raise RuntimeError(f"Save failed for {path}")
    print("Saved " + path)

if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError("PIE_ACTIVE: save the new packages in the isolated asset host")
for rune in ("chixiao_rune", "zhufeng_rune"):
    import_texture(source / f"T_Mask_{rune}.png", mask_folder, False)
    import_texture(project / "Content" / icons / f"ue_zhanmadao_blade_2_{rune}.png", icons, True)
