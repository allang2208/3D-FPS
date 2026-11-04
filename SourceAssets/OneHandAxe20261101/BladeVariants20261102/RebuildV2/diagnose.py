import bpy,json,math,statistics
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'TacticalHatchet_BladeVariants_Editable.blend'))
names=['SwiftCrescent','HeavyCleaver','FoldedArc']
report={}
for name in names:
 o=bpy.data.objects['SM_TacticalHatchet_Head_'+name];m=o.data;m.calc_loop_triangles()
 region=[v.co for v in m.vertices if .07<v.co.x<.11 and .26<v.co.z<.29 and v.co.y>.001]
 tris=[t for t in m.loop_triangles if all(.07<m.vertices[i].co.x<.11 and .26<m.vertices[i].co.z<.29 and m.vertices[i].co.y>.001 for i in t.vertices)]
 angles=[math.degrees(math.acos(min(1,abs(t.normal.y)))) for t in tris]
 report[name]={'triangles':len(m.loop_triangles),'sample_count':len(region),
   'face_y_span_mm':(max(v.y for v in region)-min(v.y for v in region))*1000,
   'geometric_normal_tilt_deg_max':max(angles),'geometric_normal_tilt_deg_median':statistics.median(angles)}
factory=bpy.data.objects['SM_TacticalHatchet_Head_Factory'];m=factory.data
sections={}
for z in [.115,.16,.18,.19,.20,.22,.24,.26,.28,.30,.32]:
 points=[]
 for e in m.edges:
  a,b=(m.vertices[i].co for i in e.vertices)
  if min(a.z,b.z)<=z<=max(a.z,b.z) and abs(b.z-a.z)>1e-9:points.append(a.lerp(b,(z-a.z)/(b.z-a.z)))
 if points:sections[str(z)]={'min_cm':[min(v[k] for v in points)*100 for k in range(3)],'max_cm':[max(v[k] for v in points)*100 for k in range(3)]}
(P/'diagnosis.json').write_text(json.dumps({'variants':report,'factory_sections':sections},indent=2))
print(json.dumps({'variants':report,'factory_sections':sections}),flush=True)
