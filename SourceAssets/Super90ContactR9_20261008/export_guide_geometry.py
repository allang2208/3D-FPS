import bpy,numpy as np
from pathlib import Path
O=Path(__file__).parent;bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O.parent/'Super90ContactR8_20261008/Diagnostics/guide.fbx'))
v=[];f=[]
for ob in bpy.data.objects:
 if ob.type=='MESH':
  off=len(v);v.extend([[*(ob.matrix_world@p.co),1.] for p in ob.data.vertices]);ob.data.calc_loop_triangles();f.extend([[off+i for i in t.vertices] for t in ob.data.loop_triangles])
np.savez(O/'guide_geometry.npz',vertices=np.array(v),faces=np.array(f));print('GUIDE',len(v),len(f),flush=True)
