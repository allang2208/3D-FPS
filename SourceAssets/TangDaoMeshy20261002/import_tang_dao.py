"""Import and save this new weapon's assets; usable from commandlet or gated bridge."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve() != P.parents[1]:
    raise RuntimeError('TangDao import requires the FPSGAME host project, not another Unreal process.')
DATA = json.loads((P / 'exports.json').read_text(encoding='utf-8'))
D = DATA['ue_root']
A = u.AssetToolsHelpers.get_asset_tools()
E = u.MaterialEditingLibrary
L = u.EditorAssetLibrary
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End the active play session before saving TangDao assets.')
RECEIPT = P / 'import_receipt.json'
receipt = json.loads(RECEIPT.read_text(encoding='utf-8')) if RECEIPT.exists() else {'assets': [], 'complete': False, 'tested': False}
done = {r['asset'] for r in receipt['assets']}

def saved(obj, source=''):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()], False):
        raise RuntimeError('TangDao asset save failed: ' + obj.get_path_name())
    if obj.get_path_name() not in done:
        receipt['assets'].append({'asset': obj.get_path_name(), 'source': source, 'saved': True})
        done.add(obj.get_path_name())
        RECEIPT.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return obj

def imported(file, name, folder, options=None):
    obj = u.load_asset(folder + '/' + name)
    if obj:
        return obj
    task = u.AssetImportTask()
    task.filename = str(file)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = False
    task.save = False
    if options:
        task.options = options
    A.import_asset_tasks([task])
    obj = u.load_asset(folder + '/' + name)
    if not obj or not task.imported_object_paths:
        raise RuntimeError('TangDao import failed: ' + str(file))
    return obj

textures = {}
for key, file in [('BaseColor', 'Image_0.png'), ('ORM', 'Image_1.png'), ('Normal', 'Image_2.png')]:
    texture = imported(P / 'Textures' / file, 'T_TangDao_' + key, D + '/Textures')
    texture.set_editor_property('srgb', key == 'BaseColor')
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP if key == 'Normal' else u.TextureCompressionSettings.TC_MASKS if key == 'ORM' else u.TextureCompressionSettings.TC_DEFAULT)
    if key == 'Normal':
        texture.set_editor_property('flip_green_channel', True)
    textures[key] = saved(texture, str(P / 'Textures' / file))

def node(material, cls, **props):
    expr = E.create_material_expression(material, cls)
    for key, value in props.items():
        expr.set_editor_property(key, value)
    return expr

def output(expr, pin, target):
    if not E.connect_material_property(expr, pin, target):
        raise RuntimeError('TangDao material connection failed: ' + str(target))

mat = u.load_asset(D + '/Materials/M_TangDaoSurface')
if not mat:
    mat = A.create_asset('M_TangDaoSurface', D + '/Materials', u.Material, u.MaterialFactoryNew())
    base = node(mat, u.MaterialExpressionTextureSample, texture=textures['BaseColor'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    normal = node(mat, u.MaterialExpressionTextureSample, texture=textures['Normal'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm = node(mat, u.MaterialExpressionTextureSample, texture=textures['ORM'], sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    output(base, 'RGB', u.MaterialProperty.MP_BASE_COLOR)
    output(normal, 'RGB', u.MaterialProperty.MP_NORMAL)
    for channel, target in [('R', u.MaterialProperty.MP_AMBIENT_OCCLUSION), ('G', u.MaterialProperty.MP_ROUGHNESS), ('B', u.MaterialProperty.MP_METALLIC)]:
        output(orm, channel, target)
    E.layout_material_expressions(mat)
    E.recompile_material(mat)
saved(mat)

mount = u.load_asset(D + '/Materials/M_TangDaoMountMetal')
if not mount:
    mount = A.create_asset('M_TangDaoMountMetal', D + '/Materials', u.Material, u.MaterialFactoryNew())
    output(node(mount, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(.18, .13, .075, 1)), '', u.MaterialProperty.MP_BASE_COLOR)
    for value, target in [(.85, u.MaterialProperty.MP_METALLIC), (.36, u.MaterialProperty.MP_ROUGHNESS)]:
        output(node(mount, u.MaterialExpressionConstant, r=value), '', target)
    E.recompile_material(mount)
saved(mount)

# This newly named directory has no pre-existing loaded packages to replace.
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
world = editor.get_editor_world() if editor else None
u.SystemLibrary.execute_console_command(world, 'Interchange.FeatureFlags.Import.FBX 0')
names = [DATA['world_mesh']] + [r['mesh'] for r in DATA['parts']] + [r['mesh'] for r in DATA['adapters'].values()]
for name in names:
    obj = u.load_asset(D + '/Meshes/' + name)
    if obj and obj.get_path_name() in done:
        continue
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal = False
    opt.import_mesh = True
    opt.import_materials = False
    opt.import_textures = False
    opt.import_animations = False
    cfg = opt.static_mesh_import_data
    cfg.combine_meshes = True
    cfg.auto_generate_collision = False
    cfg.generate_lightmap_u_vs = False
    cfg.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    # FBX applies these build settings directly in commandlets. The editor-only
    # subsystem is not initialized by the PythonScript commandlet.
    cfg.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
    # Blade-II runes use a translucent mesh overlay. Keep every blade on the
    # standard static-mesh path; guards, grips and pommels can use Nanite.
    supports_nanite = not name.startswith('SM_TangDao_Blade_')
    cfg.build_nanite = supports_nanite
    cfg.vertex_color_import_option = u.VertexColorImportOption.REPLACE
    mesh = imported(P / 'Export' / (name + '.fbx'), name, D + '/Meshes', opt)
    for slot in range(len(mesh.static_materials)):
        mesh.set_material(slot, mount if name.startswith('SM_TangDaoMount_') else mat)
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = supports_nanite
    nanite.explicit_tangents = True
    nanite.fallback_relative_error = 0.0
    mesh.set_editor_property('nanite_settings', nanite)
    saved(mesh, str(P / 'Export' / (name + '.fbx')))

# Required foreground variant is built into the new materials only.
mapping_path = P.parents[1] / 'Content/ColdSteelData/whirlwind-temporal-materials.json'
mapping = json.loads(mapping_path.read_text(encoding='utf-8-sig'))
added = {}
for source in [mat, mount]:
    target = source.get_path_name().split('.')[0] + '_Whirlwind'
    material = u.load_asset(target)
    if not material:
        material = L.duplicate_asset(source.get_path_name(), target)
        temporal = node(material, u.MaterialExpressionTemporalResponsivenessOutput)
        value = node(material, u.MaterialExpressionConstant, r=1.0)
        if not E.connect_material_expressions(value, '', temporal, ''):
            raise RuntimeError('TangDao foreground output failed')
        E.recompile_material(material)
    saved(material)
    added[source.get_path_name()] = material.get_path_name()
mapping.update(added)
mapping_path.write_text(json.dumps(mapping, indent=2) + '\n', encoding='utf-8')
receipt.update(complete=True, arms_mesh=DATA['arms_mesh'], animation_folder=DATA['animation_folder'], whirlwind_materials=added)
RECEIPT.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('TANGDAO_ASSETS_SAVED ' + str(len(receipt['assets'])))
