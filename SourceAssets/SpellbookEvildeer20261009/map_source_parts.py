import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'source-import.blend'))
result={}
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    uv=obj.data.uv_layers.active.data
    largest=sorted(obj.data.polygons,key=lambda p:p.area,reverse=True)[:8]
    result[obj.name]={'largest_faces':[{'area':round(p.area,4),'uv_center':[round(sum(uv[i].uv[k] for i in p.loop_indices)/len(p.loop_indices),4) for k in range(2)]} for p in largest]}
    if obj.name in ('openedbook','book2'):
        result[obj.name]['vertices']=[list(obj.matrix_world@v.co) for v in obj.data.vertices]
        result[obj.name]['faces']=[{'index':p.index,'verts':list(p.vertices),'uv':[[round(float(c),6) for c in uv[i].uv] for i in p.loop_indices]} for p in obj.data.polygons]
(ROOT/'source-parts.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
for name,row in result.items(): print(name,json.dumps(row['largest_faces'][:4]))
obj=bpy.data.objects['book2'];uv=obj.data.uv_layers.active.data
for p in obj.data.polygons:
    center=sum((obj.matrix_world@obj.data.vertices[v].co for v in p.vertices),__import__('mathutils').Vector())/len(p.vertices)
    u,v=[sum(uv[i].uv[k] for i in p.loop_indices)/len(p.loop_indices) for k in range(2)]
    if (u<.23 and .594<v<.685) or p.area>150:
        print('BOOK2FACE',p.index,'center',list(center),'uv',(u,v),'area',p.area)
