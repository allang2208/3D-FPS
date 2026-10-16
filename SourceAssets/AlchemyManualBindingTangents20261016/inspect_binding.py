"""Locate the two reported FBX tangent warnings on the binding only; no render."""
from pathlib import Path
from collections import defaultdict
import bpy,json
ROOT=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'AlchemyManualPersistentLeaves20261016/AlchemyManualPersistentLeaves.blend'),load_ui=False,use_scripts=False)
obj=bpy.data.objects['SM_AlchemyManualBinding'];mesh=obj.data
mesh.calc_loop_triangles();uv=mesh.uv_layers.active.data
groups=defaultdict(lambda:dict(triangles=0,zero_area=0,collapsed_uv=0,examples=[]))
for tri in mesh.loop_triangles:
    group=groups[mesh.materials[tri.material_index].name];group['triangles']+=1
    a,b,c=[mesh.vertices[i].co for i in tri.vertices]
    x,y,z=[uv[i].uv for i in tri.loops]
    area=(b-a).cross(c-a).length*.5
    determinant=(y.x-x.x)*(z.y-x.y)-(y.y-x.y)*(z.x-x.x)
    if area<1e-10:group['zero_area']+=1
    if abs(determinant)<1e-10:
        group['collapsed_uv']+=1
        if len(group['examples'])<4:group['examples'].append(dict(polygon=tri.polygon_index,area=area,uv=[list(v) for v in (x,y,z)],positions=[list(v) for v in (a,b,c)]))
mesh.calc_tangents()
zero_tangent=sum(l.tangent.length<1e-4 for l in mesh.loops)
zero_bitangent=sum(l.bitangent.length<1e-4 for l in mesh.loops)
report=dict(mesh=obj.name,materials=dict(groups),zero_tangents=zero_tangent,zero_bitangents=zero_bitangent,vertices=len(mesh.vertices))
report['uv_layers']={}
for layer in mesh.uv_layers:
    stats=defaultdict(lambda:dict(triangles=0,collapsed_uv=0))
    for tri in mesh.loop_triangles:
        name=mesh.materials[tri.material_index].name
        if name not in ('ManualAntiqueBrass','ManualLeatherBinding'):continue
        x,y,z=[layer.data[i].uv for i in tri.loops]
        stats[name]['triangles']+=1
        if abs((y.x-x.x)*(z.y-x.y)-(y.y-x.y)*(z.x-x.x))<1e-10:stats[name]['collapsed_uv']+=1
    report['uv_layers'][layer.name]=dict(stats)
(ROOT/'binding-diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
