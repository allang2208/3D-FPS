"""Build the native materials and skinned workwear inside the dedicated carpenter host."""
import gzip
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'SourceAssets/VillageCarpenterNPC/Outfit'
DEST = '/Game/Characters/VillageCarpenterNPC/Outfit'
SMITH = '/Game/Characters/VillageBlacksmithNPC20261118'
editor = u.EditorAssetLibrary
asset_tools = u.AssetToolsHelpers.get_asset_tools()
library = u.MaterialEditingLibrary
properties = u.MaterialProperty
written = []


def save(obj):
    path = obj.get_path_name().split('.')[0]
    if not path.startswith(DEST + '/') or not editor.save_loaded_asset(obj, False):
        raise RuntimeError('Unable to save carpenter package ' + path)
    written.append(path)


def existing(path):
    return u.load_asset(path) if editor.does_asset_exist(path) else None


def texture(slot, kind):
    name = f'T_Carpenter_{slot}_{kind}'
    task = u.AssetImportTask()
    source_folder = 'Detail' if slot == 'Wear' else 'Textures'
    task.filename = str(OUT / source_folder / (name + '.png'))
    task.destination_path = DEST + '/Textures'
    task.destination_name = name
    task.replace_existing = True
    task.replace_existing_settings = True
    task.automated = True
    task.save = False
    asset_tools.import_asset_tasks([task])
    asset = u.load_asset(task.destination_path + '/' + name)
    if asset is None:
        raise RuntimeError('Unable to import ' + name)
    asset.set_editor_property('srgb', kind == 'BC')
    preset = {
        'BC': (u.TextureCompressionSettings.TC_DEFAULT, u.TextureGroup.TEXTUREGROUP_CHARACTER),
        'N': (u.TextureCompressionSettings.TC_NORMALMAP, u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP),
        'ORM': (u.TextureCompressionSettings.TC_MASKS, u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR),
        'Mask': (u.TextureCompressionSettings.TC_MASKS, u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)
    }[kind]
    asset.set_editor_property('compression_settings', preset[0])
    asset.set_editor_property('lod_group', preset[1])
    address = u.TextureAddress.TA_CLAMP if slot == 'Tools' else u.TextureAddress.TA_WRAP
    asset.set_editor_property('address_x', address)
    asset.set_editor_property('address_y', address)
    save(asset)
    return asset


# Colour multiplier in polished areas, change in roughness, and clean-surface specular.
surface_response = {
    'Linen': ((1.13, 1.11, 1.08), -.045, .26),
    'Twill': ((1.42, 1.37, 1.29), -.065, .25),
    'Canvas': ((1.30, 1.26, 1.18), -.055, .27),
    'Saddle': ((1.39, 1.26, 1.16), -.18, .34),
    'Boot': ((1.43, 1.32, 1.21), -.15, .34),
    'Sole': ((1.18, 1.15, 1.10), -.06, .28),
    'Brass': ((1.12, 1.10, 1.05), -.14, .42),
    'Thread': ((1.12, 1.09, 1.06), -.03, .25),
    'Tools': ((1., 1., 1.), 0., .36),
}
cloth_fuzz = {'Linen': .18, 'Twill': .085, 'Canvas': .11, 'Thread': .09}


def work_material(slot, dust_map):
    folder = DEST + '/Materials'
    name = 'M_Carpenter_' + slot
    mat = existing(folder + '/' + name) or asset_tools.create_asset(name, folder, u.Material, u.MaterialFactoryNew())
    library.delete_all_material_expressions(mat)
    is_cloth = slot in cloth_fuzz
    mat.set_editor_property('two_sided', is_cloth)
    mat.set_editor_property('use_material_attributes', is_cloth)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_CLOTH if is_cloth
                            else u.MaterialShadingModel.MSM_DEFAULT_LIT)
    library.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)

    def node(kind, **values):
        obj = library.create_material_expression(mat, kind)
        for key, value in values.items():
            obj.set_editor_property(key, value)
        return obj

    def wire(src, channel, dest, pin):
        if not library.connect_material_expressions(src, channel, dest, pin):
            raise RuntimeError(name + ' could not connect ' + pin)

    def out(src, channel, pin):
        if not library.connect_material_property(src, channel, pin):
            raise RuntimeError(name + ' could not connect ' + str(pin))

    def sample(kind, sampler):
        return node(u.MaterialExpressionTextureSample, texture=texture(slot, kind), sampler_type=sampler)

    def vector(rgb):
        return node(u.MaterialExpressionConstant3Vector, constant=u.LinearColor(*rgb, 1.)), ''

    def scalar(value):
        return node(u.MaterialExpressionConstant, r=value), ''

    def combine(expression, a, b):
        result = node(expression)
        wire(*a, result, 'A')
        wire(*b, result, 'B')
        return result, ''

    def mix(a, b, alpha):
        result, channel = combine(u.MaterialExpressionLinearInterpolate, a, b)
        wire(*alpha, result, 'Alpha')
        return result, channel

    def wear_channel(coords, channel):
        mask = node(u.MaterialExpressionComponentMask, r=channel == 'r', g=channel == 'g', b=False, a=False)
        wire(coords, '', mask, '')
        return mask, ''

    mul, add = u.MaterialExpressionMultiply, u.MaterialExpressionAdd
    color = (sample('BC', u.MaterialSamplerType.SAMPLERTYPE_COLOR), 'RGB')
    orm = sample('ORM', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    roughness = (orm, 'G')
    normal = sample('N', u.MaterialSamplerType.SAMPLERTYPE_NORMAL) if slot != 'Tools' else None
    gain, polish, specular = surface_response[slot]
    if slot != 'Tools':
        coords = node(u.MaterialExpressionTextureCoordinate, coordinate_index=1)
        rub = wear_channel(coords, 'r')
        color = mix(color, combine(mul, color, vector(gain)), rub)
        roughness = combine(add, roughness, combine(mul, rub, scalar(polish)))
        if slot not in ('Brass', 'Thread'):
            dust = node(u.MaterialExpressionTextureSample, texture=dust_map,
                        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            deposit = combine(mul, (dust, 'R'), wear_channel(coords, 'g'))
            color = mix(color, vector((.32, .21, .105)), deposit)
            roughness = mix(roughness, scalar(.89), deposit)

    outputs = [(color, 'BaseColor', properties.MP_BASE_COLOR),
               ((orm, 'R'), 'AmbientOcclusion', properties.MP_AMBIENT_OCCLUSION),
               (roughness, 'Roughness', properties.MP_ROUGHNESS),
               ((orm, 'B'), 'Metallic', properties.MP_METALLIC),
               (scalar(specular), 'Specular', properties.MP_SPECULAR)]
    if normal:
        outputs.append(((normal, 'RGB'), 'Normal', properties.MP_NORMAL))
    if is_cloth:
        attributes = node(u.MaterialExpressionMakeMaterialAttributes)
        for signal, attribute, _ in outputs:
            wire(*signal, attributes, attribute)
        wire(*combine(mul, color, scalar(.40)), attributes, 'SubsurfaceColor')
        wire(*scalar(cloth_fuzz[slot]), attributes, 'ClearCoat')
        out(attributes, '', properties.MP_MATERIAL_ATTRIBUTES)
    else:
        for signal, _, pin in outputs:
            out(*signal, pin)
    library.layout_material_expressions(mat)
    errors = library.recompile_material(mat)
    if errors:
        raise RuntimeError('Material compilation failed for ' + name + ': ' + str(errors))
    save(mat)
    return mat


with gzip.open(OUT / 'workwear.json.gz', 'rt', encoding='utf-8') as stream:
    data = json.load(stream)
body = u.load_asset(SMITH + '/SK_Smith_Body')
old = u.load_asset(SMITH + '/SK_Smith_Outfit')
target = existing(DEST + '/SK_Carpenter_Workwear') or asset_tools.duplicate_asset('SK_Carpenter_Workwear', DEST, old)
if not body or not target:
    raise RuntimeError('Missing strong Jason body or workwear template.')
dust_map = texture('Wear', 'Mask')
materials = [work_material(slot, dust_map) for slot in data['material_slots']]

geo = u.GeometryScript_AssetUtils
binding = u.GeometryScript_BoneWeights
ref, result = geo.copy_mesh_from_skeletal_mesh(body, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(),
                                              u.GeometryScriptMeshReadLOD(lod_index=0))
if result != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot read R4 rest bones.')
points, normals, uvs, wear_uvs, weights, faces = [], [], [], [], [], []
indices = {}
for i, tri in enumerate(data['triangles']):
    out_face = []
    for j, v in enumerate(tri):
        uv, n = data['uv'][i][j], data['normals'][i][j]
        key = (v, *uv, *n)
        if key not in indices:
            indices[key] = len(points)
            points.append(u.Vector(*data['positions'][v]))
            normals.append(u.Vector(*n))
            uvs.append(u.Vector2D(*uv))
            wear_uvs.append(u.Vector2D(*data['wear_uv'][v]))
            weights.append(data['weights'][v])
        out_face.append(indices[key])
    faces.append(u.IntVector(*out_face))
dm = u.DynamicMesh()
buffers = u.GeometryScriptSimpleMeshBuffers(vertices=points, normals=normals, uv0=uvs, uv1=wear_uvs, triangles=faces)
u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm, buffers, 0, True)
binding.copy_bones_from_mesh(ref, dm)
binding.mesh_create_bone_weights(dm)
for i, row in enumerate(weights):
    binding.set_vertex_bone_weights(dm, i, [u.GeometryScriptBoneWeight(bone_index=b, weight=w) for b, w in row])
api = u.GeometryScript_Materials
set_face_materials = next(getattr(api, n) for n in dir(api) if n.lower().replace('_', '') == 'setalltrianglematerialids')
set_face_materials(dm, u.GeometryScript_List.convert_array_to_index_list(
    data['triangle_materials'], u.GeometryScriptIndexType.MATERIAL_ID), True)
settings = u.GeometryScriptCopyMeshToAssetOptions(
    replace_materials=True, new_materials=materials, new_material_slot_names=data['material_slots'],
    enable_recompute_normals=False, enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_, result = geo.copy_mesh_to_skeletal_mesh(dm, target, settings, u.GeometryScriptMeshWriteLOD(lod_index=0))
if result != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Unable to write native carpenter outfit.')
skeletal_editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not skeletal_editor.regenerate_lod(target, 3, True, False):
    raise RuntimeError('Unable to generate carpenter workwear LODs.')
save(target)
(OUT / 'saved.json').write_text(json.dumps({
    'outfit': target.get_path_name(), 'body': body.get_path_name(), 'skeleton': target.skeleton.get_path_name(),
    'lods': skeletal_editor.get_lod_count(target), 'triangles_authored': len(faces),
    'body_material_overrides': [], 'materials': [mat.get_path_name() for mat in materials],
    'packages': written
}, indent=2), encoding='utf-8')
print('CARPENTER_WORKWEAR_SAVED ' + target.get_path_name(), flush=True)
