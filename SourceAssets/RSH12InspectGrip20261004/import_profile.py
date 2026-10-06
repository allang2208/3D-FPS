"""Save the active single-RSH shared-animation grip profile; no mesh/clip reimport."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Unexpected project')
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('PIE active; profile was not modified')
path='/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_base'
asset=u.load_asset(path)
if not asset:raise RuntimeError('Active RSH profile is missing')
backup=O/'BeforeAssets';backup.mkdir(exist_ok=True)
disk=P/'Content/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_base.uasset'
if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
payload=(O/'Single/profile.json').read_text(encoding='utf8')
if not asset.set_shared_clips_from_json(payload):raise RuntimeError('Profile authoring failed')
u.EditorAssetLibrary.set_metadata_tag(asset,'GripAuthoringSource','RSH12InspectGrip20261004; fitted common grasp and inspect index/thumb endpoints; Native715 action and speedloader retained')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed')
receipt=dict(complete=True,revision='rsh12-inspect-grip-20261004',saved=[asset.get_path_name()],shared_clips=len(json.loads(payload)['clips']),meshes_reimported=0,new_animation_sequences=0,runtime_tested=False)
(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('RSH12_INSPECT_GRIP_SAVED',asset.get_path_name(),flush=True)
