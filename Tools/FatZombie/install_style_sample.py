"""Import the new style materials. Existing gameplay assets are not changed here.

The running editor performs the final one-slot mesh assignment via MCP, avoiding
an out-of-process overwrite of a loaded skeletal mesh. No preview or self-test.
"""
import json
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'SourceAssets/FatZombieStyleV1'
DEST = '/Game/Monsters/FatZombieMeshy/StyleV1'
SHARED = '/Game/Monsters/Shared/InfectedSurfaceV1'
LIB = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
manifest = json.loads((ROOT / 'authoring_manifest.json').read_text(encoding='utf-8'))

def save(asset):
    if not LIB.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())

textures = {}
for semantic, file in manifest['textures'].items():
    task = u.AssetImportTask()
    task.filename = file
    task.destination_path = DEST + '/Textures'
    task.destination_name = 'T_FatZombie_StyleV1_' + semantic
    task.automated = True
    task.replace_existing = True
    task.save = True
    TOOLS.import_asset_tasks([task])
    tex = u.load_asset(task.destination_path + '/' + task.destination_name)
    if tex is None: raise RuntimeError('Import failed: ' + file)
    tex.set_editor_property('srgb', semantic == 'BaseColor')
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP
                           if semantic == 'Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
    if semantic == 'Normal':
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('flip_green_channel', False)
    elif semantic in ['ORM', 'TissueMasks']:
        tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
    save(tex)
    textures[semantic] = tex

name = 'M_InfectedSurface_V1'
mat = u.load_asset(SHARED + '/' + name) or TOOLS.create_asset(name, SHARED, u.Material, u.MaterialFactoryNew())
MEL.delete_all_material_expressions(mat)
mat.set_editor_property('used_with_skeletal_mesh', True)
mat.set_editor_property('two_sided', False)
mat.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)

def node(cls, **props):
    n = MEL.create_material_expression(mat, cls)
    for key, value in props.items(): n.set_editor_property(key, value)
    return n

def wire(src, output, dst, pin):
    if not MEL.connect_material_expressions(src, output, dst, pin):
        raise RuntimeError('Cannot connect material input ' + pin)

def scalar(name, default):
    return node(u.MaterialExpressionScalarParameter, parameter_name=name, default_value=default)

def custom(code, inputs, width=3):
    expr = node(u.MaterialExpressionCustom, code=code,
                output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(width)))
    pins = []
    for name in inputs:
        pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    expr.set_editor_property('inputs', pins)
    for name, (src, out) in inputs.items(): wire(src, out, expr, name)
    return expr

samples = {}
for semantic, tex in textures.items():
    sampler = (u.MaterialSamplerType.SAMPLERTYPE_COLOR if semantic == 'BaseColor' else
               u.MaterialSamplerType.SAMPLERTYPE_NORMAL if semantic == 'Normal' else
               u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    samples[semantic] = node(u.MaterialExpressionTextureSampleParameter2D,
        parameter_name=semantic, texture=tex, sampler_type=sampler)

skin_tint = node(u.MaterialExpressionVectorParameter, parameter_name='SkinTint', default_value=u.LinearColor(1, 1, 1, 1))
cloth_tint = node(u.MaterialExpressionVectorParameter, parameter_name='ClothTint', default_value=u.LinearColor(1, 1, 1, 1))
color = custom('return Base * lerp(ClothTint, SkinTint, saturate(Masks.r));', {
    'Base': (samples['BaseColor'], 'RGB'), 'Masks': (samples['TissueMasks'], 'RGB'),
    'SkinTint': (skin_tint, 'RGB'), 'ClothTint': (cloth_tint, 'RGB')})
rough = custom('''
float dry = clamp(Data.g + DryBias, 0.05, 0.95);
float healed = max(dry, 0.59);
float wet = lerp(healed, dry, clamp(Wetness, 0.0, 1.0));
return clamp(lerp(dry, wet, Masks.g) + Masks.b * ScabBias, 0.08, 0.95);
''', {'Data': (samples['ORM'], 'RGB'), 'Masks': (samples['TissueMasks'], 'RGB'),
      'DryBias': (scalar('DryRoughnessBias', 0.0), ''),
      'Wetness': (scalar('WoundWetness', 1.0), ''),
      'ScabBias': (scalar('ScabRoughnessBias', 0.0), '')}, 1)
normal = custom('return normalize(float3(N.xy * max(Strength, 0.0), N.z));', {
    'N': (samples['Normal'], 'RGB'), 'Strength': (scalar('NormalStrength', 1.0), '')})
specular = custom('return lerp(Dry, Wet, Masks.g);', {
    'Masks': (samples['TissueMasks'], 'RGB'),
    'Dry': (scalar('DrySpecular', .28), ''), 'Wet': (scalar('WetSpecular', .35), '')}, 1)

connections = [
    (color, '', u.MaterialProperty.MP_BASE_COLOR, 'BaseColor'),
    (normal, '', u.MaterialProperty.MP_NORMAL, 'Normal'),
    (rough, '', u.MaterialProperty.MP_ROUGHNESS, 'Roughness'),
    (specular, '', u.MaterialProperty.MP_SPECULAR, 'Specular'),
    (samples['ORM'], 'B', u.MaterialProperty.MP_METALLIC, 'Metallic')]
substrate = node(u.MaterialExpressionSubstrateShadingModels,
                 shading_model_override=u.MaterialShadingModel.MSM_DEFAULT_LIT)
for src, out, prop, pin in connections:
    if not MEL.connect_material_property(src, out, prop): raise RuntimeError('Cannot connect ' + str(prop))
    wire(src, out, substrate, pin)
MEL.connect_material_property(samples['ORM'], 'R', u.MaterialProperty.MP_AMBIENT_OCCLUSION)
if not MEL.connect_material_property(substrate, '', u.MaterialProperty.MP_FRONT_MATERIAL):
    raise RuntimeError('Cannot connect Substrate surface')
MEL.layout_material_expressions(mat)
errors = MEL.recompile_material(mat)
if errors: raise RuntimeError('Shader compilation failed: ' + '\n'.join(errors))
LIB.set_metadata_tag(mat, 'MonsterStyle.Revision', 'FatZombieSampleV1')
save(mat)

name = 'MI_FatZombie_Infected_V1'
instance = u.load_asset(DEST + '/' + name) or TOOLS.create_asset(
    name, DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
MEL.set_material_instance_parent(instance, mat)
for semantic, tex in textures.items():
    MEL.set_material_instance_texture_parameter_value(instance, semantic, tex)
MEL.update_material_instance(instance)
save(instance)
(ROOT / 'ue_import.json').write_text(json.dumps({
    'material': mat.get_path_name(), 'instance': instance.get_path_name(),
    'textures': {k: v.get_path_name() for k, v in textures.items()},
    'target_mesh': '/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy.SK_FatZombie_Meshy',
    'target_slot': 'Material_002', 'activated': False,
    'runtime_tested': False, 'preview_rendered': False}, indent=2), encoding='utf-8')
u.log('FAT_STYLE_ASSETS_IMPORTED')
