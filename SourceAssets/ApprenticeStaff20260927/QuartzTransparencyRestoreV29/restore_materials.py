"""Restore V20 transparency in current world/UI materials and save the packages."""
import json
import runpy
import shutil
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
RECIPE = ROOT.parent / 'QuartzAimV22/ue_quartz_material.py'
TARGETS = [
    '/Game/Weapons/ApprenticeStaff20260927/QuartzAimV22/Materials/M_Staff_QuartzDenseV22',
    '/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23',
]
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(path in dirty for path in TARGETS):
    raise RuntimeError('Target quartz material has unsaved edits; preserving the current state.')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('End PIE before applying the material change.')

before = ROOT / 'Before'
before.mkdir(parents=True, exist_ok=True)
for path in TARGETS:
    src = PROJECT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    backup = before / src.name
    if not backup.exists():
        shutil.copy2(src, backup)

recipe = runpy.run_path(str(RECIPE))
receipt = {'complete': False, 'saved': [], 'runtime_tested': False, 'rendered': False,
           'restored_from': 'QuartzMilkV20/quartz_parameters.json',
           'opacity': [recipe['P']['opacity_min'], recipe['P']['opacity_max']],
           'transmittance': recipe['P']['transmittance']}
for preview in (False, True):
    material = recipe['build_quartz_material'](rebuild=True, preview=preview)
    receipt['saved'].append(material.get_path_name())
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
receipt['complete'] = True
(ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('STAFF_QUARTZ_TRANSPARENCY_RESTORED ' + json.dumps(receipt))
