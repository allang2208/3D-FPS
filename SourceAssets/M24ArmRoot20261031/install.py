import unreal as u,json,gzip,ast,copy,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;E=u.EditorAssetLibrary
before=json.load(gzip.open(O/'before.json.gz','rt'));patch=json.load(gzip.open(O/'arm_root_patch.json.gz','rt'))
previous=json.load(gzip.open(O/'saved_profiles.json.gz','rt')) if (O/'saved_profiles.json.gz').exists() else {}
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active; retain the running session')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};staged={};assets={}
backup=O/'Before';backup.mkdir(exist_ok=True)
for family,changes in patch.items():
 path=before['paths'][family]
 if path in dirty:raise RuntimeError('Unsaved target retained '+path)
 a=u.load_asset(path);spec=packed(a,family)
 for change in changes:
  dst=next(c for c in spec['clips'] if c['base']==change['base']);original=next(c for c in before['profiles'][family]['clips'] if c['base']==change['base'])
  if dst['duration']!=original['duration']:raise RuntimeError('Concurrent action timing change retained')
  for t in change['tracks']:
   n=t['bone'];live=next((v for v in dst['tracks'] if v['bone']==n),None);prior=next((v for v in original['tracks'] if v['bone']==n),None)
   previous_clip=next((c for c in previous.get(family,{}).get('clips',[]) if c['base']==dst['base']),{})
   previous_track=next((v for v in previous_clip.get('tracks',[]) if v['bone']==n),None)
   if live!=prior and live!=previous_track:raise RuntimeError('Concurrent shoulder-track change retained '+family+'/'+n)
   if live is None:dst['tracks'].append(t)
   else:live.update(t)
 disk=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
 if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
 staged[family]=spec;assets[family]=a
R={'complete':False,'saved':[],'cpp_changed':False,'gun_and_hand_targets_changed':False,'runtime_tested':False}
for family,a in assets.items():
 if not a.set_shared_clips_from_json(json.dumps(staged[family])):raise RuntimeError('Pose authoring failed '+family)
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+family)
 R['saved'].append(a.get_path_name());(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
R['complete']=True;(O/'install_receipt.json').write_text(json.dumps(R,indent=2));print('M24_ARM_ROOT_SAVED',len(R['saved']),flush=True)
