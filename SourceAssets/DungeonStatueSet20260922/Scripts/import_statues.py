"""Import the whole statue set into UE as assets: mesh + material instance + texture.

No map is touched - this case deliberately only lands assets (the user asked for the
download + import, not placement).

Per statue the same policy as the Diana case:
  * FBX static mesh, geometry only, materials/textures off on the FBX task,
  * base-colour texture imported separately (sRGB, default compression),
  * material = scan albedo x Tint + Roughness/Metallic/Specular parameters, two-sided,
  * material instance holds the tunables so the graph is never edited in place,
  * Nanite off, no simple collision primitives + CTF_USE_COMPLEX_AS_SIMPLE.

Run (no editor open):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'Config' / 'statues.json').read_text(encoding='utf-8-sig'))
BASE = CFG['content_root']
EXPECTED_EXPRESSIONS = 6

E = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
LIB = u.MaterialEditingLibrary

if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('Different project: %s' % u.Paths.project_dir())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve running play session')
for pkg in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    if 'statueset20260922' in pkg.get_name().lower():
        raise RuntimeError('Unsaved work in our own packages: %s' % pkg.get_name())

(ROOT / 'Receipts').mkdir(exist_ok=True)
receipt_path = ROOT / 'Receipts' / 'import.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig')) if receipt_path.exists() else {}
receipt.update({'stage': 'importing', 'tests_run': False, 'content_root': BASE,
                'target_map': None, 'placement': 'not placed by design', 'assets': receipt.get('assets', {})})


def write_receipt():
    receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')


write_receipt()


def import_static_mesh(fbx, name):
    task = u.AssetImportTask()
    task.filename = str(fbx).replace('\\', '/')
    task.destination_path = BASE + '/Meshes'
    task.destination_name = name
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
    mesh = u.load_asset(BASE + '/Meshes/' + name)
    if not isinstance(mesh, u.StaticMesh):
        raise RuntimeError('Static mesh import failed: %s' % name)
    return mesh


def import_texture(png, name):
    task = u.AssetImportTask()
    task.filename = str(png).replace('\\', '/')
    task.destination_path = BASE + '/Textures'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    TOOLS.import_asset_tasks([task])
    tex = u.load_asset(BASE + '/Textures/' + name)
    if not isinstance(tex, u.Texture2D):
        raise RuntimeError('Texture import failed: %s' % name)
    tex.set_editor_property('srgb', True)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_DEFAULT)
    if not E.save_loaded_asset(tex, False):
        raise RuntimeError('Texture save failed: %s' % name)
    return tex


def build_material(mat_name, tex):
    mat_path = BASE + '/Materials/' + mat_name
    material = u.load_asset(mat_path) or TOOLS.create_asset(mat_name, BASE + '/Materials',
                                                            u.Material, u.MaterialFactoryNew())
    if not isinstance(material, u.Material):
        raise RuntimeError('Material create failed: %s' % mat_name)
    existing = list(LIB.get_material_expressions(material))
    reused = bool(existing)
    if existing:
        # Re-run: rebuilding a referenced material graph asserts (!IsRooted) and kills the
        # process. Verify the shape and reuse instead.
        if len(existing) != EXPECTED_EXPRESSIONS:
            raise RuntimeError('%s has %d expressions, expected %d' % (mat_name, len(existing), EXPECTED_EXPRESSIONS))
    else:
        material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
        material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
        material.set_editor_property('two_sided', True)  # source glTF materials are doubleSided
        conns = []
        albedo = LIB.create_material_expression(material, u.MaterialExpressionTextureSampleParameter2D, -600, -100)
        albedo.set_editor_property('parameter_name', 'BaseColorTex')
        albedo.texture = tex
        albedo.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_COLOR)
        tint = LIB.create_material_expression(material, u.MaterialExpressionVectorParameter, -350, -260)
        tint.set_editor_property('parameter_name', 'Tint')
        tint.set_editor_property('default_value', u.LinearColor(1.0, 1.0, 1.0, 1.0))
        mul = LIB.create_material_expression(material, u.MaterialExpressionMultiply, -180, -140)
        conns.append(LIB.connect_material_expressions(albedo, 'RGB', mul, 'A'))
        conns.append(LIB.connect_material_expressions(tint, '', mul, 'B'))
        conns.append(LIB.connect_material_property(mul, '', u.MaterialProperty.MP_BASE_COLOR))
        rough = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -350, 20)
        rough.set_editor_property('parameter_name', 'Roughness')
        rough.set_editor_property('default_value', 0.72)
        conns.append(LIB.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS))
        metal = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -350, 140)
        metal.set_editor_property('parameter_name', 'Metallic')
        metal.set_editor_property('default_value', 0.0)
        conns.append(LIB.connect_material_property(metal, '', u.MaterialProperty.MP_METALLIC))
        spec = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -350, 260)
        spec.set_editor_property('parameter_name', 'Specular')
        spec.set_editor_property('default_value', 0.35)
        conns.append(LIB.connect_material_property(spec, '', u.MaterialProperty.MP_SPECULAR))
        if not all(conns):
            raise RuntimeError('Material wiring failed for %s: %s' % (mat_name, conns))
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('Material compile errors for %s: %s' % (mat_name, errors))
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('Material save failed: %s' % mat_name)
    return material, reused


def build_instance(mic_name, material, tex):
    mic_path = BASE + '/Materials/' + mic_name
    mic = u.load_asset(mic_path) or TOOLS.create_asset(mic_name, BASE + '/Materials',
                                                       u.MaterialInstanceConstant,
                                                       u.MaterialInstanceConstantFactoryNew())
    if not isinstance(mic, u.MaterialInstanceConstant):
        raise RuntimeError('Material instance create failed: %s' % mic_name)
    LIB.set_material_instance_parent(mic, material)
    LIB.set_material_instance_texture_parameter_value(mic, 'BaseColorTex', tex)
    LIB.set_material_instance_scalar_parameter_value(mic, 'Roughness', 0.72)
    LIB.set_material_instance_scalar_parameter_value(mic, 'Metallic', 0.0)
    LIB.set_material_instance_scalar_parameter_value(mic, 'Specular', 0.35)
    LIB.set_material_instance_vector_parameter_value(mic, 'Tint', u.LinearColor(1.0, 1.0, 1.0, 1.0))
    LIB.update_material_instance(mic)
    if not E.save_loaded_asset(mic, False):
        raise RuntimeError('Material instance save failed: %s' % mic_name)
    return mic


def mesh_stat(fn):
    try:
        return int(fn())
    except Exception as exc:  # noqa: BLE001 - recorded, not fatal
        return 'unavailable: %s' % exc


for statue in CFG['statues']:
    key = statue['key']
    mesh_name = statue['mesh_name']
    fbx = ROOT / 'Authored' / (mesh_name + '.fbx')
    png = ROOT / 'Textures' / ('T_Statue_%s_BaseColor.png' % key.capitalize())
    for required in (fbx, png):
        if not required.exists():
            raise RuntimeError('Missing import input: %s' % required)

    mesh = import_static_mesh(fbx, mesh_name)
    tex = import_texture(png, 'T_Statue_%s_BaseColor' % key.capitalize())
    material, reused = build_material(statue['material_name'], tex)
    mic = build_instance('MI_' + statue['material_name'][2:], material, tex)

    slots = list(mesh.get_editor_property('static_materials'))
    for index in range(len(slots)):
        mesh.set_material(index, mic)

    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = False
    mesh.set_editor_property('nanite_settings', nanite)
    mesh.get_editor_property('body_setup').set_editor_property(
        'collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('Static mesh save failed: %s' % mesh_name)

    bounds = mesh.get_bounds()
    receipt['assets'][key] = {
        'title': statue['title'], 'uid': statue['uid'], 'license': statue['license'], 'url': statue['url'],
        'mesh': BASE + '/Meshes/' + mesh_name,
        'material': BASE + '/Materials/' + statue['material_name'],
        'material_instance': mic.get_path_name().split('.')[0],
        'texture': BASE + '/Textures/T_Statue_%s_BaseColor' % key.capitalize(),
        'triangles_lod0': mesh_stat(lambda m=mesh: u.EditorStaticMeshLibrary.get_number_triangles(m, 0)),
        'expected_triangles': statue['expected_faces'],
        'material_slots': len(slots),
        'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
        'collision_trace_flag': str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
        'size_cm': [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                    round(float(bounds.box_extent.z) * 2, 2)],
        'origin_cm': [round(float(bounds.origin.x), 2), round(float(bounds.origin.y), 2),
                      round(float(bounds.origin.z), 2)],
        'target_height_m': statue['target_height_m'],
        'front': '+X at actor yaw 0 (source normalised to front = -Y in Blender)',
        'material_reused_from_previous_run': reused,
    }
    receipt['stage'] = 'partial'
    write_receipt()
    print('STATUE_IMPORT', key, json.dumps(receipt['assets'][key], default=str))

receipt['stage'] = 'assets_saved' if len(receipt['assets']) == len(CFG['statues']) else 'partial'
write_receipt()
u.log('STATUE_SET_IMPORT ' + json.dumps({'count': len(receipt['assets']), 'stage': receipt['stage']}))
print('STATUE_SET_IMPORT_DONE', receipt['stage'], len(receipt['assets']))
