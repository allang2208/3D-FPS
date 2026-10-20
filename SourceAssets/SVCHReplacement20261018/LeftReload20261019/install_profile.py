"""Save only the SVCh-specific contact profile; preserve source animations/V9."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
manifest=json.loads((O/'Inputs/manifest.json').read_text());path=manifest['profile']['path']
file=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
old_hash=hashlib.sha256(file.read_bytes()).hexdigest()
allowed_hashes={manifest['profile']['sha256']}
if (O/'install_receipt.json').exists():allowed_hashes.add(json.loads((O/'install_receipt.json').read_text())['after_sha256'])
if old_hash not in allowed_hashes:raise RuntimeError('Contact profile changed outside this task; preserve parallel edits')
motion=json.loads(__import__('gzip').open(O/'Inputs/motion.json.gz','rt').read())
for role in ('reload','reload_empty'):
 c=motion['clips'][role];f=P/'Content'/(c['path'].removeprefix('/Game/')+'.uasset')
 if hashlib.sha256(f.read_bytes()).hexdigest()!=c['sha256']:raise RuntimeError('Shared source clip changed; recollect before fitting')
old=json.loads((O/'Inputs/profile_before.json').read_text());new=json.loads((O/'profile_left_reload.json').read_text())
targets={motion['clips'][r]['path'] for r in ('reload','reload_empty')}
allowed={'clavicle_l','hand_l'}|{n for n in motion['names'] if n.endswith('_l') and n.startswith(('upperarm','lowerarm'))}
for a,b in zip(old['clips'],new['clips']):
 if a['base'] not in targets:
  if a!=b:raise RuntimeError('Non-reload clip changed')
 else:
  before={t['bone']:t for t in a['tracks'] if t['bone'] not in allowed};after={t['bone']:t for t in b['tracks'] if t['bone'] not in allowed}
  if before!=after:raise RuntimeError('Protected finger/right/gun track changed')
backup=O/'Before';backup.mkdir(exist_ok=True);dest=backup/(file.stem+'_'+old_hash[:12]+'.uasset')
if not dest.exists():shutil.copy2(file,dest)
asset=u.load_asset(path)
if not asset.set_shared_clips_from_json((O/'profile_left_reload.json').read_text()):raise RuntimeError('Profile setter rejected the fitted clips')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed')
receipt={'complete':True,'asset':asset.get_path_name(),'before_sha256':old_hash,'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'source_animation_assets_changed':False,'V9_mesh_weights_rest_changed':False,'right_arm_gun_finger_tracks_changed':False,'only_clips':['reload','reload_empty'],'only_tracks':sorted(allowed),'cpp_changes':False,'runtime_review_pending':True}
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));u.log('SVCH_LEFT_RELOAD_PROFILE_SAVED '+asset.get_path_name())
