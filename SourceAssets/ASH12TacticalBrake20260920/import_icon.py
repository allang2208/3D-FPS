"""Install the ASH-only production UI icon in the current editor."""
import json
import shutil
from pathlib import Path
import unreal as u
O = Path(__file__).resolve().parent
ROOT = O.parents[1]
name = 'ue_ash12_muzzle_ash12_tactical_brake'
source = O/(name+'.png')
destination = ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/source.name
shutil.copy2(source, destination)
task = u.AssetImportTask()
task.filename = str(source)
task.destination_path = '/Game/ColdSteelData/AttachmentIcons20260913'
task.destination_name = name
task.automated = True; task.replace_existing = True; task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = u.load_asset(task.destination_path+'/'+name)
if not texture:
    raise RuntimeError('Icon import failed')
texture.srgb = True
texture.compression_settings = u.TextureCompressionSettings.TC_EDITOR_ICON
texture.lod_group = u.TextureGroup.TEXTUREGROUP_UI
texture.mip_gen_settings = u.TextureMipGenSettings.TMGS_NO_MIPMAPS
if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outer()], False):
    raise RuntimeError('Icon save failed')
receipt = {'texture': texture.get_path_name(), 'png': str(destination), 'saved': True, 'tested': False}
(O/'import_icon.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('ASH12_BRAKE_ICON_IMPORTED '+json.dumps(receipt, ensure_ascii=False))
