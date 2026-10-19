import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/S12KStockReference20261018');D='/Game/Weapons/Saiga12K/SpecialStock20261018/Icons';name='T_Saiga12K_SpecialStock_Icon';path=D+'/'+name
if not u.EditorAssetLibrary.does_asset_exist(path):raise RuntimeError('Expected owned icon '+path)
t=u.AssetImportTask();t.filename=str(O/'Icons/ue_saiga12k_stock_saiga12k_bump_stock.png');t.destination_path=D;t.destination_name=name;t.automated=True;t.replace_existing=True;t.replace_existing_settings=False;t.save=False;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset(path)
if not a:raise RuntimeError('Icon import failed')
a.srgb=True;a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.never_stream=True
if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Icon save failed')
(O/'Receipts/icon-install.json').write_text(json.dumps({'complete':True,'saved':a.get_path_name(),'runtime_png':'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_saiga12k_stock_saiga12k_bump_stock.png','runtime_tested':False},indent=2),encoding='utf8');print('SAIGA_STOCK_ICON_SAVED')
