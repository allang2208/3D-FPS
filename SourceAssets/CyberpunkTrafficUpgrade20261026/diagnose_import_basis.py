"""Local source diagnosis for the actual FBX tangent import warning, no render."""
import bpy,json
from pathlib import Path
R=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(R/'Traffic_Source.blend'))
rows=[]
for c in bpy.data.collections:
 if not c.name.startswith('Source_'):continue
 for o in c.objects:
  me=o.data;badface=sum(p.area<1e-10 for p in me.polygons);badnormal=sum(n.vector.length<.01 for n in me.corner_normals)
  if badface or badnormal:rows.append(dict(object=o.name,bad_faces=badface,bad_normals=badnormal,faces=len(me.polygons)))
for o in bpy.context.scene.objects:
 if not o.name.startswith('SM_CT_'):continue
 me=o.data;uv=me.uv_layers[0];bad=0;badgeo=0
 for p in me.polygons:
  co=[uv.data[i].uv for i in p.loop_indices];det=(co[1].x-co[0].x)*(co[2].y-co[0].y)-(co[2].x-co[0].x)*(co[1].y-co[0].y)
  bad+=abs(det)<1e-12;badgeo+=p.area<1e-10
 me.calc_tangents(uvmap='SurfaceUV')
 rows.append(dict(object=o.name,bad_faces=badgeo,bad_normals=sum(n.vector.length<.01 for n in me.corner_normals),bad_tangents=sum(l.tangent.length<.01 for l in me.loops),active_uv=me.uv_layers.active.name,bad_uv=bad,faces=len(me.polygons)))
(R/'import_basis_diagnosis.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(json.dumps(rows))
