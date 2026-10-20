"""Blender: report stored-vs-geometric corner normal agreement per side for one object (read-only)."""
import bpy, sys
import numpy as np
path, objname = sys.argv[sys.argv.index('--') + 1:][:2]
bpy.ops.wm.open_mainfile(filepath=path)
obj = bpy.data.objects[objname]; me = obj.data
print('object', obj.name, 'matrix det', round(np.linalg.det(np.array(obj.matrix_world)[:3, :3]), 4), 'has custom normals', me.has_custom_normals)
cn = np.array([n.vector[:] for n in me.corner_normals])
fn = np.array([p.normal[:] for p in me.polygons])
loop_poly = np.zeros(len(me.loops), int)
for p in me.polygons: loop_poly[p.loop_start:p.loop_start + p.loop_total] = p.index
co = np.array([v.co[:] for v in me.vertices]); lv = np.array([l.vertex_index for l in me.loops])
d = np.einsum('ij,ij->i', cn, fn[loop_poly])
for name, sel in (('x<0', co[lv, 0] < 0), ('x>0', co[lv, 0] >= 0)):
    s = d[sel]; print(name, 'corners', len(s), 'dot<0: %.3f' % (s < 0).mean(), 'dot<cos35: %.3f' % (s < np.cos(np.radians(35))).mean())
mats = [m.name if m else None for m in me.materials]; print('materials', mats)
