import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ModulesV1/TacticalHatchet_Modules_Editable.blend'))
o=bpy.data.objects['SM_TacticalHatchet_Head_Factory'];m=o.data
result={'bounds':[[min(v.co[i] for v in m.vertices),max(v.co[i] for v in m.vertices)] for i in range(3)],'sections':[]}
for z in [.115,.16,.18,.19,.20,.22,.24,.26,.28,.30,.32,.34]:
    points=[]
    for e in m.edges:
        a,b=[m.vertices[i].co for i in e.vertices]
        if min(a.z,b.z)<=z<=max(a.z,b.z) and abs(b.z-a.z)>1e-9:points.append(a.lerp(b,(z-a.z)/(b.z-a.z)))
    if points:result['sections'].append({'z':z,'x':[min(p.x for p in points),max(p.x for p in points)],'y':[min(p.y for p in points),max(p.y for p in points)]})
(P/'source_sections.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
