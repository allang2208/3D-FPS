"""Owned rain/puddle revision; preserves NaturalV2 lens, weapon and sky materials.
Run after building FPSGAMEEditor with UnrealEditor-Cmd -run=pythonscript.
No external textures/code and no edits to source asset packages.
"""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
DEST = '/Game/Weather/RainVisibility'
LIB = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
API = unreal.get_default_object(unreal.NiagaraToolset_System)

def duplicate(path, name):
    target = DEST + '/' + name
    if unreal.EditorAssetLibrary.does_asset_exist(target):
        return unreal.load_asset(target)
    source = unreal.load_asset(path)
    assert source, path
    return TOOLS.duplicate_asset(name, DEST, source)

def save(asset):
    if isinstance(asset, unreal.Material):
        LIB.recompile_material(asset)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset, False), asset.get_path_name()

rain_mat = duplicate('/Game/Weather/NaturalV2/M_Natural_rain', 'M_ReadableRain')
updated = 0
for expression in LIB.get_material_expressions(rain_mat):
    if isinstance(expression, unreal.MaterialExpressionCustom) and 'return a*' in expression.get_editor_property('code'):
        expression.set_editor_property('description', 'Readable rain core')
    if isinstance(expression, unreal.MaterialExpressionCustom) and expression.get_editor_property('description') == 'Readable rain core':
        expression.set_editor_property('code', (ROOT/'SourceAssets/RainVisibility20260912/RainStreak.hlsl').read_text())
        updated += 1
assert updated == 1, 'Expected exactly one rain opacity expression'
# Volumetric NonDirectional ignores the drop normal and supplies no surface glints.
rain_mat.set_editor_property('translucency_lighting_mode', unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
floor_node = next((e for e in LIB.get_material_expressions(rain_mat)
    if isinstance(e, unreal.MaterialExpressionCustom) and e.get_editor_property('description') == 'Rain exposure floor'), None)
if floor_node is None:
    exposure = LIB.create_material_expression(rain_mat, unreal.MaterialExpressionEyeAdaptation)
    floor_node = LIB.create_material_expression(rain_mat, unreal.MaterialExpressionCustom)
    floor_node.set_editor_property('description', 'Rain exposure floor')
    floor_node.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    pin = unreal.CustomInput(); pin.set_editor_property('input_name', 'Exposure')
    floor_node.set_editor_property('inputs', [pin])
    assert LIB.connect_material_expressions(exposure, '', floor_node, 'Exposure')
floor_node.set_editor_property('code', 'return float3(.12,.14,.16) / max(Exposure, .001);')
assert LIB.connect_material_property(floor_node, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
save(rain_mat)

rain = duplicate('/Game/Weather/NaturalV2/NS_Natural_RainFine', 'NS_ReadableRain')
ref = unreal.NiagaraExt_StackItemReference()
for key, value in dict(system=rain, emitter_name='RainDrops', renderer_index=0).items():
    ref.set_editor_property(key, value)
data = unreal.NiagaraExt_RendererData()
data.set_editor_property('property_values', json.dumps({'Material': rain_mat.get_path_name()}))
API.call_method('SetRendererData', (ref, data))
assert unreal.RainAssetEditor.set_input(rain, 'RainDrops', 'ParticleSpawnScript', 'InitializeParticle',
    'Sprite Size', '/Script/CoreUObject.Vector2f', '(X=3.2,Y=46)')
assert unreal.RainAssetEditor.compile_rain(rain)
save(rain)

# Keep the existing wet film/ripple algorithm, but reduce the fraction that becomes puddles.
puddle = duplicate('/Game/Weather/Materials/M_RainWetSurface', 'M_SparsePuddles')
for expression in LIB.get_material_expressions(puddle):
    if isinstance(expression, unreal.MaterialExpressionCustom):
        code = expression.get_editor_property('code')
        if 'float puddle=' in code:
            code = code.replace('World.xy/180', 'World.xy/240').replace('smoothstep(.57,.78,noise)', 'smoothstep(.64,.84,noise)')
            code = code.replace('(.14+puddle*.58)', '(.07+puddle*.58)')
            expression.set_editor_property('code', code)
save(puddle)

library = duplicate('/Game/Weather/NaturalV2/DA_WeatherPresentation', 'DA_WeatherPresentation')
library.set_editor_property('rain', rain)
library.set_editor_property('puddles', puddle)
save(library)
report = dict(library=library.get_path_name(), rain=rain.get_path_name(), material=rain_mat.get_path_name(),
    puddles=puddle.get_path_name(), size=unreal.RainAssetEditor.read_input(rain, 'RainDrops',
    'ParticleSpawnScript', 'InitializeParticle', 'Sprite Size'), summary=API.call_method('GetSystemSummary', (rain,)).export_text())
out = ROOT/'Saved/RainVisibility20260912'
out.mkdir(parents=True, exist_ok=True)
(out/'assets.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
unreal.log('RAIN_VISIBILITY_ASSETS_PASS')
