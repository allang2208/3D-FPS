import json
from pathlib import Path
import unreal as ue

root = Path(__file__).resolve().parent
runtime = Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/AttachmentIcons20260913')
destination = '/Game/ColdSteelData/AttachmentIcons20260913'
assets = ue.AssetToolsHelpers.get_asset_tools()
receipt = {}
for key in ('shock_wrap', 'swift_grip', 'long_twohand'):
    name = 'grip_' + key
    task = ue.AssetImportTask()
    task.filename = str(runtime / (name + '.png'))
    task.destination_path = destination
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    assets.import_asset_tasks([task])
    texture = ue.load_asset(destination + '/' + name)
    if not texture:
        raise RuntimeError('Could not import icon: ' + name)
    texture.srgb = True
    texture.lod_group = ue.TextureGroup.TEXTUREGROUP_UI
    texture.compression_settings = ue.TextureCompressionSettings.TC_EDITOR_ICON
    texture.mip_gen_settings = ue.TextureMipGenSettings.TMGS_NO_MIPMAPS
    ue.EditorAssetLibrary.set_metadata_tag(texture, 'Source', 'User-requested image_gen illustrative numeric sword grip upgrade, 2026-09-15; no model change')
    if not ue.EditorAssetLibrary.save_loaded_asset(texture, False):
        raise RuntimeError('Could not save icon: ' + name)
    receipt[key] = texture.get_path_name()
(root / 'icon_import_results.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
ue.log('MELEE_GRIP_ICONS_IMPORTED')
