"""Publish the one HK416 equipment/backpack catalog texture."""
import unreal as u,json,shutil,struct,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];source=O/'ue_hk416.png'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():raise RuntimeError('Wrong content mount')
data=source.read_bytes();width,height=struct.unpack('>II',data[16:24])
folder='/Game/ColdSteelData/Icons';name='ue_hk416';asset=folder+'/'+name
if any(p.get_name()==asset for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('HK416 icon has unsaved editor edits; preserve them')
destination=P/'Content/ColdSteelData/Icons/ue_hk416.png';shutil.copy2(source,destination)
t=u.AssetImportTask();t.filename=str(destination);t.destination_path=folder;t.destination_name=name;t.automated=True;t.replace_existing=True;t.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);texture=u.load_asset(asset)
if not texture:raise RuntimeError('HK416 inventory icon import failed')
texture.srgb=True;texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI;texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
u.EditorAssetLibrary.set_metadata_tag(texture,'HK416IconSource','Current UE assembly: ColdSteelWeaponIconCatalog -Definition=ue_hk416; 20261001')
u.EditorAssetLibrary.set_metadata_tag(texture,'Attribution','HK416 Full ReWorked / MojoLeeDa / CC BY 4.0; modified for FPSGAME')
if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):raise RuntimeError('HK416 inventory icon save failed')
record={'asset':texture.get_path_name(),'png':str(destination),'source':str(source),'size':[width,height],'sha256':hashlib.sha256(data).hexdigest(),'shared_by':['equipment','backpack','warehouse','tooltip'],'runtime_tested':False}
(O/'import_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
# Keep subsequent HK416 icon publication on the current equipment image.
legacy=O.parent/'HK416Reworked20260930';shutil.copy2(source,legacy/'Icons/ue_hk416.png')
receipt_path=legacy/'icon_render_receipt.json';records=json.loads(receipt_path.read_text(encoding='utf-8'))
records['ue_hk416']={'file':str(legacy/'Icons/ue_hk416.png'),'source':'/Game/Weapons/HK416/Reworked20260930/SK_HK416_Manny','size':[width,height],'grayscale':False,'alpha':'transparent','production_recipe':str(O/'export_icon.ps1')}
receipt_path.write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('HK416_INVENTORY_ICON_IMPORTED_AND_SAVED',width,height,texture.get_path_name())
