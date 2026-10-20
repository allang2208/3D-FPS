"""Blender Cycles preview of the V9 skin (author-side look check only, not a UE render)."""
import bpy, json, math
from pathlib import Path
import numpy as np
from mathutils import Vector
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9M4_20261017'); W = R / 'Work'
d = np.load(W / 'mesh.npz'); perm = d['perm']; T = d['T']
uv = np.load(W / 'uv_new.npy')[:, perm].copy(); uv[:, :, 1] = 1 - uv[:, :, 1]
nrm = np.load(W / 'normals.npy')[:, perm] * np.array([1, -1, 1])
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('skin'); me.from_pydata([tuple(p) for p in d['X']], [], [tuple(int(v) for v in t) for t in T]); me.update()
lay = me.uv_layers.new(name='new'); lay.data.foreach_set('uv', uv.reshape(-1))
for p in me.polygons: p.use_smooth = True
me.normals_split_custom_set([tuple(n) for n in nrm.reshape(-1, 3)])
ob = bpy.data.objects.new('skin', me); bpy.context.scene.collection.objects.link(ob)
mat = bpy.data.materials.new('skin'); mat.use_nodes = True; ob.data.materials.append(mat); nt = mat.node_tree; b = nt.nodes['Principled BSDF']
def img(name, cs):
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(str(W / name)); t.image.colorspace_settings.name = cs; return t
col = img('T_M4SkinV9_Colour.png', 'sRGB'); nm = img('normal_gl16.png', 'Non-Color'); mk = img('T_M4SkinV9_Masks.png', 'Non-Color')
nmap = nt.nodes.new('ShaderNodeNormalMap'); nmap.uv_map = 'new'; nmap.inputs['Strength'].default_value = float(__import__('os').environ.get('V9_NSTR','1'))
sep = nt.nodes.new('ShaderNodeSeparateColor')
nt.links.new(col.outputs['Color'], b.inputs['Base Color']); nt.links.new(nm.outputs['Color'], nmap.inputs['Color']); nt.links.new(nmap.outputs['Normal'], b.inputs['Normal'])
nt.links.new(mk.outputs['Color'], sep.inputs['Color']); nt.links.new(sep.outputs['Green'], b.inputs['Roughness'])
b.inputs['Subsurface Weight'].default_value = .35; b.inputs['Subsurface Radius'].default_value = (.37, .14, .07)
b.inputs['Subsurface Scale'].default_value = 1.0; b.inputs['Specular IOR Level'].default_value = .45
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 48
sc.render.resolution_x, sc.render.resolution_y = 900, 640
world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True; world.node_tree.nodes['Background'].inputs['Color'].default_value = (.05, .055, .06, 1); world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1
for loc, en, size in (((-60, 40, 60), 60000, 60), ((40, 60, 20), 25000, 80), ((-20, -60, -30), 12000, 80)):
    l = bpy.data.lights.new('a', 'AREA'); l.energy = en; l.size = size; lo = bpy.data.objects.new('a', l); sc.collection.objects.link(lo)
    lo.location = loc; lo.rotation_euler = (Vector((-40, 10, -40)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
cd = bpy.data.cameras.new('c'); cam = bpy.data.objects.new('c', cd); sc.collection.objects.link(cam); sc.camera = cam
views = json.loads((W / 'preview_views.json').read_text())
for name, v in views.items():
    cam.location = v['eye']; cam.rotation_euler = (Vector(v['target']) - Vector(v['eye'])).to_track_quat('-Z', 'Y').to_euler(); cd.lens = v.get('lens', 50)
    sc.render.filepath = str(W / f'preview_{name}{__import__("os").environ.get("V9_TAG","")}.png'); bpy.ops.render.render(write_still=True)
print('PREVIEW_DONE')


