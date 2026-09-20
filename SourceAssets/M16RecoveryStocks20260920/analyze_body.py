import bpy,bmesh,json,math
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M16UniversalAttachments20260920/M16_CommonAttachments_Editable.blend'),use_scripts=False)
report={}
for key in ['skeleton','qr_performance','core_stock','tactical_telescopic']:
 o=bpy.data.objects['SM_M16_'+key];bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index==0],context='FACES')
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
 rows=[]
 for y in [.043,.046,.050,.055]:
  hits=[]
  for e in bm.edges:
   a,b=[v.co for v in e.verts]
   if (a.y-y)*(b.y-y)>0 or abs(a.y-b.y)<1e-9:continue
   p=a.lerp(b,(y-a.y)/(b.y-a.y));r=math.hypot(p.x+.000038,p.z-.0917)
   hits.append(r)
  rows.append({'y':y,'radial_mm':sorted(set(round(v*1000,3) for v in hits))})
 boundary=[{'verts':[list(v.co) for v in e.verts],'faces':len(e.link_faces),'length_mm':e.calc_length()*1000} for e in bm.edges if e.is_boundary]
 report[key]={'cross_sections':rows,'boundary':boundary}
 bm.free()
(O/'body_analysis.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
