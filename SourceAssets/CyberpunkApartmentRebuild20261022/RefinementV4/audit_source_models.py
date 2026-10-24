"""Requested per-model source checks; no frame render or game launch."""
from pathlib import Path
import json,math
import bpy
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'CyberpunkApartment_Rebuild.blend'))
manifest=json.loads((ROOT/'assembly.json').read_text('utf8'));rows=[]
for spec in manifest['meshes']:
 o=bpy.data.objects.get(spec['name'])
 if not o or o.type!='MESH':raise RuntimeError('Missing author prototype '+spec['name'])
 mesh=o.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active
 finite=all(math.isfinite(v) for p in mesh.vertices for v in p.co)
 zero_geo=sum(t.area<1e-12 for t in mesh.loop_triangles)
 zero_uv=0
 if uv:
  for t in mesh.loop_triangles:
   a,b,c=[uv.data[i].uv for i in t.loops]
   if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-14:zero_uv+=1
 rows.append(dict(key=spec['key'],finite=finite,triangles=len(mesh.loop_triangles),zero_area_triangles=zero_geo,
  has_uv=bool(uv),zero_uv_triangles=zero_uv,materials=[m.name for m in mesh.materials],
  changed_in_v4=not bool(spec.get('reused_revision')),role='source geometry only; glass/text/screens may be open surfaces'))
report=dict(models=rows,model_count=len(rows),finite_all=all(r['finite'] for r in rows),
 missing_uv=[r['key'] for r in rows if not r['has_uv']],
 zero_area=[{'key':r['key'],'count':r['zero_area_triangles']} for r in rows if r['zero_area_triangles']],
 zero_uv=[{'key':r['key'],'count':r['zero_uv_triangles']} for r in rows if r['zero_uv_triangles']],
 inspection_requested=True,rendered=False,game_run=False)
(ROOT/'source-model-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('APARTMENT_SOURCE_CHECK',json.dumps({k:v for k,v in report.items() if k!='models'}))
