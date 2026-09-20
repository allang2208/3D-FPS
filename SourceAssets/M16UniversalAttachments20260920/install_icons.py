"""Publish the M16-specific production icons, preserving shared representatives."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1];C=ROOT/'Content/ColdSteelData/AttachmentIcons20260913';D='/Game/ColdSteelData/AttachmentIcons20260913'
manifest=json.loads((O/'Icons/manifest.json').read_text());report={}
rows={name:O/'Icons'/(name+'.png') for name in manifest}
for name,file in list(rows.items()):
 if name.endswith('_false'):rows[name.replace('_false','').replace('ue_m16a2_','ue_m16a2_category_')]=file
for name,source in rows.items():
 dest=C/(name+'.png')
 if dest.exists():
  backup=O/'BeforeIcons';backup.mkdir(exist_ok=True)
  if not (backup/dest.name).exists():shutil.copy2(dest,backup/dest.name)
 shutil.copy2(source,dest)
 task=u.AssetImportTask();task.filename=str(dest);task.destination_name=name;task.destination_path=D;task.automated=True;task.replace_existing=True;task.save=False
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(D+'/'+name);tex.srgb=True;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
 if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outer()],False):raise RuntimeError('Icon save '+name)
 report[name]={'source':str(source),'png':str(dest),'texture':tex.get_path_name(),'saved':True}
 (O/'icon_install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('M16_ATTACHMENT_ICONS_SAVED')
