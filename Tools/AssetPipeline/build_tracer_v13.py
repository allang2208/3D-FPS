"""Create M_BallisticTracerVisibleV13 from M_BallisticTracerVisibleV12.

Two changes over V12, both aimed at the reported tracer problems:

1. Taper: the streak now follows the round for its whole flight, so the custom node
   code gets a head-to-tail fade (head bright, tail fading) instead of a symmetric tube.
2. TemporalResponsiveness = 1: a streak that is retired at the impact must not stay
   behind as stale TSR history, which is what produced the moving residual smear.
   Requires r.Velocity.TemporalResponsiveness.Supported=1 (already in DefaultEngine.ini).

Material authoring, compilation and save only. No game, preview or test run.
Safe to re-run: only an asset carrying our own source metadata tag is overwritten.
"""
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
DEST = '/Game/Weapons/GunplayFX'
SOURCE = DEST + '/M_BallisticTracerVisibleV12'
TARGET = DEST + '/M_BallisticTracerVisibleV13'
HLSL = ROOT / 'SourceAssets' / 'GunplayVFX20260914' / 'TracerVisibleV13.hlsl'
TAG = 'Gunplay.TracerSource'
CODE_DESCRIPTION = 'Gunplay V13 tapered tracer'

LIB = unreal.MaterialEditingLibrary
L = unreal.EditorAssetLibrary


def save(asset):
    if not L.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    unreal.log('TRACER_V13_SAVED ' + asset.get_path_name())


if not L.does_asset_exist(SOURCE):
    raise RuntimeError('Missing tracer source ' + SOURCE)
if not HLSL.exists():
    raise RuntimeError('Missing tracer shader source ' + str(HLSL))

if L.does_asset_exist(TARGET):
    material = unreal.load_asset(TARGET)
    if L.get_metadata_tag(material, TAG) != SOURCE:
        raise RuntimeError('Refusing to overwrite unowned material ' + TARGET)
else:
    material = L.duplicate_asset(SOURCE, TARGET)
    if not material:
        raise RuntimeError('Could not duplicate ' + SOURCE)

nodes = LIB.get_material_expressions(material)
shape = None
for node in nodes:
    if isinstance(node, unreal.MaterialExpressionCustom):
        if node.get_editor_property('description') in (
                'Gunplay V12 axial and side tracer visibility', CODE_DESCRIPTION):
            shape = node
            break
if shape is None:
    raise RuntimeError('Tracer custom node not found in ' + TARGET)
shape.set_editor_property('description', CODE_DESCRIPTION)
shape.set_editor_property('code', HLSL.read_text(encoding='utf-8'))

if not any(isinstance(node, unreal.MaterialExpressionTemporalResponsivenessOutput) for node in nodes):
    output = LIB.create_material_expression(
        material, unreal.MaterialExpressionTemporalResponsivenessOutput, -700, -700)
    value = LIB.create_material_expression(material, unreal.MaterialExpressionConstant, -950, -700)
    value.set_editor_property('r', 1.0)
    if not LIB.connect_material_expressions(value, '', output, ''):
        raise RuntimeError('Temporal responsiveness connection failed')

errors = LIB.recompile_material(material)
if errors:
    raise RuntimeError('Material compilation failed: ' + '\n'.join(errors))
LIB.get_statistics(material)  # finish the shader build before saving, without PIE
L.set_metadata_tag(material, TAG, SOURCE)
save(material)
unreal.log('TRACER_V13_DONE responsive=' + str(
    any(isinstance(node, unreal.MaterialExpressionTemporalResponsivenessOutput)
        for node in LIB.get_material_expressions(material))))