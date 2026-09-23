"""Import the Diana statue into UE: static mesh + base colour texture + material.

Stage 1 of 2. Writes Receipts/import.json and stops at stage 'mesh_saved';
Scripts/install_diana.py places it in the dungeon map afterwards.

Headless run (no editor open - check with Get-CimInstance Win32_Process first):
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' \
        'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript \
        -script='D:/FPS3D/FPSGAME/SourceAssets/DungeonGoddessStatue20260922/Scripts/import_diana.py' \
        -unattended -nop4 -nosplash -nullrhi -abslog='.../import-editor.log'
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'Config' / 'diana.json').read_text(encoding='utf-8'))
BASE = CFG['content_root']
MESH_NAME = CFG['mesh_name']
MAT_NAME = CFG['material_name']
MIC_NAME = CFG['material_instance_name']
FBX = ROOT / 'Authored' / (MESH_NAME + '.fbx')
TEX_SRC = ROOT / 'Textures' / 'T_GoddessStatueDiana_BaseColor.png'
TEX_NAME = 'T_GoddessStatueDiana_BaseColor'

E = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
LIB = u.MaterialEditingLibrary

# --- guards: same project, no live session, no unsaved work in our own folders ---
if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('Different project: %s' % u.Paths.project_dir())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve running play session')
for pkg in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    name = pkg.get_name().lower()
    if 'goddessstatue' in name or 'l_dungeon_authoredexpansion' in name:
        raise RuntimeError('Unsaved work in our own packages: %s' % pkg.get_name())
for required in (FBX, TEX_SRC):
    if not required.exists():
        raise RuntimeError('Missing import input: %s' % required)

(ROOT / 'Receipts').mkdir(exist_ok=True)
receipt_path = ROOT / 'Receipts' / 'import.json'
receipt = {'stage': 'importing', 'tests_run': False, 'target': CFG['target_map'],
           'content_root': BASE, 'asset_paths': {}}


def write_receipt():
    receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')


write_receipt()

# --- static mesh (geometry only; material and textures are authored here) ---
task = u.AssetImportTask()
task.filename = str(FBX).replace('\\', '/')
task.destination_path = BASE + '/Meshes'
task.destination_name = MESH_NAME
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = False
options = u.FbxImportUI()
options.import_mesh = True
options.import_materials = False
options.import_textures = False
options.import_as_skeletal = False
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
data = options.static_mesh_import_data
data.combine_meshes = True
data.convert_scene = True
data.convert_scene_unit = True
data.transform_vertex_to_absolute = True
data.auto_generate_collision = False
data.generate_lightmap_u_vs = False
data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task.options = options
task.factory = u.FbxFactory()
TOOLS.import_asset_tasks([task])

mesh_path = BASE + '/Meshes/' + MESH_NAME
mesh = u.load_asset(mesh_path)
if not isinstance(mesh, u.StaticMesh):
    raise RuntimeError('Static mesh import failed: %s' % mesh_path)

# --- base colour texture ---
tex_task = u.AssetImportTask()
tex_task.filename = str(TEX_SRC).replace('\\', '/')
tex_task.destination_path = BASE + '/Textures'
tex_task.destination_name = TEX_NAME
tex_task.automated = True
tex_task.replace_existing = True
tex_task.save = True
TOOLS.import_asset_tasks([tex_task])
tex = u.load_asset(BASE + '/Textures/' + TEX_NAME)
if not isinstance(tex, u.Texture2D):
    raise RuntimeError('Texture import failed')
tex.set_editor_property('srgb', True)
tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
if not E.save_loaded_asset(tex, False):
    raise RuntimeError('Texture save failed')

# --- material: scan albedo + stone roughness/metallic, parameters for instance tuning ---
mat_path = BASE + '/Materials/' + MAT_NAME
material = u.load_asset(mat_path) or TOOLS.create_asset(MAT_NAME, BASE + '/Materials',
                                                        u.Material, u.MaterialFactoryNew())
if not isinstance(material, u.Material):
    raise RuntimeError('Material create failed')
# BaseColorTex, Tint, Tint multiply, Roughness, Metallic, Specular
EXPECTED_EXPRESSIONS = 6
material_reused = False
existing = list(LIB.get_material_expressions(material))
if existing:
    # Re-running this import: the graph is already authored and is referenced by the
    # mesh slot. Rebuilding a referenced material's graph asserts (!IsRooted) and kills
    # the process, so verify the shape and reuse it instead.
    if len(existing) != EXPECTED_EXPRESSIONS:
        raise RuntimeError('Material has %d expressions, expected %d - refusing to guess'
                           % (len(existing), EXPECTED_EXPRESSIONS))
    material_reused = True
else:
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    # The Sketchfab source material is doubleSided; keep that so scan holes never show through.
    material.set_editor_property('two_sided', True)

    connections = []

    albedo = LIB.create_material_expression(material, u.MaterialExpressionTextureSampleParameter2D, -600, -100)
    albedo.set_editor_property('parameter_name', 'BaseColorTex')
    albedo.texture = tex
    albedo.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)

    tint = LIB.create_material_expression(material, u.MaterialExpressionVectorParameter, -350, -260)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', u.LinearColor(1.0, 1.0, 1.0, 1.0))
    tint_mul = LIB.create_material_expression(material, u.MaterialExpressionMultiply, -180, -140)
    connections.append(LIB.connect_material_expressions(albedo, 'RGB', tint_mul, 'A'))
    connections.append(LIB.connect_material_expressions(tint, '', tint_mul, 'B'))
    connections.append(LIB.connect_material_property(tint_mul, '', u.MaterialProperty.MP_BASE_COLOR))

    rough = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -350, 20)
    rough.set_editor_property('parameter_name', 'Roughness')
    rough.set_editor_property('default_value', 0.72)
    connections.append(LIB.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS))

    metal = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -350, 140)
    metal.set_editor_property('parameter_name', 'Metallic')
    metal.set_editor_property('default_value', 0.0)
    connections.append(LIB.connect_material_property(metal, '', u.MaterialProperty.MP_METALLIC))

    spec = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -350, 260)
    spec.set_editor_property('parameter_name', 'Specular')
    spec.set_editor_property('default_value', 0.35)
    connections.append(LIB.connect_material_property(spec, '', u.MaterialProperty.MP_SPECULAR))

    # connect_* returns False without raising - a silent mis-wire is worse than a crash.
    if not all(connections):
        raise RuntimeError('Material wiring failed: %s' % connections)

# Note: get_material_property_input_node crashes the MaterialEditor module under the
# interactive editor's remote execution, so wiring is not re-queried here.
errors = LIB.recompile_material(material)
if errors:
    raise RuntimeError('Material compile errors: %s' % errors)
if not E.save_loaded_asset(material, False):
    raise RuntimeError('Material save failed')

# --- material instance: the project tunes through instances, not by editing graphs ---
mic_path = BASE + '/Materials/' + MIC_NAME
mic = u.load_asset(mic_path) or TOOLS.create_asset(MIC_NAME, BASE + '/Materials',
                                                   u.MaterialInstanceConstant,
                                                   u.MaterialInstanceConstantFactoryNew())
if not isinstance(mic, u.MaterialInstanceConstant):
    raise RuntimeError('Material instance create failed')
LIB.set_material_instance_parent(mic, material)
LIB.set_material_instance_texture_parameter_value(mic, 'BaseColorTex', tex)
LIB.set_material_instance_scalar_parameter_value(mic, 'Roughness', 0.72)
LIB.set_material_instance_scalar_parameter_value(mic, 'Metallic', 0.0)
LIB.set_material_instance_scalar_parameter_value(mic, 'Specular', 0.35)
LIB.set_material_instance_vector_parameter_value(mic, 'Tint', u.LinearColor(1.0, 1.0, 1.0, 1.0))
LIB.update_material_instance(mic)
if not E.save_loaded_asset(mic, False):
    raise RuntimeError('Material instance save failed')

slots = list(mesh.get_editor_property('static_materials'))
for index in range(len(slots)):
    mesh.set_material(index, mic)

# --- shading / collision policy ---
nanite = mesh.get_editor_property('nanite_settings')
nanite.enabled = True
nanite.explicit_tangents = True
nanite.generate_fallback = u.NaniteGenerateFallback.ENABLED
nanite.fallback_target = u.NaniteFallbackTarget.PERCENT_TRIANGLES
nanite.fallback_percent_triangles = 1.0
nanite.fallback_relative_error = 0.0
mesh.set_editor_property('nanite_settings', nanite)
# Irregular scanned surface: no simple primitives, triangle mesh is the collision
# (project rule for shells/curved meshes - generated sphere/sphyl primitives would
# swallow the cavity around the statue).
mesh.get_editor_property('body_setup').set_editor_property(
    'collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
if not E.save_loaded_asset(mesh, False):
    raise RuntimeError('Static mesh save failed')

bounds = mesh.get_bounds()  # unreal.BoxSphereBounds: origin / box_extent / sphere_radius
bounds_origin = [round(float(bounds.origin.x), 2), round(float(bounds.origin.y), 2),
                 round(float(bounds.origin.z), 2)]
bounds_extent = [round(float(bounds.box_extent.x), 2), round(float(bounds.box_extent.y), 2),
                 round(float(bounds.box_extent.z), 2)]


def mesh_stat(fn):
    """Optional static-mesh statistics; the editor library may be absent headless."""
    try:
        return int(fn())
    except Exception as exc:  # noqa: BLE001 - recorded, not fatal
        return 'unavailable: %s' % exc


receipt['asset_paths'] = {'mesh': mesh_path, 'material': mat_path, 'material_instance': mic_path,
                          'texture': BASE + '/Textures/' + TEX_NAME}
receipt['mesh'] = {
    'triangles_lod0': mesh_stat(lambda: u.EditorStaticMeshLibrary.get_number_triangles(mesh, 0)),
    'vertices_lod0': mesh_stat(lambda: u.EditorStaticMeshLibrary.get_number_vertices(mesh, 0)),
    'lod_count': mesh_stat(lambda: u.EditorStaticMeshLibrary.get_lod_count(mesh)),
    'source_triangles': json.loads((ROOT / 'Receipts' / 'prepare.json').read_text(encoding='utf-8'))['source_mesh']['tris'],
    'material_slots': len(slots),
    'slot0': mic_path,
    'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
    'collision_trace_flag': str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
    'bounds_origin_cm': bounds_origin,
    'bounds_box_extent_cm': bounds_extent,
    'bounds_size_cm': [round(bounds_extent[i] * 2, 2) for i in range(3)],
    'material_reused_from_previous_run': material_reused,
}
receipt['material'] = {'base_color_texture': BASE + '/Textures/' + TEX_NAME,
                       'parameters': ['BaseColorTex', 'Tint', 'Roughness', 'Metallic', 'Specular'],
                       'roughness_default': 0.72, 'metallic_default': 0.0, 'specular_default': 0.35,
                       'two_sided': True,
                       'note': '扫描件只有漫反射贴图；粗糙度/金属度/高光用参数默认值，可在 MI 上调'}
receipt['stage'] = 'mesh_saved'
write_receipt()
u.log('GODDESS_STATUE_IMPORT ' + json.dumps(receipt['asset_paths']))
print('GODDESS_STATUE_IMPORT_MESH_SAVED', json.dumps(receipt['mesh']))
