import bpy,json,collections
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'ASH12ExtendedMagazine20260919/ASH12_ExtMag30_Editable.blend'));ob=bpy.data.objects['SM_ASH12_ExtMag30'];m=ob.data
F=Matrix(json.loads((S/'ASH12ExtendedMagazine20260919/authoring.json').read_text())['ASH12']['frame']);out={}
for attr in m.color_attributes:
 rows=collections.defaultdict(list)
 for p in m.polygons:
  z=sum((F@m.vertices[v].co).z for v in p.vertices)/len(p.vertices)
  for li in p.loop_indices:
   c=tuple(round(x,3) for x in attr.data[li if attr.domain=='CORNER' else m.loops[li].vertex_index].color)
   rows[(p.material_index,c)].append(z)
 out[attr.name]=[dict(slot=k[0],color=k[1],corners=len(v),z_min=min(v),z_max=max(v)) for k,v in rows.items()]
(O/'vertex_regions.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
