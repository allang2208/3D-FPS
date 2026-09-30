"""Workbench preview of export_frames.py output from the runtime eye.

blender -b --factory-startup --python render_frames.py -- <in.npz> <out_dir> [width]
Authoring preview only, not a game capture.
"""
import bpy, sys, math
import numpy as np
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
src, outdir = Path(args[0]), Path(args[1])
width = int(args[2]) if len(args) > 2 else 640
outdir.mkdir(parents=True, exist_ok=True)
z = np.load(src)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.light = 'STUDIO'
sc.display.shading.color_type = 'MATERIAL'
sc.display.shading.show_cavity = False
sc.render.resolution_x, sc.render.resolution_y = width, width * 9 // 16
sc.render.image_settings.file_format = 'PNG'
sc.world = bpy.data.worlds.new('W')
sc.world.color = (.35, .38, .42)
colors = {'gun': (.09, .09, .1, 1), 'cover': (.2, .12, .08, 1), 'old_feed': (.35, .3, .12, 1),
          'new_feed': (.25, .35, .15, 1), 'skin': (.8, .58, .45, 1), 'chainmail': (.45, .47, .5, 1),
          'black': (.05, .05, .05, 1), 'sweater': (.3, .35, .2, 1), 'fingerless': (.35, .22, .12, 1),
          'sleeves': (.3, .35, .22, 1), 'gloves': (.1, .1, .1, 1)}
objs = {}
names = [str(n) for n in z['names']]
for n in names:
    tri = z['tri_' + n][:, ::-1]  # back to Blender winding (Y reflected)
    p = z['pos_' + n][0].astype(float) * np.array([.01, -.01, .01])
    me = bpy.data.meshes.new(n)
    me.from_pydata(p.tolist(), [], tri.tolist())
    mat = bpy.data.materials.new(n)
    mat.diffuse_color = colors.get(n, (.5, .5, .5, 1))
    me.materials.append(mat)
    ob = bpy.data.objects.new(n, me)
    sc.collection.objects.link(ob)
    objs[n] = ob
cam = bpy.data.cameras.new('C')
cam.sensor_fit = 'VERTICAL'
cam.angle_y = math.radians(75)
cam.clip_start = .01
co = bpy.data.objects.new('C', cam)
co.rotation_euler = (math.pi / 2, 0, 0)
sc.collection.objects.link(co)
sc.camera = co
for i, t in enumerate(z['times']):
    for k, n in enumerate(names):
        ob = objs[n]
        p = z['pos_' + n][i].astype(float) * np.array([.01, -.01, .01])
        ob.data.vertices.foreach_set('co', p.ravel())
        ob.data.update()
        ob.hide_render = not bool(z['visible'][i][k])
    e = z['eye'][i] * np.array([.01, -.01, .01])
    co.location = tuple(e)
    sc.render.filepath = str(outdir / ('f_%05.2f.png' % t))
    bpy.ops.render.render(write_still=True)
    print('RENDERED', t, flush=True)
