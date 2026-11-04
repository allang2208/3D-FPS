"""Compare preserved author normals with the source and the documented grip transform."""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'TacticalHatchet_Editable.blend'))
m=next(o.data for o in bpy.context.scene.objects if o.type=='MESH')
actual=[n.vector.copy() for n in m.corner_normals]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P.parent/'Original/Meshy_AI_Tactical_Hatchet_1101133535_texture.glb'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
m=obj.data
model=json.loads((P.parent/'model.json').read_text('utf-8'))
origin=Vector(model['source_grip_origin']);fx,fy=model['grip_fit_xy']
dots=[]
for loop,n,a in zip(m.loops,m.corner_normals,actual):
    p=m.vertices[loop.vertex_index].co;q=p-origin
    t=max(0.,min(1.,p.z/.25));w=1.-t*t*(3.-2.*t)
    dw=-(6.*t-6.*t*t)/.25 if 0.<p.z<.25 else 0.
    sx=1.+(fx-1.)*w;sy=1.+(fy-1.)*w
    jac=Matrix(((-sx,0.,-q.x*(fx-1.)*dw),(0.,-sy,-q.y*(fy-1.)*dw),(0.,0.,1.)))
    e=(jac.inverted().transposed()@n.vector).normalized()
    dots.append(e.dot(a))
r={'corners':len(dots),'minimum_dot':min(dots),'mean_dot':sum(dots)/len(dots),'opposite_corners':sum(v<0 for v in dots),'below_099':sum(v<.99 for v in dots)}
(P/'normal_comparison.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
print('HATCHET_NORMAL_COMPARISON '+json.dumps(r))
