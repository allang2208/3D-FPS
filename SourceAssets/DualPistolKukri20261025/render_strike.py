"""Batch eye-view previews of the authored quick-melee thrust keys (Work/strike/*.npz from author_strike.py).

Background Blender only; fixed eye at the origin, gameplay 75 deg vertical FOV, 1280x720. One PNG per key,
strike_tXXX.png. Not a game screenshot. EEVEE for iteration speed; falls back to Cycles if unavailable.
"""
import bpy, json, math, sys
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
V4 = ROOT / 'SourceAssets/PistolBookPoseV4_20261020'
OUT = P / 'Work' / (sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv[:-1] else 'strike')
data = json.loads((OUT / 'strike_keys.json').read_text(encoding='utf-8'))
TAGS = sorted({'t%03d' % round(t * 1000) for t in [k['t'] for k in data['keys']] + data.get('preview_tweens', [])})

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
S = np.array([1, -1, 1])


def smooth_normals(mesh, x, t):
    _, weld = np.unique(np.round(x, 7), axis=0, return_inverse=True)
    f = np.cross(x[t[:, 1]] - x[t[:, 0]], x[t[:, 2]] - x[t[:, 0]])
    normals = np.zeros((weld.max() + 1, 3))
    for k in range(3):
        np.add.at(normals, weld[t[:, k]], f)
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1.e-10)
    mesh.normals_split_custom_set(normals[weld[t]].reshape(-1, 3).tolist())


def make_mesh(name, x, t, uv, uv_name):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(x.tolist(), [], t.tolist())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    for poly in mesh.polygons:
        poly.use_smooth = True
    smooth_normals(mesh, x, t)
    lay = mesh.uv_layers.new(name=uv_name)
    lay.data.foreach_set('uv', uv.reshape(-1))
    return obj, mesh


skin = bpy.data.materials.new('V9 natural bare skin')
skin.use_nodes = True
nt = skin.node_tree
bs = nt.nodes.get('Principled BSDF')
tex = ROOT / 'SourceAssets/BareSkinV9M4_20261017/Work'
def image(node_tree, name, space):
    n = node_tree.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(str(tex / name), check_existing=True)
    n.image.colorspace_settings.name = space
    return n
colour = image(nt, 'T_M4SkinV9_Colour.png', 'sRGB')
normal = image(nt, 'normal_gl16.png', 'Non-Color')
masks = image(nt, 'T_M4SkinV9_Masks.png', 'Non-Color')
nm = nt.nodes.new('ShaderNodeNormalMap')
nm.uv_map = 'V9 UV'
nm.inputs['Strength'].default_value = .8
sep = nt.nodes.new('ShaderNodeSeparateColor')
nt.links.new(colour.outputs['Color'], bs.inputs['Base Color'])
nt.links.new(normal.outputs['Color'], nm.inputs['Color'])
nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
nt.links.new(masks.outputs['Color'], sep.inputs['Color'])
nt.links.new(sep.outputs['Green'], bs.inputs['Roughness'])
bs.inputs['Subsurface Weight'].default_value = .16
bs.inputs['Subsurface Scale'].default_value = .005
bs.inputs['Subsurface Radius'].default_value = (1, .4, .2)

gun_source = json.loads((V4 / 'contact_source.json').read_text())
with bpy.data.libraries.load(gun_source['source'], link=False) as (available, loaded):
    loaded.materials = gun_source['gun_materials']

steel = bpy.data.materials.new('M_Kukri preview')
steel.use_nodes = True
kt = steel.node_tree
kb = kt.nodes.get('Principled BSDF')
ktex = ROOT / 'SourceAssets/Kukri20261020/Textures'
def kimage(name, space):
    n = kt.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(str(ktex / name), check_existing=True)
    n.image.colorspace_settings.name = space
    return n
kc = kimage('T_Kukri_BaseColor.png', 'sRGB')
kn = kimage('T_Kukri_Normal.png', 'Non-Color')
ko = kimage('T_Kukri_ORM.png', 'Non-Color')
knm = kt.nodes.new('ShaderNodeNormalMap')
knm.uv_map = 'UVMap'
ksep = kt.nodes.new('ShaderNodeSeparateColor')
kt.links.new(kc.outputs['Color'], kb.inputs['Base Color'])
kt.links.new(kn.outputs['Color'], knm.inputs['Color'])
kt.links.new(knm.outputs['Normal'], kb.inputs['Normal'])
kt.links.new(ko.outputs['Color'], ksep.inputs['Color'])
kt.links.new(ksep.outputs['Green'], kb.inputs['Roughness'])
kt.links.new(ksep.outputs['Blue'], kb.inputs['Metallic'])

for engine in ('BLENDER_EEVEE_NEXT', 'BLENDER_EEVEE', 'CYCLES'):
    try:
        scene.render.engine = engine
        break
    except Exception:
        continue
if scene.render.engine == 'CYCLES':
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('Neutral charcoal studio')
world.use_nodes = True
scene.world = world
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.075, .085, .1, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .45
for name, loc, power, size in [('Key', (-.15, -.45, .65), 22, .75), ('Fill', (.15, .65, .3), 12, .6), ('Rim', (.85, -.08, .35), 18, .5)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = power
    light.shape = 'DISK'
    light.size = size
    obj = bpy.data.objects.new(name, light)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector((.30, -.08, -.10)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
camera = bpy.data.cameras.new('Player eye')
cam = bpy.data.objects.new(camera.name, camera)
scene.collection.objects.link(cam)
scene.camera = cam
camera.sensor_fit = 'VERTICAL'
camera.sensor_height = 24
camera.clip_start = .01
camera.clip_end = 100
cam.rotation_euler = Matrix(((0, 0, -1), (-1, 0, 0), (0, 1, 0))).to_euler()
camera.lens = 24 / (2 * math.tan(math.radians(75 / 2)))

made = []
for tag in TAGS:
    arms = np.load(OUT / ('arms_%s.npz' % tag))
    uv = arms['UV'][:, ::-1].copy()
    uv[:, :, 1] = 1 - uv[:, :, 1]
    a_obj, a_mesh = make_mesh('arms_' + tag, arms['X'] * S * .01, arms['T'][:, ::-1], uv, 'V9 UV')
    a_mesh.materials.append(skin)
    g = np.load(OUT / ('gun_%s.npz' % tag))
    g_obj, g_mesh = make_mesh('gun_' + tag, g['X'] * S * .01, g['T'][:, ::-1], g['UV'][:, ::-1], 'Original gun UV')
    for mat in loaded.materials:
        g_mesh.materials.append(mat)
    for p_, s_ in zip(g_mesh.polygons, g['slots']):
        p_.material_index = int(s_)
    k = np.load(OUT / ('kukri_%s.npz' % tag))
    k_obj, k_mesh = make_mesh('kukri_' + tag, k['X'] * S * .01, k['T'], k['UV'], 'UVMap')
    k_mesh.materials.append(steel)
    made += [(a_obj, a_mesh), (g_obj, g_mesh), (k_obj, k_mesh)]
    scene.render.filepath = str(OUT / ('strike_%s.png' % tag))
    bpy.ops.render.render(write_still=True)
    print('SAVED', tag, flush=True)
    for o, m in made:
        bpy.data.objects.remove(o)
        bpy.data.meshes.remove(m)
    made = []
print('DONE', len(TAGS))
