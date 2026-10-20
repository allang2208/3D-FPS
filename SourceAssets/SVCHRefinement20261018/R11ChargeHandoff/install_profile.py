import hashlib,json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();R10=O.parent/'R10ReloadReview'
path='/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip';disk=P/'Content/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip.uasset'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior_receipt=O/'install_receipt.json'
prior=json.loads((prior_receipt if prior_receipt.exists() else R10/'install_receipt.json').read_text());source=O/'profile_charge.json'
old=json.loads((R10/'profile_native_registration.json').read_text());new=json.loads(source.read_text())
assert len(old['clips'])==len(new['clips']) and old['family']==new['family']
for a,b in zip(old['clips'],new['clips']):
 assert a['base']==b['base'] and a['duration']==b['duration']
 if a['base'].endswith('_reload_empty'):
  keep=lambda c:[t for t in c['tracks'] if t['bone']!='clavicle_r']
  assert keep(a)==keep(b),'Preserve left reload, wrist/fingers and mechanics'
 else:assert a==b,'Preserve every other action'
for spec in json.loads((O/'CurrentSource/manifest.json').read_text()).values():
 f=P/'Content'/(spec['path'].removeprefix('/Game/')+'.uasset');assert digest(f)==spec['sha256'],'Current source changed'
assert digest(disk)==prior['profile_sha256'],'Preserve parallel profile change'
assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world(),'Preserve active game'
assert all(p.get_path_name()!=path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()),'Preserve unsaved profile'
backup=O/'Before';backup.mkdir(exist_ok=True);backup_file=backup/(disk.stem+'_'+prior['profile_sha256'][:12]+disk.suffix)
assert not backup_file.exists(),'Preserve previous install'
shutil.copy2(disk,backup_file)
if prior_receipt.exists():shutil.copy2(prior_receipt,backup/('install_'+prior['profile_sha256'][:12]+'.json'))
profile=u.load_asset(path);assert profile.set_shared_clips_from_json(source.read_text())
u.EditorAssetLibrary.set_metadata_tag(profile,'SVCHChargeContact','R11: empty reload native right-arm rigid registration to actual charging handle; R10 left reload preserved')
assert u.EditorAssetLibrary.save_loaded_asset(profile,False)
receipt={'saved':True,'revision':'R11ChargeHandoff','profile':profile.get_path_name(),'profile_sha256':digest(disk),
 'source_sha256':digest(source),'previous_profile_sha256':prior['profile_sha256'],'changed_actions':['reload_empty'],
 'changed_tracks':['clavicle_r'],'left_magazine_grip_preserved':True,'native_hand_wrist_finger_locals_preserved':True,
 'source_animations_modified':False,'native_v9_mesh_modified':False,'runtime_tested':False}
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2));print('SVCH_R11_CHARGE_SAVED',json.dumps(receipt),flush=True)
