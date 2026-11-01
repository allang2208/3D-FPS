"""Deploy and save exact M24 catalog icon keys; no preview capture."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).resolve().parent;P=O.parents[1];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
mapping={}
for slot,key in [('optic','m24_custom_scope_6x'),('muzzle','m24_factory_suppressor'),('stock','m24_cheekrest')]:
    mapping['ue_m24_category_'+slot]=key
    mapping[slot+'_'+key]=key
    mapping['ue_m24_'+slot+'_none']='none'
    mapping['ue_m24_'+slot+'_false']=key
directory=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
receipt={'saved':[],'mapping':mapping,'tested':False}
for name,key in mapping.items():
    target=directory/(name+'.png')
    backup=O/'BeforeIcons'/(name+'.png');backup.parent.mkdir(exist_ok=True)
    if target.exists() and not backup.exists():shutil.copy2(target,backup)
    shutil.copy2(O/'Icons'/(key+'.png'),target)
    t=u.AssetImportTask();t.filename=str(target);t.destination_path='/Game/UI/AttachmentIcons20260913/FramedFirearms'
    t.destination_name='T_'+name;t.automated=True;t.replace_existing=True;t.save=False
    A.import_asset_tasks([t]);tex=u.load_asset(t.destination_path+'/'+t.destination_name)
    if not tex:raise RuntimeError('Icon import failed '+name)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
    if not E.save_loaded_asset(tex,False):raise RuntimeError('Icon save failed '+name)
    receipt['saved'].append(tex.get_path_name())
(O/'icon_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_REPAIR_ICONS_SAVED',len(receipt['saved']),flush=True)
