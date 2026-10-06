"""Save only the RSH Resonance support-arm profile through the existing editor."""
import json, shutil
from datetime import datetime, timezone
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = O.parents[1]
if Path(u.Paths.project_dir()).resolve() != P.resolve():
    raise RuntimeError('Unexpected project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE active; RSH Resonance profile has not been modified')
path = '/Game/Weapons/RSH12/Foregrips20261004/Profiles/DA_RSH12_angled'
asset = u.load_asset(path)
if not asset:
    raise RuntimeError('RSH Resonance profile is missing')
backup = O/'BeforeAssets'
backup.mkdir(exist_ok=True)
disk = P/'Content/Weapons/RSH12/Foregrips20261004/Profiles/DA_RSH12_angled.uasset'
if not (backup/disk.name).exists():
    shutil.copy2(disk, backup/disk.name)
payload = (O/'profile.json').read_text(encoding='utf8')
if not asset.set_shared_clips_from_json(payload):
    raise RuntimeError('RSH Resonance profile authoring failed')
u.EditorAssetLibrary.set_metadata_tag(asset, 'RSHForegripSource',
    'RSH12ResonanceWrist20261005; fixed grasp; shoulder and elbow support; forearm twist distribution')
if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
    raise RuntimeError('RSH Resonance profile save failed')
receipt = dict(complete=True, revision='rsh12-resonance-wrist-20261005',
               saved=[asset.get_path_name()], clips=len(json.loads(payload)['clips']),
               saved_utc=datetime.now(timezone.utc).isoformat(),
               runtime_tested=False, editor_started=False)
(O/'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
print('RSH_RESONANCE_WRIST_PROFILE_SAVED', asset.get_path_name(), flush=True)
