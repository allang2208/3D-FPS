"""Publish the five forged-sword cards to the PNG and Texture2D keys used by the workbench."""
from pathlib import Path
import shutil
import unreal as u


def install_stock_icons():
    here = Path(__file__).resolve().parent
    folder = '/Game/ColdSteelData/AttachmentIcons20260913'
    content = here.parents[2] / 'Content/ColdSteelData/AttachmentIcons20260913'
    saved = []
    for slot in ('blade_1', 'guard', 'grip', 'pommel', 'blade_material'):
        source = here / 'Icons' / (slot + '_factory.png')
        for suffix in ('category_' + slot, slot + '_false'):
            key = 'ue_forged_steel_greatsword_' + suffix
            target = content / (key + '.png')
            temp = target.with_suffix('.forged-stock.tmp')
            shutil.copyfile(source, temp)
            temp.replace(target)
            task = u.AssetImportTask()
            task.filename = str(target)
            task.destination_path = folder
            task.destination_name = key
            task.automated = True
            task.replace_existing = True
            task.save = False
            u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            expected = folder + '/' + key + '.' + key
            if expected not in task.imported_object_paths:
                raise RuntimeError('Icon import did not return ' + expected)
            icon = u.load_asset(expected)
            icon.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
            icon.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
            icon.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
            icon.set_editor_property('srgb', True)
            icon.set_editor_property('never_stream', True)
            if not u.EditorAssetLibrary.save_loaded_asset(icon, False):
                raise RuntimeError('Could not save ' + expected)
            saved.append(expected)
    return saved
