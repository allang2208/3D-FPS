"""Author original directional timber PBR maps, without external generation."""
from pathlib import Path
import numpy as np,json
from PIL import Image
P=Path(__file__).parent;OUT=P/'Textures';OUT.mkdir(exist_ok=True)
N=2048;rng=np.random.default_rng(260926)
u=np.arange(N,dtype=np.float32)[None,:]/N
v=np.arange(N,dtype=np.float32)[:,None]/N
def noise(w,h):
 a=rng.random((h,w)).astype('float32')
 return np.asarray(Image.fromarray(a,mode='F').resize((N,N),Image.Resampling.BICUBIC))
warp=noise(12,7)*.9+noise(32,13)*.22
rings=np.sin(2*np.pi*(u*66+warp+np.sin(v*13+u*9)*.27))
fine=np.sin(2*np.pi*(u*291+warp*2.3))
grain=noise(130,17)*.26+noise(500,90)*.055+rings*.047+fine*.013
pore=np.clip((noise(500,60)-.79)*5,0,1)*np.clip((noise(40,180)-.32)*3,0,1)
x=np.cos(2*np.pi*(u-.5));height=(rings*.06+fine*.018-pore*.06+noise(450,150)*.014)*.0001
dy,dx=np.gradient(height);nx=-dx/(.12/N);ny=dy/(1.418/N)
nz=np.ones_like(nx);length=np.sqrt(nx*nx+ny*ny+nz*nz)
normal=np.stack((nx/length,ny/length,nz/length),axis=2)*.5+.5
def save(a,name):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5),'RGB').save(OUT/name)
specs=[('Swift',(0.67,.43,.20),(.27,.105,.048),.46),('Heavy',(.32,.155,.068),(.083,.053,.029),.53),('Steady',(.71,.67,.53),(.25,.145,.078),.57)]
rows=[]
for name,base,dark,rough in specs:
 col=np.ones((N,N,3),dtype=np.float32)*base
 if name=='Swift':mask=((x>.59)&(x<.73)).astype('float32')*.88
 elif name=='Heavy':mask=np.clip((x-.52)/.045,0,1)*.95
 else:mask=np.clip((.22-np.abs(x))/.022,0,1)*.93
 col=col*(1-mask[:,:,None])+np.array(dark)*(mask[:,:,None])
 col*=np.clip(.84+grain[:,:,None]-.065*pore[:,:,None],.5,1.22)
 orm=np.stack((1-pore*.07,np.clip(rough+(grain-.1)*.17+pore*.055,0,1),np.zeros_like(grain)),axis=2)
 save(col,f'T_Bow_{name}_BaseColor.png');save(orm,f'T_Bow_{name}_ORM.png');save(normal,f'T_Bow_{name}_Normal.png')
 rows.append(dict(name=name,size=[N,N],roughness=rough,base_srgb=base,laminate_srgb=dark,normal_convention='OpenGL; Unreal flips green on import'))
(P/'texture-authoring.json').write_text(json.dumps(dict(source='Original seeded anisotropic wood grain, pores and flush laminate maps',seed=260926,maps=rows),indent=2),encoding='utf8')
print('BOW_TIMBER_TEXTURES_AUTHORED',flush=True)
