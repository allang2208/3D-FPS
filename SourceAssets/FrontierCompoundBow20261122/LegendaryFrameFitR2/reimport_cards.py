"""Refresh only the source pixels, retaining the current project's texture import settings."""
from pathlib import Path
import hashlib, json, os
import unreal as u
src=Path(__file__).resolve().parent
batch=Path(os.environ['FIT_BATCH'])
receipt=json.loads((batch/'imported.json').read_bytes())
for kind,row in receipt.items():
    package=row['icon'].split('.')[0]
    folder,key=package.rsplit('/',1)
    rel=Path('Content')/(package.removeprefix('/Game/')+'.uasset')
    prior=batch/'IconInputs'/rel
    active_copy=batch/'Host'/rel
    baseline=hashlib.sha256(prior.read_bytes()).hexdigest()
    if hashlib.sha256(active_copy.read_bytes()).hexdigest()!=baseline:raise RuntimeError('Expected current project icon in the staging host')
    texture=u.load_asset(package)
    properties=['srgb','compression_settings','lod_group','mip_gen_settings']
    settings={p:str(texture.get_editor_property(p)) for p in properties}
    task=u.AssetImportTask();task.filename=str(src/'Export'/(key+'.png'));task.destination_name=key;task.destination_path=folder
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=u.load_asset(package)
    if not task.imported_object_paths or settings!={p:str(texture.get_editor_property(p)) for p in properties}:raise RuntimeError('Icon settings changed: '+key)
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):raise RuntimeError('Failed to save '+key)
    row['icon_baseline']=baseline;row['icon_settings']=settings
(batch/'imported.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
