import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'TightGrip/A_M4_Vertical_idle.blend'))
r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
f=json.loads((O.parent/'TightGrip/fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root']);inv=G.inverted()
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or ob.name.startswith('SK_Manny'):continue
 e=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh();v=np.array([list(inv@e.matrix_world@x.co) for x in m.vertices]);near=v[(abs(v[:,0])<.027)&(abs(v[:,1])<.025)]
 if len(near):print('MOUNT',ob.name,'near',len(near),'bounds',near.min(axis=0),near.max(axis=0),flush=True)
 e.to_mesh_clear()
