import bpy,json,collections,math
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'StaticField_Editable.blend'))
rows=[];groups=collections.defaultdict(lambda:dict(objects=0,vertices=0,triangles=0));materials=collections.Counter()
for o in bpy.data.collections['StaticField_EditableParts'].objects:
    if o.type!='MESH':continue
    me=o.data;me.calc_loop_triangles();key=o.name.split('_')[0]
    groups[key]['objects']+=1;groups[key]['vertices']+=len(me.vertices);groups[key]['triangles']+=len(me.loop_triangles)
    for tri in me.loop_triangles:materials[me.materials[tri.material_index].name]+=1
    rows.append(dict(name=o.name,vertices=len(me.vertices),triangles=len(me.loop_triangles)))
report=dict(source=str(P.parent/'StaticField_Editable.blend'),groups=dict(groups),materials=dict(materials),total_triangles=sum(x['triangles'] for x in rows),objects=len(rows),top_objects=sorted(rows,key=lambda x:x['triangles'],reverse=True)[:16],rendered=False,modified=False)
(P/'source_geometry.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
