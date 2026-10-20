"""Blender (background): bake the V9 relief into a tangent-space normal map on the new UV0.

The bake mesh uses the exact triangles, final corner normals and UV0 that are written to UE, so the
MikkTSpace basis matches UE's recomputed tangents. Output Work/normal_gl16.png (OpenGL +Y); the
DirectX conversion for UE happens afterwards in finish_textures.py.
"""
import bpy, json
from pathlib import Path
import numpy as np
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9M4_20261017'); W = R / 'Work'
d = np.load(W / 'mesh.npz'); perm = d['perm']; T = d['T']
uv = np.load(W / 'uv_new.npy')[:, perm].copy(); uv[:, :, 1] = 1 - uv[:, :, 1]
nrm = np.load(W / 'normals.npy')[:, perm] * np.array([1, -1, 1])
H = json.loads((W / 'height.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
me = bpy.data.meshes.new('M4SkinBake')
me.from_pydata([tuple(p) for p in d['X']], [], [tuple(int(v) for v in t) for t in T]); me.update()
lay = me.uv_layers.new(name='new'); lay.data.foreach_set('uv', uv.reshape(-1))
me.uv_layers.active = lay; lay.active_render = True
for p in me.polygons: p.use_smooth = True
me.normals_split_custom_set([tuple(n) for n in nrm.reshape(-1, 3)])
obj = bpy.data.objects.new('M4SkinBake', me); bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj; obj.select_set(True)
mat = bpy.data.materials.new('bake'); mat.use_nodes = True; obj.data.materials.append(mat)
nt = mat.node_tree; bsdf = nt.nodes['Principled BSDF']
uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'new'
img = bpy.data.images.load(str(W / 'height16.png')); img.colorspace_settings.name = 'Non-Color'
tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = img; tex.interpolation = 'Cubic'; tex.extension = 'EXTEND'
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 1.0; bump.inputs['Distance'].default_value = H['range_cm']
nt.links.new(uvn.outputs['UV'], tex.inputs['Vector']); nt.links.new(tex.outputs['Color'], bump.inputs['Height'])
nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
target = bpy.data.images.new('normal', 4096, 4096, alpha=False, float_buffer=True); target.colorspace_settings.name = 'Non-Color'
tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = target; nt.nodes.active = tn; tn.select = True
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
sc.render.bake.margin = 16; sc.render.bake.margin_type = 'EXTEND'
sc.render.bake.normal_space = 'TANGENT'; sc.render.bake.normal_r = 'POS_X'; sc.render.bake.normal_g = 'POS_Y'; sc.render.bake.normal_b = 'POS_Z'
bpy.ops.object.bake(type='NORMAL', use_clear=True, margin=16)
target.filepath_raw = str(W / 'normal_gl16.png'); target.file_format = 'PNG'
sc.render.image_settings.color_depth = '16'
target.save_render(str(W / 'normal_gl16.png'), scene=sc)
print('M4V9_BAKE_DONE')
