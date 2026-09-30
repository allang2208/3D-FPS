import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Detail35/LMG201_D35_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];inv=(r.matrix_world@r.data.bones['WPN_root'].matrix_local).inverted();ob=bpy.data.objects['TopCover'];v=np.array([inv@ob.matrix_world@x.co for x in ob.data.vertices]);rows=[]
for i,m in enumerate(ob.data.materials):
 fs=[p for p in ob.data.polygons if p.material_index==i];ids=sorted({vi for p in fs for vi in p.vertices})
 if not ids:continue
 q=v[ids];edge=[np.linalg.norm(v[p.vertices[j]]-v[p.vertices[(j+1)%len(p.vertices)]]) for p in fs for j in range(len(p.vertices))]
 rows.append({'material':m.name,'vertices':len(ids),'faces':len(fs),'bounds':np.stack([q.min(0),q.max(0)]).tolist(),'max_edge_m':float(max(edge)),'outside_original_lid_region':int(((abs(q[:,0]-.0008)>.045)|(q[:,1]<-.25)|(q[:,1]>-.08)|(q[:,2]<.05)|(q[:,2]>.095)).sum())})
np.savez_compressed(O/'lid_vertices.npz',vertices=v)
(O/'source_geometry.json').write_text(json.dumps(rows,indent=2));print('LID_SOURCE',json.dumps(rows),flush=True)
