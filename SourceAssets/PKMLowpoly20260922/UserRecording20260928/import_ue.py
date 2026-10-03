from pathlib import Path
import unreal as u,json,shutil
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/PKMLowpoly20260922/UserRecording20260928')
rows=json.loads((P/'cuts.json').read_text());receipt=[]
for r in rows:
 dest='/Game/Weapons/PKMLowpoly20260922/'+r['folder'];path=dest+'/'+r['name'];old=u.load_asset(path)
 if old is None: raise RuntimeError('Missing existing target '+path)
 settings={k:old.get_editor_property(k) for k in ('volume','pitch','sound_class_object','loading_behavior','compression_quality')}
 disk=Path('D:/FPS3D/FPSGAME/Content/Weapons/PKMLowpoly20260922')/r['folder']
 backup=P/'backup'/r['folder'];backup.mkdir(parents=True,exist_ok=True)
 for f in disk.glob(r['name']+'.*'):
  target=backup/f.name
  if not target.exists():shutil.copy2(f,target)
 t=u.AssetImportTask();t.filename=str(P/r['wav']);t.destination_path=dest;t.destination_name=r['name'];t.automated=True;t.replace_existing=True;t.save=False
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
 if not t.imported_object_paths:raise RuntimeError('Import failed '+path)
 sound=u.load_asset(path)
 for key,value in settings.items():sound.set_editor_property(key,value)
 sound.set_editor_property('looping',False)
 if not u.EditorAssetLibrary.save_asset(path,False):raise RuntimeError('Save failed '+path)
 receipt.append(dict(asset=path,source=t.filename,saved=True))
 u.log('USER_PKM_SAVED '+path)
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.log('USER_PKM_COMPLETE '+str(len(receipt)))
