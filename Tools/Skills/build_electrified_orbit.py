"""Replace rejected solid hoops with original open, forked electric fragments.

Run through the existing editor's mutex bridge, or a background Python commandlet
when no editor owns these packages. Authoring only; no preview, PIE or tests.
"""
import json
import math
import random
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
SRC = ROOT / 'SourceAssets/ElectrifiedOrbit20260930'
DEST = '/Game/Weapons/ElectrifiedMelee/OrbitV2'
TAG = 'FPSGAME.ElectrifiedOrbit'
VERSION = 'V3'
L = u.MaterialEditingLibrary
A = u.EditorAssetLibrary
T = u.AssetToolsHelpers.get_asset_tools()
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for name in ('M_ElectrifiedOrbit', 'SM_ElectrifiedOrbit'):
    if DEST + '/' + name in dirty:
        raise RuntimeError('Preserve unsaved edits: ' + DEST + '/' + name)
A.make_directory(DEST)


def owned(path):
    if not A.does_asset_exist(path):
        return None
    asset = u.load_asset(path)
    if A.get_metadata_tag(asset, TAG) not in ('V2', VERSION):
        raise RuntimeError('Preserve existing unowned asset: ' + path)
    return asset


def node(mat, cls, **properties):
    result = L.create_material_expression(mat, cls)
    for key, value in properties.items():
        result.set_editor_property(key, value)
    return result


def wire(source, target, pin=''):
    if isinstance(pin, int):
        pin = str(L.get_material_expression_input_names(target)[pin])
    if not L.connect_material_expressions(source, '', target, pin):
        raise RuntimeError('Material connection failed: ' + str(pin))


def save(asset):
    A.set_metadata_tag(asset, TAG, VERSION)
    if not A.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save: ' + asset.get_path_name())
    u.log('ELECTRIFIED_ORBIT_SAVED ' + asset.get_path_name())


mat = owned(DEST + '/M_ElectrifiedOrbit') or T.create_asset(
    'M_ElectrifiedOrbit', DEST, u.Material, u.MaterialFactoryNew())
if not mat:
    raise RuntimeError('Could not create orbit material')
# UE 5.8 DeleteAllMaterialExpressions mutates the list it is iterating and can
# leave old outputs behind. Delete from a Python snapshot, including custom
# outputs; duplicate Temporal Responsiveness nodes caused the black fallback.
for old in list(L.get_material_expressions(mat)):
    L.delete_material_expression(mat, old)
mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property('two_sided', True)
mat.set_editor_property('enable_responsive_aa', True)
mat.set_editor_property('disable_depth_test', False)
inputs = {
    'UV': node(mat, u.MaterialExpressionTextureCoordinate, coordinate_index=0),
    'Time': node(mat, u.MaterialExpressionTime),
    'NormalWS': node(mat, u.MaterialExpressionPixelNormalWS),
    'ViewVector': node(mat, u.MaterialExpressionCameraVectorWS),
    'Exposure': node(mat, u.MaterialExpressionEyeAdaptation),
    'Phase': node(mat, u.MaterialExpressionScalarParameter, parameter_name='Phase', default_value=0.0),
    'Speed': node(mat, u.MaterialExpressionScalarParameter, parameter_name='Speed', default_value=0.27),
    'Flash': node(mat, u.MaterialExpressionScalarParameter, parameter_name='Flash', default_value=0.0),
}
effect = node(mat, u.MaterialExpressionCustom, description='V3 broken electric fragments with white cores',
              code=(SRC / 'ElectrifiedOrbit.hlsl').read_text(encoding='utf-8'),
              output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
pins = []
for name in inputs:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', name)
    pins.append(pin)
effect.set_editor_property('inputs', pins)
for name, source in inputs.items():
    wire(source, effect, name)
rgb = node(mat, u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
alpha = node(mat, u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
wire(effect, rgb)
wire(effect, alpha)
depth = node(mat, u.MaterialExpressionDepthFade, fade_distance_default=0.12)
wire(alpha, depth, 0)
if not L.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Emissive connection failed')
if not L.connect_material_property(depth, '', u.MaterialProperty.MP_OPACITY):
    raise RuntimeError('Opacity connection failed')
responsive = node(mat, u.MaterialExpressionTemporalResponsivenessOutput)
wire(node(mat, u.MaterialExpressionConstant, r=1.0), responsive, 0)
L.recompile_material(mat)
save(mat)

# Two disconnected, jagged arcs and three short forks. They cover less than
# half a circle, and are ~1/3 of the old tube thickness before weapon scaling.
# Finite topology remains open even if all shader masks are fully illuminated.
lines = ['# FPSGAME original effect geometry, centimetres, X axis', 'o SM_ElectrifiedOrbit']
positions, normals, uvs, faces = [], [], [], []
rng = random.Random(93003)


def normalized(v):
    size = math.sqrt(sum(x*x for x in v))
    return tuple(x / max(size, 1e-8) for x in v)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def tube(points, width, strand):
    base, sides = len(positions), 6
    for i, p in enumerate(points):
        tangent = normalized(tuple(b-a for a, b in zip(points[max(0, i-1)], points[min(len(points)-1, i+1)])))
        side = normalized(cross(tangent, (1, 0, 0)))
        up = normalized(cross(tangent, side))
        t = i / (len(points)-1)
        radius = width * (0.18 + 0.82 * math.sin(math.pi*t)**0.3)
        for j in range(sides+1):
            angle = math.tau*j/sides
            normal = tuple(side[k]*math.cos(angle)+up[k]*math.sin(angle) for k in range(3))
            positions.append(tuple(p[k]+radius*normal[k] for k in range(3)))
            normals.append(normal)
            uvs.append((strand*2+t, j/sides))
    for i in range(len(points)-1):
        for j in range(sides):
            a = base + i*(sides+1)+j+1
            b = a+sides+1
            faces.extend(((a, b, b+1), (a, b+1, a+1)))


def arc(start, end, count, axial):
    points = []
    for i in range(count+1):
        t = i/count
        angle = math.radians(start+(end-start)*t)
        radius = 10+rng.uniform(-.75, .75)
        points.append((axial+1.5*(t-.5)+rng.uniform(-.65, .65),
                       radius*math.cos(angle), radius*math.sin(angle)))
    return points


main = arc(0, 110, 24, 0)
secondary = arc(218, 271, 12, 1.2)
tube(main, .20, 0)
tube(secondary, .15, 1)
for strand, index in enumerate((6, 13, 19), 2):
    p = main[index]
    outward = normalized((rng.uniform(-.8, .8), p[1], p[2]))
    points = [p]
    for step in range(1, 6):
        points.append(tuple(p[k]+outward[k]*step*.60+rng.uniform(-.30, .30) for k in range(3)))
    tube(points, .11, strand)
lines.extend('v %.8f %.8f %.8f' % p for p in positions)
lines.extend('vt %.8f %.8f' % uv for uv in uvs)
lines.extend('vn %.8f %.8f %.8f' % n for n in normals)
for face in faces:
    lines.append('f ' + ' '.join('%d/%d/%d' % (v, v, v) for v in face))
SRC.mkdir(parents=True, exist_ok=True)
obj = SRC / 'SM_ElectrifiedOrbit.obj'
obj.write_text('\n'.join(lines) + '\n', encoding='utf-8')
mesh = owned(DEST + '/SM_ElectrifiedOrbit')
if mesh is None or A.get_metadata_tag(mesh, TAG) != VERSION:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.generate_lightmap_u_vs = False
    options.static_mesh_import_data.convert_scene = False
    options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = u.AssetImportTask()
    task.filename = str(obj)
    task.destination_path = DEST
    task.destination_name = 'SM_ElectrifiedOrbit'
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    task.save = False
    T.import_asset_tasks([task])
    mesh = u.load_asset(DEST + '/SM_ElectrifiedOrbit')
    if not isinstance(mesh, u.StaticMesh):
        raise RuntimeError('Orbit mesh import failed: ' + str(task.imported_object_paths))
mesh.set_material(0, mat)
save(mesh)
out = ROOT / 'Saved/ElectrifiedMelee/orbit-v3-authored.json'
out.parent.mkdir(parents=True, exist_ok=True)
receipt = {'saved': [mat.get_path_name(), mesh.get_path_name()], 'source': str(SRC),
           'triangles_per_fragment_group': len(faces), 'fragment_groups': 3,
           'presentation': 'open jagged arcs and forks; additive white core/violet halo',
           'runtime_tested': False, 'rendered': False}
out.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('ELECTRIFIED_ORBIT_AUTHORING_COMPLETE ' + json.dumps(receipt))
