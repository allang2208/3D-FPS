import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix
P=Path(__file__).parent;bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ASH12Surface20260919/ASH12_Surface_Editable.blend'));g=bpy.data.objects['ASH12_Export'];F=Matrix(json.loads((P/'source_measurements.json').read_text())['matrix']);p=np.array([tuple(F@v.co) for v in g.data.vertices]);ids={v for f in g.data.polygons if f.material_index==3 for v in f.vertices};es=np.array([tuple(e.vertices) for e in g.data.edges if all(v in ids for v in e.vertices)]);a=p[es[:,0]];b=p[es[:,1]];rows=[]
for z in np.linspace(-.08,-.19,23):
 ok=(a[:,2]-z)*(b[:,2]-z)<0;aa=a[ok];bb=b[ok];hits=aa+(bb-aa)*((z-aa[:,2])/(bb[:,2]-aa[:,2]))[:,None];rows.append([float(z),float(hits[:,0].min()),float(hits[:,0].max())])
(P/'sections.json').write_text(json.dumps(rows));print('SECTIONS',rows)
