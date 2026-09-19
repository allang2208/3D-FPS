"""Choose a continuous bronze-only texture patch for the new guard surfaces."""
import bpy,json,numpy as np
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'OriginalGuardReference.blend'))
obj=bpy.data.objects['FrostCrystalSword_Blade'];mesh=obj.data
image=next(n.image for n in mesh.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and not any(s in n.image.name for s in ['normal','metallic','roughness']))
w,h=image.size;data=np.empty(len(image.pixels),np.float32);image.pixels.foreach_get(data);data=data.reshape((h,w,4))
warm=(data[:,:,0]>data[:,:,1]*1.09)&(data[:,:,0]>data[:,:,2]*1.20)&(data[:,:,0]>.08)
# Restrict the patch search to actual outer-quillon UVs, excluding the pommel.
points=[]
for f in mesh.polygons:
    center=sum(mesh.vertices[v].co.x for v in f.vertices)/len(f.vertices)
    if abs(center)>.065:
        uv=sum((mesh.uv_layers.active.data[i].uv for i in f.loop_indices),__import__('mathutils').Vector((0,0)))/3
        points.append((min(h-1,max(0,int(uv.y*h))),min(w-1,max(0,int(uv.x*w)))))
integral=np.pad(warm.astype(np.int64),((1,0),(1,0))).cumsum(0).cumsum(1)
winner=None
for size in [96,80,64,48,32,24,16,8]:
    for y,x in points:
        x0=x-size//2;y0=y-size//2;x1=x0+size;y1=y0+size
        if x0<0 or y0<0 or x1>w or y1>h:continue
        count=integral[y1,x1]-integral[y0,x1]-integral[y1,x0]+integral[y0,x0]
        if count==size*size:
            patch=data[y0:y1,x0:x1,:3]
            score=float(np.linalg.norm(np.median(patch.reshape((-1,3)),axis=0)-np.array([.35,.27,.20])))
            if winner is None or score<winner[0]:winner=(score,x0,y0,x1,y1)
    if winner:break
if winner is None:raise RuntimeError('No continuous bronze patch in original guard texture')
_,x0,y0,x1,y1=winner
# Half-pixel insets prevent bilinear filtering from sampling neighboring colors.
finish={'uv_min':[(x0+1)/w,(y0+1)/h],'uv_max':[(x1-1)/w,(y1-1)/h],
        'source_image':image.name,'pixel_bounds':[x0,y0,x1,y1],
        'method':'Continuous bronze-only patch from original quillon; reused by all three guards.'}
(P/'finish_patch.json').write_text(json.dumps(finish,indent=2));print('BRONZE_FINISH',finish,flush=True)
