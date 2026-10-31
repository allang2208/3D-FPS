"""User-requested kitchen intersection checks; no rendering or game run."""
from pathlib import Path
import bpy,bmesh,json
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parent;K=R.parent/'CyberpunkApartmentRebuild20261022/KitchenPilot20261024'
bpy.ops.wm.open_mainfile(filepath=str(R/'KitchenRepair.blend'))
def tree(o,offset):
    m=o.data;m.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co+Vector(offset) for v in m.vertices],[tuple(t.vertices) for t in m.loop_triangles],all_triangles=True,epsilon=0)
sink=tree(bpy.data.objects['KIT_Sink'],(7.83,13.12,.947));oven=tree(bpy.data.objects['KIT_Oven'],(9.82,13.12,.947))
result=dict(check_scope='requested kitchen component intersections',pairs={},closed_shells={})
for name,x in [('SinkBody0',7.4),('SinkBody1',8.0)]:result['pairs']['Sink:'+name]=len(sink.overlap(tree(bpy.data.objects['KIT_'+name],(x,13.12,0))))
with bpy.data.libraries.load(str(K/'KitchenDetailV1.blend'),link=False) as (s,d):d.objects=['KIT_BaseBody','KIT_BaseFront','KIT_Counter','KIT_BackSplash','KIT_Dishes']
source={o.name:o for o in d.objects}
for name in ['KIT_BaseBody','KIT_BaseFront']:
    for side,x in [('Left',9.2),('Right',10.4)]:
        offset=(x,13.12,0) if name.endswith('Body') else (x-.2775,13.12-.349,0)
        result['pairs']['Oven:'+side+name]=len(oven.overlap(tree(source[name],offset)))
result['pairs']['Sink:Dishes']=len(sink.overlap(tree(source['KIT_Dishes'],(8.16,12.975,.947))))
result['pairs']['Sink:BackSplash']=len(sink.overlap(tree(source['KIT_BackSplash'],(8.9,13.474,1.225))))
for name in ['KIT_Sink','KIT_SinkBody0','KIT_SinkBody1','KIT_Oven']:
    bm=bmesh.new();bm.from_mesh(bpy.data.objects[name].data)
    result['closed_shells'][name]=dict(boundary_edges=sum(e.is_boundary for e in bm.edges),nonmanifold_edges=sum(not e.is_manifold for e in bm.edges),zero_area_faces=sum(f.calc_area()<1e-12 for f in bm.faces));bm.free()
result['all_clear']=not any(result['pairs'].values()) and all(v['boundary_edges']==0 and v['zero_area_faces']==0 for v in result['closed_shells'].values())
(R/'source_layout_check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
