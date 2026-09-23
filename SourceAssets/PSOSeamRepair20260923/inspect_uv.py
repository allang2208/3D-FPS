import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDMatteDetail20260923/SVD_base_Editable.blend'))
ob=bpy.data.objects['SM_SVD_ScopeLens'];me=ob.data
parent=list(range(len(me.vertices)))
def root(i):
 while i!=parent[i]:parent[i]=parent[parent[i]];i=parent[i]
 return i
for e in me.edges:parent[root(e.vertices[1])]=root(e.vertices[0])
groups={}
for p in me.polygons:groups.setdefault(root(p.vertices[0]),[]).append(p)
out=[]
for fs in groups.values():
 vi={v for f in fs for v in f.vertices};uv=[list(me.uv_layers[0].data[i].uv) for f in fs for i in f.loop_indices]
 out.append({'faces':[f.index for f in fs],'vertices':len(vi),'uv_min':[min(p[k] for p in uv) for k in range(2)],'uv_max':[max(p[k] for p in uv) for k in range(2)]})
print('LENS_ISLANDS',[(len(r['faces']),r['vertices'],r['uv_min'],r['uv_max']) for r in out],flush=True)
(O/'lens_islands.json').write_text(json.dumps(out,indent=2))
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDSurface20260923/SVD_Surface_Editable.blend'))
print('AUTHOR_MATS',[(m.name,list(m.keys())) for m in bpy.data.materials if m.name.startswith('AUTH_SVD_pso')],flush=True)
