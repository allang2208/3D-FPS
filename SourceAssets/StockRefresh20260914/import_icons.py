import unreal as u,json,os
from pathlib import Path
P=Path(__file__).resolve().parent
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
D='/Game/ColdSteelData/AttachmentIcons20260913';receipt=P/'icon_import_results.json'
report=json.loads(receipt.read_text()) if receipt.exists() else {}
keys=os.environ.get('STOCK_REFRESH_ICON_KEYS','false,skeleton,qr_performance,core_stock,tactical_telescopic').split(',')
for key in keys:
 name='stock_'+key;t=u.AssetImportTask();t.filename=str(P/'Icons'/(name+'.png'));t.destination_path=D;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
 A.import_asset_tasks([t]);texture=u.load_asset(D+'/'+name)
 if not texture:raise RuntimeError('Icon import failed: '+name)
 texture.srgb=True;texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI;texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 E.set_metadata_tag(texture,'Orientation','Front left, buttpad right, level orthographic actual-model render')
 if not E.save_loaded_asset(texture,False):raise RuntimeError('Icon save failed: '+name)
 report[key]=texture.get_path_name()
(P/'icon_import_results.json').write_text(json.dumps(report,indent=2));u.log('STOCK_ICON_IMPORT_COMPLETE')
