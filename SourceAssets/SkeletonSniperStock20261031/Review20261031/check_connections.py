import json,gzip
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
import numpy as np
O=Path(__file__).resolve().parent
D=json.load(gzip.open(O/'saved_geometry.json.gz','rt'));metrics=json.loads((O/'fit_metrics.json').read_text())
report={}
for key,row in D.items():
 h=row['host'];s=row['stock'];mount=Matrix(metrics[key]['stock_component_matrix'])
 hv=np.array(h['positions']);hf=np.array(h['triangles']);hi=np.array(h['material_ids'])
 mask=[i for i,m in enumerate(h['materials']) if m['slot'] in ('M24_FactoryStock','SVD_FactoryStock','KVInhibitor_stock') or m['slot'].startswith('MI_Manny')]
 hv=[Vector(p) for p in hv];sv=[mount@Vector(p) for p in s['positions']];sf=np.array(s['triangles']);si=np.array(s['material_ids'])
 trees=[BVHTree.FromPolygons(hv,hf[~np.isin(hi,mask)].tolist(),all_triangles=True),BVHTree.FromPolygons(sv,sf[si==0].tolist(),all_triangles=True),BVHTree.FromPolygons(sv,sf[si==1].tolist(),all_triangles=True)]
 report[key]={'host_adapter_intersecting_triangle_pairs':len(trees[0].overlap(trees[2])),
 'stock_adapter_intersecting_triangle_pairs':len(trees[1].overlap(trees[2])),
 'host_stock_intersecting_triangle_pairs':len(trees[0].overlap(trees[1]))}
(O/'connection_contacts.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
