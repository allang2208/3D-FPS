"""Assemble selected original supplement assets into the final editable source.

Run after author_scene, assemble_reused_assets and apply_source_surfaces.
Imports chosen original FBX once, bakes each imported world/node matrix once,
preserves all source UV/color attributes and material slots, and instances
unchanged meshes at config actor coordinates. No renders, exports or tests.
"""
import hashlib
import json
import math
import re
from pathlib import Path
import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / 'References/RevisionSupplement'
OUT = ROOT / 'Authored'
STAGE = 'revision_supplement'
HAND = json.loads((BUNDLE/'HANDOFF.json').read_text('utf8'))
META = json.loads((BUNDLE/'MATERIALS.json').read_text('utf8'))
CFG = json.loads((ROOT/'Config/scene.json').read_text('utf8'))
ASSETS = {a['name']: a for a in HAND['assets']}
SOURCE = OUT / 'FailedPowerCenter_ThreeRooms_Source.blend'
PLACEMENTS = [(r, p) for r in CFG['rooms']+CFG['connectors']
              for p in r.get('reused_parts', []) if p.get('reuse_stage') == STAGE]
SELECTED = list(dict.fromkeys(p['source_asset_id'] for r, p in PLACEMENTS))
if not SELECTED:
    raise RuntimeError('Run coordinated place_revision_supplement.py before source assembly.')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
# Remove only this script's owned instances/masters; never touch source files
# or unrelated original assets/materials. This also permits an idempotent rerun.
for obj in list(bpy.data.objects):
    if obj.get('revision_supplement_owned'):
        bpy.data.objects.remove(obj, do_unlink=True)
for name in ('Revision_Supplement_Original_Masters', 'Revision_Supplement_Existing_Instances'):
    col = bpy.data.collections.get(name)
    if col:
        bpy.data.collections.remove(col)
masters = bpy.data.collections.new('Revision_Supplement_Original_Masters')
instances = bpy.data.collections.new('Revision_Supplement_Existing_Instances')
bpy.context.scene.collection.children.link(masters)
bpy.context.scene.collection.children.link(instances)
materials_by_ue = {m.get('ue_material_path'): m for m in bpy.data.materials if m.get('ue_material_path')}
material_receipt = []
missing = []


def file_for(record):
    """Resolve exact deduplicated delivery paths; never substitute a lookalike."""
    candidates = []
    if record.get('package_path'):
        candidates.append(BUNDLE / record['package_path'])
    ref = record.get('reference', {})
    if ref.get('path'):
        candidates.extend(ROOT/'References'/name/ref['path'] for name in ('ReuseBundle', 'Supplement', 'RevisionSupplement'))
    for p in candidates:
        if p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == record['sha256']:
            return p
    missing.append(record['source_relative_path'])
    return None


texture_files = {r['source_relative_path']: file_for(r) for r in META['texture_files']}


def texpath(ending):
    for source, path in texture_files.items():
        if source.endswith(ending):
            return path
    return None


def new_node(m, kind):
    return m.node_tree.nodes.new(kind)


def math_node(m, op, a, b=0):
    n = new_node(m, 'ShaderNodeMath'); n.operation = op
    for index, value in enumerate((a, b)):
        if isinstance(value, (int, float)):
            n.inputs[index].default_value = value
        else:
            m.node_tree.links.new(value, n.inputs[index])
    return n.outputs[0]


def texture(m, path, noncolor=False, uv=None):
    if path is None:
        return None
    image = bpy.data.images.load(str(path), check_existing=True)
    if noncolor:
        image.colorspace_settings.name = 'Non-Color'
    n = new_node(m, 'ShaderNodeTexImage'); n.image = image
    if uv:
        m.node_tree.links.new(uv, n.inputs['Vector'])
    return n


def uv_node(m, name):
    n = new_node(m, 'ShaderNodeUVMap'); n.uv_map = name
    return n.outputs['UV']


def bsdf_reset(m):
    m.use_nodes = True
    m.node_tree.nodes.clear()
    bs = new_node(m, 'ShaderNodeBsdfPrincipled')
    out = new_node(m, 'ShaderNodeOutputMaterial')
    m.node_tree.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    return bs


def normal_map(m, bs, path, strength=1.0, directx=False):
    n = texture(m, path, True)
    if not n:
        return
    color = n.outputs['Color']
    if directx:
        split = new_node(m, 'ShaderNodeSeparateColor')
        combine = new_node(m, 'ShaderNodeCombineColor')
        m.node_tree.links.new(color, split.inputs['Color'])
        m.node_tree.links.new(split.outputs['Red'], combine.inputs['Red'])
        m.node_tree.links.new(math_node(m, 'SUBTRACT', 1, split.outputs['Green']), combine.inputs['Green'])
        m.node_tree.links.new(split.outputs['Blue'], combine.inputs['Blue'])
        color = combine.outputs['Color']
    normal = new_node(m, 'ShaderNodeNormalMap')
    normal.inputs['Strength'].default_value = strength
    m.node_tree.links.new(color, normal.inputs['Color'])
    m.node_tree.links.new(normal.outputs['Normal'], bs.inputs['Normal'])


def multiply_color(m, a, b):
    n = new_node(m, 'ShaderNodeMixRGB'); n.blend_type = 'MULTIPLY'; n.inputs[0].default_value = 1
    for idx, value in ((1, a), (2, b)):
        if isinstance(value, (tuple, list)):
            n.inputs[idx].default_value = tuple(value) if len(value) == 4 else (*value, 1)
        else:
            m.node_tree.links.new(value, n.inputs[idx])
    return n.outputs['Color']


def configure_material(m, path):
    """Exact supplied maps/constants where available; engine graph remains authoritative."""
    bs = bsdf_reset(m); links = m.node_tree.links
    caveats = []
    color, rough, metal = (.18, .22, .19), .64, .10
    if 'MI_WBK_WSBench_BenchWood_R3' in path:
        recipe = META['wood_source_recipe']; variant = META['wood_variants']['Abandoned']
        uv0 = uv_node(m, 'UVMap')
        base = texture(m, texpath('BenchWood_BaseColor.jpg'), uv=uv0)
        rough_map = texture(m, texpath('BenchWood_Roughness.jpg'), True, uv0)
        base_out = multiply_color(m, base.outputs['Color'], recipe['color_tint']) if base else None
        # Retain the source vertex-age input. Exact original contact-field and
        # imperfection sampling are recorded, rather than invented as geometry.
        vc = new_node(m, 'ShaderNodeVertexColor'); vc.layer_name = 'ServiceAge'
        if base_out:
            base_out = multiply_color(m, base_out, vc.outputs['Color'])
            base_out = multiply_color(m, base_out, variant['surface_tint'])
        geometry = new_node(m, 'ShaderNodeNewGeometry')
        sep = new_node(m, 'ShaderNodeSeparateXYZ'); links.new(geometry.outputs['Normal'], sep.inputs[0])
        up = math_node(m, 'MAXIMUM', 0, sep.outputs['Z'])
        dust = math_node(m, 'MULTIPLY', variant['dust'], math_node(m, 'ADD', .25, math_node(m, 'MULTIPLY', .75, up)))
        if base_out:
            blend = new_node(m, 'ShaderNodeMixRGB'); links.new(dust, blend.inputs[0]); links.new(base_out, blend.inputs[1])
            blend.inputs[2].default_value = (.14, .125, .105, 1)
            links.new(blend.outputs['Color'], bs.inputs['Base Color'])
        if rough_map:
            r = math_node(m, 'ADD', math_node(m, 'MULTIPLY', rough_map.outputs['Color'], recipe['roughness_scale']), recipe['roughness_bias'])
            r = math_node(m, 'MINIMUM', .94, math_node(m, 'MAXIMUM', .27, r))
            r = math_node(m, 'ADD', r, variant['roughness_bias'])
            r = math_node(m, 'ADD', math_node(m, 'MULTIPLY', r, math_node(m, 'SUBTRACT', 1, dust)), math_node(m, 'MULTIPLY', .88, dust))
            links.new(math_node(m, 'MINIMUM', .96, math_node(m, 'MAXIMUM', .2, r)), bs.inputs['Roughness'])
        normal_map(m, bs, texpath('BenchWood_Normal.jpg'), recipe['normal_strength'])
        # Attach the supplied original mask with its actual secondary UV scale
        # as reference. The analytic oil/hand-use graph is not approximated.
        mask = texpath('MetalImperfection_MaskR_RoughnessG.png')
        if mask:
            detail = uv_node(m, 'DetailLocal'); scale = new_node(m, 'ShaderNodeVectorMath'); scale.operation = 'MULTIPLY'
            scale.inputs[1].default_value = (2.1, 1.7, 1); links.new(detail, scale.inputs[0])
            n = texture(m, mask, True, scale.outputs[0]); n.label = 'Original UE worktop contact mask; reference input'
        bs.inputs['Specular IOR Level'].default_value = .28
        color, rough, metal = (.24, .17, .095), .78, recipe['metallic']
        caveats.append('Original base/normal/roughness, vertex color, tint and abandoned dust settings attached. Full UE analytic oil/hand-use contact fields remain UE-only; original DetailLocal mask is retained as a reference input, never synthesized.')
    elif path.endswith('M_ArchiveEquipment_Atlas'):
        base = texture(m, texpath('Equipment20260930/Authored/Textures/T_ArchiveEquipment_BaseColor.png'))
        if base:
            links.new(base.outputs['Color'], bs.inputs['Base Color'])
        orm = texture(m, texpath('T_ArchiveEquipment_ORM.png'), True)
        if orm:
            separate = new_node(m, 'ShaderNodeSeparateColor'); links.new(orm.outputs['Color'], separate.inputs['Color'])
            links.new(separate.outputs['Green'], bs.inputs['Roughness']); links.new(separate.outputs['Blue'], bs.inputs['Metallic'])
            if base:
                links.new(multiply_color(m, base.outputs['Color'], separate.outputs['Red']), bs.inputs['Base Color'])
        gl = texpath('T_ArchiveEquipment_NormalGL.png')
        normal_map(m, bs, gl or texpath('T_ArchiveEquipment_NormalDX.png'), directx=not bool(gl))
        color, rough, metal = (.3, .3, .3), .5, .1
    elif path.endswith('MI_Prop_StepLadder_All'):
        base = texture(m, texpath('T_Prop_StepLadder_All_basecolor.png'))
        ao = texture(m, texpath('T_Prop_StepLadder_All_ao.png'), True)
        if base:
            output = multiply_color(m, base.outputs['Color'], ao.outputs['Color']) if ao else base.outputs['Color']
            links.new(output, bs.inputs['Base Color'])
        color, rough, metal = (.8, .8, .8), .5, 0
        caveats.append('Original delivered basecolor/AO and source roughness .5; no normal/roughness map invented.')
    elif path.endswith(('M_Workshop_Print', 'M_Workshop_Screen', 'M_Office_Legends')):
        legends = path.endswith('M_Office_Legends')
        image = texture(m, texpath('T_Office_KeyLegends.png' if legends else 'T_Workshop_PrintAtlas.png'))
        if image:
            links.new(image.outputs['Color'], bs.inputs['Base Color'])
        rough, metal = (.52 if legends else .29 if path.endswith('Screen') else .86), 0
        if path.endswith('Screen') and image:
            links.new(image.outputs['Color'], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = .3
        if legends:
            bs.inputs['Specular IOR Level'].default_value = .22
    else:
        spec = None
        if path.endswith('M_Staff_Stainless_V6'):
            spec = META['steel']
        elif path.endswith('M_Staff_KettleRubber_V6'):
            spec = META['rubber']
        elif path.endswith('M_Warehouse_ToolPaint'):
            spec = META['paint']
        if spec:
            color, rough, metal = spec['base_color'], spec['roughness'], spec['metallic']
            caveats.append('Exact source constants; derivative-faded Unreal procedural grain/wear remains engine-only.')
        elif path.endswith('M_Workshop_OfficePlastic'):
            color, rough, metal = (.095, .105, .11), .49, 0
            caveats.append('Exact source constants; derivative-faded Unreal procedural grain remains engine-only.')
        elif path.endswith('M_Workshop_Copper'):
            color, rough, metal = (.48, .19, .065), .32, .86
            caveats.append('Exact source constants; derivative-faded Unreal procedural grain remains engine-only.')
        elif path.endswith('M_Workshop_Lamp'):
            color, rough, metal = (.5, .58, .58), .43, 0
            bs.inputs['Emission Color'].default_value = (1.1, 1.25, 1.3, 1); bs.inputs['Emission Strength'].default_value = 1
        elif path.endswith('M_Office_Keycaps'):
            color, rough, metal = (.0176, .0176, .0176), .52, 0
            bs.inputs['Specular IOR Level'].default_value = .22
        elif path.endswith('M_Office_Display'):
            color, rough, metal = (.02, .06, .05), .52, 0
            bs.inputs['Emission Color'].default_value = (*color, 1); bs.inputs['Emission Strength'].default_value = 1
            bs.inputs['Specular IOR Level'].default_value = .22
        else:
            caveats.append('Source raw shader unavailable; explicitly partial Blender preview. Original UE material path remains unchanged.')
    # Defaults only matter when the corresponding original texture is absent.
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    m.diffuse_color = (*color, 1)
    m['source_preview_only'] = True
    m['revision_supplement_preview_configured'] = True
    m['ue_material_path'] = path
    m['source_shader_recipe'] = 'References/RevisionSupplement/EXACT_SOURCE_RECIPES.txt'
    m['missing_preview_features'] = ' '.join(caveats)
    if 'preview_approximation' in m:
        del m['preview_approximation']
    material_receipt.append(dict(ue_material=path, caveats=caveats))


def preview_material(path, slot):
    key = path.split('.')[0]
    m = materials_by_ue.get(key)
    if m is None:
        m = bpy.data.materials.new('REF_Revision_' + slot)
        materials_by_ue[key] = m
    if not m.get('revision_supplement_preview_configured'):
        configure_material(m, key)
    return m


lookup, imported = {}, []
for name in SELECTED:
    source = ASSETS[name]
    fbx = BUNDLE / source['package_fbx']
    if hashlib.sha256(fbx.read_bytes()).hexdigest() != source['fbx_sha256']:
        raise RuntimeError('Original source fingerprint changed: ' + name)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(fbx), use_custom_normals=True, use_image_search=False)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == 'MESH']
    visuals = [o for o in meshes if not o.name.startswith(('UCX_', 'UBX_', 'USP_', 'UCP_'))]
    if len(visuals) != 1:
        raise RuntimeError('Expected one original render mesh: ' + name)
    visual = visuals[0]
    # Snapshot all node/world matrices before removing imported parenting.
    matrices = {o: o.matrix_world.copy() for o in meshes}
    for obj in meshes:
        obj.data.transform(matrices[obj])
        obj.parent = None
        obj.matrix_world = Matrix.Identity(4)
        obj.data.update()
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        masters.objects.link(obj)
        obj['revision_supplement_owned'] = True
        obj['owner_source_asset'] = name
        obj.hide_render = True
        obj.hide_viewport = True
    for obj in new:
        if obj.type != 'MESH':
            bpy.data.objects.remove(obj, do_unlink=True)
    visual.name = name
    visual['ue_asset'] = source['ue']
    visual['source_fbx'] = source['package_fbx']
    visual['source_sha256'] = source['fbx_sha256']
    visual['approved_existing_asset'] = True
    visual['source_material_map'] = json.dumps(source['materials'])
    original_slots = [m.name if m else None for m in visual.data.materials]
    for index, mat in enumerate(visual.data.materials):
        slot = re.sub(r'\.\d{3}$', '', mat.name) if mat else ''
        path = source['materials'].get(slot)
        if not path:
            raise RuntimeError('Missing original slot mapping: ' + name + ':' + slot)
        visual.data.materials[index] = preview_material(path, slot)
    points = [v.co for v in visual.data.vertices]
    bounds = {label: [fn(p[k] for p in points) for k in range(3)]
              for label, fn in [('min', min), ('max', max)]}
    imported.append(dict(name=name, ue_asset=source['ue'], source_sha256=source['fbx_sha256'],
        imported_world_matrix_baked_once=[list(r) for r in matrices[visual]],
        source_geometry_bounds_blender_m=bounds, original_material_slots=original_slots,
        uv_layers=[u.name for u in visual.data.uv_layers],
        color_attributes=[a.name for a in visual.data.color_attributes],
        vertices=len(visual.data.vertices), triangles=sum(len(p.vertices)-2 for p in visual.data.polygons),
        collision_mesh_count=len(meshes)-1))
    lookup[name] = visual
    print('REVISION_ORIGINAL_IMPORTED', name, json.dumps(bounds), flush=True)

placed = []
for room, p in PLACEMENTS:
    source = lookup[p['source_asset_id']]
    obj = source.copy(); obj.data = source.data
    obj.name = room['id'] + '_' + p['id']
    instances.objects.link(obj)
    if p.get('materials'):
        obj.data = obj.data.copy()
        for index, path in enumerate(p['materials']):
            key = path.split('.')[0]
            if key not in materials_by_ue:
                raise RuntimeError('Missing declared theme-only material override: '+key)
            obj.data.materials[index] = materials_by_ue[key]
    obj.hide_render = False; obj.hide_viewport = False
    obj.location = [room['origin_m'][k] + p['position_m'][k] for k in range(3)]
    obj.rotation_euler = (0, 0, math.radians(p.get('yaw_deg', 0)))
    obj.scale = (1, 1, 1)
    obj['room_id'] = room['id']; obj['ue_asset_reference'] = p['mesh']
    obj['reuse_method'] = 'Unscaled original source; FBX node/world matrix applied exactly once'
    obj['source_assembly_id'] = p.get('source_assembly_id', '')
    obj['source_anchor_blender_m'] = p['source_anchor_blender_m']
    obj['target_anchor_m'] = p['target_anchor_m']
    # Compute directly from the intended rigid transform, independent of the
    # deferred dependency graph. This is production provenance, not scene QA.
    yaw = math.radians(p.get('yaw_deg', 0)); c, s = math.cos(yaw), math.sin(yaw)
    points = [(p['position_m'][0] + c*v.co.x - s*v.co.y,
               p['position_m'][1] + s*v.co.x + c*v.co.y,
               p['position_m'][2] + v.co.z) for v in obj.data.vertices]
    bounds = {label: [fn(q[k] for q in points) for k in range(3)]
              for label, fn in [('min', min), ('max', max)]}
    placed.append(dict(id=p['id'], room=room['id'], mesh=p['mesh'],
        source_asset_id=p['source_asset_id'], source_sha256=source['source_sha256'],
        target_anchor_m=p['target_anchor_m'], actor_position_m=p['position_m'],
        position_world_m=list(obj.location), yaw_blender_deg=p.get('yaw_deg', 0),
        placed_geometry_bounds_room_m=bounds))
for image in bpy.data.images:
    if image.source == 'FILE' and image.has_data:
        image.pack()
scene = bpy.context.scene
scene['revision_supplement_integrated'] = True
scene['revision_supplement_preview_caveat'] = 'Supplied original textures/settings used; full UE-only shader features explicitly listed in revision-supplement receipt. Original UE paths and source files unchanged.'
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE))
previous_path = ROOT/'Receipts/revision-supplement.json'
previous = json.loads(previous_path.read_text('utf8')) if previous_path.is_file() else {}
receipt = dict(stage='revision_supplement_original_geometry_assembled',
    blender_version=bpy.app.version_string, source='References/RevisionSupplement/HANDOFF.json',
    selected_unique_original_meshes=len(lookup), original_mesh_instances=len(placed),
    imported_originals=imported, placements=placed,
    conservative_config_placements=previous.get('placements', []) if previous.get('stage') == 'placement_configured_pending_author_assembly' else previous.get('conservative_config_placements', []),
    material_previews=material_receipt, missing_delivered_texture_paths=missing,
    original_files_modified=False, originals_reexported=False, ue_materials_modified=False,
    tests_run=False, rendered=False, screenshots_taken=False, ue_imported=False,
    omitted_assets=next(r for r in CFG['rooms'] if r['id']=='AccumulatorControl')['revision_supplement']['omitted_assets'])
previous_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n', 'utf8')
print('REVISION_SUPPLEMENT_ASSEMBLED', len(placed), 'instances from', len(lookup), 'unchanged source meshes', flush=True)
