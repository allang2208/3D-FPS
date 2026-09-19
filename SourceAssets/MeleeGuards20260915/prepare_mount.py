"""Read the actual guard surfaces and retain the original blade/grip interface."""
import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'OriginalGuardReference.blend'))
obj=bpy.data.objects['FrostCrystalSword_Blade'];mesh=obj.data
mat=mesh.materials[0]
images={}
for n in mat.node_tree.nodes:
    if n.type=='TEX_IMAGE':
        key='base'
        for suffix in ['normal','metallic','roughness']:
            if suffix in n.image.name:key=suffix
        image=n.image;pixels=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(pixels)
        images[key]=(image.size[0],image.size[1],pixels.reshape((image.size[1],image.size[0],4)))
uv=mesh.uv_layers.active.data
def sample(key,xy):
    w,h,pix=images[key]
    return pix[min(h-1,max(0,int((xy[1]%1)*h))),min(w-1,max(0,int((xy[0]%1)*w))),:3]
guard=[];keep=[];colors=[];metal=[];rough=[]
for f in mesh.polygons:
    center=sum((mesh.vertices[i].co for i in f.vertices),start=__import__('mathutils').Vector())/len(f.vertices)
    face_uv=[uv[i].uv for i in f.loop_indices]
    color=np.mean([sample('base',sum((v*w for v,w in zip(face_uv,weights)),start=__import__('mathutils').Vector((0,0)))) for weights in [(1/3,1/3,1/3),(.6,.2,.2),(.2,.6,.2),(.2,.2,.6)]],axis=0)
    is_guard=(-.048<center.z<.051 and ((color[0]>color[2]*1.12 and color[0]>color[1]*1.02) or abs(center.x)>.058))
    if is_guard:
        guard.append(f.index)
        if abs(center.x)<=.060:keep.append(f.index)
        colors.append(color.tolist())
        metal.append(float(np.mean([sample('metallic',uv[i].uv)[0] for i in f.loop_indices])))
        rough.append(float(np.mean([sample('roughness',uv[i].uv)[0] for i in f.loop_indices])))
data={'guard_faces':guard,'retained_guard_faces':keep,'mount_half_width_m':.060,
      'base_color_texture_median':np.median(colors,axis=0).tolist(),'metallic_median':float(np.median(metal)),
      'roughness_median':float(np.median(rough)),'coordinate_frame':'WPN_root canonical; +Z blade, X crossguard width, Y thickness; metres',
      'authoring_method':'Retain the original central guard and its blade/handle contacts; replace lateral quillons from x=+-6cm; loft the generated wings onto those exact cut-boundary vertices.'}
median=np.median(colors,axis=0)
sample_loop=min((i for fi in guard for i in mesh.polygons[fi].loop_indices),key=lambda i:float(np.linalg.norm(sample('base',uv[i].uv)-median)))
data['material_sample_uv']=list(uv[sample_loop].uv)
(P/'mount_source.json').write_text(json.dumps(data,indent=2))
print('MOUNT_SURFACES',len(guard),'RETAINED',len(keep),'COLOR',data['base_color_texture_median'],'METAL',data['metallic_median'],'ROUGH',data['roughness_median'],flush=True)
