"""Physical-scale leather and forged metal PBR; no painted-in light or shadows."""
from pathlib import Path
import numpy as np,json
from PIL import Image,ImageFilter,ImageDraw
P=Path(__file__).resolve().parent;T=P/'Textures';T.mkdir(exist_ok=True)
N=4096;tile=.065;rng=np.random.default_rng(31031)
def noise(n,blur=0):
 a=rng.integers(0,256,(n,n),dtype=np.uint8)
 im=Image.fromarray(np.tile(a,(3,3))).resize((N*3,N*3),Image.Resampling.BICUBIC)
 if blur:im=im.filter(ImageFilter.GaussianBlur(blur))
 return np.asarray(im.crop((N,N,N*2,N*2)),dtype=np.float32)/255-.5
grain=noise(560,1.2);pores=noise(1400,.7);cloud=noise(30,16);hammer=noise(140,6)
# Cellular creases are shallow valleys, paired with restrained color/roughness.
crease=np.clip((-.12-grain)*3,0,1)
scr=Image.new('L',(N,N));draw=ImageDraw.Draw(scr)
for i in range(500):
 x=int(rng.integers(0,N));y=int(rng.integers(0,N));dy=int(rng.integers(20,240))
 for ox in (-N,0,N):
  for oy in (-N,0,N):draw.line((x+ox,y+oy,x+ox+int(rng.integers(-4,5)),y+oy+dy),fill=int(rng.integers(35,150)),width=1)
scratch=np.asarray(scr.filter(ImageFilter.GaussianBlur(.8)),dtype=np.float32)/255
rows=[]
for name,color,rough,metal,height in [
 ('Leather',(.105,.060,.035),.78,0.,grain*.000018+pores*.000004-crease*.000009),
 ('Steel',(.23,.245,.26),.54,.96,hammer*.000005+pores*.0000006-scratch*.000002),
 ('Silver',(.55,.56,.57),.43,.98,hammer*.0000014-scratch*.0000018)]:
 dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*tile/N);dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*tile/N)
 normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
 variation=1+cloud*.14+(grain*.07-crease*.09 if name=='Leather' else hammer*.025-scratch*.035)
 rgb=np.asarray(color,dtype=np.float32)[None,None,:]*variation[:,:,None]
 ao=np.clip(1-crease*.10,0,1) if name=='Leather' else np.ones_like(grain)
 roughmap=np.clip(rough+cloud*.08+grain*(.06 if name=='Leather' else .012)+scratch*.025,0,1)
 orm=np.stack((ao,roughmap,np.ones_like(grain)*metal),axis=-1)
 for kind,a in [('BaseColor',rgb),('ORM',orm),('Normal',normal*.5+.5)]:
  Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(T/f'T_StaticField_{name}_{kind}.png')
 rows.append(dict(material=name,resolution=N,physical_tile_m=tile,normal='OpenGL; flip green on UE import'))
 print('STATIC_FIELD_PBR_SAVED',name,flush=True)
(P/'texture_manifest.json').write_text(json.dumps(rows,indent=2))
