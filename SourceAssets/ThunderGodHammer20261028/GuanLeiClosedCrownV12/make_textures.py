"""Four material-specific PBR sets with physically scaled tangent-space normals."""
from pathlib import Path
import numpy as np,json
from PIL import Image,ImageFilter,ImageDraw
P=Path(__file__).resolve().parent;T=P/'Textures';T.mkdir(exist_ok=True)
N=4096;rng=np.random.default_rng(1203);tile=.055
def noise(n,blur):
 grid=rng.integers(0,256,(n,n),dtype=np.uint8)
 im=Image.fromarray(np.tile(grid,(3,3))).resize((N*3,N*3),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(blur)).crop((N,N,N*2,N*2))
 return np.asarray(im,dtype=np.float32)/255-.5
hammer=noise(160,10);pores=noise(460,4);patina=noise(34,22)
scratch=Image.new('L',(N,N));d=ImageDraw.Draw(scratch)
for _ in range(380):
 x=int(rng.integers(0,N));y=int(rng.integers(0,N));length=int(rng.integers(25,350));skew=int(rng.integers(-5,6))
 value=int(rng.integers(60,170));width=int(rng.integers(1,3))
 for sx in (-N,0,N):
  for sy in (-N,0,N):d.line((x+sx,y+sy,x+skew+sx,y+length+sy),fill=value,width=width)
scratch=Image.fromarray(np.tile(np.asarray(scratch),(3,3))).filter(ImageFilter.GaussianBlur(1.4)).crop((N,N,N*2,N*2))
scratches=np.asarray(scratch,dtype=np.float32)/255
rows=[]
for name,color,rough,hm,pm,sm in [('Steel',(.245,.238,.222),.46,7e-6,1.2e-6,2.5e-6),('Silver',(.53,.51,.465),.31,2e-6,.6e-6,3e-6),('Recess',(.135,.147,.158),.57,5e-6,2e-6,1e-6),('Inlay',(.55,.535,.49),.32,1.5e-6,.5e-6,2.0e-6)]:
 height=hammer*hm+pores*pm-scratches*sm
 dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(2*tile/N)
 dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(2*tile/N)
 # Image rows run downward, opposite to the UV V axis. OpenGL tangent Y
 # therefore uses +dy; UE's DirectX interpretation flips this green channel.
 normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
 Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(T/('T_GuanLei12_'+name+'_Normal.png'))
 variation=1+patina*.075+hammer*.02-scratches*.035
 rgb=np.asarray(color,dtype=np.float32)[None,None,:]*variation[:,:,None]
 Image.fromarray(np.uint8(np.clip(rgb,0,1)*255)).save(T/('T_GuanLei12_'+name+'_BaseColor.png'))
 orm=np.stack((np.ones_like(hammer),np.clip(rough+patina*.05+hammer*.02+scratches*.06,0,1),np.ones_like(hammer)*.96),axis=-1)
 Image.fromarray(np.uint8(orm*255)).save(T/('T_GuanLei12_'+name+'_ORM.png'))
 rows.append(dict(material=name,size=N,physical_tile_m=tile,normal_convention='OpenGL tangent space; flip green on UE import',features='low-pass hammering, shallow pores, directional fine scratches',normal_z_mean=float(normal[:,:,2].mean())))
 print('PBR_SAVED',name,flush=True)
(P/'texture_manifest.json').write_text(json.dumps(dict(sets=rows,normal_maps=4),indent=2),encoding='utf-8')
