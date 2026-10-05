"""Restore only the shared Fab normal atlas and translucent material; no retired static mesh.
Runs in a background commandlet or the existing editor batch bridge; no previews/tests.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/AzureDragon20261004'
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
TAG, REVISION = 'AzureDragonRevision', '1'
receipt = {'complete': False, 'saved_assets': [], 'runtime_tested': False, 'rendered': False,
           'source_listing': 'https://www.fab.com/listings/2d436c6f-7d26-4a80-8469-884b97613e5a',
           'source_author': 'CaptainHC', 'source_file': str(ROOT / 'Original/Fisto.glb')}


def record():
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')


def owned(path):
    if any(str(p.get_name()) == path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved target ' + path)
    asset = u.load_asset(path)
    if asset and E.get_metadata_tag(asset, TAG) != REVISION:
        raise RuntimeError('Preserve unowned asset ' + path)
    return asset


def save(asset):
    E.set_metadata_tag(asset, TAG, REVISION)
    E.set_metadata_tag(asset, 'SourceListing', receipt['source_listing'])
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


def import_asset(filename, folder, name, options=None):
    owned(DEST + '/' + folder + '/' + name)
    task = u.AssetImportTask()
    for key, value in {'filename': str(filename), 'destination_path': DEST + '/' + folder,
                       'destination_name': name, 'automated': True, 'replace_existing': True,
                       'save': False}.items():
        task.set_editor_property(key, value)
    if options:
        task.set_editor_property('options', options)
    A.import_asset_tasks([task])
    asset = u.load_asset(DEST + '/' + folder + '/' + name)
    if not asset:
        raise RuntimeError('Cannot import ' + name)
    return asset


record()
normal = import_asset(ROOT / 'Export/T_AzureDragonNormal.png', 'Textures', 'T_AzureDragonNormal')
normal.set_editor_property('srgb', False)
normal.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
save(normal)
mat_path = DEST + '/Materials/M_AzureDragonClaw'
mat = owned(mat_path) or A.create_asset('M_AzureDragonClaw', DEST + '/Materials', u.Material, u.MaterialFactoryNew())
if not mat:
    raise RuntimeError('Cannot create energy material')
for expression in list(L.get_material_expressions(mat)):
    L.delete_material_expression(mat, expression)
for key, value in {'blend_mode': u.BlendMode.BLEND_TRANSLUCENT,
                   'shading_model': u.MaterialShadingModel.MSM_UNLIT,
                   'two_sided': True, 'disable_depth_test': True,
                   'translucency_pass': u.MaterialTranslucencyPass.MTP_AFTER_DOF,
                   'enable_responsive_aa': True}.items():
    mat.set_editor_property(key, value)
L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
count = 0


def node(cls, **properties):
    global count
    result = L.create_material_expression(mat, cls, -1800 + (count % 8) * 240, (count // 8) * 260)
    count += 1
    for key, value in properties.items():
        result.set_editor_property(key, value)
    return result


def wire(source, target, pin=0, output=''):
    if isinstance(pin, int):
        pin = str(L.get_material_expression_input_names(target)[pin])
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Cannot connect ' + str(pin))


def srgb(hex_rgb):
    channels = [int(hex_rgb[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
    return u.LinearColor(*[x/12.92 if x <= .04045 else ((x+.055)/1.055)**2.4 for x in channels], 1.0)


sample = node(u.MaterialExpressionTextureSample, texture=normal, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
mapped_normal = node(u.MaterialExpressionTransform,
                     transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,
                     transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
wire(sample, mapped_normal, output='RGB')
inputs = {
    'Normal': mapped_normal,
    'View': node(u.MaterialExpressionCameraVectorWS),
    'Body': node(u.MaterialExpressionVectorParameter, parameter_name='Body', default_value=srgb('58B99B')),
    'Rim': node(u.MaterialExpressionVectorParameter, parameter_name='Rim', default_value=srgb('9CDBCA')),
    'Opacity': node(u.MaterialExpressionScalarParameter, parameter_name='Opacity', default_value=.42),
    'Reveal': node(u.MaterialExpressionScalarParameter, parameter_name='Reveal', default_value=1.0),
    'Age': node(u.MaterialExpressionScalarParameter, parameter_name='Age', default_value=0.0),
}
position = node(u.MaterialExpressionWorldPosition)
local = node(u.MaterialExpressionTransformPosition,
             transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
             transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
wire(position, local)
x = node(u.MaterialExpressionComponentMask, r=True)
wire(local, x)
minimum = node(u.MaterialExpressionScalarParameter, parameter_name='WristX', default_value=-45.0)
length = node(u.MaterialExpressionScalarParameter, parameter_name='LengthX', default_value=125.0)
relative = node(u.MaterialExpressionSubtract)
wire(x, relative, 'A'); wire(minimum, relative, 'B')
normalized = node(u.MaterialExpressionDivide)
wire(relative, normalized, 'A'); wire(length, normalized, 'B')
inputs['LocalX'] = normalized
custom = node(u.MaterialExpressionCustom, code=(ROOT / 'AzureDragon.hlsl').read_text(encoding='utf-8'),
              output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
pins = []
for name in inputs:
    pin = u.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
custom.set_editor_property('inputs', pins)
for name, expression in inputs.items():
    wire(expression, custom, name)
color = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
wire(custom, color); wire(custom, alpha)
exposure = node(u.MaterialExpressionEyeAdaptationInverse)
wire(color, exposure, 0); wire(node(u.MaterialExpressionConstant, r=1.0), exposure, 1)
if not L.connect_material_property(exposure, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Cannot connect energy color')
if not L.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY):
    raise RuntimeError('Cannot connect foreground claw opacity')
errors = L.recompile_material(mat)
if errors:
    raise RuntimeError('Energy material compilation failed: ' + str(errors))
save(mat)

receipt["complete"] = True
record()
print("AZURE_SHARED_SURFACE_SAVED assets=2 runtime_tested=false rendered=false")
