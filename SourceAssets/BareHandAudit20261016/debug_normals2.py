import bpy, sys
import numpy as np
path, objname = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.open_mainfile(filepath=path)
me = bpy.data.objects[objname].data
print('normals_domain', me.normals_domain, 'has_custom', me.has_custom_normals, 'attrs', [(a.name, a.domain, a.data_type) for a in me.attributes])
cnA = np.array([n.vector[:] for n in me.corner_normals])
polys = list(me.polygons)
cnB = [tuple(me.corner_normals[li].vector) for p in polys for li in p.loop_indices]
loopsB = [li for p in polys for li in p.loop_indices]
print('loop order identity', loopsB == list(range(len(me.loops))))
fn = np.array([p.normal[:] for p in polys]); lp = np.repeat(np.arange(len(polys)), [p.loop_total for p in polys])
print('A dot<cos35', (np.einsum('ij,ij->i', cnA, fn[lp]) < np.cos(np.radians(35))).mean())
print('B dot<cos35', (np.einsum('ij,ij->i', np.array(cnB), fn[lp]) < np.cos(np.radians(35))).mean())
print('loop_start monotonic', all(polys[i].loop_start < polys[i + 1].loop_start for i in range(len(polys) - 1)))
