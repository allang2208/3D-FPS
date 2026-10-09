"""Resolve the source normal-map convention from the gun's planar faces."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent/'BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(S/'Super90_Gameplay_Editable.blend'))
image=bpy.data.images.load(str(S/'Original/Source/textures/TTI_Benelli_M4_Normal_brand_friendly.png'),check_existing=False)
image.colorspace_settings.name='Non-Color'
import numpy as np
pixels=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(pixels)
w,h=image.size;pixels=pixels.reshape(h,w,4)
output={}
for name in ['Super90_body','Super90_bolt']:
    obj=bpy.data.objects[name];mesh=obj.data;mesh.calc_loop_triangles();mesh.calc_tangents(uvmap=mesh.uv_layers[0].name)
    rows=[]
    for tri in mesh.loop_triangles:
        if mesh.materials[tri.material_index].name!='TTI_Benelli_M4':continue
        if tri.area<.00005:continue
        uv=sum((mesh.uv_layers[0].data[i].uv for i in tri.loops),Vector((0,0)))/3
        # The numeric pixel array uses Blender's bottom-up image convention.
        rgb=pixels[min(h-1,int(uv.y*h)),min(w-1,int(uv.x*w)),:3]*2-1
        n=sum((mesh.corner_normals[i].vector for i in tri.loops),Vector()).normalized()
        t=sum((mesh.loops[i].tangent for i in tri.loops),Vector()).normalized()
        b=n.cross(t)*mesh.loops[tri.loops[0]].bitangent_sign
        values=[]
        for sign in (1,-1):
            mapped=(t*float(rgb[0])+b*float(rgb[1])*sign+n*float(rgb[2])).normalized()
            values.append(float(mapped.dot(tri.normal)))
        rows.append({'area':tri.area,'center':list(tri.center),'normal':list(tri.normal),
            'vertex_normal_dot':n.dot(tri.normal),'map_normal_dot_gl_dx':values})
    rows.sort(key=lambda x:x['area'],reverse=True)
    output[name]=rows[:20]
(O/'tangent_inputs.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps(output,indent=2))
