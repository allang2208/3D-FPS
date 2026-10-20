"""Save the authorized SVCh empty-reload layer in the already active profile."""
import unreal as u
import json,gzip,hashlib,shutil
from pathlib import Path

O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
manifest=json.loads((O/'Inputs/manifest.json').read_text());path=manifest['profile']['path']
file=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
digest=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
before=digest(file)
allowed={manifest['profile']['sha256']}
if (O/'install_receipt.json').exists():allowed.add(json.loads((O/'install_receipt.json').read_text())['after_sha256'])
if before not in allowed:raise RuntimeError('SVCh profile changed since collection; preserve parallel work')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('SVCh profile has unsaved editor work; no overwrite')
motion=json.load(gzip.open(O/'Inputs/motion.json.gz','rt'))
for c in motion['clips'].values():
    f=P/'Content'/(c['path'].removeprefix('/Game/')+'.uasset')
    if digest(f)!=c['sha256']:raise RuntimeError('Shared source changed; recollect before authoring')
old=json.loads((O/'Inputs/profile_before.json').read_text())
new=json.loads((O/'profile_left_bolt.json').read_text())
target=motion['clips']['reload_empty']['path']
prefix=('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')
allowed_bones={n for n in motion['names'] if n.endswith(('_l','_r')) and n.startswith(prefix)}
if len(old['clips'])!=len(new['clips']):raise RuntimeError('Unexpected clip list change')
for a,b in zip(old['clips'],new['clips']):
    if a['base']!=target:
        if a!=b:raise RuntimeError('Non-empty-reload clip changed')
    else:
        if a['base']!=b['base'] or a['duration']!=b['duration']:raise RuntimeError('Source clock changed')
        keep=lambda c:{t['bone']:t for t in c['tracks'] if t['bone'] not in allowed_bones}
        if keep(a)!=keep(b):raise RuntimeError('Mechanical or non-arm track changed')
backup=O/'Before';backup.mkdir(exist_ok=True)
dest=backup/(file.stem+'_'+before[:12]+'.uasset')
if not dest.exists():shutil.copy2(file,dest)
asset=u.load_asset(path)
if not asset.set_shared_clips_from_json((O/'profile_left_bolt.json').read_text()):raise RuntimeError('Pose-layer setter rejected input')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('SVCh profile save failed')
receipt={'complete':True,'asset':asset.get_path_name(),'before_sha256':before,'after_sha256':digest(file),
         'only_clip':'reload_empty','left_hand_charges':True,'right_hand_retains_grip':True,
         'shared_source_assets_written':False,'V9_assets_written':False,'weapon_geometry_written':False,
         'normal_reload_changed':False,'mechanical_clocks_changed':False,'cpp_changes':False,
         'runtime_tested':False,'preview_rendered':False,'user_visual_acceptance_pending':True}
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
u.log('SVCH_LEFT_BOLT_PROFILE_SAVED '+asset.get_path_name())
