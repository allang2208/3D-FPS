"""Read the authored grip/body contact surfaces to locate the reported overlap."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P = Path(__file__).parent
source = P.parent / 'BowModular20260926/Bow_ModularParts.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
body = bpy.data.objects['SM_Bow_BodyModular']
grip = bpy.data.objects['SM_Bow_GripWrap']
def info(obj):
    vs = [obj.matrix_world @ v.co for v in obj.data.vertices]
    return {'name':obj.name,'vertices':len(vs),'bounds':[[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)],'matrix':[list(r) for r in obj.matrix_world]}
bv = [body.matrix_world @ v.co for v in body.data.vertices]
tree = BVHTree.FromPolygons(bv,[list(p.vertices) for p in body.data.polygons])
records = []
for z in [-10,-7,-4,0,4,7,10]:
    row = {'z':z,'wood':[],'grip':[]}
    for o, target in [(body,'wood'),(grip,'grip')]:
        v=[o.matrix_world @ v.co for v in o.data.vertices]
        pts=[]
        for e in o.data.edges:
            a,b=[v[i] for i in e.vertices]
            if min(a.z,b.z)<=z<max(a.z,b.z):pts.append(a+(b-a)*((z-a.z)/(b.z-a.z)))
        if pts:row[target]=[[min(p[i] for p in pts),max(p[i] for p in pts)] for i in range(2)]
    records.append(row)
inside=[]
for v in grip.data.vertices:
    p=grip.matrix_world @ v.co
    center=Vector((-.7,0,p.z))
    d=p-center; radius=d.length; d.normalize()
    hit, _, _, _=tree.ray_cast(center+d*12,-d,24)
    if hit is not None:
        depth=(hit-center).dot(d)-radius
        if depth>.005:inside.append((depth,list(p)))
inside.sort(reverse=True)
result={'body':info(body),'grip':info(grip),'sections':records,'inside_vertices':len(inside),'deepest':inside[:4]}
adj=[[] for _ in grip.data.vertices]
for e in grip.data.edges:
    a,b=e.vertices;adj[a].append(b);adj[b].append(a)
unseen=set(range(len(adj)));groups=[]
while unseen:
    stack=[unseen.pop()];ids=stack.copy()
    while stack:
        for i in adj[stack.pop()]:
            if i in unseen:unseen.remove(i);stack.append(i);ids.append(i)
    zs=[grip.data.vertices[i].co.z for i in ids]
    groups.append({'count':len(ids),'z':[min(zs),max(zs)]})
result['shells']=sorted(groups,key=lambda x:x['z'][0])
with bpy.data.libraries.load(str(P.parent/'BowFlex20260927/Bow_ElasticBodies.blend'),link=False) as (a,b):
    b.objects=['SK_Bow_Flex_Original']
skin=b.objects[0]
result['skinned_body']=info(skin)
(P/'source-contact.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k not in ('sections','shells')}))
print('shells',len(groups),result['shells'][:3])
