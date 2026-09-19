import bpy,bmesh,json,sys,math
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;sys.path.insert(0,str(P.parent/'AttachmentIconAudit20260914'));from icon_geometry import components
out={}
for gun in ['M4','QBZ']:
 bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ExtMagRebuild20260919'/(gun+'_ExtMag_Editable.blend')));o=bpy.data.objects['Factory_'+gun];m=o.data;cfg=json.loads((P.parent/'ExtMagPattern20260919/parameters.json').read_text())[gun];cy,cz=cfg['center_yz'];R=cfg['radius_cm']/100;top=max((v.co for v in m.vertices),key=lambda p:p.z);tt=math.atan2(top.z-cz,top.y-cy)
 def unroll(p):return Vector((p.x,math.hypot(p.y-cy,p.z-cz)-R,math.atan2(math.sin(math.atan2(p.z-cz,p.y-cy)-tt),math.cos(math.atan2(p.z-cz,p.y-cy)-tt))*R))
 groups=components(m);out[gun]=[]
 for ids in groups:
  vs=[unroll(m.vertices[i].co) for i in ids];out[gun].append(dict(n=len(ids),bounds=[[min(v[k] for v in vs) for k in range(3)],[max(v[k] for v in vs) for k in range(3)]]))
 print(gun,json.dumps(out[gun]))
(P/'source_parts.json').write_text(json.dumps(out,indent=2))
