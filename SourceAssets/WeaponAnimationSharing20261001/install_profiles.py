"""Save shared-pose assets using current saved authoring animations, without tests."""
from pathlib import Path
import hashlib,json,shutil
import unreal as u
P=Path(u.Paths.project_dir()).resolve()
# New weapons use their own manifests/receipts while sharing this producer.
# Existing entry points keep their original directory and ownership tag.
O=Path(globals().get('ANIMATION_SHARING_JOB_ROOT',Path(__file__).parent)).resolve()
default_author=globals().get('ANIMATION_SHARING_AUTHOR','WeaponAnimationSharing20261001')
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
E=u.EditorAssetLibrary
specs=json.loads((O/'manifest.json').read_text(encoding='utf-8'))['profiles']
batch=json.loads((O/'batch.json').read_text(encoding='utf-8-sig')) if (O/'batch.json').exists() else {}
if batch.get('weapon'):specs=[s for s in specs if s['weapon']==batch['weapon']]
rp=O/'install_receipt.json'
receipt=json.loads(rp.read_text()) if rp.exists() else dict(profiles={},complete=False,tested=False,source_animations_changed=False)
def record():
 temp=rp.with_suffix('.tmp');temp.write_text(json.dumps(receipt,indent=1),encoding='utf-8');temp.replace(rp)
def disk(s):return P/'Content'/(s.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(s):return hashlib.sha256(disk(s).read_bytes()).hexdigest()
headless='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
dirty=set()
if not headless:
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('PIE active; finish preview before asset production')
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for spec in specs:
 author=spec.get('author',default_author)
 key=spec['weapon']+'/'+spec['family'];target=spec['asset']
 inputs={p:sha(p) for row in spec['pairs'] for p in (row['base'],row['authored'])}
 inputs[spec['mesh']]=sha(spec['mesh'])
 if any(p in dirty for p in list(inputs)+[target]):raise RuntimeError('Unsaved package in production inputs: '+key)
 old=receipt['profiles'].get(key)
 if old and old.get('saved') and old['inputs']==inputs and old.get('pairs')==spec['pairs']:
  if sha(target)!=old['saved_sha256']:raise RuntimeError('Profile was changed outside this production batch: '+target)
  continue
 if E.does_asset_exist(target):
  asset=u.load_asset(target)
  if E.get_metadata_tag(asset,'AnimationSharingAuthor')!=author:raise RuntimeError('Unowned destination '+target)
  backup=O/'BeforeAssets'/(target.removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
  if not backup.exists():shutil.copy2(disk(target),backup)
 else:
  factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
  folder,name=target.rsplit('/',1)
  asset=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.WeaponGripProfile,factory)
 if not asset:raise RuntimeError('Cannot create '+target)
 pending=[];retained=[];replaced=[]
 mesh=u.load_asset(spec['mesh'])
 skeleton=mesh.get_editor_property('skeleton')
 asset.set_editor_property('family','pending_'+spec['family'])
 # This manifest describes the complete profile. Drop obsolete Base/Retained
 # entries when roles are removed or a base sequence is replaced.
 if not asset.set_shared_clips_from_json(json.dumps({'family':'pending_'+spec['family'],'clips':[]})):
  raise RuntimeError('Cannot reset profile authoring data '+target)
 for row in spec['pairs']:
  base=u.load_asset(row['base']);authored=u.load_asset(row['authored'])
  if not base or not authored:raise RuntimeError('Missing authoring sequence '+str(row))
  native=base.get_editor_property('skeleton')==skeleton and authored.get_editor_property('skeleton')==skeleton
  if native and asset.bake_clip(base,authored):
   if row['base']!=row['authored']:replaced.append(row['authored'])
  else:
   detail=dict(row,base_duration=base.get_play_length(),authored_duration=authored.get_play_length(),
    base_skeleton=base.get_editor_property('skeleton').get_path_name(),authored_skeleton=authored.get_editor_property('skeleton').get_path_name(),
    mesh_skeleton=skeleton.get_path_name(),reason='native_skeleton_mismatch' if not native else 'source_duration_mismatch')
   if hasattr(asset,'keep_clip'):
    asset.keep_clip(base,authored);retained.append(detail)
   else:pending.append(detail)
 for p,digest in inputs.items():
  if sha(p)!=digest:raise RuntimeError('Source changed during production: '+p)
 if not pending:asset.set_editor_property('family',spec['family'])
 E.set_metadata_tag(asset,'AnimationSharingAuthor',author)
 E.set_metadata_tag(asset,'AnimationSharingSources',json.dumps(inputs,sort_keys=True))
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+target)
 layers=list(asset.get_editor_property('clips'))
 receipt['profiles'][key]=dict(asset=target,saved=not pending,pending_native_api=pending,retained=retained,
  replaced=sorted(set(replaced)),inputs=inputs,pairs=spec['pairs'],saved_sha256=sha(target),bytes=disk(target).stat().st_size,
  layer_count=len(layers),key_count=sum(len(t.get_editor_property('times')) for c in layers for t in c.get_editor_property('tracks')))
 del layers # Do not keep reflected array views across the next bake operation.
 record();print('ANIMATION_SHARING_SAVED',key,'ready=',not pending,'retained=',len(retained),'pending=',len(pending),flush=True)
all_specs=json.loads((O/'manifest.json').read_text(encoding='utf-8'))['profiles']
receipt['complete']=all(receipt['profiles'].get(s['weapon']+'/'+s['family'],{}).get('saved',False) for s in all_specs)
record();print('ANIMATION_SHARING_BATCH_FINISHED complete=',receipt['complete'],flush=True)
