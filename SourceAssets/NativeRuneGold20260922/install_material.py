"""Create a dedicated opaque native-ink material; preserve the source sword PBR.

Run through mcp_call_codex.ps1 -PythonScript. Saves only this task's new assets.
"""
from pathlib import Path
from datetime import datetime
import json
import unreal as u

P = Path(__file__).resolve().parent
D = '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922'
SOURCE = '/Game/Weapons/AzureRunesword20260913/M_AzureRunesword'
NAME = 'M_AzureRunesword_NativeGold'
E = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
mask = u.load_asset(D+'/T_RuneSword_NativeMask')
if not mask:
    task = u.AssetImportTask()
    task.filename = str(P/'T_RuneSword_NativeMask.png')
    task.destination_path = D
    task.destination_name = 'T_RuneSword_NativeMask'
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    mask = u.load_asset(D+'/T_RuneSword_NativeMask')
if not mask:
    raise RuntimeError('Native rune mask import failed')
mask.set_editor_property('srgb', False)
mask.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
mask.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
if not u.EditorAssetLibrary.save_loaded_asset(mask, False):
    raise RuntimeError('Could not save native mask')

mat = u.load_asset(D+'/'+NAME)
if not mat:
    mat = u.EditorAssetLibrary.duplicate_asset(SOURCE, D+'/'+NAME)
if not mat:
    raise RuntimeError('Could not copy original sword material')
nodes = list(E.get_material_expressions(mat))

def node(cls, label, **props):
    tag = 'NativeRuneGold20260922:'+label
    n = next((n for n in nodes if isinstance(n, cls) and n.get_editor_property('desc') == tag), None)
    if not n:
        n = E.create_material_expression(mat, cls)
        n.set_editor_property('desc', tag)
        nodes.append(n)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n

def link(a, out, b, pin):
    if not E.connect_material_expressions(a, out, b, pin):
        raise RuntimeError('Material connection failed: '+pin)

def first_pin(n):
    return str(E.get_material_expression_input_names(n)[0])

def keep_source(label, prop):
    tag = 'NativeRuneGold20260922:'+label
    old = next((n for n in nodes if n.get_editor_property('desc') == tag), None)
    if old:
        return old
    source = E.get_material_property_input_node(mat, prop)
    output = E.get_material_property_input_node_output_name(mat, prop)
    if not source:
        source = node(u.MaterialExpressionConstant3Vector, label+'Zero', constant=u.LinearColor(0, 0, 0, 1))
        output = ''
    reroute = node(u.MaterialExpressionReroute, label)
    link(source, output, reroute, first_pin(reroute))
    return reroute

base_source = keep_source('OriginalBase', u.MaterialProperty.MP_BASE_COLOR)
glow_source = keep_source('OriginalEmission', u.MaterialProperty.MP_EMISSIVE_COLOR)
tex = node(u.MaterialExpressionTextureSampleParameter2D, 'NativeInk',
    parameter_name='NativeRuneMask', texture=mask, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
uv = node(u.MaterialExpressionTextureCoordinate, 'OriginalUV', coordinate_index=0)
link(uv, '', tex, 'UVs')

scalars = {'GoldAmount': 0., 'GlowStrength': .75, 'BreathStrength': .055,
           'FlowStrength': .24, 'PreviewTime': -1., 'ExposureCompensation': .8}
parameters = {name: node(u.MaterialExpressionScalarParameter, name,
    parameter_name=name, default_value=value, group='Native sword runes') for name, value in scalars.items()}
colors = {'GoldColor': (.58, .285, .052, 1.), 'GlowColor': (1., .49, .10, 1.)}
parameters.update({name: node(u.MaterialExpressionVectorParameter, name,
    parameter_name=name, default_value=u.LinearColor(*value), group='Native sword runes')
    for name, value in colors.items()})

def custom(label, filename, sources):
    n = node(u.MaterialExpressionCustom, label)
    pins = []
    for name in sources:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    n.set_editor_property('code', (P/filename).read_text(encoding='utf-8'))
    n.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
    for name, (src, output) in sources.items():
        link(src, output, n, name)
    return n

base = custom('GoldBase', 'native_base.hlsl', {'SourceBase': (base_source, ''),
    'Mask': (tex, 'RGB'), 'GoldAmount': (parameters['GoldAmount'], ''),
    'GoldColor': (parameters['GoldColor'], 'RGB')})
time = node(u.MaterialExpressionTime, 'Time')
glow_inputs = {'Mask': (tex, 'RGB'), 'T': (time, ''), 'GlowColor': (parameters['GlowColor'], 'RGB')}
glow_inputs.update({k: (parameters[k], '') for k in ['GoldAmount', 'GlowStrength', 'BreathStrength', 'FlowStrength', 'PreviewTime']})
glow = custom('GoldEmission', 'native_glow.hlsl', glow_inputs)
exposure = node(u.MaterialExpressionEyeAdaptationInverse, 'LocalExposure')
pins = list(E.get_material_expression_input_names(exposure))
link(glow, '', exposure, str(pins[0]))
link(parameters['ExposureCompensation'], '', exposure, str(pins[1]))

ink_amount = node(u.MaterialExpressionMultiply, 'InkAmount')
link(tex, 'R', ink_amount, 'A')
link(parameters['GoldAmount'], '', ink_amount, 'B')
inverse = node(u.MaterialExpressionOneMinus, 'RemoveOldInkEmission')
link(ink_amount, '', inverse, first_pin(inverse))
original_remaining = node(u.MaterialExpressionMultiply, 'OriginalEmissionOutsideInk')
link(glow_source, '', original_remaining, 'A')
link(inverse, '', original_remaining, 'B')
emission = node(u.MaterialExpressionAdd, 'CombinedEmission')
link(original_remaining, '', emission, 'A')
link(exposure, '', emission, 'B')
if not E.connect_material_property(base, '', u.MaterialProperty.MP_BASE_COLOR):
    raise RuntimeError('Could not connect native gold base')
if not E.connect_material_property(emission, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Could not connect native gold emission')
mat.set_editor_property('used_with_skeletal_mesh', True)
E.layout_material_expressions(mat)
errors = list(E.recompile_material(mat))
if errors:
    raise RuntimeError('Native gold material build failed: '+str(errors))
u.EditorAssetLibrary.set_metadata_tag(mat, 'NativeRuneSourceMaterial', SOURCE)
u.EditorAssetLibrary.set_metadata_tag(mat, 'NativeRuneMaskUV', '0; R native cyan ink, G narrow halo, B physical blade length')
if not u.EditorAssetLibrary.save_loaded_asset(mat, False):
    raise RuntimeError('Could not save native gold material')
mi = u.load_asset(D+'/MI_AzureRunesword_NativeGold') or A.create_asset(
    'MI_AzureRunesword_NativeGold', D, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
E.set_material_instance_parent(mi, mat)
E.set_material_instance_scalar_parameter_value(mi, 'GoldAmount', 1.)
E.update_material_instance(mi)
if not u.EditorAssetLibrary.save_loaded_asset(mi, False):
    raise RuntimeError('Could not save native gold instance')
(P/'install_receipt.json').write_text(json.dumps({
    'installed_at': datetime.now().isoformat(timespec='seconds'), 'source_material': SOURCE,
    'mask': mask.get_path_name(), 'material': mat.get_path_name(), 'instance': mi.get_path_name(),
    'parameters': {**scalars, 'GoldAmount': 1.}, 'colors_linear': colors,
    'original_pbr': 'copied intact; only base color and emission use native ink mask',
    'shader_build_errors': errors, 'runtime_tests': 'not run; user testing',
}, indent=2), encoding='utf-8')
u.log('NATIVE_RUNE_GOLD_INSTALLED '+mi.get_path_name())
