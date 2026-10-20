import bpy,json,gzip
import numpy as np
from pathlib import Path
O=Path(__file__).parent;S=O/'Download/Extracted/Original/Native/KVInhibitor'
bpy.ops.wm.open_mainfile(filepath=str(S/'KV Inhibitor.blend'),load_ui=False)
data={}
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 ob.data.calc_loop_triangles()
 v=np.array([list(ob.matrix_world@x.co) for x in ob.data.vertices])
 dom=[ob.vertex_groups[max(x.groups,key=lambda g:g.weight).group].name for x in ob.data.vertices]
 data[ob.name.split('\\')[-1]]={'v':v.tolist(),'t':[list(x.vertices) for x in ob.data.loop_triangles],'dom':dom}
with gzip.open(O/'source_geometry.json.gz','wt') as f:json.dump(data,f)
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'SVCHRefinement20261018/R8Surface/SVCH_R8Surface.blend'),load_ui=False)
hold=json.loads((O.parent/'SVCHSketchfab20261017/Authoring/hold_frame.json').read_text());R=np.array(hold['R']);T=np.array(hold['t_cm'])
data={}
for ob in bpy.data.objects:
 if ob.type!='MESH':continue
 ob.data.calc_loop_triangles();v=np.array([list(ob.matrix_world@x.co) for x in ob.data.vertices]);v*=np.array([100,-100,100])
 g=(v-T)@R;n=np.column_stack((g[:,0]+18.7444,g[:,2],g[:,1]+1.5268))
 data[ob.name]={'v':v.tolist(),'native':n.tolist(),'t':[list(x.vertices) for x in ob.data.loop_triangles],'m':[ob.data.materials[x.material_index].name for x in ob.data.loop_triangles]}
with gzip.open(O/'previous_geometry.json.gz','wt') as f:json.dump(data,f)
print('AUTHORING_GEOMETRY_EXTRACTED')
