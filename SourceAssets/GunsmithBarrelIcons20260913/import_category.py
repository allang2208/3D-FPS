"""Import the missing barrel category texture, preserving other category assets."""
from pathlib import Path
import json
import unreal

root = Path(unreal.Paths.project_dir())
source = root / 'SourceAssets/GunsmithBarrelIcons20260913'
destination = '/Game/UI/GunsmithWorkbench/ColdGlass'
name = 'T_Category_barrel'

task = unreal.AssetImportTask()
task.set_editor_property('filename', str(source / 'category_barrel.png'))
task.set_editor_property('destination_path', destination)
task.set_editor_property('destination_name', name)
task.set_editor_property('factory', unreal.TextureFactory())
task.set_editor_property('automated', True)
task.set_editor_property('replace_existing', True)
task.set_editor_property('save', True)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

texture = unreal.load_asset(destination + '/' + name)
if texture is None:
    raise RuntimeError('Barrel category texture import did not return an asset')
texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('srgb', True)
texture.set_editor_property('never_stream', True)
unreal.EditorAssetLibrary.save_loaded_asset(texture)

report = {
    'category_texture': texture.get_path_name(),
    'category_material': '/Game/UI/GunsmithWorkbench/ColdGlass/M_CategoryIcon.M_CategoryIcon',
    'category_display': 'Existing near-black keyed UI material',
    'option_images': [
        'Content/ColdSteelData/AttachmentIcons20260913/barrel_short.png',
        'Content/ColdSteelData/AttachmentIcons20260913/barrel_long.png',
    ],
    'factory_option': 'Existing category brush fallback',
    'tests': 'Not run, per user instruction',
}
(source / 'import-result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('BARREL_ICONS_IMPORT_COMPLETE ' + json.dumps(report))
