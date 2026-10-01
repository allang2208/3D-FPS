import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930';P=O.parents[1]
ROOT='/Game/Weapons/HK416/Reworked20260930/Icons'
keys=['ue_hk416_underbarrel_vertical_foregrip','ue_hk416_tactical_flashlight','ue_hk416_tactical_laser','ue_hk416_category_underbarrel','ue_hk416_category_tactical']
report={'saved':[],'icons':{}}
for key in keys:
    source=S/'Icons'/(key+'.png');dest=P/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png');shutil.copy2(source,dest)
    task=u.AssetImportTask();task.filename=str(dest);task.destination_path=ROOT;task.destination_name=key
    task.automated=True;task.replace_existing=True;task.save=False;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(ROOT+'/'+key)
    if not tex:raise RuntimeError('Missing '+key)
    tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Save failed '+key)
    report['saved'].append(tex.get_path_name());report['icons'][key]={'asset':tex.get_path_name(),'png':str(dest),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'grayscale':True}
(O/'icon_import_receipt.json').write_text(json.dumps(report,indent=2));print('HK416_CORRECTED_ATTACHMENT_ICONS_SAVED',len(keys))
