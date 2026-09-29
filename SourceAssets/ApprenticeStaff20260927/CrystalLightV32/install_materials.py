"""Save exposure-aware crystal glow, preserving the existing translucent graph."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
BASE = '/Game/Weapons/ApprenticeStaff20260927'
TARGETS = [BASE + '/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'] + [
    BASE + '/Materials/M_Staff_' + element for element in ('ice', 'fire', 'light', 'electric')]
if '-nullrhi' in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('A rendering RHI is required for the material compilation.')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(TARGETS):
    raise RuntimeError('Unsaved edits in target crystal materials; preserving them.')

before = ROOT / 'Before'
before.mkdir(parents=True, exist_ok=True)
upgrade = runpy.run_path(str(ROOT.parent / 'CrystalLightV31/material_emission.py'))['add_light_control']
receipt = {'complete': False, 'saved': [], 'runtime_tested': False, 'preview_rendered': False}
for path in TARGETS:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing material: ' + path)
    backup = before / (material.get_name() + '.uasset')
    if not backup.exists():
        shutil.copy2(PROJECT / 'Content' / (path.removeprefix('/Game/') + '.uasset'), backup)
    upgrade(material)
    errors = u.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError(str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save ' + path)
    receipt['saved'].append({'material': path, 'compile_errors': []})
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
receipt['complete'] = True
(ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('STAFF_LIGHT_V32_SAVED ' + json.dumps(receipt))
