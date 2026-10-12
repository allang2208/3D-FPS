import bpy,gzip,json
from pathlib import Path
import numpy as np
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
ob=bpy.data.objects['Super90_V7_ContinuousSkin'];d=json.loads(gzip.decompress((O/'arms_before.json.gz').read_bytes()))
patch=json.loads((O/'patches.json').read_text())['arms'];expected=np.array(d['positions'])
for vi,p in patch['positions']:expected[vi]=p
actual=np.array([list(ob.matrix_world@v.co) for v in ob.data.vertices])*[100,-100,100]
groups={g.index:g.name for g in ob.vertex_groups}
weights=[{groups[g.group]:g.weight for g in v.groups} for v in ob.data.vertices]
error=max(abs(row.get(n,0)-d['weights'][i].get(n,0)) for i,row in enumerate(weights) for n in set(row)|set(d['weights'][i]))
faces=[list(p.vertices) for p in ob.data.polygons]
positions_error=float(np.max(np.linalg.norm(actual-expected,axis=1))*10)
report={'vertices':len(actual),'triangles':len(faces),'max_position_error_mm':positions_error,'weight_error':error,'triangles_equal':faces==d['triangles'],'rig':ob.parent.name,'actions':len(bpy.data.actions)}
assert positions_error<.001 and error<1e-7 and report['triangles_equal']
# Cross product in Blender must agree with the saved custom normal overlay.
normals=np.array([list(n.vector) for n in ob.data.corner_normals]);t=np.array(faces);p=actual*[1,-1,1]
fn=np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]);fn/=np.maximum(np.linalg.norm(fn,axis=1,keepdims=True),1e-12)
dot=np.sum(fn*normals.reshape(-1,3,3).mean(1),axis=1);report['normal_direction_median_dot']=float(np.median(dot));assert report['normal_direction_median_dot']>.9
(O/'source_checks.json').write_text(json.dumps(report,indent=2));print('SUPER90_EDITABLE_CHECK_PASSED',report)
