"""Save the current RSH equipment/backpack icon, preserving unrelated assets."""
import hashlib
import json
import shutil
import struct
from pathlib import Path
import unreal as u

out=Path(__file__).resolve().parent
project=out.parents[1]
source=out/'ue_rsh12.png'
folder='/Game/ColdSteelData/Icons'
name='ue_rsh12'
asset=folder+'/'+name
if Path(u.Paths.project_dir()).resolve()!=project:raise RuntimeError('Wrong project')
if any(p.get_name()==asset for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('RSH icon has unsaved editor edits; preserve them')
destination=project/'Content/ColdSteelData/Icons/ue_rsh12.png'
shutil.copy2(source,destination)
task=u.AssetImportTask()
task.filename=str(destination)
task.destination_path=folder
task.destination_name=name
task.automated=True
task.replace_existing=True
task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(asset)
if not texture:raise RuntimeError('RSH icon import failed')
texture.srgb=True
texture.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
texture.lod_group=u.TextureGroup.TEXTUREGROUP_UI
texture.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
texture.never_stream=True
u.EditorAssetLibrary.set_metadata_tag(texture,'RSH12IconSource','Current UE factory assembly with RSH private mechanical profile; physical barrel frame level; ColdSteelWeaponIconCatalog -Definition=ue_rsh12; 20261006')
u.EditorAssetLibrary.set_metadata_tag(texture,'Attribution','Rsh-12 by Medji / CC BY 4.0; modified for FPSGAME')
if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):raise RuntimeError('RSH inventory icon save failed')
data=destination.read_bytes()
receipt={'asset':texture.get_path_name(),'png':str(destination),'source':str(source),'size':list(struct.unpack('>II',data[16:24])),'sha256':hashlib.sha256(data).hexdigest(),'source_mesh':'/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny','production_recipe':str(out/'export_icon.ps1'),'shared_by':['equipment','backpack','warehouse','tooltip'],'saved':True,'gameplay_tested':False}
receipt['icon_frame']='RSH12MuzzleAssets::Mount rotation, transformed by the current WPN_root pose'
receipt['mechanical_profile']='/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_base'
(out/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('RSH12_INVENTORY_ICON_IMPORTED_AND_SAVED '+json.dumps(receipt,ensure_ascii=False))
