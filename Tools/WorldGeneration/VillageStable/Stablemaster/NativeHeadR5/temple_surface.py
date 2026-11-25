"""Retouch the temples in native UV space using hair from the same side of the head."""
from pathlib import Path
import sys
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import distance_transform_edt

root=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(root/'Tools/VillageHerbalist/Face'))
import author_face_texture as raster
raster.W,raster.H,raster.SS=600,625,1
src=root/'SourceAssets/HillsVillageStable/StablemasterMeshyR3/Authoring'
out=src.parent.parent/'StablemasterHeadR5'
data=np.load(out/'HeadSurface.npz')
p=data['pos'][data['tri']]
uv=data['uv']
tex=np.asarray(Image.open(src/'T_Stablemaster_Body_0_Color.png').convert('RGB'))
dst=tex.copy()
height,width=tex.shape[:2]
alpha=np.zeros((height,width),np.float32)

def feather(points,radius):
    a=np.zeros((625,600),np.uint8)
    cv2.fillPoly(a,[np.asarray(points,'i')],255)
    return cv2.GaussianBlur(a,(0,0),radius).astype('f')/255

front=feather([(132,189),(144,159),(167,137),(194,126),(210,136),(201,154),(187,181),(170,202),(147,216),(132,214)],3)
front+=feather([(410,134),(429,128),(451,143),(469,174),(477,212),(455,216),(433,185),(420,161)],3)
side=feather([(140,137),(185,138),(234,163),(255,193),(239,216),(195,206),(158,181),(141,163)],4)
wisps=np.zeros_like(front)
rng=np.random.default_rng(518)
for flip in [-1,1]:
    stroke=np.zeros((1250,1200),np.uint8)
    for i in range(22):
        u=np.linspace(0,1,45)
        start=rng.uniform(140,163) if flip<0 else rng.uniform(450,464)
        y=rng.uniform(251,277)
        fx=start-flip*(rng.uniform(5,16)*u+1.8*np.sin(np.pi*u))
        fy=y+rng.uniform(38,73)*u
        for j in range(1,len(u)):
            a=(int(fx[j-1]*2),int(fy[j-1]*2));b=(int(fx[j]*2),int(fy[j]*2))
            cv2.line(stroke,a,b,int(205*(1-u[j]**1.7)),max(1,round(3*(1-u[j]))),cv2.LINE_AA)
    wisps+=cv2.resize(stroke,(600,625),interpolation=cv2.INTER_AREA).astype('f')/255

pts=p.reshape(-1,3); coords=uv.reshape(-1,2)
ids=np.arange(len(pts),dtype=np.int32).reshape(-1,3)
projected=np.stack([300+pts[:,1]*20,(168.8-pts[:,2])*20],1).astype('f')
profiles={}
for sign in [-1,1]:
    dep,face,loc=raster.projection(projected,sign*pts[:,0],coords,ids)
    col=cv2.remap(tex,loc[:,:,0]*width-.5,loc[:,:,1]*height-.5,cv2.INTER_LINEAR,borderMode=cv2.BORDER_WRAP)
    yy,xx=np.mgrid[:625,:600]
    donor=(face>=0)&(xx>175)&(xx<323)&(yy>68)&(yy<181)&(col[:,:,0]<73)&(col[:,:,1]<58)
    near=distance_transform_edt(~donor,return_distances=False,return_indices=True)
    profiles[sign]=(dep,col,near)
for xyz,atlas in zip(p,uv):
    if xyz[:,2].max()<150 or xyz[:,2].min()>164 or np.abs(xyz[:,0]).max()<4 or xyz[:,1].min()>1:continue
    xy=atlas*[width,height]-.5
    a,b,c=xy
    d=b-a;e=c-a;det=d[0]*e[1]-d[1]*e[0]
    if abs(det)<.001:continue
    lo=np.maximum(np.ceil(xy.min(0)).astype(int),0)
    hi=np.minimum(np.floor(xy.max(0)).astype(int),[width-1,height-1])
    if np.any(hi<lo):continue
    sy,sx=np.mgrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
    x=sx-a[0];y=sy-a[1]
    u=(x*e[1]-y*e[0])/det;v=(y*d[0]-x*d[1])/det
    inside=(u>=0)&(v>=0)&(u+v<=1)
    if not inside.any():continue
    sy,sx=sy[inside],sx[inside]
    q=xyz[0]+u[inside,None]*(xyz[1]-xyz[0])+v[inside,None]*(xyz[2]-xyz[0])
    fx=np.clip(np.rint(300+q[:,0]*20).astype(int),0,599)
    px=np.clip(np.rint(300+q[:,1]*20).astype(int),0,599)
    py=np.clip(np.rint((168.8-q[:,2])*20).astype(int),0,624)
    sign=1 if xyz[:,0].mean()>0 else -1
    dep,col,near=profiles[sign]
    visibility=np.clip((1.4-(dep[py,px]-sign*q[:,0]))/1.1,0,1)
    patch=np.maximum(front[py,fx]*np.clip((280-px)/25,0,1),side[py,px])
    strand=wisps[py,fx]*np.clip((px-161)/25,0,1)*np.clip((285-px)/30,0,1)
    weight=np.maximum(patch,strand)*visibility*np.clip((np.abs(q[:,0])-4.4)/1.6,0,1)
    # Preserve the original dark strands; replace exposed light flecks with adjacent dark hair.
    light=tex[sy,sx] @ [.36,.48,.16]
    weight*=np.clip((light-18)/46,.12,1)
    dy=np.clip(py-27,80,177);dx=np.clip(px+44,179,320)
    donor=col[near[0,dy,dx],near[1,dy,dx]].astype('f')
    dst[sy,sx]=np.clip(tex[sy,sx]*(1-weight[:,None])+donor*weight[:,None],0,255)
    alpha[sy,sx]=weight
# Carry only the correction across the UV gutter. The body still uses its own untouched material.
delta=dst.astype(np.int16)-tex
region=(alpha>.015).astype(np.uint8)
if not region.any():raise RuntimeError('Empty temple selection')
dist,label=cv2.distanceTransformWithLabels(1-region,cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
border=(dist>0)&(dist<=3)
values=delta[region.astype(bool)]
dst[border]=np.clip(tex[border].astype(np.int16)+values[label[border]-1],0,255)
Image.fromarray(dst).save(out/'T_Stablemaster_Head_R5_Color.png')
print('Temple surface texels',int(region.sum()))
