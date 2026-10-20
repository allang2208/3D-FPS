"""Save only the SVCH reload shoulder layer; preserve current V9 and contacts."""
import unreal as u,json,gzip,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();E=u.EditorAssetLibrary
manifest=json.loads((O/'Inputs/manifest.json').read_text());path=manifest['profile']['path'];file=P/'Content'/(path.removeprefix('/Game/')+'.uasset')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=digest(file);allowed={manifest['profile']['sha256']}
if (O/'install_receipt.json').exists():allowed.add(json.loads((O/'install_receipt.json').read_text())['after_sha256'])
if before not in allowed:raise RuntimeError('SVCH profile changed during authoring; preserve parallel work')
es=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if es and es.get_game_world():raise RuntimeError('Preserve active PIE pose-layer pointers; save after PIE ends')
if path in {x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved SVCH profile')
motion=json.load(gzip.open(O/'Inputs/motion.json.gz','rt'))
for c in motion['clips'].values():
    f=P/'Content'/(c['path'].removeprefix('/Game/')+'.uasset')
    if digest(f)!=c['sha256']:raise RuntimeError('Shared source sequence changed during authoring')
af=P/'Content'/(manifest['arms']['path'].removeprefix('/Game/')+'.uasset')
if digest(af)!=manifest['arms']['sha256']:raise RuntimeError('Current V9 source changed during shoulder authoring')
old=json.loads((O/'Inputs/profile_before.json').read_text());new=json.loads((O/'profile_root_clearance.json').read_text())
targets={motion['clips'][r]['path'] for r in ('reload','reload_empty')}
changed={n for n in motion['names'] if n in ('clavicle_l','hand_l') or (n.endswith('_l') and n.startswith(('upperarm','lowerarm')))}
# Scope guard before replacing serialized tracks: only these two left-arm layers.
for a,b in zip(old['clips'],new['clips']):
    if a['base'] not in targets:
        if a!=b:raise RuntimeError('Unrelated clip differs; preserve it')
    else:
        keep=lambda c:{t['bone']:t for t in c['tracks'] if t['bone'] not in changed}
        if keep(a)!=keep(b):raise RuntimeError('Protected finger, right-arm or mechanical track differs')
backup=Path('D:/FPS3D/FPSGAME_Backups/SVCHRootClearance20261019');backup.mkdir(parents=True,exist_ok=True)
dest=backup/(file.stem+'_'+before[:12]+'.uasset')
if not dest.exists():shutil.copy2(file,dest)
asset=u.load_asset(path)
if not asset.set_shared_clips_from_json((O/'profile_root_clearance.json').read_text()):raise RuntimeError('Pose-layer import failed')
if not E.save_loaded_asset(asset,False):raise RuntimeError('SVCH pose-layer save failed')
receipt={'complete':True,'asset':asset.get_path_name(),'before_sha256':before,'after_sha256':digest(file),'backup':str(dest),
 'modified_clips':['reload','reload_empty'],'V9_written':False,'shared_animation_sequences_written':False,
 'right_hand_tracks_changed':False,'finger_tracks_changed':False,'mechanical_tracks_changed':False,
 'hand_world_contact_targets_preserved':True,'runtime_tested':False}
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('SVCH_ROOT_CLEARANCE_SAVED',flush=True)
