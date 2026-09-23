"""Read local surface contacts of the user-reported held pose for authoring."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
d=json.loads((S/'SVDNaturalGrasp20260923/inputs.json').read_text());surface=json.loads((O/'before_surface.json').read_text())
fit=json.loads((S/'SVDNaturalGrasp20260923/grasp_fit.json').read_text());oldpads=json.loads((S/'SVDMagazineFit20260923/grasp_fit.json').read_text())['pad_regions']
hand=surface['parts'][0];mag=surface['parts'][1];tree=BVHTree.FromPolygons([Vector(v) for v in mag['vertices']],mag['faces'])
out={}
for n in oldpads:
 ids=oldpads[n];actual=[]
 for i in ids:
  v=Vector(hand['vertices'][i]);closest,normal,face,dist=tree.find_nearest(v)
  actual.append(dist*1000)
 inv=Matrix(d['rest'][n]).inverted();local=[inv@Vector(d['vertices'][i]) for i in ids]
 allids=[i for i,l in enumerate(d['labels']) if l==n];whole=[inv@Vector(d['vertices'][i]) for i in allids]
 out[n]={'actual_patch_mean_mm':sum(actual)/len(actual),'patch_max_mm':max(actual),
  'patch_bone_local_mean_mm':[sum(v[k] for v in local)/len(local)*1000 for k in range(3)],
  'bone_local_min_mm':[min(v[k] for v in whole)*1000 for k in range(3)],'bone_local_max_mm':[max(v[k] for v in whole)*1000 for k in range(3)],
  'joint_in_mag_mm':[x*1000 for x in surface['joints'][n]]}
(O/'contact_inputs.json').write_text(json.dumps(out,indent=2))
for n,x in out.items():print(n,'true_pad_mean_mm',round(x['actual_patch_mean_mm'],2),'bone_local_patch',list(map(lambda y:round(y,1),x['patch_bone_local_mean_mm'])),'joint',list(map(lambda y:round(y,1),x['joint_in_mag_mm'])),flush=True)
