import bpy,json,collections
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'ThorSeatsPrecisionV4.blend'))
names=['SM_ThunderGodHammer_head_mount_factory']+[r['mesh'] for r in json.loads((P/'model_manifest.json').read_text(encoding='utf-8'))['parts']]
rows=[]
for name in names:
 m=bpy.data.objects[name].data;m.calc_tangents(uvmap=m.uv_layers[0].name);bad=collections.Counter();zero_uv=collections.Counter();zero_geometry=collections.Counter()
 for f in m.polygons:
  material=m.materials[f.material_index].name
  if f.area<1e-14:zero_geometry[material]+=1
  if any(m.loops[i].tangent.length<1e-4 or m.loops[i].bitangent.length<1e-4 for i in f.loop_indices):bad[material]+=1
  if len(f.loop_indices)==3:
   u,v,w=[m.uv_layers[0].data[i].uv for i in f.loop_indices];a=v-u;b=w-u
   if abs(a.x*b.y-a.y*b.x)<1e-12:zero_uv[material]+=1
 rows.append(dict(mesh=name,bad_tangent_faces=dict(bad),collapsed_uv_faces=dict(zero_uv),degenerate_faces=dict(zero_geometry)))
(P/'tangent_inspection.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows),flush=True)
