"""Save only this bow's factory icons in the production-path staging project."""
import json
import os
from pathlib import Path
import unreal as ue

source = Path(__file__).resolve().parent / 'Export/PartIcons'
receipt = Path(os.environ['FRONTIER_BOW_BATCH']) / 'part-icons.json'
folder = '/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'
packages = {}
for slot in ('riser', 'grip', 'arrow_rest'):
    name = 'bow_frontier_compound_'+slot+'_false'
    task = ue.AssetImportTask()
    task.filename = str(source/(name+'.png'))
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    icon = ue.load_asset(folder+'/'+name)
    icon.lod_group = ue.TextureGroup.TEXTUREGROUP_UI
    icon.compression_settings = ue.TextureCompressionSettings.TC_EDITOR_ICON
    icon.mip_gen_settings = ue.TextureMipGenSettings.TMGS_NO_MIPMAPS
    icon.srgb = True
    if not ue.EditorLoadingAndSavingUtils.save_packages([icon.get_outermost()], False):
        raise RuntimeError('Unable to save '+name)
    packages[name] = icon.get_path_name()
receipt.write_text(json.dumps(packages, indent=2), encoding='utf8')
