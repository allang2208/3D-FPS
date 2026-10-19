import unreal as u,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KMagazine20261017'
key='ue_saiga12k_magazine_saiga12k_ext12';folder='ColdSteelData/AttachmentIcons20260913/FramedFirearms';dest='/Game/'+folder
t=u.AssetImportTask();t.filename=str(P/'Content'/folder/(key+'.png'));t.destination_path=dest;t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset(dest+'/'+key)
a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;a.srgb=True;a.never_stream=True
if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Icon save failed')
(O/'Receipts/icon.json').write_text(json.dumps({'saved':a.get_path_name(),'png':t.filename,'ui_group':True,'srgb':True,'never_stream':True,'runtime_tested':False},indent=2),encoding='utf-8')
print('SAIGA_EXT12_ICON_SAVED')
