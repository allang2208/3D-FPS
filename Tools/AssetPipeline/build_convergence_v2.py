"""Author, compile and save the dedicated convergence material; no preview/PIE."""
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
SOURCE = '/Game/Weapons/GunplayFX/M_BallisticTracerVisibleV13'
TARGET = '/Game/Weapons/GunplayFX/M_ConvergenceBeamV2'
TAG = 'Gunplay.ConvergenceSource'
DESCRIPTION = 'Convergence V2 blue density layers'
LIB = unreal.MaterialEditingLibrary
ASSETS = unreal.EditorAssetLibrary

if ASSETS.does_asset_exist(TARGET):
    material = unreal.load_asset(TARGET)
    if ASSETS.get_metadata_tag(material, TAG) != SOURCE:
        raise RuntimeError('Refusing to overwrite unowned material: ' + TARGET)
else:
    material = ASSETS.duplicate_asset(SOURCE, TARGET)
    if not material:
        raise RuntimeError('Could not duplicate ' + SOURCE)
    ASSETS.set_metadata_tag(material, TAG, SOURCE)

nodes = LIB.get_material_expressions(material)
shape = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionCustom)
             and n.get_editor_property('description') in ('Gunplay V13 tapered tracer', 'Convergence V2 neutral white layers', DESCRIPTION))
shape.set_editor_property('description', DESCRIPTION)
shape.set_editor_property('code', (ROOT / 'SourceAssets/ConvergenceVFX20260929/ConvergenceBeamV2.hlsl').read_text(encoding='utf-8'))

inputs = list(shape.get_editor_property('inputs'))
names = {str(pin.get_editor_property('input_name')) for pin in inputs}
for name in ('Layer', 'LengthCM', 'NearFadeCM'):
    if name not in names:
        pin = unreal.CustomInput()
        pin.set_editor_property('input_name', name)
        inputs.append(pin)
shape.set_editor_property('inputs', inputs)
for row, (name, default) in enumerate((('Layer', 0.0), ('LengthCM', 800.0), ('NearFadeCM', 65.0))):
    param = next((n for n in nodes if isinstance(n, unreal.MaterialExpressionScalarParameter)
                  and str(n.get_editor_property('parameter_name')) == name), None)
    if param is None:
        param = LIB.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -1100, 800 + row * 160)
    param.set_editor_property('parameter_name', name)
    param.set_editor_property('default_value', default)
    if not LIB.connect_material_expressions(param, '', shape, name):
        raise RuntimeError('Failed to connect ' + name)

# Keep the saved material default consistent with the runtime convergence colour.
tint = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionVectorParameter)
            and str(n.get_editor_property('parameter_name')) == 'Tint')
tint.set_editor_property('default_value', unreal.LinearColor(0.08, 0.35, 1.0, 1.0))

# Preserve V13's depth intersection fade and temporal responsiveness output.
errors = LIB.recompile_material(material)
if errors:
    raise RuntimeError('Material compilation failed: ' + str(errors))
LIB.get_statistics(material)  # finish shader compilation before saving
if not ASSETS.save_loaded_asset(material, False):
    raise RuntimeError('Could not save ' + TARGET)
unreal.log('CONVERGENCE_V2_SAVED ' + material.get_path_name())
