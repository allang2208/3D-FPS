"""Production catalog icon from the original textured geometry; no acceptance capture."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
O=Path(__file__).parent;P=O.parents[1];T=O/'Original/Extracted/textures'
parts=json.loads((O/'icon_geometry.json').read_text())
atlas=np.asarray(Image.open(T/'DefaultMaterial_albedo.jpg').convert('RGB'))/255.
metal=np.asarray(Image.open(T/'DefaultMaterial_metallic.jpg').convert('L'))/255.
rough=np.asarray(Image.open(T/'DefaultMaterial_roughness.jpg').convert('L'))/255.
size=768;pixels=np.zeros((size,size,4),np.uint8);depth=np.full((size,size),-np.inf)
direction=np.array([1.,.18,.12]);direction/=np.linalg.norm(direction)
right=np.array([.18,-1.,0.]);right/=np.linalg.norm(right);up=np.cross(direction,right)
verts=np.concatenate([np.array(p['verts']) for p in parts]);xy=np.stack((verts@right,verts@up),axis=1)
lo,hi=xy.min(0),xy.max(0);scale=size*.88/max(hi-lo);center=(lo+hi)*.5
light=np.array([.65,-.25,.72]);light/=np.linalg.norm(light);half=light+direction;half/=np.linalg.norm(half)
for part in parts:
 v=np.array(part['verts']);screen=(np.stack((v@right,v@up),axis=1)-center)*scale+size*.5;screen[:,1]=size-screen[:,1]
 z=v@direction;cursor=0
 for face in part['faces']:
  faceuv=np.array(part['uv'][cursor:cursor+len(face)]);cursor+=len(face)
  for j in range(1,len(face)-1):
   ids=[face[0],face[j],face[j+1]];q=screen[ids];zz=z[ids];a,b,c=q
   den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
   if abs(den)<1e-8:continue
   xmin,ymin=np.maximum(np.floor(q.min(0)).astype(int),0);xmax,ymax=np.minimum(np.ceil(q.max(0)).astype(int),size-1)
   if xmin>xmax or ymin>ymax:continue
   x,y=np.meshgrid(np.arange(xmin,xmax+1)+.5,np.arange(ymin,ymax+1)+.5)
   w0=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;w1=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;w2=1-w0-w1
   region=depth[ymin:ymax+1,xmin:xmax+1];candidate=w0*zz[0]+w1*zz[1]+w2*zz[2]
   mask=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)&(candidate>region)
   if not mask.any():continue
   tu=w0*faceuv[0,0]+w1*faceuv[j,0]+w2*faceuv[j+1,0];tv=w0*faceuv[0,1]+w1*faceuv[j,1]+w2*faceuv[j+1,1]
   tx=np.clip((tu*atlas.shape[1]).astype(int),0,atlas.shape[1]-1);ty=np.clip(((1-tv)*atlas.shape[0]).astype(int),0,atlas.shape[0]-1)
   normal=np.cross(v[ids[1]]-v[ids[0]],v[ids[2]]-v[ids[0]]);normal/=max(np.linalg.norm(normal),1e-12)
   if normal@direction<0:normal=-normal
   base=atlas[ty,tx]**2.2;shine=max(0.,normal@half)**28
   color=np.clip(base*(.62+.65*max(0.,normal@light))+.06*shine,0,1)**(1/2.2)
   dest=pixels[ymin:ymax+1,xmin:xmax+1];dest[mask,:3]=(color[mask]*255).astype(np.uint8);dest[mask,3]=255;region[mask]=candidate[mask]
target=P/'Content/ColdSteelData/Icons/ue_rsh12.png';target.parent.mkdir(parents=True,exist_ok=True)
Image.fromarray(pixels).resize((512,512),Image.Resampling.LANCZOS).save(target)
(O/'icon_receipt.json').write_text(json.dumps(dict(file=str(target),source='Original RSH-12 FBX UV and albedo',purpose='Inventory icon production',acceptance_render=False)),encoding='utf8')
print('RSH12_CATALOG_ICON_SAVED')
