import json,shutil,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1]
key='ue_pit_viper2011_reargrip_pit_viper_vip_scales'
folder='/Game/Weapons/PitViper2011/VipGrip20261002/Icons';name='T_'+key;path=folder+'/'+name
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Wrong production project')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Preserve unsaved VIP icon')
current=O.parent/'PitViper2011ViperLongitudinalGrip20261003'
src=current/'Icons'/(key+'.png');dest=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'/(key+'.png')
backup=O/'Before/Icons'/dest.name;backup.parent.mkdir(parents=True,exist_ok=True)
if dest.exists() and not backup.exists():shutil.copy2(dest,backup)
shutil.copy2(src,dest)
task=u.AssetImportTask();task.filename=str(dest);task.destination_path=folder;task.destination_name=name
task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(path)
if not tex:raise RuntimeError('VIP icon import failed')
tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI
tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;tex.never_stream=True
if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('VIP icon save failed')
receipt={'status':'imported_and_saved','part':'pit_viper_vip_scales','png':str(dest),'asset':tex.get_path_name(),
  'master':str(src),'source_render':str(current/'Icons/viper-grip-model-gray.png'),
  'frame':str(O.parent/'FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'),
  'mode':'imagegen frame composition constrained by the current Blender model; grayscale UI asset',
  'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'game_tested':False,'acceptance_rendered':False}
(O/'icon_delivery.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf8')
record=json.loads((O/'import_receipt.json').read_text(encoding='utf8'));record['icon']=receipt
(O/'import_receipt.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf8')
print('PIT_VIPER_GRIP_REBUILT_ICON_IMPORTED_AND_SAVED',flush=True)
