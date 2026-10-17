import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;D=json.loads((O/'grip_input.json').read_text(encoding='utf-8'))
g=D['geometry']['M870_body'];tree=BVHTree.FromPolygons(g['points'],g['faces'])
t=D['geometry']['M870_trigger'];trigger=BVHTree.FromPolygons(t['points'],t['faces'])
report={}
for kind in ('old_points','reference_points'):
 points=D[kind];rows={}
 for label,names in [('palm',['hand_r']),('thumb',['thumb_02_r','thumb_03_r']),('index',['index_03_r']),('middle',['middle_02_r','middle_03_r']),('ring',['ring_02_r','ring_03_r']),('pinky',['pinky_02_r','pinky_03_r'])]:
  ids=[i for i in D['hand_ids'] if sum(D['weights'][i].get(n,0) for n in names)>.85]
  surf=trigger if label=='index' else tree
  samples=[]
  for i in ids:
   p=Vector(points[i]);q,no,fi,d=surf.find_nearest(p);samples.append((d, (p-q).dot(no),i,list(q),list(no)))
  samples.sort()
  rows[label]={'nearest_mm':samples[0][0]*1000,'closest_vertex':samples[0][2],'surface_point':samples[0][3],'surface_normal':samples[0][4], 'deepest_negative_mm':min(v[1] for v in samples)*1000,'negative_over_2mm':sum(v[1]<-.002 for v in samples),'samples':len(samples)}
 report[kind]=rows
(O/'contact_layout.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
