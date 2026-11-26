"""Sample the selected Meshy neck around the clothes opening; each atlas row is a real horizontal section."""
from pathlib import Path
import json
import math
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
import trimesh
from pattern import SRC

head=SRC/"HeadR4"
out=SRC/"WorkwearR6"
fit=json.loads((head/"fit.json").read_text())
mesh=trimesh.load_scene(head/"Head/Head.glb",process=False).dump()[0]
p=(np.asarray(mesh.vertices)[:,[0,2,1]]-fit["nose_source"])*fit["uniform_scale"]+[0.,13.2,164.9]
uv=np.asarray(mesh.visual.uv).copy();uv[:,1]=1.-uv[:,1]
tri=np.asarray(mesh.faces);q=p[tri]
image=np.asarray(Image.open(head/"T_ArtisanHead.png").convert("RGB"));height,width=image.shape[:2]
W,H=512,80
result=np.zeros((H,W,3),np.uint8)
valid=np.zeros((H,W),bool)
def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]
for row in range(H):
    z=152.75+4.2*(row+.5)/H
    ids=np.flatnonzero((q[:,:,2].min(1)<z)&(q[:,:,2].max(1)>=z))
    segments=[];tex=[]
    for idx in ids:
        points=[];coords=[]
        for a,b in [(0,1),(1,2),(2,0)]:
            if (q[idx,a,2]<z)==(q[idx,b,2]<z):continue
            t=(z-q[idx,a,2])/(q[idx,b,2]-q[idx,a,2])
            points.append(q[idx,a,:2]*(1-t)+q[idx,b,:2]*t-[.1,-.85])
            coords.append(uv[tri[idx,a]]*(1-t)+uv[tri[idx,b]]*t)
        if len(points)==2:segments.append(points);tex.append(coords)
    segments=np.array(segments);tex=np.array(tex)
    if not len(segments):continue
    a=segments[:,0];e=segments[:,1]-a
    for col in range(W):
        angle=math.tau*((col+.5)/W-.5);ray=np.array([math.sin(angle),math.cos(angle)])
        den=cross(ray,e);den[np.abs(den)<1e-9]=np.nan
        s=cross(a,ray)/den;d=cross(a,e)/den
        hits=np.flatnonzero((s>=0)&(s<=1)&(d>0))
        if not len(hits):continue
        k=hits[np.argmax(d[hits])]
        coord=(tex[k,0]*(1-s[k])+tex[k,1]*s[k])%1
        x,y=coord*[width,height]-.5;i,j=math.floor(x),math.floor(y);u,v=x-i,y-j
        result[row,col]=(1-v)*((1-u)*image[j%height,i%width]+u*image[j%height,(i+1)%width])+v*((1-u)*image[(j+1)%height,i%width]+u*image[(j+1)%height,(i+1)%width])
        valid[row,col]=True
# The imported bust's lower cut is inclined. Reflect nearby skin grain below that edge instead of stretching one row.
for col in range(W):
    rows=np.flatnonzero(valid[:,col])
    if not len(rows):raise ValueError("Neck atlas is missing an entire angle")
    sample=np.arange(H);sample=np.where(sample<rows[0],np.minimum(2*rows[0]-sample,rows[-1]),sample)
    for ch in range(3):result[:,col,ch]=np.interp(sample,rows,result[rows,col,ch])
result=np.uint8(np.round(gaussian_filter(result.astype(float),(.65,1.15,0),mode=("nearest","wrap","nearest"))))
Image.fromarray(result).save(out/"T_ArtisanCollarSeam.png")
