"""Authoring measurements in the factory magazine bone frame; no rendering."""
import bpy, json
import numpy as np
from pathlib import Path
O = Path(__file__).parent
source = O.parent / 'SVDRefinedFinish20260923/SK_SVD_ModularStock.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE' and 'WPN_root' in o.data.bones)
rig.data.pose_position = 'REST'
bpy.context.view_layer.update()
mag = bpy.data.objects['SM_SVD_Magazine']
socket = rig.matrix_world @ rig.data.bones['WPN_SOCKET_Magazine'].matrix_local
xf = socket.inverted() @ mag.matrix_world
coords = np.array([xf @ v.co for v in mag.data.vertices])
record = {'source': str(source), 'object': mag.name, 'vertices':len(coords), 'faces':len(mag.data.polygons),
          'bounds': [coords.min(axis=0).tolist(),coords.max(axis=0).tolist()],
          'materials':[m.name for m in mag.data.materials], 'socket_matrix':[list(row) for row in socket],
          'root_matrix':[list(row) for row in rig.matrix_world @ rig.data.bones['WPN_root'].matrix_local],
          'uv_layers':[u.name for u in mag.data.uv_layers], 'slices':[]}
# Slanted factory base is z=-.21871*y-.028055 in this bone frame.
t = coords[:,2] + .21871*coords[:,1]
for h in np.arange(t.min(),t.max(),.005):
    p = coords[(t>=h)&(t<h+.005)]
    if len(p):record['slices'].append({'height':float(h),'count':len(p),'bounds':[p.min(axis=0).tolist(),p.max(axis=0).tolist()]})
(O/'source_geometry.json').write_text(json.dumps(record,indent=2))
np.savez_compressed(O/'factory_surface.npz', vertices=coords,
    triangles=np.array([[mag.data.loops[i].vertex_index for i in f.loop_indices] for f in mag.data.polygons]),
    material_ids=np.array([f.material_index for f in mag.data.polygons]))
print('SVD_EXTMAG_MEASURE '+json.dumps(record),flush=True)
