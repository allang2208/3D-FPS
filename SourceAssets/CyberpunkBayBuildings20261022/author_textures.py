"""Author architectural PBR atlases from physical window/frame layers.
The height master produces DirectX normals for UE and OpenGL normals for Blender.
"""
from PIL import Image,ImageDraw
import numpy as np,json,random
from design import *
FACADES.mkdir(parents=True,exist_ok=True)
N=2048
for family,seed in [('Office',221021),('Residential',221022),('Tech',221023)]:
 r=random.Random(seed)
 bc=Image.new('RGB',(N,N),(28,35,45));em=Image.new('RGB',(N,N),(0,0,0))
 height=Image.new('L',(N,N),155);orm=Image.new('RGB',(N,N),(245,145,105))
 b=ImageDraw.Draw(bc);e=ImageDraw.Draw(em);h=ImageDraw.Draw(height);q=ImageDraw.Draw(orm)
 # 24 bays x 32 floors; 3.2 m bay width and 3.8 m floor height.
 for j in range(32):
  floorlit=r.uniform(.18,.75);floorcolor=r.choice([(122,169,194),(185,198,203),(220,170,105),(116,172,177)])
  for i in range(24):
   x=round(i*N/24);xn=round((i+1)*N/24);y=j*64
   tone=r.randint(24,36)
   b.rectangle((x+1,y+1,xn-2,y+62),fill=(tone,tone+5,tone+11))
   h.rectangle((x+2,y+2,xn-3,y+62),fill=168)
   inset=7 if family=='Office' else (12 if family=='Residential' else 9)
   a=(x+inset,y+9,xn-inset,y+49)
   b.rectangle(a,fill=(7,15,24));h.rectangle(a,fill=70);q.rectangle(a,fill=(215,63,175))
   # Recessed reveal, aluminum frame, reflective upper pane.
   b.rectangle(a,outline=(43,53,65),width=2);h.rectangle(a,outline=145,width=2)
   b.line((x+inset+2,y+11,xn-inset-2,y+11),fill=(30,45,58),width=2)
   occupied=r.random()<floorlit
   if family=='Tech':occupied=(j%8 in (1,2,3,5)) and (i%6<4)
   if occupied:
    color=floorcolor if family!='Residential' else r.choice([(215,155,86),(164,193,206),(202,181,144)])
    if family=='Tech':color=(72,156,193) if j%8<4 else (166,111,158)
    gain=r.uniform(.40,.92);c=tuple(int(v*gain) for v in color)
    e.rectangle((a[0]+3,a[1]+3,a[2]-3,a[3]-3),fill=c)
    # Interior partition silhouettes and occasional blind banks, not random dots.
    mid=round((x+xn)/2)
    e.line((mid,y+11,mid,y+48),fill=(0,0,0),width=3)
    if r.random()<.28:
     for yy in range(y+17,y+45,8):e.line((a[0]+3,yy,a[2]-3,yy),fill=tuple(int(v*.35) for v in c),width=2)
   b.line((x,y+56,xn,y+56),fill=(45,53,64),width=2);h.line((x,y+56,xn,y+56),fill=190,width=2)
   q.line((x,y+56,xn,y+56),fill=(235,115,160),width=2)
   # Raised spandrel joints remain visible in normal and roughness channels.
   if family=='Tech' and i%4==0:
    for yy in range(y+12,y+48,5):
     b.line((xn-10,yy,xn-3,yy),fill=(5,10,17),width=2);h.line((xn-10,yy,xn-3,yy),fill=100,width=2)
 arr=np.asarray(height,dtype=np.float32)/255
 dx=(np.roll(arr,-1,1)-np.roll(arr,1,1))*2.2
 dy=(np.roll(arr,-1,0)-np.roll(arr,1,0))*2.2
 vec=np.stack((-dx,dy,np.ones_like(arr)),axis=-1);vec/=np.linalg.norm(vec,axis=-1,keepdims=True)
 normal=np.uint8(np.clip(vec*.5+.5,0,1)*255)
 Image.fromarray(normal).save(FACADES/f'T_{family}_N.png')
 normal[:,:,1]=255-normal[:,:,1];Image.fromarray(normal).save(FACADES/f'T_{family}_N_GL.png')
 for suffix,img in [('BC',bc),('E',em),('H',height),('ORM',orm)]:img.save(FACADES/f'T_{family}_{suffix}.png')
(ROOT/'texture-source.json').write_text(json.dumps(dict(size=N,families=['Office','Residential','Tech'],bay_metres=3.2,
 floor_metres=FLOOR,normal_convention='DirectX',channel_packing='R ambient occlusion, G roughness, B metallic',
 signs_reused=str(OLD/'Textures/T_BaySigns_E.png')),indent=2),encoding='utf8')
print('DETAILED_BAY_TEXTURES_AUTHORED',flush=True)
