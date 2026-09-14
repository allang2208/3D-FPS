"""Re-author metal PBR on the accepted 715 UV0, without changing its rig or mesh.

Texture baking is asset production. This entry does not render a preview or run
gameplay checks. The latest accepted left-recovery actions remain in the source.
"""
import ast
import json
from pathlib import Path

import bpy
from mathutils import Matrix

O = Path(__file__).parent
T = O / 'Textures'
T.mkdir(exist_ok=True)
SOURCE = O.parent / 'DanWesson715LeftRecovery20260914/DanWesson715_LeftRecovery_Editable.blend'
PRIOR = O.parent / 'DanWesson715Upgrade20260914'
bpy.context.preferences.filepaths.save_version = 0
try:
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):
        raise

s = bpy.context.scene
rig = bpy.data.objects['SK_DW715_Manny']
inverse_bind = rig.data.bones['WPN_root'].matrix_local.inverted()
source_base = bpy.data.images.load(str(O.parent / 'DanWesson71520260913/Textures/T_DW715_BaseColor.png'), check_existing=True)
source_base.colorspace_settings.name = 'sRGB'
source_normal = bpy.data.images.load(str(O.parent / 'DanWesson71520260913/Textures/T_DW715_Normal.png'), check_existing=True)
source_normal.colorspace_settings.name = 'Non-Color'
prior = json.loads((PRIOR / 'textures.json').read_text())

# Linear reflectance, roughness, object-space grain frequency (cycles/metre).
# Cylinder and cases use axial variation to describe circumferential machining.
FINISH = {
    'Frame': dict(base=(.49, .515, .54), rough=.285, grain=(1800, 55, 1800), normal=.46, depth=.0000010),
    'Cylinder': dict(base=(.53, .545, .56), rough=.225, grain=(65, 2200, 65), normal=0, depth=.0000008),
    'Steel': dict(base=(.45, .47, .49), rough=.245, grain=(1600, 70, 1600), normal=.46, depth=.0000010),
    'Ammo': dict(base=(.56, .345, .115), rough=.255, grain=(90, 1900, 90), normal=0, depth=.0000008),
}

def activate(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[-1]

def author_material(group, engraved=False):
    cfg = FINISH[group]
    m = bpy.data.materials.new('AUTH_DW715_Finish_' + group + ('_Engraving' if engraved else ''))
    m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    n.clear()
    out = n.new('ShaderNodeOutputMaterial')
    bs = n.new('ShaderNodeBsdfPrincipled')
    l.new(bs.outputs[0], out.inputs['Surface'])
    co = n.new('ShaderNodeTexCoord')

    def op(kind, a, b=0):
        node = n.new('ShaderNodeMath')
        node.operation = kind
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                node.inputs[i].default_value = v
            else:
                l.new(v, node.inputs[i])
        return node.outputs[0]

    def noise(scale):
        stretch = n.new('ShaderNodeVectorMath')
        stretch.operation = 'MULTIPLY'
        l.new(co.outputs['Object'], stretch.inputs[0])
        stretch.inputs[1].default_value = scale
        tex = n.new('ShaderNodeTexNoise')
        tex.inputs['Scale'].default_value = 1
        tex.inputs['Detail'].default_value = 1
        tex.inputs['Roughness'].default_value = .4
        l.new(stretch.outputs['Vector'], tex.inputs['Vector'])
        return tex.outputs['Fac']

    grain = noise(cfg['grain'])
    cloud = noise((42, 42, 42))
    base_ramp = n.new('ShaderNodeValToRGB')
    base_ramp.color_ramp.elements[0].color = (*(x * .992 for x in cfg['base']), 1)
    base_ramp.color_ramp.elements[1].color = (*(x * 1.008 for x in cfg['base']), 1)
    l.new(cloud, base_ramp.inputs[0])
    base = base_ramp.outputs[0]
    rough = op('ADD', cfg['rough'], op('MULTIPLY', op('SUBTRACT', grain, .5), .018))
    rough = op('ADD', rough, op('MULTIPLY', op('SUBTRACT', cloud, .5), .012))

    # A small contact polish on true convex edges, not a painted white rim.
    geometry = n.new('ShaderNodeNewGeometry')
    edge = op('MINIMUM', op('MAXIMUM', op('MULTIPLY', op('SUBTRACT', geometry.outputs['Pointiness'], .505), 18), 0), 1)
    rough = op('SUBTRACT', rough, op('MULTIPLY', edge, .035))
    bump = n.new('ShaderNodeBump')
    bump.inputs['Distance'].default_value = cfg['depth']
    bump.inputs['Strength'].default_value = .12
    l.new(grain, bump.inputs['Height'])
    if engraved:
        uv = n.new('ShaderNodeUVMap')
        uv.uv_map = 'SourceUV'
        original = n.new('ShaderNodeTexImage')
        original.image = source_base
        l.new(uv.outputs[0], original.inputs['Vector'])
        lum = n.new('ShaderNodeRGBToBW')
        l.new(original.outputs['Color'], lum.inputs[0])
        remap = n.new('ShaderNodeMapRange')
        remap.inputs['From Min'].default_value = .018
        remap.inputs['From Max'].default_value = .20
        remap.inputs['To Min'].default_value = .11
        remap.inputs['To Max'].default_value = 1
        remap.clamp = True
        l.new(lum.outputs[0], remap.inputs['Value'])
        # Retain restrained marking contrast without rebaking the old shadows
        # into most of the metal reflectance (previous blend was 0.86).
        tint = n.new('ShaderNodeMixRGB')
        tint.blend_type = 'MULTIPLY'
        tint.inputs[0].default_value = .22
        l.new(base, tint.inputs[1])
        l.new(remap.outputs[0], tint.inputs[2])
        base = tint.outputs[0]
        tex = n.new('ShaderNodeTexImage')
        tex.image = source_normal
        l.new(uv.outputs[0], tex.inputs['Vector'])
        nm = n.new('ShaderNodeNormalMap')
        nm.uv_map = 'SourceUV'
        nm.inputs['Strength'].default_value = cfg['normal']
        l.new(tex.outputs['Color'], nm.inputs['Color'])
        l.new(nm.outputs[0], bump.inputs['Normal'])
    l.new(base, bs.inputs['Base Color'])
    l.new(rough, bs.inputs['Roughness'])
    bs.inputs['Metallic'].default_value = 1
    l.new(bump.outputs[0], bs.inputs['Normal'])
    ao = n.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value = .0018
    ao.samples = 16
    ao.only_local = True
    # AO stays a separate, restrained cavity term instead of dirty albedo.
    orm = n.new('ShaderNodeCombineColor')
    l.new(op('ADD', .35, op('MULTIPLY', ao.outputs['AO'], .65)), orm.inputs[0])
    l.new(rough, orm.inputs[1])
    orm.inputs[2].default_value = 1
    m['base_node'], m['base_socket'], m['orm_node'] = base.node.name, base.name, orm.name
    m['physical_grain_frequency'] = cfg['grain']
    return m

materials = {(group, engraved): author_material(group, engraved) for group in FINISH for engraved in (False, True)}
tree = ast.parse((O.parent / 'M1911Hero20260913/build.py').read_text())
exec(compile(ast.Module(body=[x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'emit'], type_ignores=[]), 'existing_bake_routing', 'exec'))

def bake_copy(objects, label, high):
    copies = []
    for ob in objects:
        ob.hide_set(False)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg) if high else ob.data.copy()
        if not high:
            me.transform(inverse_bind)
            me.update()
        x = bpy.data.objects.new(label + '_part', me)
        s.collection.objects.link(x)
        copies.append(x)
    activate(copies)
    bpy.ops.object.join()
    result = bpy.context.object
    result.name = label
    return result

s.render.engine = 'CYCLES'
s.cycles.samples = 16
s.cycles.use_denoising = False
s.render.bake.margin = 16
s.render.bake.use_selected_to_active = True
s.render.bake.use_clear = False
s.render.bake.cage_extrusion = .00065
s.render.bake.max_ray_distance = .002
s.render.bake.normal_space = 'TANGENT'
s.render.bake.normal_r, s.render.bake.normal_g, s.render.bake.normal_b = 'POS_X', 'POS_Y', 'POS_Z'
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'
prefs.get_devices()
for device in prefs.devices:
    device.use = device.type == 'OPTIX'
s.cycles.device = 'GPU' if any(d.use for d in prefs.devices) else 'CPU'
visibility = {ob: (ob.hide_render, ob.hide_get()) for ob in s.objects}
for ob in s.objects:
    if ob.type == 'MESH':
        ob.hide_render = True

manifest = {}
for group, cfg in FINISH.items():
    info = prior[group]
    lows = [bpy.data.objects[name] for name in info['objects']]
    highs = [bpy.data.objects[name + '_HIGH'] for name in info['objects']]
    for high in highs:
        for index, old in enumerate(high.data.materials):
            if 'DarkInterior' in old.name:
                continue
            high.data.materials[index] = materials[group, 'SourceEngraving' in old.name]
    bl = bake_copy(lows, 'TEMP_FINISH_LOW', False)
    bh = bake_copy(highs, 'TEMP_FINISH_HIGH', True)
    for high in highs:
        high.hide_set(True)
    bl.data.uv_layers.active = bl.data.uv_layers['HeroUV']
    bl.data.uv_layers.active.active_render = True
    target = bpy.data.materials.new('BAKE_FINISH_TARGET_' + group)
    target.use_nodes = True
    bl.data.materials.clear()
    bl.data.materials.append(target)
    for poly in bl.data.polygons:
        poly.material_index = 0
    maps = {}
    for kind in ('BaseColor', 'ORM', 'Normal'):
        suffix = 'NormalGL' if kind == 'Normal' else kind
        im = bpy.data.images.new('T_DW715_Finish_' + group + '_' + suffix, width=info['size'], height=info['size'], alpha=False)
        im.colorspace_settings.name = 'sRGB' if kind == 'BaseColor' else 'Non-Color'
        im.generated_color = (.5, .5, 1, 1) if kind == 'Normal' else (1, cfg['rough'], 1, 1) if kind == 'ORM' else (*cfg['base'], 1)
        nodes = target.node_tree.nodes
        tex = nodes.get('BAKE_TARGET') or nodes.new('ShaderNodeTexImage')
        tex.name, tex.image = 'BAKE_TARGET', im
        nodes.active = tex
        emit(bh, kind)
        bl.hide_render, bh.hide_render = False, False
        activate([bh, bl])
        bpy.ops.object.bake(type='NORMAL' if kind == 'Normal' else 'EMIT')
        bl.hide_render, bh.hide_render = True, True
        im.filepath_raw = str(T / (im.name + '.png'))
        im.file_format = 'PNG'
        im.save()
        maps[kind] = im
        print('DW715_FINISH_BAKED', group, kind, flush=True)
    emit(bh, 'Normal')
    bpy.data.objects.remove(bl, do_unlink=True)
    bpy.data.objects.remove(bh, do_unlink=True)
    # Preserve material slot identity for future exports of the accepted source.
    existing = bpy.data.materials.get(info['material'])
    if existing:
        existing.name = info['material'] + '_PreviousFinish'
    m = bpy.data.materials.new(info['material'])
    m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    bs = next(x for x in n if x.type == 'BSDF_PRINCIPLED')
    uv = n.new('ShaderNodeUVMap')
    uv.uv_map = 'HeroUV'
    for kind, im in maps.items():
        tex = n.new('ShaderNodeTexImage')
        tex.image = im
        l.new(uv.outputs[0], tex.inputs['Vector'])
        if kind == 'BaseColor':
            l.new(tex.outputs[0], bs.inputs['Base Color'])
        elif kind == 'Normal':
            nm = n.new('ShaderNodeNormalMap')
            nm.uv_map = 'HeroUV'
            l.new(tex.outputs[0], nm.inputs['Color'])
            l.new(nm.outputs[0], bs.inputs['Normal'])
        else:
            sep = n.new('ShaderNodeSeparateColor')
            l.new(tex.outputs[0], sep.inputs[0])
            l.new(sep.outputs[1], bs.inputs['Roughness'])
            l.new(sep.outputs[2], bs.inputs['Metallic'])
    for lo in lows:
        lo.data.materials[0] = m
    manifest[group] = dict(size=info['size'], slot=info['material'], material='M_DW715_Finish_' + group,
                           textures={k: im.filepath_raw for k, im in maps.items()}, objects=info['objects'], finish=cfg)
    (O / 'textures.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

for ob, (render, hidden) in visibility.items():
    ob.hide_render = render
    ob.hide_set(hidden)
for material in materials.values():
    material.use_fake_user = True
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'DanWesson715_MetalFinish_Editable.blend'))
print('DW715_METAL_FINISH_SOURCE_COMPLETE', flush=True)
