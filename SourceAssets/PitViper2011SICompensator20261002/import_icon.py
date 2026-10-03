"""Import the single exclusive SI card icon; shared muzzle icons are reused."""
import hashlib,json,shutil
from pathlib import Path
import unreal as u

O=Path(__file__).parent;P=O.parents[1]
KEY='ue_pit_viper2011_muzzle_pit_viper_si_compensator'
FOLDER='/Game/Weapons/PitViper2011/SICompensator20261003/Icons'
NAME='T_'+KEY;ASSET=FOLDER+'/'+NAME
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong production project')
receipt_path=O/'integration_receipt.json'
receipt=json.loads(receipt_path.read_text(encoding='utf8'))
if receipt.get('status')!='imported_and_saved':raise RuntimeError('Save SI model assets before the card icon')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if ASSET in dirty:raise RuntimeError('Preserve unsaved SI card icon')
src=O/'Icons'/(KEY+'.png')
dest=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(KEY+'.png')
if not src.is_file():raise RuntimeError('Produce the exclusive SI icon before import')
backup=O/'Integration20261003/Before/Icons'/dest.name
if dest.exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,backup)
dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
task=u.AssetImportTask();task.filename=str(dest);task.destination_path=FOLDER;task.destination_name=NAME
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(ASSET)
if not tex:raise RuntimeError('SI icon import failed')
tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
tex.never_stream=True
if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('SI icon save failed')
icon={'status':'imported_and_saved','part':'pit_viper_si_compensator','png':str(dest),
      'asset':tex.get_path_name(),'master':str(src),'source_render':str(O/'Icons/SICompensator_Model_Gray.png'),
      'frame':str(O.parent/'FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'),
      'mode':'exclusive SI model composed into the existing grayscale attachment frame',
      'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'game_tested':False,'acceptance_rendered':False}
(O/'icon_delivery.json').write_text(json.dumps(icon,ensure_ascii=False,indent=2),encoding='utf8')
receipt['icon']=icon;receipt['saved'].append(tex.get_path_name())
receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print('PIT_VIPER_SI_COMPENSATOR_ICON_IMPORTED_AND_SAVED',flush=True)
