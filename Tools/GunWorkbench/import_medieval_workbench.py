"""Import the medieval workbench: FBX -> new asset dir, author the two new
materials (Leather/Clay) with vertex-color weathering, bind every slot to the
surveyed inventory materials, copy Nanite/collision from the live bench, and
retarget the build palette entry. Run via pythonscript commandlet."""
import json, re
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
ROOT = P / 'SourceAssets/GunWorkbenchMedieval20260928'
MAN = json.loads((ROOT / 'Authored/manifest.json').read_text(encoding='utf-8'))
TEXDIR = P / 'Saved/GunWorkbench20260927/texpreview'
DEST = MAN['target_dir']
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
ENTRY_ID = 'gun_workbench_table'

E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()

if Path(u.Paths.project_dir()).resolve() != P.resolve():
    raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Stop PIE before updating the workbench asset')

receipt = {'stage': 'importing', 'tests_run': False, 'renders_run': False,
           'game_started': False}


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())


def node(mat, cls):
    return L.create_material_expression(mat, cls)


def scalar(mat, value):
    n = node(mat, u.MaterialExpressionConstant)
    n.r = value
    return n


def link(source, pin, target, input_name):
    inputs = list(L.get_material_expression_input_names(target))
    if input_name not in inputs and len(inputs) == 1:
        input_name = inputs[0]
    if not L.connect_material_expressions(source, pin, target, input_name):
        raise RuntimeError('connect failed: ' + input_name)


def output(source, pin, prop):
    if not L.connect_material_property(source, pin, getattr(u.MaterialProperty, 'MP_' + prop)):
        raise RuntimeError('property connect failed: ' + prop)


# ---------------------------------------------------------------- textures
def import_texture(filename, srgb):
    src = TEXDIR / filename
    name = 'T_GWM_' + Path(filename).stem
    path = DEST + '/Textures/' + name
    existing = u.load_asset(path)
    if existing:
        return existing
    task = u.AssetImportTask()
    task.filename = str(src)
    task.destination_path = DEST + '/Textures'
    task.destination_name = name
    task.automated = True
    task.save = False
    E.make_directory(DEST + '/Textures')
    A.import_asset_tasks([task])
    tex = u.load_asset(path)
    if not tex:
        raise RuntimeError('Texture import failed: ' + filename)
    tex.set_editor_property('srgb', srgb)
    if not srgb:
        for comp in ('compression_settings',):
            try:
                tex.set_editor_property(comp, u.TextureCompressionSettings.TC_MASKS)
            except Exception:
                pass
    save(tex)
    return tex


# ---------------------------------------------------------------- materials
def build_material(name, maps, vertex_weather):
    path = DEST + '/Materials/M_' + name
    mat = u.load_asset(path)
    if not mat:
        mat = A.create_asset('M_' + name, DEST + '/Materials', u.Material,
                             u.MaterialFactoryNew())
    if not mat:
        raise RuntimeError('Material create failed: ' + name)
    L.delete_all_material_expressions(mat)
    base = node(mat, u.MaterialExpressionTextureSample)
    base.texture = import_texture(maps['BaseColor'], True)
    base.sampler_type = u.MaterialSamplerType.SAMPLERTYPE_COLOR
    source = base
    if vertex_weather:
        vc = node(mat, u.MaterialExpressionVertexColor)
        mul = node(mat, u.MaterialExpressionMultiply)
        link(vc, '', mul, 'A')
        link(base, 'RGB', mul, 'B')
        source = mul
    output(source, 'RGB' if not vertex_weather else '', 'BASE_COLOR')
    rough = node(mat, u.MaterialExpressionTextureSample)
    rough.texture = import_texture(maps['Roughness'], False)
    rough.sampler_type = u.MaterialSamplerType.SAMPLERTYPE_GRAYSCALE
    output(rough, 'R', 'ROUGHNESS')
    if 'Normal' in maps:
        nrm = node(mat, u.MaterialExpressionTextureSample)
        nrm.texture = import_texture(maps['Normal'], False)
        nrm.sampler_type = u.MaterialSamplerType.SAMPLERTYPE_NORMAL
        output(nrm, 'RGB', 'NORMAL')
    output(scalar(mat, 0.0), '', 'METALLIC')
    mat.set_editor_property('two_sided', False)
    try:
        mat.set_editor_property('bUsedWithNanite', True)
    except Exception:
        pass
    L.recompile_material(mat)
    save(mat)
    return mat


new_materials = {
    'Leather': build_material('GWLeather', {
        'BaseColor': 'leather_basecolor.png',
        'Roughness': 'leather_rough.png',
        'Normal': 'leather_normal.png'}, True),
    'Clay': build_material('GWClay', {
        'BaseColor': 'clay_basecolor.png',
        'Roughness': 'clay_rough.png',
        'Normal': 'clay_normal.png'}, True),
}
receipt['new_materials'] = {k: v.get_path_name() for k, v in new_materials.items()}

# ---------------------------------------------------------------- mesh import
palette = u.load_asset(PALETTE)
entry = next(e for e in palette.get_editor_property('components')
             if str(e.get_editor_property('id')) == ENTRY_ID)
previous = entry.get_editor_property('mesh')
nanite = previous.get_editor_property('nanite_settings')
receipt['previous_mesh'] = previous.get_path_name()

task = u.AssetImportTask()
task.filename = MAN['fbx']
task.destination_path = DEST
task.destination_name = 'SM_GunWorkbench'
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = False
opt = u.FbxImportUI()
opt.import_mesh = True
opt.import_materials = False
opt.import_textures = False
opt.import_as_skeletal = False
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
data = opt.static_mesh_import_data
data.combine_meshes = True
data.convert_scene = True
data.convert_scene_unit = True
data.transform_vertex_to_absolute = True
data.generate_lightmap_u_vs = False
data.auto_generate_collision = False
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options = opt
task.factory = u.FbxFactory()
A.import_asset_tasks([task])
mesh = u.load_asset(DEST + '/SM_GunWorkbench')
if not mesh:
    raise RuntimeError('Workbench import failed')


def canon(name):
    return re.sub(r'[^a-z0-9]', '', re.sub(r'[._][0-9]{3}$', '', str(name)).lower())


bindings = {canon(k): v for k, v in MAN['bindings'].items()}
for key, val in new_materials.items():
    bindings[canon(key)] = val.get_path_name()
bound = {}
for index, slot in enumerate(mesh.get_editor_property('static_materials')):
    key = canon(slot.material_slot_name)
    if key not in bindings:
        raise RuntimeError('Material binding missing: ' + key)
    mat = u.load_asset(bindings[key])
    if not mat:
        raise RuntimeError('Bound material missing: ' + bindings[key])
    mesh.set_material(index, mat)
    bound[key] = bindings[key]
mesh.set_editor_property('nanite_settings', nanite)
mesh.get_editor_property('body_setup').set_editor_property(
    'collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
save(mesh)
receipt['mesh'] = mesh.get_path_name()
receipt['slots'] = bound

# ---------------------------------------------------------------- palette
components = list(palette.get_editor_property('components'))
for index, current in enumerate(components):
    if str(current.get_editor_property('id')) == ENTRY_ID:
        current.set_editor_property('mesh', mesh)
        components[index] = current
        break
else:
    raise RuntimeError('Palette entry missing: ' + ENTRY_ID)
palette.modify()
palette.set_editor_property('components', components)
if not E.save_loaded_asset(palette, False):
    raise RuntimeError('Palette save failed')
receipt['palette_entry'] = ENTRY_ID
receipt['saved'] = True
receipt['preserved'] = ['build ID', 'footprint', 'interaction',
                        'gun-assembly anchors (bbox matched)',
                        'previous asset untouched on disk']
(ROOT / 'Receipts').mkdir(exist_ok=True)
(ROOT / 'Receipts/import.json').write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('MEDIEVAL_WORKBENCH_SAVED ' + json.dumps(receipt, ensure_ascii=False))
