"""Repair the one disconnected Fabric09 roughness input, preserving the existing graph."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/WitchRebuilt20260921/Revision11'
PACKAGE = '/Game/Monsters/WitchRebuilt/Materials/M_WitchRebuilt_Fabric09'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != ROOT / 'FPSGAME.uproject':
    raise RuntimeError('Unexpected project')
if any(p.get_path_name() == PACKAGE for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved fabric material preserved')
source = ROOT / 'Content/Monsters/WitchRebuilt/Materials/M_WitchRebuilt_Fabric09.uasset'
backup = OUT / 'Before/M_WitchRebuilt_Fabric09.uasset'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(source, backup)
lib = u.MaterialEditingLibrary
material = u.load_asset(PACKAGE)
expressions = lib.get_material_expressions(material)
clamps = [x for x in expressions if isinstance(x, u.MaterialExpressionClamp)]
rough_adds = []
for expr in expressions:
    if not isinstance(expr, u.MaterialExpressionAdd):
        continue
    inputs = lib.get_inputs_for_material_expression(material, expr)
    if any(isinstance(x, u.MaterialExpressionScalarParameter) and str(x.get_editor_property('parameter_name')) == 'Roughness' for x in inputs):
        rough_adds.append(expr)
if len(clamps) != 1 or len(rough_adds) != 1:
    raise RuntimeError('Fabric09 graph differs; no graph edit performed')
clamp, rough = clamps[0], rough_adds[0]
pins = list(lib.get_material_expression_input_names(clamp))
before = [x.get_name() if x else None for x in lib.get_inputs_for_material_expression(material, clamp)]
if not lib.connect_material_expressions(rough, '', clamp, pins[0]):
    raise RuntimeError('Could not connect the actual Clamp input pin')
errors = list(lib.recompile_material(material))
after = [x.get_name() if x else None for x in lib.get_inputs_for_material_expression(material, clamp)]
report = {'material': PACKAGE, 'clamp_pins': pins, 'before_inputs': before, 'after_inputs': after,
          'source_node': rough.get_name(), 'compile_errors': errors,
          'backup': str(backup), 'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(), 'saved': False}
(OUT / 'fabric_repair.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
if errors:
    raise RuntimeError('Fabric09 compile errors: ' + str(errors))
report['saved'] = u.EditorAssetLibrary.save_loaded_asset(material, False)
(OUT / 'fabric_repair.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
if not report['saved']:
    raise RuntimeError('Material corrected in memory but save did not complete')
print(json.dumps(report))
