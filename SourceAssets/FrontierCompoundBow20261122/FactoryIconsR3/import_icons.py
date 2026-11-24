"""Run in the isolated UE authoring host with FRONTIER_FACTORY_SOURCE and FRONTIER_FACTORY_BATCH."""
import json
import os
from pathlib import Path
import unreal as u

folder = '/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'
export = Path(os.environ['FRONTIER_FACTORY_SOURCE']) / 'Export'
saved = {}
for path in sorted(export.glob('bow_frontier_compound_*_r3.png')):
    task = u.AssetImportTask()
    task.filename = str(path)
    task.destination_path = folder
    task.destination_name = path.stem
    task.automated = True
    task.replace_existing = True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(folder + '/' + path.stem)
    texture.lod_group = u.TextureGroup.TEXTUREGROUP_UI
    texture.compression_settings = u.TextureCompressionSettings.TC_EDITOR_ICON
    texture.mip_gen_settings = u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    texture.srgb = True
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
        raise RuntimeError(path.stem)
    saved[path.stem] = texture.get_path_name()
if len(saved) != 6:
    raise RuntimeError(f'Expected 6 source icons, got {len(saved)}')
(Path(os.environ['FRONTIER_FACTORY_BATCH']) / 'saved-textures.json').write_text(json.dumps(saved, indent=2))
