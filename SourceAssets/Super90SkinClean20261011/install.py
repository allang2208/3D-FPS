"""Save a Super90-only material pass on the restored meshes; no mesh processing."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
import unreal as u

O = Path('D:/FPS3D/FPSGAME/SourceAssets/Super90SkinClean20261011')
P = O.parents[1]
if (O / 'REJECTED.json').exists():
    raise RuntimeError('This surface revision is retired.')
sys.path.insert(0, str(O))
from super90_skin_clean import create_materials, bind_materials, save

if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Stop PIE before saving Super90 skin materials.')
targets = [
    ('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7.SK_Super90_V7',
     'a14cdeb917a74b6c97f2d2aae858968f27efda4ee5a423737eff988b2ed6f647'),
    ('/Game/Characters/ModularOutfit20260924/Super90Source20261006/Super90/SK_Super90_BareArmsV7.SK_Super90_BareArmsV7',
     '4b46b50ddb222712dc837754a9d75ee9746aac840706bdf817250f75e2d95c09')]
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
receipt = O / 'saved.json'
previous = json.loads(receipt.read_text()) if receipt.exists() else {}
pending = []
for path, expected in targets:
    package_name = path.split('.')[0]
    file = P / 'Content' / (package_name.removeprefix('/Game/') + '.uasset')
    current = hashlib.sha256(file.read_bytes()).hexdigest()
    if package_name in dirty:
        raise RuntimeError('Retain unsaved mesh changes: ' + path)
    if path in previous and current == previous[path]['saved_sha256']:
        continue
    if current != expected:
        raise RuntimeError('Retain newer Super90 edits; material binding paused: ' + path)
    backup = O / 'Before' / file.relative_to(P)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(file, backup)
    pending.append((path, file, current))

create_materials()
for path, file, before_hash in pending:
    mesh = u.load_asset(path)
    if mesh is None:
        raise RuntimeError('Missing Super90 mesh ' + path)
    changes = bind_materials(mesh)
    if len(changes) != 3:
        raise RuntimeError('Expected the three Super90 skin material slots: ' + path)
    u.EditorAssetLibrary.set_metadata_tag(mesh, 'Super90SkinClean', '20261011: material slots only; restored native geometry and skinning')
    save(mesh)
    previous[path] = dict(before_sha256=before_hash, saved_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
        material_slots=changes, geometry_edited=False, weights_edited=False, uv_edited=False,
        rig_edited=False, animations_edited=False, texture_pixels_edited=False, runtime_tested=False)
    receipt.write_text(json.dumps(previous, indent=2))
    print('SUPER90_SKIN_CLEAN_BOUND_AND_SAVED', path, flush=True)
print('SUPER90_SKIN_CLEAN_COMPLETE', flush=True)
