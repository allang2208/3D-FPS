"""Install the five framed images and three category aliases, save Texture2D."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];data=json.loads((O/'icon_generation.json').read_text());C=P/'Content/ColdSteelData/AttachmentIcons20260913'
record={'mode':data['mode'],'icons':{},'runtime_tested':False}
generated=O/'FramedIcons';generated.mkdir(exist_ok=True)
jobs={}
for key,file in data['manifest'].items():
 src=generated/('ue_hk416_'+key+'.png');shutil.copy2(Path(data['sourceDirectory'])/file,src);jobs['ue_hk416_'+key]=src
for slot in ['stock','reargrip','magazine']:jobs['ue_hk416_category_'+slot]=jobs['ue_hk416_'+slot+'_false']
for key,source in jobs.items():
 saved=[]
 for folder in ['', 'FramedFirearms']:
  dest=C/folder/(key+'.png');dest.parent.mkdir(exist_ok=True);shutil.copy2(source,dest)
  task=u.AssetImportTask();task.filename=str(dest);task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913'+('/'+folder if folder else '');task.destination_name=key;task.automated=True;task.replace_existing=True;task.save=False
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(task.destination_path+'/'+key)
  if not tex:raise RuntimeError('Icon import failed '+key)
  tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;tex.never_stream=True
  if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Icon save failed '+key)
  saved.append(tex.get_path_name())
 record['icons'][key]={'source':str(source),'assets':saved};(O/'icon_import_receipt.json').write_text(json.dumps(record,indent=2))
record['status']='Eight framed option/category keys saved to both lookup paths';(O/'icon_import_receipt.json').write_text(json.dumps(record,indent=2));print('HK416_FRAMED_ICONS_SAVED',len(jobs))
