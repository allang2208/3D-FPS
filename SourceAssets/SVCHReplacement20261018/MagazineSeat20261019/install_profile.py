"""Update magazine grasp only, on top of the current left-handed charge."""
import unreal as u,json,gzip,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();E=u.EditorAssetLibrary
manifest=json.loads((O/'Inputs/manifest.json').read_text());path=manifest['profile']['path'];file=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=digest(file);allowed={manifest['profile']['sha256']}
if (O/'profile_receipt.json').exists():allowed.add(json.loads((O/'profile_receipt.json').read_text())['after_sha256'])
if before not in allowed:raise RuntimeError('Current left-bolt profile changed; preserve it')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE pose-layer pointers; save after PIE ends')
if path in {x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved profile')
motion=json.load(gzip.open(O/'Inputs/motion.json.gz','rt'))
for c in motion['clips'].values():
    f=P/'Content'/(c['path'].removeprefix('/Game/')+'.uasset')
    if digest(f)!=c['sha256']:raise RuntimeError('Source sequence changed')
old=json.loads((O/'Inputs/profile_before.json').read_text());new=json.loads((O/'profile_magazine_seat.json').read_text())
targets={motion['clips'][r]['path'] for r in ('reload','reload_empty')}
changed={n for n in motion['names'] if n in ('clavicle_l','hand_l') or (n.endswith('_l') and n.startswith(('upperarm','lowerarm')))}
for a,b in zip(old['clips'],new['clips']):
    if a['base'] not in targets:
        if a!=b:raise RuntimeError('Unrelated action changed')
    else:
        keep=lambda c:{t['bone']:t for t in c['tracks'] if t['bone'] not in changed}
        if keep(a)!=keep(b):raise RuntimeError('Protected fingers, right hand or mechanical track changed')
backup=O/'Before';backup.mkdir(exist_ok=True);dst=backup/(file.stem+'_'+before[:12]+'.uasset')
if not dst.exists():shutil.copy2(file,dst)
asset=u.load_asset(path)
if not asset.set_shared_clips_from_json((O/'profile_magazine_seat.json').read_text()):raise RuntimeError('Pose import failed')
if not E.save_loaded_asset(asset,False):raise RuntimeError('Pose save failed')
receipt={'complete':True,'asset':asset.get_path_name(),'before_sha256':before,'after_sha256':digest(file),'V9_written':False,'source_sequences_written':False,'right_hand_tracks_changed':False,'finger_tracks_changed':False,'bolt_tracks_changed':False,'left_charge_contact_from_frame_292_preserved':True,'runtime_tested':False}
(O/'profile_receipt.json').write_text(json.dumps(receipt,indent=2));print('SVCH_MAGAZINE_CONTACT_SAVED',flush=True)
