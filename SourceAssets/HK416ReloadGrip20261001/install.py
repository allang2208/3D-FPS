"""Publish only current HK416 reload grip tracks and refresh runtime layers."""
import gzip,hashlib,importlib.util,json,shutil
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/HK416ReloadGrip20261001');P=O.parents[1]
staging=bool(globals().get('staging',False))
content=O/'PackageStaging/Content' if staging else P/'Content'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=content.resolve():raise RuntimeError('Wrong content root; no assets changed')
headless='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; preserve the running session')
E=u.EditorAssetLibrary
def disk(path):return content/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
clips={}
for file in ('standard_tracks.json.gz','drum_tracks.json.gz'):
 with gzip.open(O/file,'rt',encoding='utf8') as f:clips.update(json.load(f)['clips'])
receipt_path=O/('staged_delivery.json' if staging else 'delivery.json')
if staging and not receipt_path.exists():shutil.copy2(O/'delivery.json',receipt_path)
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'revision':'HK416ReloadGrip20261001','animations':{},'profiles':{},'runtime_tested':False,'editor_launched':False}
profiles={'/Game/Weapons/AnimationProfiles20261001/ue_hk416/DA_'+f for f in ('vertical','canted','prism','angled','drum')}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&(set(clips)|profiles):raise RuntimeError('Preserve unsaved HK416 edits: '+str(dirty&(set(clips)|profiles)))
if not headless:
 # An already open MP editor shares the main Content through a junction. Resume
 # the exact saved boundary without retaining a stale loaded AnimSequence.
 reloads=[]
 for key in receipt['animations']:
  loaded=u.find_object(None,key+'.'+key.rsplit('/',1)[-1])
  if loaded and E.get_metadata_tag(loaded,'HK416ReloadGripSource')=='':reloads.append(loaded.get_outermost())
 if reloads:
  if not u.EditorLoadingAndSavingUtils.reload_packages(reloads,u.ReloadPackagesInteractionMode.ASSUME_POSITIVE):raise RuntimeError('Could not refresh saved HK416 clips; preserve editor state')
  del reloads,loaded
for key,s in clips.items():
 saved=receipt['animations'].get(key)
 expected=saved['saved_sha256'] if saved else s['source_sha256']
 if sha(key)!=expected:raise RuntimeError('Clip changed during authoring: '+key)
 # Backups and original hashes are recorded before any package is mutated.
 backup=O/'Before'/(key.removeprefix('/Game/')+'.uasset')
 if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk(key),backup)
for path in profiles:
 backup=O/'Before'/(path.removeprefix('/Game/')+'.uasset')
 if disk(path).exists() and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(disk(path),backup)
def record():receipt_path.write_text(json.dumps(receipt,indent=1),encoding='utf8')
for key,s in clips.items():
 if key in receipt['animations']:continue
 a=u.load_asset(key)
 controller=a.get_editor_property('controller');controller.open_bracket('HK416 magazine-relative natural reload contact',False)
 try:
  for bone,rows in s['tracks'].items():
   if not controller.set_bone_track_keys(bone,[u.Vector(*r[:3]) for r in rows],[u.Quat(*r[3:7]) for r in rows],[u.Vector(*r[7:10]) for r in rows],False):raise RuntimeError('Track write failed '+key+'/'+bone)
 finally:controller.close_bracket(False)
 u.AKMAnimationAuditLibrary.finish_animation_compression(a)
 E.set_metadata_tag(a,'HK416ReloadGripSource','HK416ReloadGrip20261001; magazine-relative M4/AKM wrap' if s['kind'] in ('reload','reload_empty') else 'HK416ReloadGrip20261001; fixed palm; native skin finger adduction and drum wrap')
 if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError('Save failed '+key)
 receipt['animations'][key]={'saved':True,'saved_sha256':sha(key),'source_sha256':s['source_sha256'],'family':s['family'],'kind':s['kind'],'tracks':len(s['tracks']),'seconds':a.get_play_length()};record()
 print('HK416_RELOAD_GRIP_SAVED',s['family'],s['kind'],flush=True)
spec=importlib.util.spec_from_file_location('hk416_reload_grip_profiles',P/'SourceAssets/HK416CommonAttachments20260930/import_grip_profiles.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
for kind in ('reload','reload_empty','drum_reload','drum_reload_empty'):
 if kind in receipt['profiles']:continue
 receipt['profiles'][kind]=module.refresh_profiles(O,kind);record();print('HK416_RELOAD_GRIP_LAYERS_SAVED',kind,flush=True)
receipt['status']='Twenty HK416 reload animations and affected entries of five runtime grip profiles saved'+(' in isolated staging' if staging else '');receipt['saved']=True;receipt['staged']=staging;record()
print('HK416_RELOAD_GRIP_PUBLICATION_COMPLETE',len(receipt['animations']),flush=True)
