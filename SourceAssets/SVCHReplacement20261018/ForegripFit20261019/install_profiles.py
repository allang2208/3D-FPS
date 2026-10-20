"""Save the four private SVCH families; never rewrite accepted base/V9 assets."""
import unreal as u,json,gzip,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();E=u.EditorAssetLibrary
manifest=json.loads((O/'Inputs/manifest.json').read_text())
motion=json.load(gzip.open(O/'Inputs/motion.json.gz','rt'));donors=json.load(gzip.open(O/'Inputs/donors.json.gz','rt'))
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def digest(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
inputs=list(manifest.values())+list(motion['clips'].values())
for donor in donors.values():
 if 'path' in donor:inputs.append(donor)
 inputs.append(donor['mesh'])
for spec in inputs:
 if digest(spec['path'])!=spec['sha256']:raise RuntimeError('Authoring input changed; preserve current '+spec['path'])
es=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if es and es.get_game_world():raise RuntimeError('Preserve active PIE asset references')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
root='/Game/Weapons/SVCH/Replacement20261018/ForegripFit20261019'
receipt={'complete':False,'assets':{},'runtime_tested':False,'base_profile_unchanged':True,'V9_written':False,'source_animations_written':False}
for family in ('angled','vertical','canted','prism'):
 name='DA_SVCH_Grip_'+family;path=root+'/'+name
 if path in dirty:raise RuntimeError('Preserve unsaved asset '+path)
 if E.does_asset_exist(path):
  asset=u.load_asset(path)
  if E.get_metadata_tag(asset,'GripProfileAuthor')!='SVCHForegripFit20261019':raise RuntimeError('Unowned asset '+path)
  backup=Path('D:/FPS3D/FPSGAME_Backups/SVCHForegripFit20261019');backup.mkdir(parents=True,exist_ok=True)
  dest=backup/(name+'_'+digest(path)[:12]+'.uasset')
  if not dest.exists():shutil.copy2(disk(path),dest)
 else:
  factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
  asset=u.AssetToolsHelpers.get_asset_tools().create_asset(name,root,u.WeaponGripProfile,factory)
 if not asset or not asset.set_shared_clips_from_json((O/'Profiles'/(name+'.json')).read_text()):raise RuntimeError('Profile authoring import failed '+family)
 E.set_metadata_tag(asset,'GripProfileAuthor','SVCHForegripFit20261019')
 E.set_metadata_tag(asset,'SVCHBaseInput',manifest['profile']['sha256'])
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed '+family)
 receipt['assets'][family]={'path':path,'sha256':digest(path),'clips':len(asset.get_editor_property('clips'))}
 (O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
 print('SVCH_FOREGRIP_SAVED',family,flush=True)
receipt['complete']=True
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SVCH_FOREGRIP_INSTALL_COMPLETE',flush=True)
