import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1];D=R/'Content/ColdSteelData/AttachmentIcons20260913';report=json.loads((P/'audit_report.json').read_text());out=[]
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
for change in report['changes']:
 key=change['key'];task=u.AssetImportTask();task.filename=str(D/(key+'.png'));task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';task.destination_name=key;task.automated=True;task.replace_existing=True;task.save=False
 A.import_asset_tasks([task]);asset=u.load_asset(task.destination_path+'/'+key)
 if not isinstance(asset,u.Texture2D):raise RuntimeError('Icon texture import failed '+key)
 asset.srgb=True;asset.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;asset.lod_group=u.TextureGroup.TEXTUREGROUP_UI;asset.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 E.set_metadata_tag(asset,'AttachmentIconRule','20260914 actual model front-left, one part, transparent')
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Icon texture save failed '+key)
 out.append({'key':key,'asset':asset.get_path_name(),'source':task.filename});(P/'import_receipt.json').write_text(json.dumps(out,indent=2))
 u.log('ATTACHMENT_ICON_IMPORTED '+key)
u.log('ATTACHMENT_ICON_IMPORT_COMPLETE '+str(len(out)))
