"""Rebake three Kukri grip finishes without changing geometry, UVs or runtime IDs."""
import bpy, json, math, sys
from pathlib import Path
P = Path(__file__).resolve().parent
SOURCE = P.parent / 'KukriComponentVariants20261026'
sys.path.insert(0, str(SOURCE))
from asset_tools import node, put, op, mix, tex, make_mat, activate, bake

for folder in ('Textures', 'IconInputs', 'Icons', 'Before', 'Receipts'):
    (P / folder).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE / 'Kukri_Components_Editable.blend'))
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
prefs = bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = device.type == 'OPTIX'
    if any(d.use for d in prefs.devices):
        scene.cycles.device = 'GPU'
except Exception:
    scene.cycles.device = 'CPU'
BASE = P.parent / 'Kukri20261020/Textures'

def scale_vector(nt, coord, scale):
    v = node(nt, 'ShaderNodeVectorMath', operation='MULTIPLY')
    put(nt, v.inputs[0], coord)
    v.inputs[1].default_value = scale
    return v.outputs[0]

def noise(nt, coord, scale, detail=2):
    n = node(nt, 'ShaderNodeTexNoise')
    put(nt, n.inputs['Vector'], coord)
    n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    n.inputs['Roughness'].default_value = .65
    return n.outputs['Fac']

def clamp(nt, value, low=0., high=1.):
    return op(nt, 'MINIMUM', op(nt, 'MAXIMUM', value, low), high)

def ramp(nt, value, low, high):
    t = clamp(nt, op(nt, 'DIVIDE', op(nt, 'SUBTRACT', value, low), high-low))
    return op(nt, 'MULTIPLY', op(nt, 'MULTIPLY', t, t), op(nt, 'SUBTRACT', 3, op(nt, 'MULTIPLY', t, 2)))

def author_material(kind):
    m, nt, bs, out = make_mat('Author_GripSurfaceV2_' + kind)
    tc = node(nt, 'ShaderNodeTexCoord')
    xyz = node(nt, 'ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], xyz.inputs[0])
    x, y, z = xyz.outputs
    coord = tc.outputs['Object']
    original = tex(nt, BASE / 'T_Kukri_BaseColor.png', True, 'SourceUV')
    old_orm = tex(nt, BASE / 'T_Kukri_ORM.png', False, 'SourceUV')
    old = node(nt, 'ShaderNodeSeparateColor')
    nt.links.new(old_orm.outputs[0], old.inputs[0])
    # The whole non-metal grip is replaced. The previous Z falloff exposed wood
    # under rubber/leather at both ends; actual metal rivets remain source metal.
    region = op(nt, 'SUBTRACT', 1, ramp(nt, old.outputs[2], .35, .65))
    broad = noise(nt, coord, 90, 2)
    fine = noise(nt, coord, 3000, 3)
    if kind == 'GripCheckered':
        a = op(nt, 'ABSOLUTE', op(nt, 'SINE', op(nt, 'MULTIPLY', op(nt, 'ADD', x, z), 800)))
        b = op(nt, 'ABSOLUTE', op(nt, 'SINE', op(nt, 'MULTIPLY', op(nt, 'SUBTRACT', x, z), 800)))
        cell = op(nt, 'POWER', op(nt, 'MULTIPLY', a, b), .48)
        plateau = ramp(nt, cell, .10, .85)
        tone = op(nt, 'ADD', op(nt, 'MULTIPLY', plateau, .72), op(nt, 'MULTIPLY', broad, .28))
        color = mix(nt, tone, (.009, .012, .013, 1), (.027, .032, .034, 1))
        rough = op(nt, 'ADD', .43, op(nt, 'ADD', op(nt, 'MULTIPLY', op(nt, 'SUBTRACT', 1, plateau), .09), op(nt, 'MULTIPLY', fine, .045)))
        macro, macro_depth = plateau, .00013
        micro, micro_depth = fine, .000025
        cavity = op(nt, 'ADD', .90, op(nt, 'MULTIPLY', plateau, .10))
    elif kind == 'GripLeather':
        phase = op(nt, 'MULTIPLY', op(nt, 'ADD', z, op(nt, 'MULTIPLY', x, .65)), 480)
        seam = op(nt, 'ABSOLUTE', op(nt, 'SINE', phase))
        roll = ramp(nt, seam, .035, .38)
        hide_grain = noise(nt, scale_vector(nt, coord, (1, 1, .7)), 1650, 3)
        pores = node(nt, 'ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE')
        nt.links.new(coord, pores.inputs['Vector'])
        pores.inputs['Scale'].default_value = 2200
        pore_height = ramp(nt, pores.outputs['Distance'], .015, .14)
        tone = op(nt, 'MULTIPLY', roll, op(nt, 'ADD', .38, op(nt, 'ADD', op(nt, 'MULTIPLY', broad, .42), op(nt, 'MULTIPLY', hide_grain, .2))))
        color = mix(nt, tone, (.017, .006, .0025, 1), (.105, .037, .013, 1))
        rough = op(nt, 'ADD', .35, op(nt, 'ADD', op(nt, 'MULTIPLY', op(nt, 'SUBTRACT', 1, roll), .16), op(nt, 'MULTIPLY', hide_grain, .13)))
        macro, macro_depth = roll, .00017
        micro = op(nt, 'ADD', op(nt, 'MULTIPLY', pore_height, .6), op(nt, 'MULTIPLY', fine, .4))
        micro_depth = .000035
        cavity = op(nt, 'ADD', .86, op(nt, 'MULTIPLY', roll, .14))
    else:
        elongated = scale_vector(nt, coord, (1, 1, .025))
        fibres = noise(nt, elongated, 3500, 2)
        flow = noise(nt, scale_vector(nt, coord, (1, 1, .12)), 120, 2)
        phase = op(nt, 'ADD', op(nt, 'MULTIPLY', x, 1600), op(nt, 'ADD', op(nt, 'MULTIPLY', y, 250), op(nt, 'ADD', op(nt, 'MULTIPLY', flow, 5), op(nt, 'MULTIPLY', op(nt, 'SINE', op(nt, 'MULTIPLY', z, 55)), 1.5))))
        grain = op(nt, 'MULTIPLY', op(nt, 'ADD', op(nt, 'SINE', phase), 1), .5)
        layer_phase = op(nt, 'ADD', op(nt, 'MULTIPLY', x, 580), op(nt, 'ADD', op(nt, 'MULTIPLY', z, 10), op(nt, 'MULTIPLY', flow, .7)))
        layers = op(nt, 'MULTIPLY', op(nt, 'ADD', op(nt, 'SINE', layer_phase), 1), .5)
        tone = op(nt, 'ADD', op(nt, 'MULTIPLY', layers, .55), op(nt, 'ADD', op(nt, 'MULTIPLY', grain, .30), op(nt, 'MULTIPLY', fibres, .15)))
        color = mix(nt, tone, (.032, .009, .003, 1), (.20, .071, .022, 1))
        rough = op(nt, 'ADD', .27, op(nt, 'ADD', op(nt, 'MULTIPLY', fibres, .055), op(nt, 'MULTIPLY', broad, .025)))
        macro, macro_depth = grain, .000018
        micro, micro_depth = fibres, .000022
        cavity = 1.
    base = mix(nt, region, original.outputs[0], color)
    roughness = mix(nt, region, old.outputs[1], rough)
    metallic = op(nt, 'MULTIPLY', old.outputs[2], op(nt, 'SUBTRACT', 1, region))
    ao = op(nt, 'MULTIPLY', old.outputs[0], op(nt, 'ADD', op(nt, 'SUBTRACT', 1, region), op(nt, 'MULTIPLY', region, cavity)))
    packed = node(nt, 'ShaderNodeCombineColor')
    for socket, value in zip(packed.inputs, (ao, roughness, metallic)):
        put(nt, socket, value)
    # Preserve the original fine metal normal in its own UV basis. New material
    # uses geometry normals so the old wood relief cannot bleed through rubber.
    original_normal = tex(nt, BASE / 'T_Kukri_Normal.png', False, 'SourceUV')
    nm = node(nt, 'ShaderNodeNormalMap', uv_map='SourceUV')
    nt.links.new(original_normal.outputs[0], nm.inputs['Color'])
    geometry = node(nt, 'ShaderNodeNewGeometry')
    normal = mix(nt, region, nm.outputs[0], geometry.outputs['Normal'])
    for label, height, depth in [('Structure', macro, macro_depth), ('Micrograin', micro, micro_depth)]:
        bump = node(nt, 'ShaderNodeBump', label=label)
        bump.inputs['Distance'].default_value = depth
        nt.links.new(region, bump.inputs['Strength'])
        put(nt, bump.inputs['Height'], height)
        nt.links.new(normal, bump.inputs['Normal'])
        normal = bump.outputs[0]
    put(nt, bs.inputs['Base Color'], base)
    put(nt, bs.inputs['Roughness'], roughness)
    put(nt, bs.inputs['Metallic'], metallic)
    put(nt, bs.inputs['Normal'], normal)
    return m, {'BaseColor': base, 'ORM': packed.outputs[0]}, bs, out

data = json.loads((SOURCE / 'components.json').read_text(encoding='utf-8'))
entries = [e for e in data['variants'] if e['slot'] == 'grip']
result = {'source': str(SOURCE / 'Kukri_Components_Editable.blend'), 'normal_convention': 'OpenGL tangent, UE green flip',
          'geometry_changed': False, 'uv_changed': False, 'numeric_changes': False, 'runtime_tested': False, 'variants': []}
for o in scene.objects:
    o.hide_render = True
    o.hide_set(True)
for entry in entries:
    kind = entry['kind']
    obj = bpy.data.objects[entry['object']]
    prefix = 'T_Kukri_' + kind
    for image in list(bpy.data.images):
        if image.name.startswith(prefix):
            image.name = 'PreviousSurface_' + image.name
    old_mat = bpy.data.materials.get('M_Kukri_' + kind)
    if old_mat:
        old_mat.name = 'PreviousSurface_' + old_mat.name
    obj.data.uv_layers.active_index = 0
    obj.data.uv_layers[0].active_render = True
    material = author_material(kind)
    obj.data.materials.clear()
    obj.data.materials.append(material[0])
    maps = bake(obj, [material], prefix, P / 'Textures', 2048)
    result['variants'].append({**entry, 'textures': maps,
        'source_blend': str(P / 'Kukri_Grip_SurfaceV2_Editable.blend'),
        'icon_input': str(P / 'IconInputs' / (entry['icon_key'] + '.png')),
        'icon': str(P / 'Icons' / (entry['icon_key'] + '.png'))})
    obj.hide_render = True
    obj.hide_set(True)
    (P / 'surfaces.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('KUKRI_GRIP_SURFACE_V2_BAKED ' + kind, flush=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Kukri_Grip_SurfaceV2_Editable.blend'))
print('KUKRI_GRIP_SURFACE_V2_AUTHORING_COMPLETE', flush=True)
