"""Import and save the isolated M24 source assets in a UE commandlet.

No changes to gameplay, inventory, V9 hands, existing weapons, or maps.
"""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
ROOT = '/Game/Weapons/M24/CustomScope20261026'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
L = u.MaterialEditingLibrary
source = json.loads((O / 'authoring.json').read_text(encoding='utf-8'))
receipt = {'complete': False, 'root': ROOT, 'saved': [], 'clips': {},
    'runtime_registered': False, 'v9_adapted': False, 'runtime_tested': False}

def checkpoint():
    (O / 'import_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    if asset.get_path_name() not in receipt['saved']:
        receipt['saved'].append(asset.get_path_name())
    checkpoint()

def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Asset import did not produce ' + path)
    return asset

def import_file(file, folder, name, options=None):
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.save = False
    if options:
        task.options = options
        task.factory = u.FbxFactory()
    A.import_asset_tasks([task])
    return load(folder + '/' + name)

g = json.loads((O / 'Original/GLTF/scene.gltf').read_text(encoding='utf-8'))
material_names = {'sniper': 'M24_Body', 'Scope.002': 'M24_Scope',
    'ScopeGlass.002': 'M24_ScopeGlass', 'Plexiglass.002': 'M24_TopGlass'}
materials = {}
textures = {}

def texture(file, name, kind):
    if name in textures:
        return textures[name]
    tex = import_file(file, ROOT + '/Textures', name)
    tex.set_editor_property('srgb', kind == 'color')
    tex.set_editor_property('compression_settings',
        u.TextureCompressionSettings.TC_NORMALMAP if kind == 'normal' else
        u.TextureCompressionSettings.TC_DEFAULT if kind == 'color' else u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('lod_group',
        u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if kind == 'normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
    if kind == 'normal':
        # glTF defines tangent normals with the OpenGL (+Y) convention.
        tex.set_editor_property('flip_green_channel', True)
    save(tex)
    textures[name] = tex
    return tex

def sample(mat, tex, kind, y):
    node = L.create_material_expression(mat, u.MaterialExpressionTextureSample, -500, y)
    node.texture = tex
    node.sampler_type = (u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind == 'normal' else
        u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind == 'color' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    return node

def gltf_texture(index, name, kind):
    image = g['images'][g['textures'][index]['source']]['uri']
    return texture(O / 'Original/GLTF' / image, name, kind)

for row in g['materials']:
    ident = material_names[row['name']]
    package = ROOT + '/Materials/M_' + ident
    mat = u.load_asset(package) if E.does_asset_exist(package) else A.create_asset(
        'M_' + ident, ROOT + '/Materials', u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    mat.set_editor_property('two_sided', row.get('doubleSided', False))
    pbr = row['pbrMetallicRoughness']
    color = sample(mat, gltf_texture(pbr['baseColorTexture']['index'], 'T_' + ident + '_BC', 'color'), 'color', 0)
    orm = sample(mat, gltf_texture(pbr['metallicRoughnessTexture']['index'], 'T_' + ident + '_ORM', 'mask'), 'mask', 200)
    normal = sample(mat, gltf_texture(row['normalTexture']['index'], 'T_' + ident + '_N', 'normal'), 'normal', 400)
    for node, channel, prop in ((color, 'RGB', u.MaterialProperty.MP_BASE_COLOR),
        (orm, 'R', u.MaterialProperty.MP_AMBIENT_OCCLUSION),
        (orm, 'G', u.MaterialProperty.MP_ROUGHNESS),
        (orm, 'B', u.MaterialProperty.MP_METALLIC),
        (normal, 'RGB', u.MaterialProperty.MP_NORMAL)):
        L.connect_material_property(node, channel, prop)
    if row.get('alphaMode') == 'BLEND':
        mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
        transmission = row.get('extensions', {}).get('KHR_materials_transmission', {})
        if 'transmissionTexture' in transmission:
            trans = sample(mat, gltf_texture(transmission['transmissionTexture']['index'],
                'T_' + ident + '_Transmission', 'mask'), 'mask', 600)
            inverse = L.create_material_expression(mat, u.MaterialExpressionOneMinus, -250, 600)
            L.connect_material_expressions(trans, 'R', inverse, '')
            coverage = L.create_material_expression(mat, u.MaterialExpressionMultiply, -100, 500)
            L.connect_material_expressions(inverse, '', coverage, 'A')
            L.connect_material_expressions(color, 'A', coverage, 'B')
            minimum = L.create_material_expression(mat, u.MaterialExpressionMax, 50, 500)
            minimum.set_editor_property('const_b', .06)
            L.connect_material_expressions(coverage, '', minimum, 'A')
            L.connect_material_property(minimum, '', u.MaterialProperty.MP_OPACITY)
        else:
            L.connect_material_property(color, 'A', u.MaterialProperty.MP_OPACITY)
    L.recompile_material(mat)
    E.set_metadata_tag(mat, 'M24Source', 'M37_R / DJMaesen / MaximDeduytsche; CC BY 4.0')
    save(mat)
    materials[ident] = mat

# Original author skin is kept on the source viewmodel only.
ident = 'M24_SourceArms'
package = ROOT + '/Materials/M_' + ident
mat = u.load_asset(package) if E.does_asset_exist(package) else A.create_asset(
    'M_' + ident, ROOT + '/Materials', u.Material, u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)
L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
for suffix, file, kind, prop in (
    ('BC', 'armColor.png', 'color', u.MaterialProperty.MP_BASE_COLOR),
    ('N', 'armNormal.png', 'normal', u.MaterialProperty.MP_NORMAL),
    ('AO', 'armAO.png', 'mask', u.MaterialProperty.MP_AMBIENT_OCCLUSION),
    ('Metallic', 'armmetallic.png', 'mask', u.MaterialProperty.MP_METALLIC),
    ('Smoothness', 'armsmoothness.png', 'mask', u.MaterialProperty.MP_ROUGHNESS)):
    node = sample(mat, texture(O / 'Donor/Source/textures' / file, 'T_' + ident + '_' + suffix, kind), kind, 150 * len(textures))
    if suffix == 'Smoothness':
        inv = L.create_material_expression(mat, u.MaterialExpressionOneMinus, -100, 600)
        L.connect_material_expressions(node, 'R', inv, 'Input')
        L.connect_material_property(inv, '', prop)
    else:
        L.connect_material_property(node, 'RGB' if kind in ('color', 'normal') else 'R', prop)
L.recompile_material(mat)
save(mat)
materials[ident] = mat

flag = 'Interchange.FeatureFlags.Import.FBX'
old = u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None, flag + ' 0')
try:
    skeleton = None
    for name in ('SK_M24_CustomScope_SourceArms', 'SK_M24_CustomScope_Weapon'):
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
        options.import_as_skeletal = True
        options.import_mesh = True
        options.import_animations = False
        options.import_materials = False
        options.import_textures = False
        options.create_physics_asset = False
        if skeleton:
            options.skeleton = skeleton
        options.skeletal_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        mesh = import_file(O / 'Exports' / (name + '.fbx'), ROOT, name, options)
        skeleton = mesh.skeleton
        slots = list(mesh.materials)
        for i, slot in enumerate(slots):
            key = str(slot.material_slot_name)
            slot.material_interface = materials[key]
            slots[i] = slot
        mesh.set_editor_property('materials', slots)
        subsystem = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        settings = subsystem.get_lod_build_settings(mesh, 0)
        settings.use_full_precision_u_vs = True
        settings.recompute_normals = False
        settings.recompute_tangents = True
        subsystem.set_lod_build_settings(mesh, 0, settings)
        E.set_metadata_tag(mesh, 'M24ImportStage', 'Native source asset; not registered for gameplay; V9 adaptation pending')
        save(mesh)
        save(skeleton)
        receipt[name] = mesh.get_path_name()
    for file in [O / 'Exports/SM_M24_CustomScope.fbx', *sorted((O / 'Exports/Parts').glob('*.fbx'))]:
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh = True
        options.import_materials = False
        options.import_textures = False
        options.static_mesh_import_data.combine_meshes = True
        options.static_mesh_import_data.auto_generate_collision = False
        options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        folder = ROOT if file.parent.name != 'Parts' else ROOT + '/Parts'
        mesh = import_file(file, folder, file.stem, options)
        slots = list(mesh.static_materials)
        for i, slot in enumerate(slots):
            slot.material_interface = materials[str(slot.material_slot_name)]
            slots[i] = slot
        mesh.set_editor_property('static_materials', slots)
        save(mesh)
    for role, row in source['clips'].items():
        name = 'A_M24_' + role
        options = u.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh = False
        options.import_animations = True
        options.skeleton = skeleton
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 30)
        clip = import_file(Path(row['file']), ROOT + '/Animations', name, options)
        E.set_metadata_tag(clip, 'M24SourceFrames', str(row['source_frames']))
        E.set_metadata_tag(clip, 'M24Source', 'DJMaesen; b48999a250b2433da59f705c371a49b2; CC BY 4.0')
        save(clip)
        receipt['clips'][role] = {'asset': clip.get_path_name(), 'seconds': clip.get_play_length(), 'source_frames': row['source_frames']}
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(old))
receipt['complete'] = True
checkpoint()
print('M24_IMPORT_COMPLETE', len(receipt['saved']), 'saved assets;', ROOT, flush=True)
