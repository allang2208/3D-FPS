"""Import the user's free Fab axe and bind its supplied textures. No PIE/render tests."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/FreeProductionTools20260913'
DEST = '/Game/Items/ProductionTools/FreeFab20260913/Axe'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
report = {'listing': 'https://www.fab.com/listings/cd5e9124-55b7-4021-8544-a4dc9a7ca0d7',
          'author': 'VEE ANIMATION', 'license': 'Fab Standard License',
          'saved': [], 'runtime_tested': False}


def save(asset):
    if not asset or not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save axe asset: ' + str(asset))
    report['saved'].append(asset.get_path_name())


def import_asset(file, name, options=None):
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    asset = u.load_asset(DEST + '/' + name)
    if not asset:
        raise RuntimeError('Failed to import ' + str(file))
    return asset


def node(material, cls, **properties):
    result = LIB.create_material_expression(material, cls)
    for key, value in properties.items():
        result.set_editor_property(key, value)
    return result


def wire(source, target, pin, output=''):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect ' + pin)


EAL.make_directory(DEST)
textures = {}
texture_sources = {}
for channel in ['BaseColor', 'Normal', 'Roughness', 'AO']:
    file = SOURCE / 'Textures/Axe textures' / ('Axe_lambert2_' + channel + '.png')
    texture = import_asset(file, 'T_FreeAxe_' + channel)
    texture.set_editor_property('srgb', channel == 'BaseColor')
    texture.set_editor_property('never_stream', False)
    texture.set_editor_property('max_texture_size', 1024)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if channel == 'Normal'
                                else u.TextureCompressionSettings.TC_DEFAULT if channel == 'BaseColor'
                                else u.TextureCompressionSettings.TC_MASKS)
    save(texture)
    textures[channel] = texture
    texture_sources[channel] = {'file': str(file), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}

material = u.load_asset(DEST + '/M_FreeAxe') or TOOLS.create_asset('M_FreeAxe', DEST, u.Material, u.MaterialFactoryNew())
for expression in list(LIB.get_material_expressions(material)):
    LIB.delete_material_expression(material, expression)
material.set_editor_property('two_sided', False)
material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
samples = {}
for channel, texture in textures.items():
    samples[channel] = node(material, u.MaterialExpressionTextureSample, texture=texture,
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel == 'Normal'
        else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel == 'BaseColor'
        else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
for channel, property_name in [('BaseColor', 'BASE_COLOR'), ('Normal', 'NORMAL'),
                               ('Roughness', 'ROUGHNESS'), ('AO', 'AMBIENT_OCCLUSION')]:
    if not LIB.connect_material_property(samples[channel], 'RGB' if channel in ['BaseColor', 'Normal'] else 'R',
            getattr(u.MaterialProperty, 'MP_' + property_name)):
        raise RuntimeError('Could not bind ' + channel)
mask = node(material, u.MaterialExpressionVertexColor)
metalness = node(material, u.MaterialExpressionCustom,
    code='float rust = saturate((Color.r - Color.b) * 10.0); return Steel * lerp(0.9, 0.08, rust);',
    description='Geometry steel mask; brown oxidation is non-metallic',
    output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
pins = []
for name in ['Color', 'Steel']:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', name)
    pins.append(pin)
metalness.set_editor_property('inputs', pins)
wire(samples['BaseColor'], metalness, 'Color', 'RGB')
wire(mask, metalness, 'Steel', 'R')
LIB.connect_material_property(metalness, '', u.MaterialProperty.MP_METALLIC)
LIB.layout_material_expressions(material)
LIB.recompile_material(material)
save(material)

options = u.FbxImportUI()
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_as_skeletal = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.automated_import_should_detect_type = False
options.static_mesh_import_data.combine_meshes = True
options.static_mesh_import_data.auto_generate_collision = True
options.static_mesh_import_data.generate_lightmap_u_vs = True
options.static_mesh_import_data.vertex_color_import_option = u.VertexColorImportOption.REPLACE
options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh = import_asset(SOURCE / 'UE/Axe.fbx', 'SM_Free_Axe', options)
mesh.set_material(0, material)
settings = mesh.get_editor_property('nanite_settings')
settings.enabled = False
mesh.set_editor_property('nanite_settings', settings)
save(mesh)
report.update({'mesh': mesh.get_path_name(), 'material': material.get_path_name(),
               'textures': texture_sources, 'height_cm': 78,
               'metalness': 'Authored vertex mask for steel head/wedge and wood handle; ZIP has no metalness map.'})
(SOURCE / 'axe-import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('FREE_FAB_AXE_IMPORTED')
