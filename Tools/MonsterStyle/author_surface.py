"""Existing rigged monsters -> localized shape edits and UV-baked PBR.

Run in Blender with -- <handbrain|maggot|mutant>. No preview or testing.
Uses existing source material connections, including their normal convention.
"""
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / 'SourceAssets/MonsterStyleV1'
SETTINGS = json.loads((ROOT / 'settings.json').read_text(encoding='utf-8'))
PALETTE = json.loads((PROJECT / SETTINGS['palette_source']).read_text(encoding='utf-8'))
MODE = sys.argv[sys.argv.index('--') + 1]
P = SETTINGS[MODE]
OUT = ROOT / MODE
(OUT / 'Textures').mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(PROJECT / P['source']))
scene = bpy.context.scene
if 'objects' in P:
    meshes = [bpy.data.objects[name] for name in P['objects']]
else:
    meshes = [o for o in scene.objects if o.type == 'MESH' and any(m.type == 'ARMATURE' for m in o.modifiers)]
rig = next(m.object for o in meshes for m in o.modifiers if m.type == 'ARMATURE')
rig.data.pose_position = 'REST'
for obj in scene.objects:
    if obj.type == 'MESH': obj.hide_render = obj not in meshes
bpy.context.view_layer.update()

def point_attribute(obj, name, data):
    attr = obj.data.attributes.get(name) or obj.data.attributes.new(name, 'FLOAT', 'POINT')
    attr.data.foreach_set('value', np.asarray(data, np.float32))

def coordinates(obj):
    a = np.empty(len(obj.data.vertices) * 3, np.float32)
    obj.data.vertices.foreach_get('co', a)
    return a.reshape(-1, 3).astype(np.float64)

def clear_custom_normals(obj):
    if obj.data.has_custom_normals:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.mesh.customdata_custom_splitnormals_clear()

if MODE == 'handbrain':
    body = meshes[0]
    co = coordinates(body)
    norm = np.array([v.normal[:] for v in body.data.vertices])
    features = json.loads((PROJECT / P['features']).read_text(encoding='utf-8'))['features']
    allowed = np.zeros(len(co), dtype=bool)
    for face in body.data.polygons:
        if face.material_index == 0: allowed[list(face.vertices)] = True
    for face in body.data.polygons:
        if face.material_index != 0: allowed[list(face.vertices)] = False
    delta = np.zeros_like(co)
    nails = np.zeros(len(co)); creases = nails.copy(); tendons = nails.copy()
    for f in features:
        center = np.array(f['center']); axis = np.array(f['axis'])
        side = np.array(f['side']); normal = np.array(f['normal'])
        length = max(f['length'], .004); width = max(f['width'], .003)
        ids = np.where(allowed & np.all(np.abs(co - center) < max(length, width) * 3 + .02, axis=1))[0]
        d = co[ids] - center
        x, y, z = d @ axis, d @ side, d @ normal
        gate = np.exp(-.5 * (z / .017) ** 2) * np.clip((norm[ids] @ normal - .18) / .62, 0, 1)
        weight = np.exp(-.5 * ((x / length) ** 2 + (y / width) ** 2)) * gate
        kind = f['kind']
        if kind in ['bone', 'tendon', 'wrist']:
            amount = {'bone': .0009, 'tendon': .00065, 'wrist': -.00035}[kind]
            delta[ids] += weight[:, None] * normal * amount
            if kind == 'tendon': tendons[ids] = np.maximum(tendons[ids], weight)
        elif kind == 'shaft':
            # Narrow the side of a mapped phalanx, leaving its joints in place.
            delta[ids] -= weight[:, None] * np.tanh(y / width)[:, None] * side * .00075
        elif kind == 'nail':
            nails[ids] = np.maximum(nails[ids], weight)
        elif kind == 'crease':
            creases[ids] = np.maximum(creases[ids], weight)
    length = np.linalg.norm(delta, axis=1)
    delta *= np.minimum(1.0, P['max_shape_shift_m'] / np.maximum(length, 1e-9))[:, None]
    body.data.vertices.foreach_set('co', (co + delta).astype(np.float32).ravel())
    body.data.update(); clear_custom_normals(body)
    for name, values in [('StyleNail', nails), ('StyleCrease', creases), ('StyleTendon', tendons)]:
        point_attribute(body, name, values)
elif MODE == 'maggot':
    body = meshes[0]; co = coordinates(body)
    x, y, z = co.T
    # Keep contact feet, mouth, head and the underside at their original positions.
    t = np.clip((z - .26) / .15, 0, 1); t = t * t * (3 - 2 * t)
    h = np.clip((.86 - x) / .23, 0, 1); h = h * h * (3 - 2 * h)
    gate = t * h
    delta = np.zeros_like(co)
    delta[:, 1] = gate * (.0045 * np.sin(x * 7.3 + .4) + y * .009 * np.sin(x * 14.1 + 1.2))
    delta[:, 2] = gate * .004 * np.sin(x * 11.7 + y * 4.0)
    length = np.linalg.norm(delta, axis=1)
    delta *= np.minimum(1.0, P['max_shape_shift_m'] / np.maximum(length, 1e-9))[:, None]
    body.data.vertices.foreach_set('co', (co + delta).astype(np.float32).ravel())
    body.data.update(); clear_custom_normals(body)

class Graph:
    def __init__(self, material):
        self.material = material
        self.nodes = material.node_tree.nodes
        self.links = material.node_tree.links
        self.bs = next(n for n in self.nodes if n.type == 'BSDF_PRINCIPLED')
        self.out = next(n for n in self.nodes if n.type == 'OUTPUT_MATERIAL')
        self.position = self.node('ShaderNodeNewGeometry').outputs['Position']
    def node(self, kind, label=''):
        n = self.nodes.new(kind)
        if label: n.label = label
        return n
    def value(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket): self.links.new(value, socket)
        else:
            if socket.type == 'RGBA' and isinstance(value, (int, float)): value = (value, value, value, 1)
            socket.default_value = value
    def source(self, name):
        sock = self.bs.inputs[name]
        if sock.is_linked: return sock.links[0].from_socket
        v = sock.default_value
        return tuple(v) if hasattr(v, '__len__') else float(v)
    def math(self, op, a, b=None):
        n = self.node('ShaderNodeMath'); n.operation = op
        self.value(n.inputs[0], a)
        if b is not None: self.value(n.inputs[1], b)
        return n.outputs[0]
    def mul(self, a, b): return self.math('MULTIPLY', a, b)
    def add(self, a, b): return self.math('ADD', a, b)
    def sub(self, a, b): return self.math('SUBTRACT', a, b)
    def inv(self, a): return self.sub(1, a)
    def ramp(self, a, low, high, v0=0, v1=1):
        n = self.node('ShaderNodeMapRange'); n.clamp = True; n.interpolation_type = 'SMOOTHSTEP'
        for k, v in [('Value', a), ('From Min', low), ('From Max', high), ('To Min', v0), ('To Max', v1)]: self.value(n.inputs[k], v)
        return n.outputs[0]
    def mix(self, a, b, t):
        n = self.node('ShaderNodeMixRGB')
        for i, v in enumerate([t, a, b]): self.value(n.inputs[i], v)
        return n.outputs[0]
    def cmul(self, a, b):
        n = self.node('ShaderNodeMixRGB'); n.blend_type = 'MULTIPLY'
        for i, v in enumerate([1.0, a, b]): self.value(n.inputs[i], v)
        return n.outputs[0]
    def noise(self, scale, detail=2.0):
        n = self.node('ShaderNodeTexNoise'); self.value(n.inputs['Vector'], self.position)
        n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
        return n.outputs['Fac']
    def gray(self, color):
        n = self.node('ShaderNodeRGBToBW'); self.value(n.inputs[0], color); return n.outputs[0]
    def separate(self, color):
        n = self.node('ShaderNodeSeparateColor'); self.value(n.inputs[0], color); return n.outputs
    def attribute(self, name):
        n = self.node('ShaderNodeAttribute'); n.attribute_name = name; return n.outputs['Fac']
    def library(self, semantic, scale=12):
        mapping = self.node('ShaderNodeVectorMath'); mapping.operation = 'SCALE'
        self.value(mapping.inputs[0], self.position); mapping.inputs[3].default_value = scale
        n = self.node('ShaderNodeTexImage'); n.image = bpy.data.images.load(
            str(PROJECT / SETTINGS['skin_library'] / ('T_ZombieSkinMaterial1_' + semantic + '.png')), check_existing=True)
        n.image.colorspace_settings.name = 'Non-Color'; n.projection = 'BOX'; n.projection_blend = .35
        self.value(n.inputs['Vector'], mapping.outputs[0]); return n.outputs['Color']
    def bump(self, normal, height, strength, distance):
        n = self.node('ShaderNodeBump')
        for k, v in [('Normal', normal), ('Height', height), ('Strength', strength), ('Distance', distance)]: self.value(n.inputs[k], v)
        return n.outputs[0]
    def pack(self, a, b, c):
        n = self.node('ShaderNodeCombineColor')
        for i, v in enumerate([a, b, c]): self.value(n.inputs[i], v)
        return n.outputs[0]

def author_material(obj, index):
    material = obj.data.materials[index].copy()
    material.name = 'StyleV1_' + MODE + '_' + obj.name + '_' + str(index)
    obj.data.materials[index] = material
    g = Graph(material)
    base, rough = g.source('Base Color'), g.source('Roughness')
    normal = g.source('Normal') if g.bs.inputs['Normal'].is_linked else g.node('ShaderNodeNewGeometry').outputs['Normal']
    lum = g.gray(base)
    fine = g.noise(190); broad = g.noise(9, 3); medium = g.noise(37, 2.5)
    skin, wet, scab, ao = 1.0, 0.0, 0.0, 1.0
    semantic = 'skin'
    oral = MODE == 'handbrain' and obj.name == 'HandBrain_Body' and index == 1
    teeth = MODE == 'handbrain' and obj.name == 'HandBrain_OralTeeth'
    if oral:
        semantic = 'oral'
        base = g.cmul(g.mix(PALETTE['tissue_color_low'], PALETTE['tissue_color_high'], medium), g.ramp(lum, .001, .08, .65, 1.1))
        rough = g.ramp(fine, .1, .9, .30, .40)
        wet = 1.0
        normal = g.bump(normal, fine, .12, .0002)
    elif teeth:
        semantic = 'teeth'; skin = 0.0
        base = g.cmul(g.mix(base, (.23, .195, .12, 1), .18), g.ramp(broad, .1, .9, .90, 1.02))
        rough = g.ramp(rough, .0, 1.0, .43, .62)
    elif MODE == 'handbrain':
        rgb = g.separate(base)
        wound = g.ramp(g.sub(rgb[0], g.mul(rgb[1], 1.10)), .006, .055)
        wet = g.mul(g.ramp(wound, .50, .89), g.ramp(fine, .2, .8, .72, 1.0))
        scab = g.mul(g.mul(g.ramp(wound, .08, .38), g.inv(g.ramp(wound, .52, .82))), g.ramp(fine, .25, .8, .3, .95))
        tone = g.ramp(lum, .015, .20, .65, 1.09)
        skin_color = g.cmul(g.mix(P['skin_dark'], P['skin_light'], broad), tone)
        skin_color = g.mix(skin_color, (.14, .088, .076, 1), g.mul(wound, .38))
        base = g.mix(skin_color, g.mix(PALETTE['tissue_color_low'], PALETTE['tissue_color_high'], fine), wet)
        base = g.mix(base, g.mix(PALETTE['scab_color_low'], PALETTE['scab_color_high'], fine), scab)
        rough = g.ramp(g.library('roughness'), .05, .95, .59, .71)
        rough = g.mix(rough, .79, scab); rough = g.mix(rough, g.ramp(fine, .1, .9, .31, .40), wet)
        normal = g.bump(normal, g.library('height'), .27, .00019)
        if obj.name == 'HandBrain_Body' and index == 0:
            nail, crease, tendon = [g.attribute(n) for n in ['StyleNail', 'StyleCrease', 'StyleTendon']]
            base = g.mix(base, (.18, .158, .105, 1), g.mul(nail, .45))
            base = g.cmul(base, g.sub(1.0, g.mul(crease, .08)))
            rough = g.mix(rough, .49, g.mul(nail, .65))
            relief = g.sub(g.add(g.mul(nail, .5), g.mul(tendon, .3)), g.mul(crease, .52))
            normal = g.bump(normal, relief, .46, .0009)
        normal = g.bump(normal, fine, .12, .000055)
        ao = g.ramp(g.library('ambientocclusion'), 0, 1, .93, 1)
    elif MODE == 'maggot':
        skin = g.ramp(lum, .045, .20)
        xyz = g.node('ShaderNodeSeparateXYZ'); g.value(xyz.inputs[0], g.position)
        x, y, z = xyz.outputs[0], xyz.outputs[1], xyz.outputs[2]
        ring = g.math('ABSOLUTE', g.math('SINE', g.mul(g.add(x, .97), math.pi / .27)))
        groove = g.mul(g.inv(g.ramp(ring, .08, .37)), skin)
        body_color = g.cmul(g.mix(P['skin_dark'], P['skin_light'], broad), g.ramp(lum, .1, .65, .75, 1.05))
        body_color = g.mix(body_color, (.20, .17, .19, 1), g.mul(g.ramp(medium, .54, .73), .16))
        body_color = g.mix(body_color, (.125, .12, .074, 1), g.mul(groove, .20))
        veins = g.node('ShaderNodeTexVoronoi'); veins.feature = 'DISTANCE_TO_EDGE'
        g.value(veins.inputs['Vector'], g.position); veins.inputs['Scale'].default_value = 39
        vein = g.mul(g.inv(g.ramp(veins.outputs['Distance'], .006, .025)), .055)
        body_color = g.mix(body_color, (.12, .093, .115, 1), vein)
        base = g.mix(g.cmul(base, .9), body_color, skin)
        mouth = g.mul(g.ramp(x, .75, 1.04), g.inv(g.ramp(lum, .045, .17)))
        wet = g.math('MAXIMUM', mouth, g.mul(g.mul(skin, g.ramp(medium, .59, .75)), .67))
        rough = g.mix(g.ramp(rough, .0, 1, .49, .71), g.ramp(fine, .1, .9, .45, .58), skin)
        rough = g.mix(rough, g.ramp(fine, .1, .9, .28, .38), wet)
        # Insect cuticle uses fine striations and smooth membrane, not human pores.
        wave = g.node('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'X'
        g.value(wave.inputs['Vector'], g.position); wave.inputs['Scale'].default_value = 85
        wave.inputs['Distortion'].default_value = 3.5; wave.inputs['Detail'].default_value = 2
        normal = g.bump(normal, wave.outputs['Fac'], g.mul(skin, .075), .00014)
        normal = g.bump(normal, fine, g.mul(skin, .07), .000065)
    else:
        skin = g.ramp(lum, .068, .18)
        clean = g.cmul(g.mix(P['skin_dark'], P['skin_light'], broad), g.ramp(lum, .05, .60, .62, 1.07))
        bruise = g.mul(g.ramp(medium, .55, .75), .15)
        clean = g.mix(clean, (.14, .095, .10, 1), bruise)
        base = g.mix(g.cmul(base, .87), clean, skin)
        rough = g.mix(g.ramp(rough, .0, 1, .76, .90), g.ramp(g.library('roughness'), .05, .95, .57, .69), skin)
        normal = g.bump(normal, g.library('height', 17), g.mul(skin, .19), .00014)
        normal = g.bump(normal, fine, g.mul(skin, .11), .00005)
        ao = g.mix(1.0, g.ramp(g.library('ambientocclusion'), 0, 1, .95, 1), skin)
    g.value(g.bs.inputs['Base Color'], base); g.value(g.bs.inputs['Roughness'], rough)
    g.value(g.bs.inputs['Normal'], normal); g.bs.inputs['Metallic'].default_value = 0.0
    for link in list(g.bs.inputs['Metallic'].links): g.links.remove(link)
    g.bs.inputs['Specular IOR Level'].default_value = .30
    g.bs.inputs['Subsurface Weight'].default_value = .035 if MODE == 'maggot' else 0.0
    g.value(g.out.inputs['Surface'], g.bs.outputs[0])
    size = P.get('texture_size', P.get('other_texture_size', 2048))
    if MODE == 'handbrain' and obj.name == 'HandBrain_Body' and index == 0: size = P['body_texture_size']
    return {'graph': g, 'object': obj.name, 'slot': index, 'name': material.name,
            'semantic': semantic, 'size': size,
            'outputs': {'BaseColor': base, 'ORM': g.pack(ao, rough, 0.0), 'TissueMasks': g.pack(skin, wet, scab), 'Normal': None}, 'textures': {}}

records = []
for obj in meshes:
    for index in range(len(obj.data.materials)):
        records.append(author_material(obj, index))
    obj.data.uv_layers.active.active_render = True

scene.render.engine = 'CYCLES'; scene.cycles.samples = 8
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'; prefs.get_devices()
for device in prefs.devices: device.use = device.type != 'CPU'
scene.cycles.device = 'GPU'
scene.render.bake.use_selected_to_active = False
scene.render.bake.use_clear = True; scene.render.bake.margin = 16

for obj in meshes:
    own = [r for r in records if r['object'] == obj.name]
    for semantic in ['BaseColor', 'ORM', 'TissueMasks', 'Normal']:
        active = []
        for r in own:
            g = r['graph']
            image = bpy.data.images.new('T_' + r['name'] + '_' + semantic, r['size'], r['size'], alpha=False)
            image.colorspace_settings.name = 'sRGB' if semantic == 'BaseColor' else 'Non-Color'
            image.generated_color = (0.5, .5, 1, 1) if semantic == 'Normal' else (0, 0, 0, 1)
            target = g.node('ShaderNodeTexImage'); target.image = image; g.nodes.active = target
            em = None
            if semantic != 'Normal':
                em = g.node('ShaderNodeEmission'); g.value(em.inputs['Color'], r['outputs'][semantic]); g.value(g.out.inputs['Surface'], em.outputs[0])
            active.append((r, image, em))
        bpy.ops.object.select_all(action='DESELECT'); obj.hide_set(False); obj.select_set(True); bpy.context.view_layer.objects.active = obj
        if semantic == 'Normal': bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', normal_r='POS_X', normal_g='NEG_Y', normal_b='POS_Z')
        else: bpy.ops.object.bake(type='EMIT')
        for r, image, em in active:
            g = r['graph']
            if em: g.nodes.remove(em)
            g.value(g.out.inputs['Surface'], g.bs.outputs[0])
            image.filepath_raw = str(OUT / 'Textures' / (image.name + '.png'))
            image.file_format = 'PNG'; image.save()
            r['textures'][semantic] = image.filepath_raw
        print('MONSTER_STYLE_BAKED', MODE, obj.name, semantic, flush=True)

bpy.ops.file.pack_all()
authoring = OUT / (MODE + '_StyleV1_Authoring.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(authoring))
export_path = None
if MODE != 'mutant':
    # Export only the selected gameplay surfaces, retaining the original rig.
    for obj in meshes:
        for attr in list(obj.data.attributes):
            if attr.name.startswith('Style') or attr.name in ['SurfaceRegion', 'SculptNail', 'SculptArea']:
                obj.data.attributes.remove(attr)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes: obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1: bpy.ops.object.join()
    mesh = bpy.context.view_layer.objects.active
    bpy.ops.object.select_all(action='DESELECT'); mesh.select_set(True); rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    export_path = OUT / ('SK_' + MODE + '_StyleV1.fbx')
    bpy.ops.export_scene.fbx(filepath=str(export_path), use_selection=True, object_types={'ARMATURE', 'MESH'},
        path_mode='STRIP', embed_textures=False, add_leaf_bones=False, bake_anim=False,
        axis_forward='-Y', axis_up='Z', bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False)

report = {'mode': MODE, 'source': P['source'], 'authoring': str(authoring),
          'mesh_fbx': str(export_path) if export_path else None,
          'shape_edit_limit_metres': P.get('max_shape_shift_m', 0),
          'materials': [{k: v for k, v in r.items() if k not in ['graph', 'outputs']} for r in records],
          'changes': 'Material plus localized same-topology vertex offsets' if export_path else 'Material only',
          'animations_modified': False, 'preview_rendered': False, 'runtime_tested': False}
(OUT / 'authoring_manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('MONSTER_STYLE_AUTHORING_COMPLETE', MODE, flush=True)
