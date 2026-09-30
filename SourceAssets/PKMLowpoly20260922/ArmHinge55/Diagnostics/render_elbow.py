"""blender -b --factory-startup --python render_elbow.py -- <in.npz> <out_dir> <tag>"""
import bpy, sys, math
import numpy as np
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
z = np.load(args[0])
outdir = Path(args[1])
tag = args[2]
outdir.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'SINGLE'
sc.display.shading.single_color = (.8, .6, .5)
sc.display.shading.show_cavity = True
sc.render.resolution_x = sc.render.resolution_y = 520
sc.world = bpy.data.worlds.new('W')
sc.world.color = (.3, .33, .36)
S = np.array([.01, -.01, .01])
tri = z['tri'][:, ::-1]
me = bpy.data.meshes.new('arm')
me.from_pydata((z['pos'][0].astype(float) * S).tolist(), [], tri.tolist())
me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
ob = bpy.data.objects.new('arm', me)
sc.collection.objects.link(ob)
cam = bpy.data.cameras.new('C')
cam.lens = 50
cam.clip_start = .005
co = bpy.data.objects.new('C', cam)
sc.collection.objects.link(co)
sc.camera = co
for i, t in enumerate(z['times']):
    ob.data.vertices.foreach_set('co', (z['pos'][i].astype(float) * S).ravel())
    ob.data.update()
    c = Vector((z['cam'][i] * S).tolist())
    l = Vector((z['look'][i] * S).tolist())
    co.location = c
    co.rotation_euler = (l - c).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = str(outdir / ('%s_%05.2f.png' % (tag, t)))
    bpy.ops.render.render(write_still=True)
print('ELBOW_RENDERED', tag, len(z['times']))
