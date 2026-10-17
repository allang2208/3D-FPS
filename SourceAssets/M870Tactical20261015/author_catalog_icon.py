"""Produce the catalog fallback icon directly from the downloaded textured mesh."""
from pathlib import Path
import json,numpy as np
from PIL import Image
O=Path(__file__).parent;P=O.parents[1];gpath=next((O/'Original/Gltf').glob('*.gltf'));g=json.loads(gpath.read_text());buffers=[(gpath.parent/b['uri']).read_bytes() for b in g['buffers']]
def accessor(index):
 a=g['accessors'][index];v=g['bufferViews'][a['bufferView']];dt={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',np.dtype(dt).itemsize*n)
 return np.ndarray((a['count'],n),dtype=dt,buffer=buffers[v['buffer']],offset=offset,strides=(stride,np.dtype(dt).itemsize)).copy()
p=g['meshes'][0]['primitives'][0];v=accessor(p['attributes']['POSITION']);norm=accessor(p['attributes']['NORMAL']);uv=accessor(p['attributes']['TEXCOORD_0']);faces=accessor(p['indices']).reshape(-1,3)
texindex=g['materials'][0]['pbrMetallicRoughness']['baseColorTexture']['index'];file=gpath.parent/g['images'][g['textures'][texindex]['source']]['uri'];texture=np.asarray(Image.open(file).convert('RGB'),dtype=float)/255
H,W=512,1024;screen=np.stack([-v[:,1],v[:,2]],axis=1);mid=(screen.min(0)+screen.max(0))/2;span=screen.max(0)-screen.min(0);scale=.91*min(W/span[0],H/span[1]);screen=(screen-mid)*scale;screen[:,0]+=W/2;screen[:,1]=H/2-screen[:,1]
canvas=np.zeros((H,W,4),np.float32);depth=np.full((H,W),-np.inf);light=np.array([1,-.35,.8]);light/=np.linalg.norm(light)
for face in faces:
 pts=screen[face];lo=np.maximum(np.floor(pts.min(0)).astype(int),0);hi=np.minimum(np.ceil(pts.max(0)).astype(int),[W-1,H-1])
 if np.any(hi<lo):continue
 x,y=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5);a,b,c=pts;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
 if abs(den)<1e-10:continue
 wa=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;wb=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;wc=1-wa-wb;weights=np.stack([wa,wb,wc],axis=-1);z=weights@v[face,0];area=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1];mask=(weights.min(-1)>=-1e-5)&(z>area)
 if not mask.any():continue
 tx=weights@uv[face];ix=np.clip((tx[...,0]*texture.shape[1]).astype(int),0,texture.shape[1]-1);iy=np.clip((tx[...,1]*texture.shape[0]).astype(int),0,texture.shape[0]-1);color=texture[iy,ix];normal=weights@norm[face];normal/=np.maximum(np.linalg.norm(normal,axis=-1,keepdims=True),1e-8);shade=.52+.62*np.maximum(0,normal@light);color=np.clip(color*shade[...,None],0,1)
 patch=canvas[lo[1]:hi[1]+1,lo[0]:hi[0]+1];patch[mask,:3]=color[mask];patch[mask,3]=1;area[mask]=z[mask]
out=P/'Content/ColdSteelData/Icons/ue_m870.png';Image.fromarray((canvas*255).astype(np.uint8),'RGBA').resize((512,256),Image.Resampling.LANCZOS).save(out);print('M870_CATALOG_ICON',str(out))
