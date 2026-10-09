"""Read adjacent source triangles to resolve the normal bake convention."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
im=bpy.data.images.load(str(S/'Original/Source/textures/TTI_Benelli_M4_Normal_brand_friendly.png'),check_existing=False)
im.colorspace_settings.name='Non-Color';px=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(px);w,h=im.size;px=px.reshape(h,w,4)
obj=bpy.data.objects['Super90_body'];me=obj.data;me.calc_loop_triangles();me.calc_tangents(uvmap=me.uv_layers[0].name)
def sample(uv):
    x=uv.x*w-.5;y=uv.y*h-.5;ix=int(x);iy=int(y);fx=x-ix;fy=y-iy
    return ((px[iy%h,ix%w,:3]*(1-fx)+px[iy%h,(ix+1)%w,:3]*fx)*(1-fy)+(px[(iy+1)%h,ix%w,:3]*(1-fx)+px[(iy+1)%h,(ix+1)%w,:3]*fx)*fy)*2-1
edges={};counts={'gl':[],'dx':[],'negx':[],'negxy':[]};pos=[]
for tr in me.loop_triangles:
    if me.materials[tr.material_index].name!='TTI_Benelli_M4':continue
    for j in range(3):
        loops=[tr.loops[j],tr.loops[(j+1)%3]];vs=[me.vertices[me.loops[i].vertex_index].co for i in loops]
        key=tuple(sorted(tuple(round(c,6) for c in v) for v in vs))
        uv=sum((me.uv_layers[0].data[i].uv for i in loops),Vector((0,0)))/2
        n=sum((me.corner_normals[i].vector for i in loops),Vector()).normalized()
        t=sum((me.loops[i].tangent for i in loops),Vector()).normalized();b=n.cross(t)*me.loops[loops[0]].bitangent_sign
        rgb=sample(uv);norms={}
        for label,sx,sy in [('gl',1,1),('dx',1,-1),('negx',-1,1),('negxy',-1,-1)]:norms[label]=(t*float(rgb[0])*sx+b*float(rgb[1])*sy+n*float(rgb[2])).normalized()
        edges.setdefault(key,[]).append((n,norms,tr.normal.copy(),uv,vs[0]-vs[1]))
for key,rows in edges.items():
    if len(rows)!=2:continue
    a,b=rows
    if a[2].dot(b[2])<.9:continue
    if a[0].dot(b[0])<.98:continue
    for label in counts:counts[label].append(1-a[1][label].dot(b[1][label]))
    if len(pos)<30 and counts['gl'][-1]>0.02:pos.append({'edge':key,'gl':counts['gl'][-1],'dx':counts['dx'][-1]})
result={k:{'mean':float(np.mean(v)),'p95':float(np.quantile(v,.95)),'p99':float(np.quantile(v,.99)),'bad':sum(x>.02 for x in v),'edges':len(v)} for k,v in counts.items()}
result['examples']=pos
areas=[];scores={k:[] for k in ['orig_gl','orig_dx','rot_gl','rot_dx','geometry']}
for tr in me.loop_triangles:
    if me.materials[tr.material_index].name!='TTI_Benelli_M4' or tr.area<1.e-7:continue
    uv=sum((me.uv_layers[0].data[i].uv for i in tr.loops),Vector((0,0)))/3
    n=sum((me.corner_normals[i].vector for i in tr.loops),Vector()).normalized()
    t=sum((me.loops[i].tangent for i in tr.loops),Vector()).normalized();b=n.cross(t)*me.loops[tr.loops[0]].bitangent_sign
    for rot in [False,True]:
        rgb=sample(Vector((1-uv.x,1-uv.y)) if rot else uv)
        for g in [1,-1]:
            mapped=(t*float(rgb[0])+b*float(rgb[1])*g+n*float(rgb[2])).normalized()
            scores[('rot' if rot else 'orig')+('_gl' if g==1 else '_dx')].append(1-mapped.dot(tr.normal))
    scores['geometry'].append(1-n.dot(tr.normal));areas.append(tr.area)
result['area_alignment']={k:float(np.average(v,weights=areas)) for k,v in scores.items()}
(O/'normal_convention.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
