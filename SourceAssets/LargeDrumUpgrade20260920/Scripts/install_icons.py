"""Install real-model icons for the existing large_drum option."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/LargeDrumUpgrade20260920')
C=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/AttachmentIcons20260913')
D='/Game/ColdSteelData/AttachmentIcons20260913';E=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Icon saving requires leaving PIE')
backup_dir=O/'Before/Icons';backup_dir.mkdir(exist_ok=True)
rows=[('M4','magazine_large_drum'),('M4','ue_m4a1_magazine_large_drum'),('AKM','ue_akm_magazine_large_drum'),('QBZ191','ue_qbz191_magazine_large_drum')]
report_file=O/'icon_install_receipt.json'
report=json.loads(report_file.read_text()) if report_file.exists() else {}
for gun,name in rows:
 if report.get(name,{}).get('saved'):continue
 src=O/'Icons'/(gun+'_magazine_large_drum.png');dst=C/(name+'.png')
 old_png=dst.exists();old_asset=E.does_asset_exist(D+'/'+name)
 if old_png and not (backup_dir/(name+'.png')).exists():shutil.copy2(dst,backup_dir/(name+'.png'))
 backed_up=report.get(name,{}).get('previous_asset_backed_up',False)
 if old_asset and name not in report:
  b=E.duplicate_asset(D+'/'+name,'/Game/Weapons/LargeDrumUpgrade20260920/Before/'+name)
  if not b or not E.save_loaded_asset(b,False):raise RuntimeError('Icon backup failed '+name)
  backed_up=True
 shutil.copy2(src,dst)
 task=u.AssetImportTask();task.filename=str(dst);task.destination_path=D;task.destination_name=name
 task.automated=True;task.replace_existing=old_asset;task.save=False
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(D+'/'+name)
 if not tex:raise RuntimeError('Icon import failed '+name)
 tex.srgb=True;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON
 saved=bool(E.save_loaded_asset(tex,False))
 report[name]={'source':str(src),'png':str(dst),'texture':tex.get_path_name(),'previous_png_backed_up':(backup_dir/(name+'.png')).exists(),'previous_asset_backed_up':backed_up,'saved':saved}
 (O/'icon_install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 if not saved:raise RuntimeError('Icon save failed '+name)
print('LARGE_DRUM_ICONS_INSTALLED '+','.join(report))
