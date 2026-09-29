"""Replace the broken quartz graphs, compile on the editor RHI, and save."""
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

command_line = u.SystemLibrary.get_command_line().lower()
if '-nullrhi' in command_line:
    raise RuntimeError('Repair needs a rendering RHI to compile the actual material shaders.')
editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
if editor and editor.is_in_play_in_editor():
    raise RuntimeError('End PIE before replacing the quartz material graphs.')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(path in dirty for path in TARGETS):
    raise RuntimeError('Target quartz material has unsaved edits; preserving the current state.')

before = ROOT / 'Before'
before.mkdir(parents=True, exist_ok=True)
receipt = {'complete': False, 'saved': [], 'runtime_tested': False,
           'rendered': False, 'source_recipe': str(RECIPE), 'before': []}
for path in TARGETS:
    material = u.load_asset(path)
    if not material:
        raise RuntimeError('Missing quartz material: ' + path)
    nodes = list(u.MaterialEditingLibrary.get_material_expressions(material))
    receipt['before'].append({
        'material': path,
        'expression_count': len(nodes),
        'thin_outputs': sum(isinstance(n, u.MaterialExpressionThinTranslucentMaterialOutput) for n in nodes),
    })
    src = PROJECT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    backup = before / src.name
    if not backup.exists():
        shutil.copy2(src, backup)

def save_receipt():
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')

save_receipt()
recipe = runpy.run_path(str(RECIPE))
receipt['opacity'] = [recipe['P']['opacity_min'], recipe['P']['opacity_max']]
receipt['transmittance'] = recipe['P']['transmittance']
for preview in (False, True):
    # The recipe raises on compiler errors or failure to save this package.
    material = recipe['build_quartz_material'](rebuild=True, preview=preview)
    nodes = list(u.MaterialEditingLibrary.get_material_expressions(material))
    receipt['saved'].append({
        'material': material.get_path_name(),
        'expression_count': len(nodes),
        'thin_outputs': sum(isinstance(n, u.MaterialExpressionThinTranslucentMaterialOutput) for n in nodes),
        'compile_errors': [],
    })
    save_receipt()
receipt['complete'] = True
save_receipt()
print('STAFF_QUARTZ_GRAPH_REPAIRED ' + json.dumps(receipt))
