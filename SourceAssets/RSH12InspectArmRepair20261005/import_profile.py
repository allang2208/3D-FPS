"""Save the revised inspect profile without starting an editor or gameplay."""
import json, shutil
from datetime import datetime, timezone
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1]
if Path(u.Paths.project_dir()).resolve()!=P.resolve():raise RuntimeError('Unexpected project')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE active; no profile changed')
path='/Game/Weapons/RSH12/Foregrips20261004/Profiles/DA_RSH12_angled'
asset=u.load_asset(path)
if not asset:raise RuntimeError('RSH Resonance profile is missing')
backup=O/'BeforeAssets';backup.mkdir(exist_ok=True)
disk=P/'Content/Weapons/RSH12/Foregrips20261004/Profiles/DA_RSH12_angled.uasset'
if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
payload=(O/'profile.json').read_text(encoding='utf8')
if not asset.set_shared_clips_from_json(payload):raise RuntimeError('Inspect profile import failed')
u.EditorAssetLibrary.set_metadata_tag(asset,'RSHForegripSource',
    'RSH12InspectArmRepair20261005; fitted wrist; continuous held support during inspect')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Inspect profile save failed')
current=O.parent/'RSH12Foregrips20261004/Profiles'
(current/'angled.json').write_text(payload,encoding='utf8')
shutil.copy2(O/'RSH12_InspectArm_Editable.blend',current/'RSH12_angled_Editable.blend')
receipt=dict(complete=True,saved=[asset.get_path_name()],revision='rsh12-inspect-arm-20261005',
    saved_utc=datetime.now(timezone.utc).isoformat(),changed_clip='inspect',
    runtime_tested=False,editor_started=False)
(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('RSH_INSPECT_ARM_PROFILE_SAVED',asset.get_path_name(),flush=True)
