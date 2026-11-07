"""Import and save only the oath icon Texture2D. No gameplay or scene operations."""
from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent
KEY='ue_highland_claymore_blade_2_highland_oath_rune'
DEST='/Game/ColdSteelData/AttachmentIcons20260913'
task=u.AssetImportTask()
task.filename=str(P/'OathRune_Framed_V2.png');task.destination_path=DEST;task.destination_name=KEY
task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(DEST+'/'+KEY)
if not texture or not task.imported_object_paths:raise RuntimeError('Oath icon import failed')
texture.set_editor_property('srgb',True)
texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property('never_stream',True)
texture.set_editor_property('address_x',u.TextureAddress.TA_CLAMP)
texture.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Oath icon save failed')
(P/'saved-icon.json').write_text(json.dumps({'complete':True,'texture':texture.get_path_name(),'source':task.filename,'never_stream':True,'gameplay_tested':False},indent=2),encoding='utf-8')
print('OATH_ICON_V2_SAVED')
