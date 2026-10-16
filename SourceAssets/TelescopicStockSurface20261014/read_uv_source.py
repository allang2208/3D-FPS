import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;result={}
for key in ['M4','M16','HK416','Super90']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.fbx(filepath=str(O/'Inputs'/(key+'.fbx')))
 rows=[]
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  row={'name':ob.name,'vertices':len(ob.data.vertices),'faces':len(ob.data.polygons),'uv':[]}
  for layer in ob.data.uv_layers:
   uv=np.array([tuple(x.uv) for x in layer.data]);t=uv.reshape(-1,3,2)
   e=t[:,1]-t[:,0];f=t[:,2]-t[:,0];det=e[:,0]*f[:,1]-e[:,1]*f[:,0]
   row['uv'].append({'name':layer.name,'zero_faces':int((abs(det)<1e-12).sum()),'range':[uv.min(axis=0).tolist(),uv.max(axis=0).tolist()]})
  ob.data.calc_tangents()
  row['zero_tangent_loops']=sum(x.tangent.length<.5 for x in ob.data.loops)
  rows.append(row)
 result[key]=rows
(O/'original_uv_source.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
