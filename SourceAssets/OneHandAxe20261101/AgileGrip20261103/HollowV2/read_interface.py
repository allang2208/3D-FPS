import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'TacticalHatchet_AgileGrip_Editable.blend'))
o=bpy.data.objects['SM_TacticalHatchet_GripAgile'];m=o.data
edges=[(m.vertices[e.vertices[0]].co.copy(),m.vertices[e.vertices[1]].co.copy()) for e in m.edges]
r={'bounds':[[min(v.co[i] for v in m.vertices),max(v.co[i] for v in m.vertices)] for i in range(3)],'sections':[]}
for z in [-.02,-.04,-.06,-.08,-.10,-.12,-.14,-.16,-.18]:
    pts=[a.lerp(b,(z-a.z)/(b.z-a.z)) for a,b in edges if min(a.z,b.z)<=z<=max(a.z,b.z) and abs(b.z-a.z)>1e-9]
    r['sections'].append({'z':z,'x':[min(p.x for p in pts),max(p.x for p in pts)],'y':[min(p.y for p in pts),max(p.y for p in pts)]})
(P/'interface_source.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
