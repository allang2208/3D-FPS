from pathlib import Path
import json, shutil, unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
NAME = 'blade_material_meteoric_iron'
source = P / 'meteoric_iron.png'
destination = ROOT / 'Content/ColdSteelData/AttachmentIcons20260913' / (NAME + '.png')
asset_root = '/Game/ColdSteelData/AttachmentIcons20260913'
if destination.exists():
    backup = P / 'BeforeIcons' / destination.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(destination, backup)
shutil.copy2(source, destination)
task = u.AssetImportTask()
task.filename = str(destination)
task.destination_path = asset_root
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = u.load_asset(asset_root + '/' + NAME)
if not texture:
    raise RuntimeError('Missing imported icon')
for key, value in [('lod_group', u.TextureGroup.TEXTUREGROUP_UI),
                   ('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON),
                   ('srgb', True), ('never_stream', True),
                   ('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)]:
    texture.set_editor_property(key, value)
if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
    raise RuntimeError('Icon save failed')
(P / 'icon-receipt.json').write_text(json.dumps({
    'asset': texture.get_path_name(), 'saved': True, 'source': str(source), 'png': str(destination)
}, indent=2) + '\n', encoding='utf8')
print('METEORIC_IRON_ICON_SAVED', texture.get_path_name())
