"""Author and save the approved shatter material and eight-face crystal. No PIE."""
from pathlib import Path
import math
import unreal as u

ROOT = Path(u.Paths.project_dir())
DEST = '/Game/Weapons/ShatterVFX20260930'
SRC = ROOT / 'SourceAssets/ShatterVFX20260930'
TAG = 'FPSGAME.ShatterVFX'
VERSION = 'VioletV1'
L = u.MaterialEditingLibrary
A = u.EditorAssetLibrary
T = u.AssetToolsHelpers.get_asset_tools()


def owned(path):
    if not A.does_asset_exist(path):
        return None
    asset = u.load_asset(path)
    if A.get_metadata_tag(asset, TAG) != VERSION:
        raise RuntimeError('Unowned shatter asset: ' + path)
    return asset


def save(asset):
    A.set_metadata_tag(asset, TAG, VERSION)
    if not A.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    u.log('SHATTER_VIOLET_SAVED ' + asset.get_path_name())


def node(mat, cls, **props):
    n = L.create_material_expression(mat, cls)
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n


def wire(src, dst, pin=''):
    if isinstance(pin, int):
        pin = str(L.get_material_expression_input_names(dst)[pin])
    if not L.connect_material_expressions(src, '', dst, pin):
        raise RuntimeError('Material connection failed: ' + str(pin))


def interp(mat, source):
    n = node(mat, u.MaterialExpressionVertexInterpolator)
    wire(source, n, 0)
    return n


def instance(mat, index, default):
    return interp(mat, node(mat, u.MaterialExpressionPerInstanceCustomData,
                           data_index=index, const_default_value=default))


path = DEST + '/M_ShatterVioletV1'
mat = owned(path) or T.create_asset('M_ShatterVioletV1', DEST, u.Material, u.MaterialFactoryNew())
if not mat:
    raise RuntimeError('Could not create shatter material')
# Delete from a snapshot: bulk deletion can retain an old temporal output.
for expression in list(L.get_material_expressions(mat)):
    L.delete_material_expression(mat, expression)
mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
mat.set_editor_property('two_sided', True)
mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
L.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
inputs = {
    'LocalPosition': interp(mat, node(mat, u.MaterialExpressionPreSkinnedPosition)),
    'NormalWS': node(mat, u.MaterialExpressionPixelNormalWS),
    'ViewVector': node(mat, u.MaterialExpressionCameraVectorWS),
    'Exposure': node(mat, u.MaterialExpressionEyeAdaptation),
    'Tint': node(mat, u.MaterialExpressionVectorParameter, parameter_name='Tint', default_value=u.LinearColor(.30, .065, 1., 1.)),
    'Emission': node(mat, u.MaterialExpressionScalarParameter, parameter_name='Emission', default_value=1.6),
    'Layer': node(mat, u.MaterialExpressionScalarParameter, parameter_name='Layer', default_value=0.),
    'Opacity': instance(mat, 0, 1.),
    'LengthCM': instance(mat, 1, 500.),
    'Age': instance(mat, 2, 0.),
}
shape = node(mat, u.MaterialExpressionCustom, description='Shatter violet crystal layers',
             code=(SRC / 'ShatterVioletV1.hlsl').read_text(encoding='utf-8'),
             output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
pins = []
for name in inputs:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', name)
    pins.append(pin)
shape.set_editor_property('inputs', pins)
for name, source in inputs.items():
    wire(source, shape, name)
rgb = node(mat, u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
alpha = node(mat, u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
wire(shape, rgb); wire(shape, alpha)
depth = node(mat, u.MaterialExpressionDepthFade, fade_distance_default=2.)
wire(alpha, depth, 0)
if not L.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Emissive connection failed')
if not L.connect_material_property(depth, '', u.MaterialProperty.MP_OPACITY):
    raise RuntimeError('Opacity connection failed')
responsive = node(mat, u.MaterialExpressionTemporalResponsivenessOutput)
wire(node(mat, u.MaterialExpressionConstant, r=1.), responsive, 0)
errors = L.recompile_material(mat)
if errors:
    raise RuntimeError('Shatter shader compilation failed: ' + str(errors))
L.get_statistics(mat)
save(mat)

# An original 100 cm octahedron with flat face normals. Runtime instance scales
# produce 2-4 cm-wide / 7-17 cm-long shards; no external mesh or texture license.
vertices = [(50, 0, 0), (0, 50, 0), (-50, 0, 0), (0, -50, 0), (0, 0, 50), (0, 0, -50)]
faces = [(4, 0, 1), (4, 1, 2), (4, 2, 3), (4, 3, 0), (5, 1, 0), (5, 2, 1), (5, 3, 2), (5, 0, 3)]
lines = ['# FPSGAME original crystal; centimetres', 'o SM_ShatterCrystal']
lines.extend('v %g %g %g' % p for p in vertices)
for a, b, c in faces:
    ab = [vertices[b][k] - vertices[a][k] for k in range(3)]
    ac = [vertices[c][k] - vertices[a][k] for k in range(3)]
    n = [ab[1]*ac[2]-ab[2]*ac[1], ab[2]*ac[0]-ab[0]*ac[2], ab[0]*ac[1]-ab[1]*ac[0]]
    length = math.sqrt(sum(x*x for x in n))
    lines.append('vn %g %g %g' % tuple(x/length for x in n))
lines.extend(('vt 0.5 1', 'vt 0 0', 'vt 1 0'))
for i, face in enumerate(faces):
    lines.append('f ' + ' '.join('%d/%d/%d' % (v+1, j+1, i+1) for j, v in enumerate(face)))
SRC.mkdir(parents=True, exist_ok=True)
obj = SRC / 'SM_ShatterCrystal.obj'
obj.write_text('\n'.join(lines) + '\n', encoding='utf-8')
mesh = owned(DEST + '/SM_ShatterCrystal')
if mesh is None or A.get_metadata_tag(mesh, 'FPSGAME.ShatterMeshUV') != 'V1':
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.generate_lightmap_u_vs = False
    options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = u.AssetImportTask()
    task.filename = str(obj); task.destination_path = DEST; task.destination_name = 'SM_ShatterCrystal'
    task.automated = True; task.options = options; task.save = False
    task.replace_existing = mesh is not None
    T.import_asset_tasks([task])
    mesh = u.load_asset(DEST + '/SM_ShatterCrystal')
    if not isinstance(mesh, u.StaticMesh):
        raise RuntimeError('Crystal import failed: ' + str(task.imported_object_paths))
mesh.set_material(0, mat)
A.set_metadata_tag(mesh, 'FPSGAME.ShatterMeshUV', 'V1')
save(mesh)
u.log('SHATTER_VIOLET_AUTHORING_COMPLETE')
