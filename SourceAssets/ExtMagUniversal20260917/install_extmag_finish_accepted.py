"""Bind the accepted per-rifle finish to the extended magazines.

M4A1  : the magazine takes the same physical-UV finish material the accepted M4
        attachments use (duplicated from M_M4_drum_1, UV channel switched from
        the drum's index 2 to this mesh's index 1).
QBZ191: the magazine takes a receiver-coating material built exactly like
        QBZ191MetalCoat20260913/import_coating.py - the rifle coating baked onto
        the part's own atlas, original UV0 normal/cavity paths kept, white
        markings masked out of the original base colour.
AKM   : rebuilt factory magazine, keeps the rifle's own magazine material.

Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
D = '/Game/Weapons/ExtMagUniversal20260917'
MD = D + '/Materials'
M4_REFERENCE = '/Game/Weapons/AttachmentFinish20260913/M4/Materials/M_M4_drum_1.M_M4_drum_1'
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())


def node(material, cls, **props):
    expression = L.create_material_expression(material, cls)
    for key, value in props.items():
        expression.set_editor_property(key, value)
    return expression


def link(a, out, b, pin):
    pins = [str(x) for x in L.get_material_expression_input_names(b)]
    if pin == 'Input' and pin not in pins:
        pin = pins[0]
    if not L.connect_material_expressions(a, out, b, pin):
        raise RuntimeError('Connection failed ' + pin)


def output(source, out, prop):
    if not L.connect_material_property(source, out, prop):
        raise RuntimeError('Output failed ' + str(prop))


def constant(material, value):
    return node(material, u.MaterialExpressionConstant, r=value)


def import_mesh(fbx, name):
    task = u.AssetImportTask()
    task.filename = str(O / 'FBX' / fbx)
    task.destination_path = D
    task.destination_name = name
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    data = options.static_mesh_import_data
    data.combine_meshes = True
    data.convert_scene_unit = False
    data.auto_generate_collision = False
    data.generate_lightmap_u_vs = False
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    mesh = u.load_asset(D + '/' + name)
    if not mesh:
        raise RuntimeError('Mesh missing after import: ' + name)
    return mesh


def bind(mesh, material):
    slots = mesh.get_editor_property('static_materials')
    for index, slot in enumerate(slots):
        slot.material_interface = material
        slots[index] = slot
    mesh.set_editor_property('static_materials', slots)
    save(mesh)


def import_texture(path, name, srgb):
    task = u.AssetImportTask()
    task.filename = str(path)
    task.destination_path = D + '/Textures'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])
    texture = u.load_asset(task.destination_path + '/' + name)
    if not texture:
        raise RuntimeError('Texture missing ' + name)
    texture.set_editor_property('srgb', srgb)
    texture.set_editor_property('compression_settings',
                                u.TextureCompressionSettings.TC_DEFAULT if srgb
                                else u.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
    save(texture)
    return texture


report = {}

# ------------------------------------------------------------------ M4A1
reference = u.load_asset(M4_REFERENCE)
if not reference:
    raise RuntimeError('Missing accepted M4 finish material ' + M4_REFERENCE)
m4_path = MD + '/M_M4_ext_mag'
for stale in (m4_path,):
    if E.does_asset_exist(stale):
        E.delete_asset(stale)
m4_material = E.duplicate_asset(reference.get_path_name(), m4_path)
if not m4_material:
    raise RuntimeError('Duplicate failed for the M4 finish material')
for expression in u.MaterialEditingLibrary.get_material_expressions(m4_material):
    if expression.get_class().get_name() == 'MaterialExpressionTextureCoordinate' \
            and expression.get_editor_property('coordinate_index') == 2:
        expression.set_editor_property('coordinate_index', 1)
E.set_metadata_tag(m4_material, 'WeaponFinishReference', M4_REFERENCE)
E.set_metadata_tag(m4_material, 'WeaponFinishUV', '1')
L.recompile_material(m4_material)
save(m4_material)
m4_mesh = import_mesh('SM_ExtMag_M440_finish_uv.fbx', 'SM_ExtMag_M440')
bind(m4_mesh, m4_material)
report['SM_ExtMag_M440'] = {'material': m4_material.get_path_name(),
                            'from': M4_REFERENCE, 'uv_index': 1}

# ----------------------------------------------------------------- QBZ-191
qbz_textures = {}
for kind, name in (('BaseColor', 'T_ExtMag_QBZ191_BaseColor'), ('ORM', 'T_ExtMag_QBZ191_ORM')):
    qbz_textures[kind] = import_texture(O / 'Textures' / 'QBZ' / (name + '.png'), name,
                                        kind == 'BaseColor')
qbz_mesh = import_mesh('SM_ExtMag_QBZ40_finish_uv.fbx', 'SM_ExtMag_QBZ40')
original = u.load_asset('/Game/Weapons/QBZ191/Attachments20260913/Materials/'
                        'M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer.'
                        'M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer')
if not original:
    raise RuntimeError('Missing original QBZ magazine material')
qbz_path = MD + '/M_QBZ191_ext_mag_Receiver_0'
if E.does_asset_exist(qbz_path):
    E.delete_asset(qbz_path)
qbz_material = E.duplicate_asset(original.get_path_name(), qbz_path)
uv = node(qbz_material, u.MaterialExpressionTextureCoordinate, coordinate_index=1)
samples = {}
for kind, texture in qbz_textures.items():
    sampler = (u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind == 'BaseColor'
               else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    sample = node(qbz_material, u.MaterialExpressionTextureSample, texture=texture, sampler_type=sampler)
    link(uv, '', sample, 'UVs')
    samples[kind] = sample
old_base = L.get_material_property_input_node(qbz_material, u.MaterialProperty.MP_BASE_COLOR)
old_out = L.get_material_property_input_node_output_name(qbz_material, u.MaterialProperty.MP_BASE_COLOR)
mask = None
if old_base:
    lum = node(qbz_material, u.MaterialExpressionDesaturation)
    link(old_base, old_out, lum, 'Input')
    link(constant(qbz_material, 1), '', lum, 'Fraction')
    white = node(qbz_material, u.MaterialExpressionSmoothStep, const_min=.55, const_max=.82)
    link(lum, '', white, 'Value')
    mask = node(qbz_material, u.MaterialExpressionOneMinus)
    link(white, '', mask, 'Input')
for prop, sample, out in ((u.MaterialProperty.MP_BASE_COLOR, samples['BaseColor'], 'RGB'),
                          (u.MaterialProperty.MP_ROUGHNESS, samples['ORM'], 'G'),
                          (u.MaterialProperty.MP_METALLIC, samples['ORM'], 'B')):
    previous = L.get_material_property_input_node(qbz_material, prop)
    previous_out = L.get_material_property_input_node_output_name(qbz_material, prop)
    if mask and previous:
        blend = node(qbz_material, u.MaterialExpressionLinearInterpolate)
        link(previous, previous_out, blend, 'A')
        link(sample, out, blend, 'B')
        link(mask, '', blend, 'Alpha')
        output(blend, '', prop)
    else:
        output(sample, out, prop)
E.set_metadata_tag(qbz_material, 'QBZReceiverCoating', '20260918_extmag')
E.set_metadata_tag(qbz_material, 'WeaponFinishUV', '1')
L.recompile_material(qbz_material)
save(qbz_material)
bind(qbz_mesh, qbz_material)
report['SM_ExtMag_QBZ40'] = {'material': qbz_material.get_path_name(),
                             'textures': {k: v.get_path_name() for k, v in qbz_textures.items()},
                             'uv_index': 1}

# -------------------------------------------------------------------- AKM
akm_mesh = import_mesh('SM_ExtMag_AKM40_factory.fbx', 'SM_ExtMag_AKM40')
akm_material = u.load_asset('/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR.M_AKM_Soviet_PBR')
if not akm_material:
    raise RuntimeError('Missing AKM magazine material')
bind(akm_mesh, akm_material)
report['SM_ExtMag_AKM40'] = {'material': akm_material.get_path_name(),
                             'note': 'rebuilt factory magazine, rifle magazine material',
                             'triangles': akm_mesh.get_num_triangles(0)}

(O / 'finish_install_accepted_receipt.json').write_text(
    json.dumps(report, indent=2, ensure_ascii=False, default=str))
u.log('EXTMAG_FINISH_ACCEPTED ' + json.dumps(report, ensure_ascii=False, default=str))
