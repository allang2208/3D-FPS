import bpy,json
from pathlib import Path
from collections import defaultdict
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006';O.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
ob=bpy.data.objects['Super90_body'];me=ob.data
parent=list(range(len(me.vertices)))
def find(i):
    while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
    return i
def join(a,b):parent[find(a)]=find(b)
points={}
for v in me.vertices:
    key=tuple(round(x,6) for x in v.co)
    if key in points:join(v.index,points[key])
    else:points[key]=v.index
for e in me.edges:join(*e.vertices)
groups=defaultdict(list)
for v in me.vertices:groups[find(v.index)].append(v.index)
rows=[]
for vs in groups.values():
    p=[me.vertices[i].co for i in vs];lo=[min(v[k] for v in p) for k in range(3)];hi=[max(v[k] for v in p) for k in range(3)]
    rows.append({'id':min(vs),'vertices':vs,'lo':lo,'hi':hi})
(O/'body_regions.json').write_text(json.dumps(rows))
print('TOP_REGIONS',json.dumps([{k:v for k,v in row.items() if k!='vertices'}|{'count':len(row['vertices'])} for row in rows if row['hi'][2]>-.733]))
tops=defaultdict(list)
for face in me.polygons:
    if face.normal.z>.98 and face.center.z>-.735 and -.16<face.center.y<.15:
        tops[round(face.center.z,6)].append(face)
print('RAIL_PLANES',json.dumps([{'z':z,'area':sum(f.area for f in fs),'y':[min(me.vertices[v].co.y for f in fs for v in f.vertices),max(me.vertices[v].co.y for f in fs for v in f.vertices)],'x':[min(me.vertices[v].co.x for f in fs for v in f.vertices),max(me.vertices[v].co.x for f in fs for v in f.vertices)]} for z,fs in sorted(tops.items())]))
