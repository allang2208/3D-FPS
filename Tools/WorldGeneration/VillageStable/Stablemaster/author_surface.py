"""Transfer diffuse facial pigmentation to the existing facial UVs without copying eye reflections."""
import json
from pathlib import Path
import numpy as np
import cv2
from scipy.interpolate import RBFInterpolator
from PIL import Image

root=Path(__file__).resolve().parents[4]
out=root/'SourceAssets/HillsVillageStable/StablemasterR2'
native=json.loads((root/'SourceAssets/ChapelNun20261115/ProductionR1/Inputs/native_head.json').read_bytes())
positions=np.asarray(native['positions']);tri=np.asarray(native['triangles'])
# DynamicMesh material ID 0 is the head surface in this capture (includes neck and scalp).
skin=np.asarray(native['triangle_materials'])==0
tri=tri[skin];uv=np.asarray(native['uv'])[skin]
base=np.array(Image.open(out/'Inputs/NativeBase.png').convert('RGBA'))
h,w=base.shape[:2]
photo=np.array(Image.open(out/'FaceTurnaround.png').convert('RGB'))[:,:492].astype(np.float32)
# Suppress studio illumination; retain local skin colour, freckles and lip pigment.
soft=cv2.GaussianBlur(photo,(0,0),24)
corrected=np.clip(photo-(soft-np.array([183.,137.,112.],np.float32))*.63,0,255)
source=[];target=[]
def pair(x,z,u,y):
    source.extend([(x,z),(-x,z)]);target.extend([(245+u,y),(245-u,y)])
def middle(z,y):
    source.append((0,z));target.append((245,y))
for z,y in [(145.4,580),(146.75,555),(148.73,514),(149.49,498),(150.22,482),(152.25,444),(153.1,425),(156.93,333),(160.8,245),(164.5,167)]:middle(z,y)
for x,z,u,v in [(1.92,155.73,34,354),(3.33,156.26,66,349),(4.72,156.41,98,348),(4.4,158.0,95,319),(1.2,158.25,30,326),(1.16,152.1,28,441),(2.63,149.41,57,495),(4.7,154.4,92,398),(6.3,154.6,127,397),(5.5,150.0,111,492),(3.4,147,79,550),(6,161,120,238)]:pair(x,z,u,v)
project=RBFInterpolator(np.array(source),np.array(target),smoothing=.065)
visible=np.unique(tri);xy=np.empty((len(positions),2))
for ids in np.array_split(visible,10):xy[ids]=project(positions[ids][:,[0,2]])
def ramp(a,b,v):
    s=np.clip((v-a)/(b-a),0,1);return s*s*(3-2*s)
x,y,z=positions.T
mask=ramp(4.6,8.2,y)*ramp(145.3,147.8,z)*(1-ramp(162,163.7,z))*(1-ramp(5.65,6.8,abs(x)))
# Keep the tear line, eyes and eyebrow hair on their native independent surfaces.
eye=((abs(x)-3.36)/1.72)**2+((z-156.23)/.90)**2
mask*=ramp(.58,1.20,eye)
mt=np.zeros((h,w),np.float32);mx=np.zeros_like(mt);my=np.zeros_like(mt)
for ids,tex in zip(tri,uv):
    if max(mask[ids])<.001:continue
    pix=tex*[w,h]-.5
    lo=np.maximum(np.floor(pix.min(0)).astype(int),0);hi=np.minimum(np.ceil(pix.max(0)).astype(int)+1,[w,h])
    if (hi<=lo).any():continue
    a,b,c=pix;u=b-a;v=c-a;det=u[0]*v[1]-v[0]*u[1]
    if abs(det)<1e-6:continue
    yy,xx=np.mgrid[lo[1]:hi[1],lo[0]:hi[0]];dx=xx-a[0];dy=yy-a[1]
    tb=(v[1]*dx-v[0]*dy)/det;tc=(-u[1]*dx+u[0]*dy)/det;ta=1-tb-tc
    inside=(ta>=-.0001)&(tb>=-.0001)&(tc>=-.0001)
    yy=yy[inside];xx=xx[inside]
    bary=np.stack([ta[inside],tb[inside],tc[inside]],axis=1)
    mapped=bary@xy[ids];mx[yy,xx],my[yy,xx]=mapped.T;mt[yy,xx]=bary@mask[ids]
pigment=cv2.remap(corrected,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
native_rgb=base[:,:,:3].astype(np.float32)
sel=mt>.89
# Match adjacent native skin at the cheeks before feathering across the seam.
tone= (my>384)&(my<433)&(abs(mx-245)>48)&(abs(mx-245)<103)&sel
if tone.any():pigment+=np.median(native_rgb[tone],axis=0)-np.median(pigment[tone],axis=0)
alpha=(.68*mt)[:,:,None]
base[:,:,:3]=np.clip(native_rgb*(1-alpha)+pigment*alpha,0,255).astype(np.uint8)
Image.fromarray(base).save(out/'T_Stablemaster_Face_BC.png')
for side in 'LR':
    im=np.array(Image.open(out/'Inputs'/('Iris'+side+'.png')).convert('RGBA'))
    rgb=im[:,:,:3].astype(float)/255.
    lum=rgb@np.array([.2126,.7152,.0722])
    # Retain the native radial fibres, inner pupil and dark limbal ring.
    gain=ramp(.035,.27,lum)[:,:,None]
    turquoise=np.clip(lum[:,:,None]*np.array([.77,1.085,1.075]),0,1)
    im[:,:,:3]=np.uint8(np.clip((rgb*(1-.83*gain)+turquoise*.83*gain)*255,0,255))
    Image.fromarray(im).save(out/('T_Stablemaster_Iris'+side+'.png'))
