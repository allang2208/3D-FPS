import bpy,json
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Kukri_Refinement_Editable.blend'))
path=P/'surfaces.json';data=json.loads(path.read_text(encoding='utf-8'))
for e in data['variants']:
    if 'dynamics' not in e:continue
    obj=bpy.data.objects[e['object']]
    e['author_bounds_cm']=[[min(v.co[i] for v in obj.data.vertices)*100 for i in range(3)],[max(v.co[i] for v in obj.data.vertices)*100 for i in range(3)]]
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
