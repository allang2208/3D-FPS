"""Author axe/pickaxe materials and save their existing mesh material slots.

Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>
-unattended -nop4 -AllowCommandletRendering. Does not run PIE or capture previews.
Licensed source textures and mesh backups remain on the local machine.
"""
from pathlib import Path
import hashlib
import json
import shutil
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = Path(__file__).resolve().parent
DEST = '/Game/Items/ProductionTools/Materials'
OUT = ROOT / 'SourceAssets/ProductionToolMaterials20260913'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT / 'Before'
LIB = u.MaterialEditingLibrary
EAL = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
report = {'saved': [], 'source_textures': [], 'mesh_bindings': [], 'runtime_tested': False}


def backup_asset(path):
    relative = Path('Content') / (path.removeprefix('/Game/') + '.uasset')
    src = ROOT / relative
    dst = BACKUP / relative
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        with (OUT / 'backups.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'original': str(src), 'backup': str(dst),
                'bytes': src.stat().st_size, 'sha256': hashlib.sha256(dst.read_bytes()).hexdigest()}) + '\n')


def save(asset):
    if not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name())


def node(material, cls, **properties):
    expression = LIB.create_material_expression(material, cls)
    for key, value in properties.items():
        expression.set_editor_property(key, value)
    return expression


def wire(source, target, pin, output=''):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Cannot connect material pin ' + pin)


def prop(source, name, output=''):
    if not LIB.connect_material_property(source, output, getattr(u.MaterialProperty, 'MP_' + name)):
        raise RuntimeError('Cannot connect material property ' + name)


EAL.make_directory(DEST)
textures = {}
for key, name, normal in [
    ('WoodColor', 'T_WoodSurface_00A_BaseColor', False),
    ('WoodNormal', 'T_WoodSurface_00A_Normal', True),
    ('MetalColor', 'T_MetalRust_00A_BaseColor', False),
    ('MetalNormal', 'T_MetalRust_00A_Normal', True),
]:
    source_path = '/Game/UnrealNormandy/Textures/' + name
    path = DEST + '/T_Production_' + key
    backup_asset(path)
    tex = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source_path, path)
    if not tex:
        raise RuntimeError('Missing source texture ' + source_path)
    # Keep the close-view detail in four shared 2K textures, with regular mip streaming.
    tex.set_editor_property('max_texture_size', 2048)
    tex.set_editor_property('never_stream', False)
    tex.set_editor_property('srgb', not normal)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT)
    save(tex)
    textures[key] = tex
    report['source_textures'].append(source_path)

master_path = DEST + '/M_ProductionTool_Weathered'
backup_asset(master_path)
material = u.load_asset(master_path) if EAL.does_asset_exist(master_path) else TOOLS.create_asset(
    'M_ProductionTool_Weathered', DEST, u.Material, u.MaterialFactoryNew())
for expression in list(LIB.get_material_expressions(material)):
    LIB.delete_material_expression(material, expression)
material.set_editor_property('two_sided', False)
material.set_editor_property('tangent_space_normal', False)
material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)

world = node(material, u.MaterialExpressionWorldPosition)
position = node(material, u.MaterialExpressionTransformPosition,
    transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
    transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
wire(world, position, '')
world_normal = node(material, u.MaterialExpressionVertexNormalWS)
local_normal = node(material, u.MaterialExpressionTransform,
    transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
    transform_type=u.MaterialVectorCoordTransform.TRANSFORM_LOCAL)
wire(world_normal, local_normal, '')
inputs = {'Position': position, 'LocalNormal': local_normal,
          'UV': node(material, u.MaterialExpressionTextureCoordinate, coordinate_index=0)}
for key, tex in textures.items():
    inputs[key] = node(material, u.MaterialExpressionTextureObjectParameter,
        parameter_name=key, texture=tex,
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key.endswith('Normal') else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
for name, value in {'WoodLength': 85.0, 'MetalSize': 32.0, 'RustAmount': 0.16,
                    'WoodRoughness': 0.71, 'WoodNormalStrength': 0.30, 'MetalNormalStrength': 0.18}.items():
    inputs[name] = node(material, u.MaterialExpressionScalarParameter, parameter_name=name, default_value=value)
for name, value in {'WoodTint': (1.10, 1.04, 0.93, 1.0), 'SteelTint': (0.115, 0.121, 0.125, 1.0)}.items():
    inputs[name] = node(material, u.MaterialExpressionVectorParameter,
        parameter_name=name, default_value=u.LinearColor(*value))
custom_inputs = []
for name in inputs:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', name)
    custom_inputs.append(pin)
extra_outputs = []
for name, output_type in [('Roughness', u.CustomMaterialOutputType.CMOT_FLOAT1),
                          ('Metallic', u.CustomMaterialOutputType.CMOT_FLOAT1),
                          ('SurfaceNormal', u.CustomMaterialOutputType.CMOT_FLOAT3)]:
    pin = u.CustomOutput()
    pin.set_editor_property('output_name', name)
    pin.set_editor_property('output_type', output_type)
    extra_outputs.append(pin)
surface = node(material, u.MaterialExpressionCustom,
    code=(SOURCE / 'ProductionToolSurface.hlsl').read_text(encoding='utf-8'),
    description='Tool-local wood, forged steel and worn grip',
    output_type=u.CustomMaterialOutputType.CMOT_FLOAT3, inputs=custom_inputs,
    additional_outputs=extra_outputs)
for name, expression in inputs.items():
    wire(expression, surface, name)
normal = node(material, u.MaterialExpressionTransform,
    transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_LOCAL,
    transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
wire(surface, normal, '', 'SurfaceNormal')
prop(surface, 'BASE_COLOR')
prop(surface, 'ROUGHNESS', 'Roughness')
prop(surface, 'METALLIC', 'Metallic')
prop(normal, 'NORMAL')
prop(node(material, u.MaterialExpressionConstant, r=0.35), 'SPECULAR')
LIB.layout_material_expressions(material)
LIB.recompile_material(material)
save(material)

for name, rust, wood_tint in [('Hatchet', 0.12, (1.10, 1.04, 0.93, 1)),
                               ('Pickaxe', 0.19, (0.97, 0.96, 0.90, 1))]:
    path = DEST + '/MI_Production_' + name
    backup_asset(path)
    instance = u.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        'MI_Production_' + name, DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
    LIB.set_material_instance_parent(instance, material)
    LIB.set_material_instance_scalar_parameter_value(instance, 'RustAmount', rust)
    LIB.set_material_instance_vector_parameter_value(instance, 'WoodTint', u.LinearColor(*wood_tint))
    LIB.update_material_instance(instance)
    save(instance)
    # Keep the existing path so held tools, dropped tools and saved items use the change.
    mesh_path = '/Game/EasyBuildingSystem/Meshes/Tools/Polygonal/SM_Polygonal_' + name
    backup_asset(mesh_path)
    mesh = u.load_asset(mesh_path)
    if not mesh:
        raise RuntimeError('Missing tool mesh ' + mesh_path)
    mesh.set_material(0, instance)
    save(mesh)
    report['mesh_bindings'].append({'mesh': mesh_path, 'slot': 0, 'material': path})

(OUT / 'material-install.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('PRODUCTION_TOOL_MATERIALS_INSTALLED')
