"""Read the actual retained riser surface for authoring the wooden saddle."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).parent;BASE=P.parent/'DarkBow20260925/WoodLongbow20260925'
bpy.ops.wm.open_mainfile(filepath=str(BASE/'WoodLongbow_Editable.blend'))
o=bpy.data.objects['SM_DarkBow_WoodLongbow']
# This saved Blend is the centimetre export source; convert Blender Y to UE Y.
scale=100 if max(o.dimensions)<5 else 1
verts=[o.matrix_world@v.co*scale for v in o.data.vertices]
verts=[Vector((v.x,-v.y,v.z)) for v in verts]
faces=[list(p.vertices) for p in o.data.polygons]
# Select the largest connected shell (wooden body), excluding bound cord loops.
adj=[[] for v in verts]
for e in o.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
unseen=set(range(len(verts)));islands=[]
while unseen:
    seed=unseen.pop();stack=[seed];group=[seed]
    while stack:
        for v in adj[stack.pop()]:
            if v in unseen:unseen.remove(v);stack.append(v);group.append(v)
    islands.append(group)
body=set(max(islands,key=lambda g:max(verts[i].z for i in g)-min(verts[i].z for i in g)))
body_faces=[(p,face) for p,face in enumerate(faces) if face[0] in body]
tree=BVHTree.FromPolygons(verts,[f for p,f in body_faces],all_triangles=False)
uv=o.data.uv_layers.active
samples=[]
for z in (10,12,14,16,18,20,22):
    p,n,i,d=tree.find_nearest(Vector((0,-4,z)))
    face=body_faces[i][0];poly=o.data.polygons[face]
    samples.append({'z':z,'surface_cm':list(p),'normal':list(n),'uv':list(uv.data[poly.loop_start].uv)})
info={'units_cm_scale':scale,'samples':samples,'body_vertices':len(body),'shells':len(islands),
      'shell_bounds':[{'vertices':len(g),'min':[min(verts[i][k] for i in g) for k in range(3)],
                       'max':[max(verts[i][k] for i in g) for k in range(3)]} for g in islands]}
(P/'mount-source.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
