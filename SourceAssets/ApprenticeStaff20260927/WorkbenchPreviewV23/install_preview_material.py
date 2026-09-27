"""Save the workbench-only quartz material; leave weapon mesh bindings intact."""
import json
import runpy
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
BASE = '/Game/Weapons/ApprenticeStaff20260927'
PREVIEW = '/Game/UI/GunsmithWorkbench/M_StaffQuartzPreviewV23'
WORLD = BASE + '/QuartzAimV22/Materials/M_Staff_QuartzDenseV22'
receipt = {'revision': 23, 'complete': False, 'runtime_tested': False,
           'preview_rendered': False, 'world_bindings': []}

if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('End PIE before creating or saving the preview material.')

dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if PREVIEW in dirty:
    raise RuntimeError('Unsaved preview material already open: ' + PREVIEW)

world_material = u.load_asset(WORLD)
if not world_material:
    raise RuntimeError('Missing installed V22 quartz material')
receipt['world_shading_model'] = str(world_material.get_editor_property('shading_model'))

for name in ('SM_Staff_head_crystal_false', 'SM_Staff_Base'):
    mesh = u.load_asset(BASE + '/Meshes/' + name)
    if not mesh:
        raise RuntimeError('Missing installed staff mesh: ' + name)
    slots = [{'slot': i, 'material': s.material_interface.get_path_name() if s.material_interface else None}
             for i, s in enumerate(mesh.static_materials)]
    if not any(s['material'] == world_material.get_path_name() for s in slots):
        raise RuntimeError('Expected V22 quartz slot on ' + name)
    receipt['world_bindings'].append({'mesh': mesh.get_path_name(), 'slots': slots})

(ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
recipe = runpy.run_path(str(ROOT.parent / 'QuartzAimV22/ue_quartz_material.py'))
material = recipe['build_quartz_material'](rebuild=True, preview=True)
receipt.update({
    'complete': True,
    'material': material.get_path_name(),
    'shading_model': str(material.get_editor_property('shading_model')),
    'blend_mode': str(material.get_editor_property('blend_mode')),
    'translucency_pass': str(material.get_editor_property('translucency_pass')),
    'parameters_source': str(ROOT.parent / 'QuartzAimV22/quartz_parameters.json'),
    'world_assets_modified': False,
})
(ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('STAFF_PREVIEW_V23_SAVED ' + json.dumps(receipt))
