"""Rasterize only the original head for texture-space edits and landmark authoring."""
import gzip, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw
from numba import njit
ROOT=Path(__file__).resolve().parents[4]/'SourceAssets/VillageBlacksmithNPC20261118'
OLD=ROOT/'HeadHair'
OUT=ROOT/'FinishR2/HeadHair'
TEX=OUT/'Textures'
TEX.mkdir(parents=True, exist_ok=True)
PREFIX='T_Smith_Face_'
def load_face(path=OLD):
    return json.loads(gzip.decompress((path/'face.json.gz').read_bytes()))
@njit(cache=True)
def raster(xy,depth,tris,width,height):
    zbuf=np.full((height,width),-1e9,np.float32)
    index=np.full((height,width),-1,np.int32)
    weights=np.zeros((height,width,2),np.float32)
    for i in range(len(tris)):
        a,b,c=tris[i]
        x0,y0=xy[a];x1,y1=xy[b];x2,y2=xy[c]
        ex=x1-x0;ey=y1-y0;fx=x2-x0;fy=y2-y0
        det=ex*fy-ey*fx
        if abs(det)<1e-8:continue
        for y in range(max(0,int(np.ceil(min(y0,y1,y2)))),min(height,int(np.floor(max(y0,y1,y2)))+1)):
            for x in range(max(0,int(np.ceil(min(x0,x1,x2)))),min(width,int(np.floor(max(x0,x1,x2)))+1)):
                u=((x-x0)*fy-(y-y0)*fx)/det;v=(ex*(y-y0)-ey*(x-x0))/det
                if u < -1e-6 or v < -1e-6 or 1-u-v < -1e-6:continue
                z=depth[a]+u*(depth[b]-depth[a])+v*(depth[c]-depth[a])
                if z>=zbuf[y,x]:
                    zbuf[y,x]=z;index[y,x]=i;weights[y,x,0]=u;weights[y,x,1]=v
    return index,weights,zbuf
def interp(ids,bary,tris,field):
    tri=tris[ids];a,b,c=field[tri[:,0]],field[tri[:,1]],field[tri[:,2]]
    if field.ndim==1:return a+(b-a)*bary[:,0]+(c-a)*bary[:,1]
    return a+(b-a)*bary[:,:1]+(c-a)*bary[:,1:]
def projection(folder, slug, x0=-8, x1=8, z0=162.5, z1=173.5, scale=77, annotate=False):
    d=load_face(folder);p=np.array(d['p']);tris=np.array(d['tri'])[np.array(d['m'])==0];uv=np.array(d['uv'],np.float32)
    xy=np.stack([(p[:,0]-x0)*scale,(z1-p[:,2])*scale],axis=1)
    W,H=round((x1-x0)*scale),round((z1-z0)*scale)
    index,bary,depth=raster(xy,p[:,1],tris,W,H);valid=index>=0
    coords=interp(index[valid],bary[valid],tris,uv)
    texture=np.array(Image.open(folder/'Textures'/(PREFIX+'BC.png')).convert('RGB'));hh,ww=texture.shape[:2]
    output=np.full((H,W,3),130,np.uint8)
    output[valid]=texture[np.clip((coords[:,1]*hh).astype(int),0,hh-1),np.clip((coords[:,0]*ww).astype(int),0,ww-1)]
    im=Image.fromarray(output)
    if annotate:
        draw=ImageDraw.Draw(im)
        for x in np.arange(x0,x1+.001,.5):
            px=int((x-x0)*scale);draw.line((px,0,px,8),fill=(0,255,0));draw.text((px+1,10),str(x),fill='white')
        for z in np.arange(z0,z1+.001,.5):
            py=int((z1-z)*scale);draw.line((0,py,12,py),fill=(0,255,0));draw.text((12,py),str(z),fill='white')
    im.save(OUT/(slug+'.png'))
if __name__=='__main__':projection(OLD,'eye_landmarks',annotate=True)
