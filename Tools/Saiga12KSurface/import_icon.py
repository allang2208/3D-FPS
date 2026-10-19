import unreal as u,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KSurface20261018';name='ue_saiga12k_magazine_saiga12k_ext12';dest='/Game/Weapons/Saiga12K/SurfaceRebuild20261018/Icons'
t=u.AssetImportTask();t.filename=str(P/('Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/'+name+'.png'));t.destination_path=dest;t.destination_name=name;t.automated=True;t.save=False;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset(dest+'/'+name);a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;a.srgb=True;a.never_stream=True
if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Icon save failed')
(O/'Receipts/icon.json').write_text(json.dumps({'saved':a.get_path_name(),'png':t.filename,'ui_group':True,'compression':'Editor Icon','srgb':True,'never_stream':True,'generation':'built-in image_gen from actual rebuilt magazine'},indent=2),encoding='utf-8')
