"""Save the authored RSH profile without starting play or changing other assets."""
import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Unexpected project')
if u.EditorLevelLibrary.get_game_world():raise RuntimeError('PIE active; profile was not modified')
path='/Game/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_base'
asset=u.load_asset(path)
if not asset:raise RuntimeError('Active RSH profile missing')
backup=O/'BeforeAssets';backup.mkdir(exist_ok=True)
disk=P/'Content/Weapons/RSH12/Native71520261003/Profiles/DA_RSH12_base.uasset'
if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
payload=(O/'Single/profile.json').read_text(encoding='utf8')
if not asset.set_shared_clips_from_json(payload):raise RuntimeError('Profile authoring failed')
u.EditorAssetLibrary.set_metadata_tag(asset,'GripAuthoringSource','RSH12UnifiedGrip20261004; two-hand anatomical flexion; native inspect index; shared-grip ADS')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed')
(O/'import_receipt.json').write_text(json.dumps(dict(complete=True,revision='rsh12-unified-grip-20261004',saved=[asset.get_path_name()],shared_clips=len(json.loads(payload)['clips']),runtime_tested=False),indent=2),encoding='utf8')
print('RSH12_UNIFIED_GRIP_SAVED',asset.get_path_name(),flush=True)
