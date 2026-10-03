"""Save the gameplay mesh and PBR materials; no maps or gameplay runs."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/Bread20261003')
SPEC = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
DEST = '/Game/Items/Consumables/Bread20261003'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None:
    raise RuntimeError('Stop Play before saving the bread assets; the current game was left untouched.')
receipt = {'saved': False, 'meshes': {}, 'textures': {}, 'runtime_tested': False}
def record():
    (OUT / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
def save(asset):
    if not EAL.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
def expression(material, kind, **properties):
    node = LIB.create_material_expression(material, kind)
    for key, value in properties.items():
        node.set_editor_property(key, value)
    return node
textures = {}
for name, source in SPEC['textures'].items():
    asset_name = 'T_Bread_' + name
    texture = u.load_asset(DEST + '/Textures/' + asset_name)
    if texture is None:
        task = u.AssetImportTask()
        task.filename = source
        task.destination_name = asset_name
        task.destination_path = DEST + '/Textures'
        task.automated = True
        task.save = False
        TOOLS.import_asset_tasks([task])
        texture = u.load_asset(DEST + '/Textures/' + asset_name)
    if not isinstance(texture, u.Texture2D):
        raise RuntimeError('Texture import failed: ' + name)
    texture.set_editor_property('srgb', name == 'BaseColor')
    if name == 'Normal':
        texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
    save(texture)
    textures[name] = texture
    receipt['textures'][name] = texture.get_path_name()
    record()
material = u.load_asset(DEST + '/Materials/M_Bread') or TOOLS.create_asset(
    'M_Bread', DEST + '/Materials', u.Material, u.MaterialFactoryNew())
for node in list(LIB.get_material_expressions(material)):
    LIB.delete_material_expression(material, node)
for name, property_name in (('BaseColor', u.MaterialProperty.MP_BASE_COLOR),
    ('Roughness', u.MaterialProperty.MP_ROUGHNESS), ('Normal', u.MaterialProperty.MP_NORMAL),
    ('AO', u.MaterialProperty.MP_AMBIENT_OCCLUSION), ('Specular', u.MaterialProperty.MP_SPECULAR)):
    node = expression(material, u.MaterialExpressionTextureSample, texture=textures[name])
    node.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL if name == 'Normal'
        else u.MaterialSamplerType.SAMPLERTYPE_COLOR if name == 'BaseColor'
        else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    if not LIB.connect_material_property(node, 'RGB' if name in ('BaseColor', 'Normal') else 'R', property_name):
        raise RuntimeError('Could not connect material input ' + name)
metal = expression(material, u.MaterialExpressionConstant, r=0)
LIB.connect_material_property(metal, '', u.MaterialProperty.MP_METALLIC)
LIB.recompile_material(material)
save(material)
receipt['material'] = material.get_path_name()
record()
options = u.FbxImportUI()
options.import_mesh = True
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
data = options.static_mesh_import_data
data.combine_meshes = False
data.auto_generate_collision = False
data.generate_lightmap_u_vs = True
data.one_convex_hull_per_ucx = True
data.convert_scene = True
data.convert_scene_unit = True
data.force_front_x_axis = False
data.import_uniform_scale = 1.0
data.import_rotation = u.Rotator(0, 0, 0)
data.import_translation = u.Vector(0, 0, 0)
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task = u.AssetImportTask()
task.filename = SPEC['mesh']
task.destination_name = 'SM_Bread'
task.destination_path = DEST
task.automated = True
task.save = False
task.replace_existing = True
task.replace_existing_settings = True
task.options = options
# Explicit factory keeps these FBX unit/axis settings authoritative instead
# of sending a legacy options object into the Interchange import path.
task.factory = u.FbxFactory()
TOOLS.import_asset_tasks([task])
mesh = u.load_asset(DEST + '/SM_Bread')
if not isinstance(mesh, u.StaticMesh):
    raise RuntimeError('Bread mesh import failed')
for slot in range(len(mesh.static_materials)):
    mesh.set_material(slot, material)
nanite = mesh.get_editor_property('nanite_settings')
nanite.enabled = False
mesh.set_editor_property('nanite_settings', nanite)
save(mesh)
receipt['meshes']['bread'] = mesh.get_path_name()
bounds = mesh.get_bounds()
receipt['dimensions_cm'] = [bounds.box_extent.x * 2, bounds.box_extent.y * 2, bounds.box_extent.z * 2]
receipt['grip_center_cm'] = [bounds.origin.x, bounds.origin.y, bounds.origin.z]
receipt['saved'] = True
record()
u.log('BREAD_ASSETS_SAVED ' + mesh.get_path_name())
