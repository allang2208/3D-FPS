"""Blender (background) geometry-only review renders of offline poses. Usage:
blender -b -P blender_probe.py -- <npz with keys like lbs110/cor110 and cam110> <out prefix> key1,key2,... angle
"""
import bpy, sys, math
import numpy as np
from mathutils import Vector
from pathlib import Path
R = Path('D:/FPS3D/FPSGAME/SourceAssets/BareSkinV9M4_20261017')
argv = sys.argv[sys.argv.index('--') + 1:]
src, prefix, keys, tag = argv[0], argv[1], argv[2].split(','), argv[3]
d = np.load(src); mesh = np.load(R / 'Work/mesh.npz'); T = mesh['T']
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene; scene.render.engine = 'BLENDER_WORKBENCH'
sh = scene.display.shading; sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (.78, .58, .48)
sh.show_cavity = True; sh.cavity_type = 'BOTH'; sh.show_specular_highlight = True; sh.show_backface_culling = True
scene.render.resolution_x, scene.render.resolution_y = 720, 540
cam_data = bpy.data.cameras.new('c'); cam = bpy.data.objects.new('c', cam_data); scene.collection.objects.link(cam); scene.camera = cam
cam_data.lens = 50
c = d['cam' + tag]; E = Vector(c[0:3] * np.array([1, -1, 1])); fd = Vector(c[3:6] * np.array([1, -1, 1])); up = Vector(c[6:9] * np.array([1, -1, 1])); hinge = Vector(c[9:12] * np.array([1, -1, 1]))
views = {'side': hinge, 'inner': (fd - up).normalized(), 'outer': (up - fd).normalized()}
for k in keys:
    X = d[k] * np.array([1, -1, 1])
    me = bpy.data.meshes.new(k); me.from_pydata([tuple(p) for p in X], [], [tuple(int(v) for v in t) for t in T]); me.update()
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(k, me); scene.collection.objects.link(ob)
    for o in scene.objects:
        if o.type == 'MESH': o.hide_render = o is not ob
    for vname, vdir in views.items():
        cam.location = E + vdir * 22
        cam.rotation_euler = (E - cam.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(R / 'Work' / f'{prefix}_{k}_{vname}.png'); bpy.ops.render.render(write_still=True)
print('PROBE_DONE')

