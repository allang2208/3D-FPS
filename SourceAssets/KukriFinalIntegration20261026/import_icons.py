"""Import and save only the final Kukri menu icon packages through the locked bridge."""
import json
from datetime import datetime
from pathlib import Path
import unreal as u
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/KukriFinalIntegration20261026')
deployment=json.loads((P/'Receipts/deployment.json').read_text(encoding='utf-8'))
if not deployment['complete']:raise RuntimeError('Deploy all final masters before import')
tools=u.AssetToolsHelpers.get_asset_tools()
receipt={'complete':False,'started':datetime.now().astimezone().isoformat(),'saved_assets':[],
         'runtime_tested':False,'numeric_changes':False}
for job in deployment['bindings']:
    task=u.AssetImportTask();task.filename=job['source']
    task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';task.destination_name=job['key']
    task.automated=True;task.replace_existing=True;task.save=False
    tools.import_asset_tasks([task]);tex=u.load_asset(job['texture'])
    if not tex:raise RuntimeError('Icon import failed: '+job['key'])
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('max_texture_size',1024)
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):
        raise RuntimeError('Save failed: '+job['key'])
    receipt['saved_assets'].append(tex.get_path_name())
    (P/'Receipts/import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
receipt['complete']=True
(P/'Receipts/import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('KUKRI_STANDARD_ICON_PACKAGES_SAVED '+str(len(receipt['saved_assets'])))
