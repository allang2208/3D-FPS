"""Read the current approved M4 V9 authoring inputs; write only M24 source files."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent / 'V9'
O.mkdir(exist_ok=True)
path = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'
mesh = u.load_asset(path)
if not mesh:
    raise RuntimeError('Current V9 template is unavailable')
task = u.AssetExportTask()
task.object = mesh
task.filename = str(O / 'M4_V9_Template.fbx')
task.automated = True
task.prompt = False
task.replace_identical = True
task.exporter = u.SkeletalMeshExporterFBX()
options = u.FbxExportOption()
options.set_editor_property('export_morph_targets', True)
options.set_editor_property('level_of_detail', False)
task.options = options
if not u.Exporter.run_asset_export_task(task):
    raise RuntimeError('V9 template FBX export failed')
record = {'mesh': mesh.get_path_name(), 'skeleton': mesh.skeleton.get_path_name(),
    'materials': [{'slot': str(s.material_slot_name), 'asset': s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.materials]}
(O / 'template.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('M24_V9_TEMPLATE_EXPORTED', task.filename)
