import json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2];ID='ue_xuanchi_zhenyue'
jobs=json.loads((P/'Icons/deployments.json').read_text())
inventory=R/'Content/ColdSteelData/Icons'/(ID+'.png')
shutil.copy2(inventory,P/'Icons'/(ID+'.png'))
jobs.append({'file':str(inventory),'asset':'/Game/ColdSteelData/Icons/'+ID})
receipt={'complete':False,'assets':[],'game_tested':False}
for row in jobs:
    path=row['asset'];folder,name=path.rsplit('/',1)
    task=u.AssetImportTask();task.filename=row['file'];task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(path)
    if not tex:raise RuntimeError('Icon import failed: '+path)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('never_stream',True);tex.set_editor_property('srgb',True)
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Icon save failed: '+path)
    receipt['assets'].append(tex.get_path_name());(P/'Icons/import_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;(P/'Icons/import_receipt.json').write_text(json.dumps(receipt,indent=2));print('XUANCHI_ICONS_SAVED')
