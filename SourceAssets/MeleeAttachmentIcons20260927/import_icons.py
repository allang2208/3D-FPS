"""Deploy the reviewed PNGs and save their matching UE UI textures in one mutex batch."""
from pathlib import Path
from datetime import datetime
import json,hashlib,shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
DIR=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
PACKAGE='/Game/ColdSteelData/AttachmentIcons20260913/'
audit=json.loads((P/'audit.json').read_text(encoding='utf-8'))
if audit['completed']!=audit['requested'] or audit['issues']:
 raise RuntimeError('Finish the requested icon review before deployment.')
approval=json.loads((P/'visual_review.json').read_text(encoding='utf-8'))
if not approval['all_sheets_reviewed']:raise RuntimeError('Visual review incomplete.')
jobs=[r for r in audit['icons'] if r['action']!='retain']
targets={PACKAGE+r['key'] for r in jobs}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Preserving unsaved icon packages: '+str(targets.intersection(dirty)))
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt_file=P/'import_receipt.json'
receipt=json.loads(receipt_file.read_text(encoding='utf-8')) if receipt_file.exists() else []
done={r['key']:r for r in receipt if r['saved']}
backup=P/'BeforePackages';backup.mkdir(exist_ok=True)
backup_rows=[]
for r in jobs:
 if r['key'] in done:continue
 src=Path(r['output']);dst=DIR/(r['key']+'.png')
 if digest(src)!=r['output_sha256']:raise RuntimeError('Staged image changed after review: '+str(src))
 if dst.exists() and (not r['resolved'] or Path(r['resolved'])!=dst or digest(dst)!=r['sha256']):
  raise RuntimeError('Runtime PNG changed concurrently: '+str(dst))
 for extension in ['.png','.uasset','.uexp','.ubulk']:
  file=dst.with_suffix(extension)
  if file.exists():
   old=backup/file.name
   if old.exists() and digest(old)!=digest(file):raise RuntimeError('Backup differs: '+str(file))
   if not old.exists():shutil.copy2(file,old)
   backup_rows.append({'path':str(file),'backup':str(old),'sha256':digest(file)})
(P/'backup_manifest.json').write_text(json.dumps(backup_rows,indent=2),encoding='utf-8')
lib=u.EditorAssetLibrary;asset_tools=u.AssetToolsHelpers.get_asset_tools()
for r in jobs:
 key=r['key']
 if key in done:continue
 dst=DIR/(key+'.png');shutil.copy2(r['output'],dst)
 task=u.AssetImportTask();task.filename=str(dst);task.destination_path=PACKAGE.rstrip('/');task.destination_name=key
 task.automated=True;task.replace_existing=True;task.save=False
 asset_tools.import_asset_tasks([task])
 tex=u.load_asset(PACKAGE+key)
 if not tex or not task.imported_object_paths:raise RuntimeError('Texture import failed: '+key)
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
 tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
 tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
 tex.set_editor_property('srgb',True)
 if not lib.save_loaded_asset(tex,False):raise RuntimeError('Texture save failed: '+key)
 row={'key':key,'png':str(dst),'sha256':r['output_sha256'],'asset':tex.get_path_name(),
      'saved':True,'time':datetime.now().isoformat()}
 done[key]=row
 receipt_file.write_text(json.dumps(list(done.values()),indent=2),encoding='utf-8')
 print('MELEE_ICON_SAVED '+key)
print('MELEE_ICON_IMPORT_COMPLETE '+str(len(done)))
