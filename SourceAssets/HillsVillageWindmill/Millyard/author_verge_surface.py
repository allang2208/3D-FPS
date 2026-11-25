"""Bake the two surveyed verge shoulders and the exposed gravel into one fitted skin."""
import json
import math
import os
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from earth_form import elevation
from author_work_tools import reset
from author_work_tools import save

src=HERE/'WorkDetails'
layout=json.loads((src/'MillVergeLayout.json').read_text(encoding='utf8'))
x0,x1,y0,y1=layout['extent']
banks=layout['banks']
# PNG data is presented bottom-up by Blender. The same pixel coordinates become
# UE UVs after legacy FBX reverses V. The source Y axis is reflected on import.
mask=bpy.data.images.load(str(src/'MillVergeMask.png'))
mw,mh=mask.size[:]
mask.colorspace_settings.name='Non-Color'
pixels=np.empty(mw*mh*4,dtype=np.float32)
mask.pixels.foreach_get(pixels)
alpha=pixels.reshape(mh,mw,4)[::-1,:,0].copy()
reset()
survey=np.load(src/'MillVergeSurvey.npz')['ground']

def support(x,y):
    row=int(np.clip(round((y-y0)/20),0,survey.shape[0]-1))
    col=int(np.clip(round((x-x0)/20),0,survey.shape[1]-1))
    z=survey[row,col]
    if z<-100:
        # Only feather polygons reach an unsurveyed edge. They run underneath
        # the opacity cutoff, at the level village pad datum.
        z=-4.
    for bx,by,heading,s,bz in banks:
        dx=x-bx;dy=y-by
        a=math.radians(heading)
        lx=dx*math.cos(a)+dy*math.sin(a)
        ly=-dx*math.sin(a)+dy*math.cos(a)
        z=max(z,bz+s[2]*elevation(lx/s[0],-ly/s[1],252,88,21,False))
    return float(z)+1.05

nx=math.ceil((x1-x0)/9)
ny=math.ceil((y1-y0)/9)
verts=[];faces=[];indices={};uvs=[]
def vertex(i,j):
    if (i,j) not in indices:
        u,v=i/nx,j/ny
        x,y=x0+u*(x1-x0),y0+v*(y1-y0)
        indices[i,j]=len(verts)
        verts.append((x,-y,support(x,y)));uvs.append((u,1-v))
    return indices[i,j]

for j in range(ny):
    for i in range(nx):
        ax=max(0,int(i*mw/nx)-2);bx=min(mw,int((i+1)*mw/nx)+3)
        ay=max(0,int(j*mh/ny)-2);by=min(mh,int((j+1)*mh/ny)+3)
        if np.max(alpha[ay:by,ax:bx])<.038:continue
        faces.append(tuple(vertex(u,v) for u,v in ((i,j),(i,j+1),(i+1,j+1),(i+1,j))))
me=bpy.data.meshes.new('Windmill verge surface');me.from_pydata(verts,[],faces);me.update()
ob=bpy.data.objects.new('Fitted turf and gravel',me);bpy.context.collection.objects.link(ob)
me.materials.append(bpy.data.materials.new('Ground'))
uv=me.uv_layers.new(name='Yard UV')
for poly in me.polygons:
    poly.use_smooth=True
    for k in poly.loop_indices:uv.data[k].uv=uvs[me.loops[k].vertex_index]
save('VergeSurface')
print('Mill verge: vertices',len(verts),'triangles',len(faces)*2)
