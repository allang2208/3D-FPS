"""Publish six shared PNG keys and save their corresponding UE UI textures."""
import json,shutil,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
ICONS=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
DEST='/Game/ColdSteelData/AttachmentIcons20260913'
rows=json.loads((P/'source_manifest.json').read_text(encoding='utf-8'))
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Exit PIE before replacing and saving the shared icon textures; no changes made')
for row in rows:
    if not (P/'Generated'/(row['key']+'.png')).is_file():
        raise RuntimeError('Framed icon generation is incomplete: '+row['key'])
retired=ROOT/'trash/shared-pommel-icons-20261005';retired.mkdir(parents=True,exist_ok=True)
receipt={'complete':False,'shared_icons':[],'archived_previous':[],
    'per_weapon_images_generated':0,'game_tested':False}
def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
for row in rows:
    key=row['key'];source=P/'Generated'/(key+'.png');target=ICONS/(key+'.png')
    for previous in [target,target.with_suffix('.uasset')]:
        if previous.exists():
            backup=retired/previous.name
            if not backup.exists():shutil.copy2(previous,backup)
            receipt['archived_previous'].append({'file':str(previous),'archive':str(backup),'archive_sha256':digest(backup)})
    shutil.copy2(source,target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_path=DEST;task.destination_name=key
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=u.load_asset(DEST+'/'+key)
    if not texture or not task.imported_object_paths:raise RuntimeError('Icon import failed: '+key)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',True)
    u.EditorAssetLibrary.set_metadata_tag(texture,'SharedPommelIconRevision','FramedGrayscale20261005')
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):
        raise RuntimeError('Icon save failed: '+key)
    receipt['shared_icons'].append({'key':key,'label':row['label'],'image':str(target),
        'asset':texture.get_path_name(),'source_image':str(source),'sha256':digest(target),
        'runtime_mesh':row['runtime_mesh']})
    record()

# Keep XuanChi's deployment record on the same common keys. The icon resolver
# also prefers these keys for all other compatible melee weapons.
deployment=ROOT/'SourceAssets/XuanChiZhenYue20261004/ModelV1/Icons/deployments.json'
original=deployment.read_bytes();jobs=json.loads(original.decode('utf-8-sig'))
before=P/'Before/deployments.json';before.parent.mkdir(exist_ok=True)
if not before.exists():before.write_bytes(original)
for row in receipt['shared_icons']:
    existing=next((job for job in jobs if Path(job['file']).stem==row['key']),None)
    entry={'source':row['source_image'],'file':row['image'],'asset':DEST+'/'+row['key'],'slot':'pommel'}
    if existing:existing.update(entry)
    else:jobs.append(entry)
if deployment.read_bytes()!=original:raise RuntimeError('Icon deployment manifest changed during merge')
tmp=deployment.with_suffix('.shared-pommel-icons.tmp')
tmp.write_text(json.dumps(jobs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(deployment)
(retired/'manifest.json').write_text(json.dumps(receipt['archived_previous'],indent=2)+'\n',encoding='utf-8')
receipt['complete']=True;record()
print('SIX_SHARED_POMMEL_ICONS_SAVED '+json.dumps({'count':len(receipt['shared_icons']),
    'per_weapon_images_generated':0,'complete':True,'game_tested':False}),flush=True)
