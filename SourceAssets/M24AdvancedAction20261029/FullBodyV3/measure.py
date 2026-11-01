import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
S=O.parents[1]
bpy.ops.wm.open_mainfile(filepath=str(S/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'),use_scripts=False)
result={'objects':[o.name for o in bpy.data.objects if o.type=='MESH']}
for name in ('M24_base','M24_barrel'):
 ob=bpy.data.objects.get(name)
 if not ob:continue
 vs=[v.co.copy() for v in ob.data.vertices]
 result[name]={'matrix':[list(r) for r in ob.matrix_world],'bounds':[[min(v[i] for v in vs),max(v[i] for v in vs)] for i in range(3)],'materials':[m.name for m in ob.data.materials]}
 result[name]['sections']={}
 for y in (-.08,-.05,0,.04,.08,.12,.18,.24,.28,.32,.40,.45,.50,.60):
  pts=[v for v in vs if abs(v.y-y)<.012]
  if pts:result[name]['sections'][str(y)]={'count':len(pts),'x':[min(v.x for v in pts),max(v.x for v in pts)],'z':[min(v.z for v in pts),max(v.z for v in pts)]}
ob=bpy.data.objects['M24_base']
src=ob.data;parent=list(range(len(src.vertices)));seen={}
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def unite(a,b):parent[root(a)]=root(b)
for v in src.vertices:
 key=tuple(round(x,6) for x in v.co)
 if key in seen:unite(v.index,seen[key])
 else:seen[key]=v.index
for e in src.edges:unite(*e.vertices)
islands={}
for v in src.vertices:islands.setdefault(root(v.index),[]).append(v.index)
result['stock_island']=root(0)
result['islands']=[dict(id=k,count=len(ids),bounds=[[round(min(src.vertices[i].co[j] for i in ids),5),round(max(src.vertices[i].co[j] for i in ids),5)] for j in range(3)]) for k,ids in islands.items() if len(ids)>12]
from mathutils.bvhtree import BVHTree
tree=BVHTree.FromPolygons([v.co for v in src.vertices],[list(p.vertices) for p in src.polygons])
result['underside']={}
for y in (.28,.32,.40,.45,.50,.59):
 result['underside'][str(y)]=[]
 for x in (-.02,-.01,0,.01,.02):
  hit,n,i,d=tree.ray_cast(Vector((x,y,-.1)),Vector((0,0,1)))
  result['underside'][str(y)].append([x,list(hit) if hit else None])
result['triangles_crossing_y']={str(y):sum(1 for p in ob.data.polygons if min(ob.data.vertices[i].co.y for i in p.vertices)<y<max(ob.data.vertices[i].co.y for i in p.vertices)) for y in (0,.02,.04,.06,.08,.10)}
bpy.ops.wm.open_mainfile(filepath=str(S/'M24Bipod20261029/M24_Bipod_Editable.blend'),use_scripts=False)
result['bipod']={}
for ob in bpy.data.objects:
 if ob.type=='MESH' and 'Base' in ob.name:
  pts=[ob.matrix_world@v.co for v in ob.data.vertices]
  result['bipod'][ob.name]=[[min(v[i] for v in pts),max(v[i] for v in pts)] for i in range(3)]
(O/'measurements.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
