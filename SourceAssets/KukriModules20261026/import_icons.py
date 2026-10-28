"""Save the new kukri UI Texture2D assets; runtime PNG mappings come from deploy_icons.py."""
import json
from pathlib import Path
import unreal as u
P=Path(globals().get('__file__') or r'D:\FPS3D\FPSGAME\SourceAssets\KukriModules20261026\import_icons.py').resolve().parent
jobs=json.loads((P/'icon_deployments.json').read_text(encoding='utf-8'))
tools=u.AssetToolsHelpers.get_asset_tools()
dest='/Game/ColdSteelData/AttachmentIcons20260913'
receipt={'complete':False,'saved_assets':[],'runtime_tested':False}
for job in jobs:
    task=u.AssetImportTask();task.filename=job['source'];task.destination_path=dest;task.destination_name=job['key']
    task.automated=True;task.replace_existing=True;task.save=False
    tools.import_asset_tasks([task]);tex=u.load_asset(dest+'/'+job['key'])
    if not tex:raise RuntimeError('Icon import failed: '+job['key'])
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('max_texture_size',1024)
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Save failed: '+job['key'])
    receipt['saved_assets'].append(tex.get_path_name())
    (P/'icon_import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['complete']=True
(P/'icon_import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('KUKRI_ICONS_SAVED '+str(len(receipt['saved_assets'])))
