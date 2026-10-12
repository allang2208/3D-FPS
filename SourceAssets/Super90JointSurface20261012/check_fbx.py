import bpy,json,gzip
from pathlib import Path
import numpy as np
from mathutils.kdtree import KDTree
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(S/'Exports/SK_Super90_BareArmsV7.fbx'),use_anim=False)
d=json.loads(gzip.decompress((O/'arms_before.json.gz').read_bytes()));expected=np.array(d['positions'])
for i,p in json.loads((O/'patches.json').read_text())['arms']['positions']:expected[i]=p
tree=KDTree(len(expected))
for i,p in enumerate(expected):tree.insert(p,i)
tree.balance();max_pos=0.;max_weight=0.;count=0;faces=0
for ob in bpy.context.scene.objects:
 if ob.type!='MESH':continue
 groups={g.index:g.name for g in ob.vertex_groups}
 for vertex in ob.data.vertices:
  q=ob.matrix_world@vertex.co;q=(q.x*100,-q.y*100,q.z*100)
  _,i,dist=tree.find(q);max_pos=max(max_pos,dist*10)
  row={groups[g.group]:g.weight for g in vertex.groups};old=d['weights'][i]
  max_weight=max(max_weight,max((abs(row.get(n,0)-old.get(n,0)) for n in set(row)|set(old)),default=0));count+=1
 faces+=len(ob.data.polygons)
report=dict(vertices=count,triangles=faces,max_position_error_mm=max_pos,max_weight_error=max_weight)
assert count==len(expected) and faces==len(d['triangles']) and max_pos<.002 and max_weight<2e-6,report
(O/'fbx_checks.json').write_text(json.dumps(report,indent=2));print('SUPER90_FBX_ROUNDTRIP_PASSED',report)
