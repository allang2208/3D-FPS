import bpy,numpy as np,json
from pathlib import Path
O=Path(__file__).parent;D=json.loads((O/'capture.json').read_text());R={}
for key,row in D['assets'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=row['export']);r={'invalid_corners':0,'invalid_corners_on_nondegenerate_faces':0,'near_zero_area_faces':0}
 for ob in bpy.context.scene.objects:
  if ob.type!='MESH':continue
  me=ob.data;p=np.asarray([tuple(v.co) for v in me.vertices]);t=np.asarray([list(f.vertices) for f in me.polygons]);v=p[t]
  area=np.linalg.norm(np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]),axis=1)/2
  n=np.asarray([tuple(n.vector) for n in me.corner_normals]).reshape(-1,3,3);bad=~np.isfinite(n).all(axis=2)|(np.linalg.norm(n,axis=2)<.9)
  r['invalid_corners']+=int(bad.sum());r['invalid_corners_on_nondegenerate_faces']+=int((bad&(area[:,None]>1e-12)).sum());r['near_zero_area_faces']+=int((area<=1e-12).sum())
 R[key]=r
(O/'degenerate_normal_check.json').write_text(json.dumps(R,indent=2),encoding='utf-8');print(json.dumps(R),flush=True)
