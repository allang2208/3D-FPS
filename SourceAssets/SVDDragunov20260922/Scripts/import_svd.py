"""Import the SVD into UE: body + scope, each with its own material and 4096 maps.

Lands in /Game/Weapons/SVDDragunov20260922/{Meshes,Materials,Textures}. The two parts
keep the source's separation and share one coordinate frame, so placing both at the same
transform reproduces the assembled rifle (the scope can be detached/hidden later).

Policy matches the rest of the project's imports: no Nanite, triangle-mesh collision,
material graph parameterised and values carried by a material instance, per-role texture
compression (normal = TC_NORMALMAP with flipped green, masks = TC_MASKS).

Run (no editor open):
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
PREP = json.loads((ROOT / 'Receipts' / 'prepare.json').read_text(encoding='utf-8-sig'))
BASE = SPEC['content_root']

E = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
LIB = u.MaterialEditingLibrary

if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('Different project: %s' % u.Paths.project_dir())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve running play session')
for pkg in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    if 'svddragunov20260922' in pkg.get_name().lower():
        raise RuntimeError('Unsaved work in our own packages: %s' % pkg.get_name())

(ROOT / 'Receipts').mkdir(exist_ok=True)
receipt_path = ROOT / 'Receipts' / 'import.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig')) if receipt_path.exists() else {}
receipt.update({'stage': 'importing', 'tests_run': False, 'content_root': BASE,
                'parts': receipt.get('parts', {}),
                'scope_note': 'assets only: no arms rig, no animations, no item registration'})


def write_receipt():
    receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')


write_receipt()

ROLE_SETTINGS = {
    'basecolor': (u.MaterialSamplerType.SAMPLERTYPE_COLOR, True, u.TextureCompressionSettings.TC_DEFAULT, False),
    'normal': (u.MaterialSamplerType.SAMPLERTYPE_NORMAL, False, u.TextureCompressionSettings.TC_NORMALMAP, True),
    'roughness': (u.MaterialSamplerType.SAMPLERTYPE_MASKS, False, u.TextureCompressionSettings.TC_MASKS, False),
    'metallic': (u.MaterialSamplerType.SAMPLERTYPE_MASKS, False, u.TextureCompressionSettings.TC_MASKS, False),
    'ao': (u.MaterialSamplerType.SAMPLERTYPE_MASKS, False, u.TextureCompressionSettings.TC_MASKS, False),
}


def slot_key(name):
    return ''.join(ch for ch in str(name).lower() if ch.isalnum())


def import_mesh(fbx, name):
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
        raise RuntimeError('mesh import failed: %s' % name)
    return mesh


def import_texture(path, name, role):
    sampler, srgb, compression, flip = ROLE_SETTINGS[role]
    task = u.AssetImportTask()
    task.filename = str(path).replace('\\', '/')
    task.destination_path = BASE + '/Textures'
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    TOOLS.import_asset_tasks([task])
    tex = u.load_asset(BASE + '/Textures/' + name)
    if not isinstance(tex, u.Texture2D):
        raise RuntimeError('texture import failed: %s' % name)
    tex.set_editor_property('srgb', srgb)
    tex.set_editor_property('compression_settings', compression)
    if flip:
        tex.set_editor_property('flip_green_channel', True)
    if not E.save_loaded_asset(tex, False):
        raise RuntimeError('texture save failed: %s' % name)
    return tex


def build_material(part, tex_map):
    # part_name is explicit: str.capitalize() lower-cases the rest and produced
    # "MI_SVD_Charginghandle" instead of the project's CamelCase convention.
    suffix = part.get('part_name') or part['key'].capitalize()
    name = 'M_SVD_%s' % suffix
    path = BASE + '/Materials/' + name
    material = u.load_asset(path) or TOOLS.create_asset(name, BASE + '/Materials', u.Material,
                                                        u.MaterialFactoryNew())
    if not isinstance(material, u.Material):
        raise RuntimeError('material create failed: %s' % name)
    reused = bool(list(LIB.get_material_expressions(material)))
    if reused:
        errors = LIB.recompile_material(material)
        if errors:
            raise RuntimeError('reused material %s compile errors: %s' % (name, errors))
        return material, reused

    material.set_editor_property('blend_mode', u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('two_sided', False)

    conns = []

    def sample(role, y):
        entry = tex_map.get(role)
        if not entry:
            return None
        tex = import_texture(entry['output'], entry['asset_name'], role)
        node = LIB.create_material_expression(material, u.MaterialExpressionTextureSampleParameter2D, -760, y)
        node.set_editor_property('parameter_name', 'Tex_' + role)
        node.texture = tex
        node.set_editor_property('sampler_type', ROLE_SETTINGS[role][0])
        return node

    albedo = sample('basecolor', -200)
    if albedo is None:
        raise RuntimeError('%s: base colour map missing' % name)
    tint = LIB.create_material_expression(material, u.MaterialExpressionVectorParameter, -760, -520)
    tint.set_editor_property('parameter_name', 'Tint')
    tint.set_editor_property('default_value', u.LinearColor(1.0, 1.0, 1.0, 1.0))
    mul = LIB.create_material_expression(material, u.MaterialExpressionMultiply, -440, -320)
    conns.append(LIB.connect_material_expressions(albedo, 'RGB', mul, 'A'))
    conns.append(LIB.connect_material_expressions(tint, '', mul, 'B'))

    final_color = mul
    ao = sample('ao', -40)
    if ao is not None:
        ao_mul = LIB.create_material_expression(material, u.MaterialExpressionMultiply, -240, -220)
        conns.append(LIB.connect_material_expressions(mul, '', ao_mul, 'A'))
        conns.append(LIB.connect_material_expressions(ao, 'R', ao_mul, 'B'))
        final_color = ao_mul
    conns.append(LIB.connect_material_property(final_color, '', u.MaterialProperty.MP_BASE_COLOR))

    normal = sample('normal', 160)
    if normal is not None:
        conns.append(LIB.connect_material_property(normal, 'RGB', u.MaterialProperty.MP_NORMAL))

    rough = sample('roughness', 340)
    if rough is not None:
        scale = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -760, 420)
        scale.set_editor_property('parameter_name', 'RoughnessScale')
        scale.set_editor_property('default_value', 1.0)
        rmul = LIB.create_material_expression(material, u.MaterialExpressionMultiply, -440, 380)
        conns.append(LIB.connect_material_expressions(rough, 'R', rmul, 'A'))
        conns.append(LIB.connect_material_expressions(scale, '', rmul, 'B'))
        conns.append(LIB.connect_material_property(rmul, '', u.MaterialProperty.MP_ROUGHNESS))

    metal = sample('metallic', 560)
    if metal is not None:
        conns.append(LIB.connect_material_property(metal, 'R', u.MaterialProperty.MP_METALLIC))
    else:
        m = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -760, 560)
        m.set_editor_property('parameter_name', 'Metallic')
        m.set_editor_property('default_value', 0.0)
        conns.append(LIB.connect_material_property(m, '', u.MaterialProperty.MP_METALLIC))

    if not all(conns):
        raise RuntimeError('material wiring failed for %s: %s' % (name, conns))
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('material compile errors for %s: %s' % (name, errors))
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('material save failed: %s' % name)
    return material, reused


def build_instance(part, material):
    suffix = part.get('part_name') or part['key'].capitalize()
    name = 'MI_SVD_%s' % suffix
    path = BASE + '/Materials/' + name
    mic = u.load_asset(path) or TOOLS.create_asset(name, BASE + '/Materials', u.MaterialInstanceConstant,
                                                   u.MaterialInstanceConstantFactoryNew())
    if not isinstance(mic, u.MaterialInstanceConstant):
        raise RuntimeError('material instance create failed: %s' % name)
    LIB.set_material_instance_parent(mic, material)
    LIB.set_material_instance_scalar_parameter_value(mic, 'RoughnessScale', 1.0)
    LIB.set_material_instance_vector_parameter_value(mic, 'Tint', u.LinearColor(1.0, 1.0, 1.0, 1.0))
    LIB.update_material_instance(mic)
    if not E.save_loaded_asset(mic, False):
        raise RuntimeError('material instance save failed: %s' % name)
    return mic


# Assets retired or mis-named by earlier passes. Removed through the asset API - deleting
# .uasset files while an editor has them loaded is what put this folder in a dirty state.
STALE_ASSETS = [
    BASE + '/Materials/M_SVD_Charginghandle', BASE + '/Materials/MI_SVD_Charginghandle',
    BASE + '/Materials/M_SVD_Safetylever', BASE + '/Materials/MI_SVD_Safetylever',
    BASE + '/Materials/M_SVD_Scope', BASE + '/Materials/MI_SVD_Scope',
    BASE + '/Meshes/SM_SVD_Scope',
]
for stale in STALE_ASSETS:
    if E.does_asset_exist(stale):
        if not E.delete_asset(stale):
            raise RuntimeError('cannot retire stale asset: %s' % stale)
        print('RETIRED', stale)

tex_manifest = json.loads((ROOT / 'Receipts' / 'textures.json').read_text(encoding='utf-8-sig'))
tex_by_set_role = {}
for entry in tex_manifest:
    if entry.get('missing'):
        continue
    tex_by_set_role.setdefault(entry['texture_set'], {})[entry['role']] = entry

for part in SPEC['parts']:
    mesh_name = part['mesh_name']
    fbx = ROOT / 'Authored' / (mesh_name + '.fbx')
    if not fbx.exists():
        raise RuntimeError('missing FBX for %s: %s' % (mesh_name, fbx))
    mesh = import_mesh(fbx, mesh_name)

    imported_slots = [str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')]
    if len(imported_slots) != 1:
        raise RuntimeError('%s: expected exactly 1 material slot, got %s' % (mesh_name, imported_slots))
    expected_slot = part.get('source_slot')
    if expected_slot and slot_key(imported_slots[0]) != slot_key(expected_slot):
        raise RuntimeError('%s: slot %r does not match spec slot %r'
                           % (mesh_name, imported_slots[0], expected_slot))

    material, reused = build_material(part, tex_by_set_role.get(part['texture_set'], {}))
    mic = build_instance(part, material)
    mesh.set_material(0, mic)

    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = False
    mesh.set_editor_property('nanite_settings', nanite)
    mesh.get_editor_property('body_setup').set_editor_property(
        'collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('mesh save failed: %s' % mesh_name)

    bounds = mesh.get_bounds()
    receipt['parts'][mesh_name] = {
        'path': BASE + '/Meshes/' + mesh_name,
        'material_instance': mic.get_path_name().split('.')[0],
        'material_reused': reused,
        'slot': imported_slots[0],
        'texture_set': part['texture_set'],
        'source_tris': part['tris'],
        'size_cm': [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                    round(float(bounds.box_extent.z) * 2, 2)],
        'origin_cm': [round(float(bounds.origin.x), 2), round(float(bounds.origin.y), 2),
                      round(float(bounds.origin.z), 2)],
        'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
        'collision_trace_flag': str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')),
    }
    receipt['stage'] = 'partial'
    write_receipt()
    print('SVD_IMPORT', mesh_name, json.dumps(receipt['parts'][mesh_name], default=str))

receipt['stage'] = 'assets_saved'
# Drop receipts for parts that are no longer in the spec (e.g. the single scope mesh that
# the body/scope split replaced), so the receipt matches the content folder exactly.
valid = {p['mesh_name'] for p in SPEC['parts']}
for stale in [k for k in receipt['parts'] if k not in valid]:
    receipt['parts'].pop(stale)
    receipt.setdefault('superseded', []).append(stale)
write_receipt()
u.log('SVD_IMPORT_DONE ' + json.dumps({'parts': len(receipt['parts']), 'stage': receipt['stage']}))
print('SVD_IMPORT_DONE', receipt['stage'], len(receipt['parts']))
