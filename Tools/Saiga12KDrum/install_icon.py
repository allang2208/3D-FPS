import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KDrum20261018');D='/Game/Weapons/Saiga12K/Drum20261018/Icons';name='T_Saiga12K_Drum20_Icon';path=D+'/'+name
if u.EditorAssetLibrary.does_asset_exist(path):raise RuntimeError('Preserve existing '+path)
t=u.AssetImportTask();t.filename=str(O/'Icons/ue_saiga12k_magazine_saiga12k_drum20.png');t.destination_path=D;t.destination_name=name;t.automated=True;t.save=False;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset(path)
if not a:raise RuntimeError('Icon import failed')
a.srgb=True;a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.never_stream=True
if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Icon save failed')
(O/'Receipts/icon-install.json').write_text(json.dumps({'complete':True,'saved':a.get_path_name(),'runtime_png':'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/ue_saiga12k_magazine_saiga12k_drum20.png','runtime_tested':False},indent=2),encoding='utf8');print('SAIGA_DRUM_ICON_SAVED')
