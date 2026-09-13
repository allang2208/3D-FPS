"""Import Basic Pickaxe PBR materials and the author's three LODs. No gameplay tests."""
import hashlib
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/FreeProductionTools20260913'
DEST = '/Game/Items/ProductionTools/FreeFab20260913/Pickaxe'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
report = {'listing': 'https://www.fab.com/listings/46ea08b2-1947-40f8-b1e7-f1254d49a912',
          'author': 'REAL DEDICATED', 'license': 'Fab Standard License',
          'saved': [], 'runtime_tested': False}


def save(asset):
    if not asset or not EAL.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save pickaxe asset: ' + str(asset))
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


EAL.make_directory(DEST)
textures = {}
texture_sources = {}
for channel in ['BaseColor', 'Normal', 'Metallic', 'Roughness', 'Occlusion']:
    file = SOURCE / 'Original/Pickaxe' / f'T_BasicPickaxe_{channel}.tga'
    texture = import_asset(file, 'T_FreePickaxe_' + channel)
    texture.set_editor_property('srgb', channel == 'BaseColor')
    texture.set_editor_property('never_stream', False)
    texture.set_editor_property('max_texture_size', 1024)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if channel == 'Normal'
                                else u.TextureCompressionSettings.TC_DEFAULT if channel == 'BaseColor'
                                else u.TextureCompressionSettings.TC_MASKS)
    save(texture)
    textures[channel] = texture
    texture_sources[channel] = {'file': str(file), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()}

material = u.load_asset(DEST + '/M_FreePickaxe') or TOOLS.create_asset('M_FreePickaxe', DEST, u.Material, u.MaterialFactoryNew())
for expression in list(LIB.get_material_expressions(material)):
    LIB.delete_material_expression(material, expression)
material.set_editor_property('two_sided', False)
material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
for channel, property_name in [('BaseColor', 'BASE_COLOR'), ('Normal', 'NORMAL'),
                               ('Metallic', 'METALLIC'), ('Roughness', 'ROUGHNESS'),
                               ('Occlusion', 'AMBIENT_OCCLUSION')]:
    sample = LIB.create_material_expression(material, u.MaterialExpressionTextureSample)
    sample.set_editor_property('texture', textures[channel])
    sample.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if channel == 'Normal'
        else u.MaterialSamplerType.SAMPLERTYPE_COLOR if channel == 'BaseColor'
        else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    if not LIB.connect_material_property(sample, 'RGB' if channel in ['BaseColor', 'Normal'] else 'R',
            getattr(u.MaterialProperty, 'MP_' + property_name)):
        raise RuntimeError('Could not bind ' + channel)
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
options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
mesh = import_asset(SOURCE / 'UE/Pickaxe_LOD0.fbx', 'SM_Free_Pickaxe', options)
mesh.set_material(0, material)
# Commandlets do not automatically instantiate all editor subsystems.
editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for index in [1, 2]:
    if editor.import_lod(mesh, index, str(SOURCE / f'UE/Pickaxe_LOD{index}.fbx')) != index:
        raise RuntimeError(f'Could not import authored pickaxe LOD{index}')
if not editor.set_lod_screen_sizes(mesh, [1.0, 0.15, 0.05]):
    raise RuntimeError('Could not set pickaxe LOD transitions')
settings = mesh.get_editor_property('nanite_settings')
settings.enabled = False
mesh.set_editor_property('nanite_settings', settings)
save(mesh)
report.update({'mesh': mesh.get_path_name(), 'material': material.get_path_name(),
               'textures': texture_sources, 'height_cm': 70,
               'lod_triangles': [510, 374, 190], 'lod_screen_sizes': [1.0, 0.15, 0.05]})
(SOURCE / 'pickaxe-import.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
u.log('FREE_FAB_PICKAXE_IMPORTED')
