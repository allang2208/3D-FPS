import unreal as u,json,gzip,ast,copy,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
before=json.load(gzip.open(O.parent/'M24RightGripCheck20261031/before.json.gz','rt'))
patch=json.load(gzip.open(O/'right_grip_patch.json.gz','rt'));owned=set(json.loads((O/'authoring_receipt.json').read_text())['owned_bones'])
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active; retain running session')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
root='/Game/Weapons/M24/ReceiverGripRebuild20261031/Profiles';staged={};assets={}
backup=O/'Before';backup.mkdir(exist_ok=True)
previous=json.load(gzip.open(O/'saved_profiles.json.gz','rt')) if (O/'saved_profiles.json.gz').exists() else {}
# Read both source profiles before mutating either one, retaining unrelated edits.
live={f:packed(u.load_asset(before['paths'][f]),f) for f in ('skeleton_base','skeleton_mag10')}
for family,p in patch.items():
 path=root+'/DA_M24_'+family;sf=p['source_family'];source=live[sf]
 if path in dirty or before['paths'][sf] in dirty:raise RuntimeError('Unsaved profile retained: '+path)
 spec=copy.deepcopy(source);spec['family']=family
 for c in spec['clips']:
  old=next(v for v in before['profiles'][sf]['clips'] if v['base']==c['base']);change=next(v for v in p['clips'] if v['base']==c['base'])
  was={t['bone']:t for t in old['tracks'] if t['bone'] in owned};now={t['bone']:t for t in c['tracks'] if t['bone'] in owned}
  prior=next((v for v in previous.get(sf,{}).get('clips',[]) if v['base']==c['base']),{})
  prior_tracks={t['bone']:t for t in prior.get('tracks',[]) if t['bone'] in owned}
  if c['duration']!=old['duration'] or (now!=was and now!=prior_tracks):raise RuntimeError('Concurrent right-arm edit retained: '+sf+'/'+c['base'])
  c['tracks']=[t for t in c['tracks'] if t['bone'] not in owned]+change['tracks']
 if E.does_asset_exist(path):
  asset=u.load_asset(path)
  if family not in before['paths'] and family not in previous:raise RuntimeError('New variant already exists; retained: '+path)
  disk=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
  if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
 else:asset=None
 staged[family]=spec;assets[family]=asset
R={'complete':False,'saved':[],'runtime_tested':False,'owned_bones':sorted(owned)};saved={}
for family,spec in staged.items():
 asset=assets[family]
 if not asset:
  factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
  asset=A.create_asset('DA_M24_'+family,root,u.WeaponGripProfile,factory)
 if not asset or not asset.set_shared_clips_from_json(json.dumps(spec)):raise RuntimeError('Profile import failed '+family)
 E.set_metadata_tag(asset,'Source',str(O/'author.py'))
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed '+family)
 saved[family]=packed(asset,family)
 with gzip.open(O/'saved_profiles.json.gz','wt') as f:json.dump(saved,f)
 R['saved'].append(asset.get_path_name());(O/'install_receipt.json').write_text(json.dumps(R,indent=2))
R['complete']=True;(O/'install_receipt.json').write_text(json.dumps(R,indent=2));print('M24_RIGHT_GRIP_SAVED',len(saved),flush=True)
