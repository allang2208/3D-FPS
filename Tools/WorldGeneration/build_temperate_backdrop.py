"""Author the hills backdrop and Normandy fog adaptation; no gameplay run.

Requires the backdrop-enabled FPSGAMEEditor module. Saves only owned assets,
preserving the current grass/river references and every source-pack material.
"""
import json
import shutil
import struct
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
BASE = '/Game/WorldGeneration/TemperateHills'
DEST = BASE+'/Backdrop'
OUT = ROOT/'Saved/TemperateBackdrop'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT/('Before-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
BACKUP.mkdir()
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
REPORT = {'saved': [], 'scope': 'Asset authoring only; no gameplay or visual tests'}

def load(path):
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing authoring dependency: '+path)
    return asset

def save(asset):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    REPORT['saved'].append(asset.get_path_name())

def node(mat, cls):
    return LIB.create_material_expression(mat, cls)

def wire(source, dest, pin, output=''):
    if not LIB.connect_material_expressions(source, output, dest, pin):
        raise RuntimeError('Could not connect '+pin)

def prop(source, name):
    if not LIB.connect_material_property(source, '', getattr(u.MaterialProperty, 'MP_'+name)):
        raise RuntimeError('Could not connect '+name)

def scalar(mat, name, value):
    result = node(mat, u.MaterialExpressionScalarParameter)
    result.set_editor_property('parameter_name', name)
    result.set_editor_property('default_value', value)
    return result

def custom(mat, code, inputs, width):
    result = node(mat, u.MaterialExpressionCustom)
    result.set_editor_property('code', code)
    result.set_editor_property('output_type', getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT'+str(width)))
    entries = []
    for name in inputs:
        entry = u.CustomInput()
        entry.set_editor_property('input_name', name)
        entries.append(entry)
    result.set_editor_property('inputs', entries)
    for name, source in inputs.items():
        wire(source, result, name)
    return result

def placeholder(name, bgra, srgb):
    path = DEST+'/'+name
    if EAL.does_asset_exist(path):
        result = load(path)
    else:
        # Tiny original solid-color defaults; the world replaces both at runtime.
        source = OUT/(name+'.tga')
        source.write_bytes(struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, 4, 4, 32, 0x28)+bytes(bgra)*16)
        task = u.AssetImportTask()
        task.set_editor_property('filename', str(source))
        task.set_editor_property('destination_path', DEST)
        task.set_editor_property('destination_name', name)
        task.set_editor_property('automated', True)
        task.set_editor_property('save', False)
        TOOLS.import_asset_tasks([task])
        result = load(path)
    result.set_editor_property('srgb', srgb)
    result.set_editor_property('filter', u.TextureFilter.TF_BILINEAR if srgb else u.TextureFilter.TF_NEAREST)
    result.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
    result.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
    save(result)
    return result

def sample(mat, name, texture, uv, srgb):
    result = node(mat, u.MaterialExpressionTextureSampleParameter2D)
    result.set_editor_property('parameter_name', name)
    result.set_editor_property('texture', texture)
    result.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR if srgb else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    # Respect the runtime textures' bilinear-color / nearest-coverage filtering.
    result.set_editor_property('sampler_source', u.SamplerSourceMode.SSM_FROM_TEXTURE_ASSET)
    wire(uv, result, 'UVs')
    return result

for name in ('DA_TemperateHillsStreaming', 'MI_ValleyLowFog', 'Backdrop/M_TemperateBackdrop'):
    source = ROOT/'Content/WorldGeneration/TemperateHills'/(name+'.uasset')
    if source.exists():
        destination = BACKUP/(name+'.uasset')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

EAL.make_directory(DEST)
color = placeholder('T_BackdropDefault', (99, 125, 135, 255), True)
coverage = placeholder('T_CoverageDefault', (0, 0, 0, 255), False)
path = DEST+'/M_TemperateBackdrop'
mat = load(path) if EAL.does_asset_exist(path) else TOOLS.create_asset('M_TemperateBackdrop', DEST, u.Material, u.MaterialFactoryNew())
LIB.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED)
world = node(mat, u.MaterialExpressionWorldPosition)
half = scalar(mat, 'PlayableHalf', 51200)
outer = scalar(mat, 'BackdropHalf', 512000)
uv = custom(mat, 'return (P.xy+H)/(2*H);', {'P': world, 'H': outer}, 2)
mask_uv = custom(mat, 'return saturate((P.xy+H)/(2*H));', {'P': world, 'H': half}, 2)
base = sample(mat, 'BackdropColor', color, uv, True)
mask = sample(mat, 'TerrainCoverage', coverage, mask_uv, False)
opacity = custom(mat, 'float inside=(abs(P.x)<H && abs(P.y)<H)?1.0:0.0; return 1.0-inside*C.r;', {'P': world, 'H': half, 'C': mask}, 1)
prop(base, 'BASE_COLOR')
prop(opacity, 'OPACITY_MASK')
prop(scalar(mat, 'Roughness', 1), 'ROUGHNESS')
prop(scalar(mat, 'Specular', 0), 'SPECULAR')
LIB.recompile_material(mat)
save(mat)

fog = load(BASE+'/MI_ValleyLowFog')
for name in ('UseDistanceFields?', 'UseEmissive?'):
    # UE 5.8's implementation applies the value but always returns false.
    LIB.set_material_instance_static_switch_parameter_value(fog, name, False)
for name, value in {'FogOverallDensity': .32, 'FogEdgeRoundness': 2, 'EmissiveIntensity': 0}.items():
    LIB.set_material_instance_scalar_parameter_value(fog, name, value)
LIB.update_material_instance(fog)
save(fog)

assets = load(BASE+'/DA_TemperateHillsStreaming')
assets.set_editor_property('backdrop_material', mat)
assets.set_editor_property('valley_fog_density', .32)
save(assets)
REPORT['backdrop'] = {'meshes': 3, 'triangles': 25088, 'macro_color_size': 1024, 'outer_half_extent_m': 5120}
REPORT['fog'] = {'source_parent': fog.get_editor_property('parent').get_path_name(), 'UseDistanceFields?': False, 'density': .32, 'max_nearby_volumes': 4}
REPORT['backup'] = str(BACKUP)
(OUT/'authoring.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('TEMPERATE_BACKDROP_AUTHORING_COMPLETE '+str(OUT/'authoring.json'))
