"""Background commandlet install for the five tier crates: textures, materials, static meshes.
Run via UnrealEditor-Cmd -run=pythonscript. No PIE, no renders, no acceptance tests.
"""
import json
from pathlib import Path
import unreal as u

HERE = Path(__file__).parent
PROJECT = HERE.parents[1]
ROOT = '/Game/Props/WarehouseCrateTiers20260924'
E = u.EditorAssetLibrary; L = u.MaterialEditingLibrary
AT = u.AssetToolsHelpers.get_asset_tools()
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():
    raise RuntimeError('Asset import needs editor mode; a game world is loaded.')
saved = []

def save(asset):
    path = asset.get_path_name().split('.')[0]
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(path)], False):
        raise RuntimeError('Cannot save ' + path)
    saved.append(asset.get_path_name())

def import_texture(name, normal=False):
    if E.does_asset_exist(ROOT + '/Textures/' + name):
        E.delete_asset(ROOT + '/Textures/' + name)
    task = u.AssetImportTask(); task.filename = str(HERE / 'Textures' / (name + '.png'))
    task.destination_path = ROOT + '/Textures'; task.destination_name = name
    task.automated = True; task.replace_existing = True; task.save = False
    task.set_editor_property('async_', False)
    AT.import_asset_tasks([task])
    texture = next((a for a in task.get_objects() if isinstance(a, u.Texture2D)), None)
    if texture is None: raise RuntimeError('Texture import failed ' + name)
    texture.set_editor_property('srgb', False)
    texture.set_editor_property('compression_settings',
        u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_MASKS)
    save(texture); return texture

FAMILIES = ('Wood', 'Stone', 'Iron', 'Gold', 'Silver')
textures = {f: (import_texture('T_Crate_' + f + '_Surface'), import_texture('T_Crate_' + f + '_Normal', True))
            for f in FAMILIES}

def connect(a, out, b, port):
    if not L.connect_material_expressions(a, out, b, port): raise RuntimeError('Material connection failed ' + port)
def output(node, prop):
    if not L.connect_material_property(node, '', prop): raise RuntimeError('Material output failed ' + str(prop))

# Linear-space albedo pairs (dark, bright), metallic, rough range, UV tiling (texture = 1/tiling meters).
recipes = {
    'Crate_Wood':     ('Wood', (.048, .024, .011), (.17, .095, .045), .0, .52, .74, 1.6),
    'Crate_WoodDark': ('Wood', (.024, .012, .006), (.085, .048, .024), .0, .55, .78, 1.6),
    'Crate_Stone':    ('Stone', (.055, .053, .050), (.235, .230, .215), .0, .74, .96, 2.2),
    'Crate_Iron':     ('Iron', (.055, .056, .060), (.38, .385, .40), .85, .34, .62, 3.0),
    'Crate_IronDark': ('Iron', (.020, .020, .022), (.062, .064, .070), .80, .45, .70, 3.0),
    'Crate_Gold':     ('Gold', (.24, .125, .035), (.62, .39, .13), .90, .24, .42, 4.0),
    'Crate_Silver':   ('Silver', (.28, .29, .31), (.565, .575, .60), .95, .14, .34, 3.5),
}
materials = {}
for name, (family, dark, bright, metal, rmin, rmax, tiling) in recipes.items():
    mat = u.load_asset(ROOT + '/Materials/M_' + name)
    if mat is None: mat = AT.create_asset('M_' + name, ROOT + '/Materials', u.Material, u.MaterialFactoryNew())
    L.delete_all_material_expressions(mat)
    def node(cls, x, y): return L.create_material_expression(mat, cls, x, y)
    uv = node(u.MaterialExpressionTextureCoordinate, -700, 0)
    uv.set_editor_property('u_tiling', float(tiling)); uv.set_editor_property('v_tiling', float(tiling))
    surface = node(u.MaterialExpressionTextureSample, -470, 0); surface.set_editor_property('texture', textures[family][0])
    surface.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    connect(uv, '', surface, 'UVs')
    lo = node(u.MaterialExpressionConstant3Vector, -450, -320); lo.set_editor_property('constant', u.LinearColor(*dark, 1))
    hi = node(u.MaterialExpressionConstant3Vector, -450, -180); hi.set_editor_property('constant', u.LinearColor(*bright, 1))
    color = node(u.MaterialExpressionLinearInterpolate, -170, -230)
    connect(lo, '', color, 'A'); connect(hi, '', color, 'B'); connect(surface, 'R', color, 'Alpha')
    output(color, u.MaterialProperty.MP_BASE_COLOR)
    metallic = node(u.MaterialExpressionConstant, -150, -20); metallic.set_editor_property('r', metal)
    output(metallic, u.MaterialProperty.MP_METALLIC)
    rough = node(u.MaterialExpressionLinearInterpolate, -150, 150)
    rough.set_editor_property('const_a', rmin); rough.set_editor_property('const_b', rmax)
    connect(surface, 'B', rough, 'Alpha'); output(rough, u.MaterialProperty.MP_ROUGHNESS)
    normal = node(u.MaterialExpressionTextureSample, -460, 340); normal.set_editor_property('texture', textures[family][1])
    normal.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    connect(uv, '', normal, 'UVs'); output(normal, u.MaterialProperty.MP_NORMAL)
    compile_result = L.recompile_material(mat)
    if isinstance(compile_result, (list, tuple)) and compile_result:
        raise RuntimeError('Material compile failed ' + name + ': ' + str(compile_result))
    E.set_metadata_tag(mat, 'CrateTierMaterial', '1')
    E.set_metadata_tag(mat, 'Source', 'Authored seamless procedural surface maps; WarehouseCrateTiers20260924')
    save(mat); materials[name] = mat

# Gem: untextured polished sapphire-like dielectric.
mat = u.load_asset(ROOT + '/Materials/M_Crate_Gem')
if mat is None: mat = AT.create_asset('M_Crate_Gem', ROOT + '/Materials', u.Material, u.MaterialFactoryNew())
L.delete_all_material_expressions(mat)
def node_g(cls, x, y): return L.create_material_expression(mat, cls, x, y)
base = node_g(u.MaterialExpressionConstant3Vector, -200, -200); base.set_editor_property('constant', u.LinearColor(.012, .075, .40, 1))
output(base, u.MaterialProperty.MP_BASE_COLOR)
met = node_g(u.MaterialExpressionConstant, -200, -20); met.set_editor_property('r', 0.0); output(met, u.MaterialProperty.MP_METALLIC)
rgh = node_g(u.MaterialExpressionConstant, -200, 120); rgh.set_editor_property('r', 0.07); output(rgh, u.MaterialProperty.MP_ROUGHNESS)
spec = node_g(u.MaterialExpressionConstant, -200, 240); spec.set_editor_property('r', 0.8); output(spec, u.MaterialProperty.MP_SPECULAR)
compile_result = L.recompile_material(mat)
if isinstance(compile_result, (list, tuple)) and compile_result:
    raise RuntimeError('Material compile failed Gem: ' + str(compile_result))
E.set_metadata_tag(mat, 'CrateTierMaterial', '1')
save(mat); materials['Crate_Gem'] = mat

MESHES = ['SM_WarehouseCrate_T1_Wood', 'SM_WarehouseCrate_T2_StoneWood', 'SM_WarehouseCrate_T3_Iron',
          'SM_WarehouseCrate_T4_IronGold', 'SM_WarehouseCrate_T5_SilverGem']
import re
subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

def import_mesh(name):
    if E.does_asset_exist(ROOT + '/' + name):
        E.delete_asset(ROOT + '/' + name)
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.import_materials = False; options.import_textures = False; options.import_animations = False
    options.create_physics_asset = False; options.import_mesh = True; options.import_as_skeletal = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    data = options.static_mesh_import_data
    data.convert_scene = True; data.convert_scene_unit = True; data.import_uniform_scale = 1
    data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.combine_meshes = True; data.auto_generate_collision = True; data.generate_lightmap_u_vs = True
    task = u.AssetImportTask(); task.filename = str(HERE / 'Authored' / (name + '.fbx'))
    task.destination_path = ROOT; task.destination_name = name; task.automated = True
    task.save = False; task.replace_existing = False
    task.set_editor_property('async_', False); task.factory = u.FbxFactory(); task.options = options
    AT.import_asset_tasks([task]); results = task.get_objects()
    mesh = next((a for a in results if a.get_path_name() == ROOT + '/' + name + '.' + name), None)
    if not mesh: raise RuntimeError('Mesh import failed ' + name)
    bound = mesh.get_bounds()
    ext = bound.box_extent
    size_cm = [round(ext.x * 2, 1), round(ext.y * 2, 1), round(ext.z * 2, 1)]
    for index, slot in enumerate(mesh.get_editor_property('static_materials')):
        slot_name = re.sub(r'[._][0-9]{3}$', '', str(slot.get_editor_property('material_slot_name')))
        if slot_name not in materials: raise RuntimeError('Unknown slot ' + slot_name + ' on ' + name)
        mesh.set_material(index, materials[slot_name])
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
        u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    build = subsystem.get_lod_build_settings(mesh, 0)
    build.recompute_tangents = True; build.use_mikk_t_space = True
    build.use_high_precision_tangent_basis = True; build.use_full_precision_u_vs = True
    subsystem.set_lod_build_settings(mesh, 0, build)
    nanite = mesh.get_editor_property('nanite_settings'); nanite.enabled = True
    mesh.set_editor_property('nanite_settings', nanite)
    E.set_metadata_tag(mesh, 'CrateTier', name.split('_')[-2])
    E.set_metadata_tag(mesh, 'Source', 'Blender authoring WarehouseCrateTiers20260924; references warehouse chest RitualV8')
    save(mesh)
    return {'name': name, 'size_cm': size_cm, 'slots': [str(s.get_editor_property('material_slot_name')) for s in mesh.get_editor_property('static_materials')]}

flag = 'Interchange.FeatureFlags.Import.FBX'
previous_flag = u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None, flag + ' 0')
    mesh_report = [import_mesh(name) for name in MESHES]
finally:
    u.SystemLibrary.execute_console_command(None, flag + ' ' + str(previous_flag))

receipt = dict(saved=saved, meshes=mesh_report, gui_editor_started=False, tested=False, rendered=False)
(HERE / 'install_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('CRATES_INSTALLED ' + json.dumps({'assets': len(saved), 'meshes': [m['name'] for m in mesh_report]}))
