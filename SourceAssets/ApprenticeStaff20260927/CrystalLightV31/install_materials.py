"""Compile/save the five installed crystal materials; no game or preview run."""
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
    raise RuntimeError('Use a rendering RHI for material compilation.')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('End PIE before editing crystal materials.')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(TARGETS):
    raise RuntimeError('Unsaved crystal material edits; preserving the current state.')

before = ROOT / 'Before'
before.mkdir(parents=True, exist_ok=True)
receipt = {'complete': False, 'saved': [], 'tested': False, 'preview_rendered': False,
           'parameter': 'StaffLightAmount', 'default': 0.}
add_light_control = runpy.run_path(str(ROOT / 'material_emission.py'))['add_light_control']
for path in TARGETS:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing crystal material: ' + path)
    backup = before / (material.get_name() + '.uasset')
    if not backup.exists():
        shutil.copy2(PROJECT / 'Content' / (path.removeprefix('/Game/') + '.uasset'), backup)
    add_light_control(material)
    errors = u.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError('Crystal light material compilation failed: ' + str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError('Cannot save ' + path)
    receipt['saved'].append({'material': material.get_path_name(), 'compile_errors': []})
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
receipt['complete'] = True
(ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('STAFF_CRYSTAL_LIGHT_MATERIALS_SAVED ' + json.dumps(receipt))
