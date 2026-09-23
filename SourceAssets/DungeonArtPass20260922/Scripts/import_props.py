"""Import the seven props into UE under one content root.

Everything lands in /Game/Dungeons/ArtPass20260922 with a single naming scheme:
    Meshes/SM_Prop_*      Materials/M_Prop_*_<Slot>   Materials/MI_Prop_*_<Slot>   Textures/T_Prop_*_<Role>

Material policy follows the spec (Config/import_spec.json): per source slot a graph is
built from whatever maps exist (base colour, normal, roughness, metallic, AO, opacity
mask) with scalar parameters for the tunables, then a material instance carries the
values so the graph is never edited in place. Cobwebs and the barrel use MASKED blend
(separate alpha map / albedo alpha). Collision is per spec: 'complex' for solid props,
'none' for the cobweb cards.

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
    if 'artpass20260922' in pkg.get_name().lower():
        raise RuntimeError('Unsaved work in our own packages: %s' % pkg.get_name())

(ROOT / 'Receipts').mkdir(exist_ok=True)
receipt_path = ROOT / 'Receipts' / 'import.json'
receipt = json.loads(receipt_path.read_text(encoding='utf-8-sig')) if receipt_path.exists() else {}
receipt.update({'stage': 'importing', 'tests_run': False, 'content_root': BASE,
                'placement': 'assets only, nothing placed', 'props': receipt.get('props', {}),
                'meshes': receipt.get('meshes', {})})


def write_receipt():
    receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')


write_receipt()

# role -> (sampler type, srgb, compression, flip green)
ROLE_SETTINGS = {
    'basecolor': (u.MaterialSamplerType.SAMPLERTYPE_COLOR, True, u.TextureCompressionSettings.TC_DEFAULT, False),
    'basecolor_alpha': (u.MaterialSamplerType.SAMPLERTYPE_COLOR, True, u.TextureCompressionSettings.TC_DEFAULT, False),
    'normal': (u.MaterialSamplerType.SAMPLERTYPE_NORMAL, False, u.TextureCompressionSettings.TC_NORMALMAP, True),
    'roughness': (u.MaterialSamplerType.SAMPLERTYPE_MASKS, False, u.TextureCompressionSettings.TC_MASKS, False),
    'metallic': (u.MaterialSamplerType.SAMPLERTYPE_MASKS, False, u.TextureCompressionSettings.TC_MASKS, False),
    'metallic_from_r': (u.MaterialSamplerType.SAMPLERTYPE_MASKS, False, u.TextureCompressionSettings.TC_MASKS, False),
    'ao': (u.MaterialSamplerType.SAMPLERTYPE_MASKS, False, u.TextureCompressionSettings.TC_MASKS, False),
    'opacity_mask_source': (u.MaterialSamplerType.SAMPLERTYPE_MASKS, False, u.TextureCompressionSettings.TC_MASKS, False),
}


def slot_tag(slot):
    if slot == '*':
        return 'All'
    return ''.join(ch for ch in slot.title() if ch.isalnum())


def slot_key(slot):
    """Loose comparison key: UE re-import turned the source slot 'metal ' into 'metal_'."""
    return ''.join(ch for ch in str(slot).lower() if ch.isalnum())


def import_mesh(fbx, name, prop_key, out_entry):
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


def import_texture(png, name, role):
    sampler, srgb, compression, flip = ROLE_SETTINGS[role]
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
        raise RuntimeError('texture import failed: %s' % name)
    tex.set_editor_property('srgb', srgb)
    tex.set_editor_property('compression_settings', compression)
    if flip:
        tex.set_editor_property('flip_green_channel', True)
    if not E.save_loaded_asset(tex, False):
        raise RuntimeError('texture save failed: %s' % name)
    return tex


def build_material(prop, mat_spec, tex_map):
    name = 'M_Prop_%s_%s' % (prop['name'], slot_tag(mat_spec['slot']))
    path = BASE + '/Materials/' + name
    material = u.load_asset(path) or TOOLS.create_asset(name, BASE + '/Materials', u.Material,
                                                        u.MaterialFactoryNew())
    if not isinstance(material, u.Material):
        raise RuntimeError('material create failed: %s' % name)
    reused = bool(list(LIB.get_material_expressions(material)))
    if reused:
        errors = LIB.recompile_material(material)
        if errors:
            raise RuntimeError('reused material %s has compile errors: %s' % (name, errors))
        return material, reused

    blend = mat_spec.get('blend', 'opaque')
    material.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED if blend == 'masked'
                                 else u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property('two_sided', bool(mat_spec.get('two_sided', False)))

    conns = []
    consts = mat_spec.get('constants') or {}
    maps = mat_spec.get('maps') or {}
    nodes = {}

    def sample(role, y):
        entry = tex_map.get(role)
        if not entry or entry.get('missing'):
            return None
        tex = import_texture(entry['output'], entry['asset_name'], role)
        node = LIB.create_material_expression(material, u.MaterialExpressionTextureSampleParameter2D, -700, y)
        node.set_editor_property('parameter_name', 'Tex_' + role)
        node.texture = tex
        node.set_editor_property('sampler_type', ROLE_SETTINGS[role][0])
        nodes[role] = node
        return node

    albedo_node = sample('basecolor', -300) or sample('basecolor_alpha', -300)
    tint = LIB.create_material_expression(material, u.MaterialExpressionVectorParameter, -700, -520)
    tint.set_editor_property('parameter_name', 'Tint')
    base_color = consts.get('base_color') or [1.0, 1.0, 1.0, 1.0]
    tint.set_editor_property('default_value', u.LinearColor(*[float(c) for c in base_color]))
    tint_mul = LIB.create_material_expression(material, u.MaterialExpressionMultiply, -420, -380)
    if albedo_node is not None:
        conns.append(LIB.connect_material_expressions(albedo_node, 'RGB', tint_mul, 'A'))
    else:
        flat = LIB.create_material_expression(material, u.MaterialExpressionConstant3Vector, -700, -700)
        flat.constant = u.LinearColor(*[float(c) for c in base_color])
        conns.append(LIB.connect_material_expressions(flat, '', tint_mul, 'A'))
    conns.append(LIB.connect_material_expressions(tint, '', tint_mul, 'B'))

    final_color = tint_mul
    ao_node = sample('ao', -60)
    if ao_node is not None:
        ao_mul = LIB.create_material_expression(material, u.MaterialExpressionMultiply, -240, -260)
        conns.append(LIB.connect_material_expressions(tint_mul, '', ao_mul, 'A'))
        conns.append(LIB.connect_material_expressions(ao_node, 'R', ao_mul, 'B'))
        final_color = ao_mul
    conns.append(LIB.connect_material_property(final_color, '', u.MaterialProperty.MP_BASE_COLOR))

    normal_node = sample('normal', 120)
    if normal_node is not None:
        conns.append(LIB.connect_material_property(normal_node, 'RGB', u.MaterialProperty.MP_NORMAL))

    rough_node = sample('roughness', 300)
    if rough_node is not None:
        conns.append(LIB.connect_material_property(rough_node, 'R', u.MaterialProperty.MP_ROUGHNESS))
    else:
        rough = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -700, 300)
        rough.set_editor_property('parameter_name', 'Roughness')
        rough.set_editor_property('default_value', float(consts.get('roughness', 0.7)))
        conns.append(LIB.connect_material_property(rough, '', u.MaterialProperty.MP_ROUGHNESS))

    metal_node = sample('metallic', 480) or sample('metallic_from_r', 480)
    if metal_node is not None:
        conns.append(LIB.connect_material_property(metal_node, 'R', u.MaterialProperty.MP_METALLIC))
    else:
        metal = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter, -700, 480)
        metal.set_editor_property('parameter_name', 'Metallic')
        metal.set_editor_property('default_value', float(consts.get('metallic', 0.0)))
        conns.append(LIB.connect_material_property(metal, '', u.MaterialProperty.MP_METALLIC))

    if blend == 'masked':
        # The opacity sample node must be created here: it is not one of the roles sampled
        # above, so looking it up in `nodes` alone never found it.
        mask_node = sample('opacity_mask_source', 660)
        if mask_node is not None:
            conns.append(LIB.connect_material_property(mask_node, 'R', u.MaterialProperty.MP_OPACITY_MASK))
        elif albedo_node is not None and 'basecolor_alpha' in maps:
            conns.append(LIB.connect_material_property(albedo_node, 'A', u.MaterialProperty.MP_OPACITY_MASK))
        else:
            raise RuntimeError('%s is masked but has no alpha source (maps=%s)' % (name, sorted(maps)))

    if not all(conns):
        raise RuntimeError('material wiring failed for %s: %s' % (name, conns))
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError('material compile errors for %s: %s' % (name, errors))
    if not E.save_loaded_asset(material, False):
        raise RuntimeError('material save failed: %s' % name)
    return material, reused


def build_instance(prop, mat_spec, material):
    name = 'MI_Prop_%s_%s' % (prop['name'], slot_tag(mat_spec['slot']))
    path = BASE + '/Materials/' + name
    mic = u.load_asset(path) or TOOLS.create_asset(name, BASE + '/Materials',
                                                   u.MaterialInstanceConstant,
                                                   u.MaterialInstanceConstantFactoryNew())
    if not isinstance(mic, u.MaterialInstanceConstant):
        raise RuntimeError('material instance create failed: %s' % name)
    LIB.set_material_instance_parent(mic, material)
    consts = mat_spec.get('constants') or {}
    if not (mat_spec.get('maps') or {}).get('roughness'):
        LIB.set_material_instance_scalar_parameter_value(mic, 'Roughness', float(consts.get('roughness', 0.7)))
    if not ((mat_spec.get('maps') or {}).get('metallic') or (mat_spec.get('maps') or {}).get('metallic_from_r')):
        LIB.set_material_instance_scalar_parameter_value(mic, 'Metallic', float(consts.get('metallic', 0.0)))
    base_color = consts.get('base_color') or [1.0, 1.0, 1.0, 1.0]
    LIB.set_material_instance_vector_parameter_value(mic, 'Tint', u.LinearColor(*[float(c) for c in base_color]))
    LIB.update_material_instance(mic)
    if not E.save_loaded_asset(mic, False):
        raise RuntimeError('material instance save failed: %s' % name)
    return mic


def mesh_stat(fn):
    try:
        return int(fn())
    except Exception as exc:  # noqa: BLE001
        return 'unavailable: %s' % exc


for prop in SPEC['props']:
    key = prop['key']
    prepared = PREP['props'].get(key)
    if not prepared:
        raise RuntimeError('no prepared data for %s' % key)

    tex_manifest = json.loads((ROOT / 'Receipts' / 'textures.json').read_text(encoding='utf-8-sig')).get(key, [])
    tex_by_role = {}
    for entry in tex_manifest:
        if entry.get('missing'):
            continue
        slot = 'All'
        for mat_spec in prop.get('materials', []):
            if mat_spec.get('slot') == '*':
                continue
            if slot_tag(mat_spec['slot']) in Path(entry['output']).name:
                slot = slot_tag(mat_spec['slot'])
        entry = dict(entry)
        entry['asset_name'] = Path(entry['output']).stem
        tex_by_role.setdefault(slot, {})
        # keep the first map per role for each slot
        role = entry['role']
        if role not in tex_by_role[slot] or slot == 'All':
            tex_by_role[slot][role] = entry

    for output in prepared['outputs']:
        mesh_name = output['mesh_name']
        fbx = Path(output['fbx'])
        mesh = import_mesh(fbx, mesh_name, key, output)
        imported_slots = [str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')]

        assigned = []
        for index, slot_name in enumerate(imported_slots):
            mat_spec = None
            for candidate in prop.get('materials', []):
                if candidate.get('slot') == '*':
                    mat_spec = candidate
                    break
                if slot_key(candidate['slot']) == slot_key(slot_name):
                    mat_spec = candidate
                    break
            if mat_spec is None:
                raise RuntimeError('%s: no spec for slot %r (have %s)'
                                   % (mesh_name, slot_name, [m.get('slot') for m in prop.get('materials', [])]))
            tag = slot_tag(mat_spec['slot'])
            tex_map = tex_by_role.get(tag) or tex_by_role.get('All') or {}
            material, reused = build_material(prop, mat_spec, tex_map)
            mic = build_instance(prop, mat_spec, material)
            mesh.set_material(index, mic)
            assigned.append({'slot': slot_name, 'material_instance': mic.get_path_name().split('.')[0],
                             'material_reused': reused})

        nanite = mesh.get_editor_property('nanite_settings')
        nanite.enabled = False
        mesh.set_editor_property('nanite_settings', nanite)
        if prop.get('collision') == 'none':
            mesh.get_editor_property('body_setup').set_editor_property(
                'collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        else:
            mesh.get_editor_property('body_setup').set_editor_property(
                'collision_trace_flag', u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        if not E.save_loaded_asset(mesh, False):
            raise RuntimeError('mesh save failed: %s' % mesh_name)

        bounds = mesh.get_bounds()
        receipt['meshes'][mesh_name] = {
            'path': BASE + '/Meshes/' + mesh_name,
            'prop': key, 'slots': assigned,
            'size_cm': [round(float(bounds.box_extent.x) * 2, 2), round(float(bounds.box_extent.y) * 2, 2),
                        round(float(bounds.box_extent.z) * 2, 2)],
            'origin_cm': [round(float(bounds.origin.x), 2), round(float(bounds.origin.y), 2),
                          round(float(bounds.origin.z), 2)],
            'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
            'collision': prop.get('collision'),
            'source_tris': output['tris'],
        }
        receipt['stage'] = 'partial'
        write_receipt()
        print('PROP_IMPORT', mesh_name, json.dumps(receipt['meshes'][mesh_name], default=str))

receipt['stage'] = 'assets_saved'
write_receipt()
u.log('ART_PASS_IMPORT ' + json.dumps({'meshes': len(receipt['meshes']), 'stage': receipt['stage']}))
print('ART_PASS_IMPORT_DONE', receipt['stage'], len(receipt['meshes']))
