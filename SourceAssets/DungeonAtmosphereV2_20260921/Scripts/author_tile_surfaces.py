"""Author original ceramic and mortar PBR maps; no photographic inputs or renders."""
from pathlib import Path
import json
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored/TilePolish/Textures';OUT.mkdir(parents=True,exist_ok=True)
R=random.Random(921220);N=np.random.default_rng(921220)

def noise(w,h,scale):
    values=N.integers(0,256,(max(2,h//scale),max(2,w//scale)),dtype=np.uint8)
    return np.asarray(Image.fromarray(values).resize((w,h),Image.Resampling.BICUBIC),dtype=np.float32)/255

def normal(height,strength):
    dy,dx=np.gradient(height)
    v=np.stack((-dx*strength,dy*strength,np.ones_like(dx)),axis=-1)
    v/=np.linalg.norm(v,axis=-1,keepdims=True)
    return np.uint8(np.clip(v*.5+.5,0,1)*255)

def save(name,base,rough,height,strength):
    maps={'BaseColor':np.uint8(np.clip(base,0,255)),
          'Roughness':np.uint8(np.clip(rough,0,1)*255),
          'Normal':normal(height,strength)}
    paths={}
    for channel,data in maps.items():
        path=OUT/(name+'_'+channel+'.png');Image.fromarray(data).save(path);paths[channel]=str(path)
    return paths

W,H=512,256
color=np.zeros((H*8,W*8,3),dtype=np.float32)
roughness=np.zeros((H*8,W*8),dtype=np.float32)
heightmap=np.zeros_like(roughness)
yy,xx=np.mgrid[0:H,0:W]
edge=np.exp(-np.minimum.reduce([xx,W-1-xx,yy,H-1-yy])/12)
for index in range(64):
    macro=noise(W,H,80);mid=noise(W,H,14);grain=noise(W,H,2)
    damp=index in range(32,48)
    crazed=index>=48
    clay=np.array([181,178,158],dtype=np.float32)*R.uniform(.94,1.055)
    grime=np.maximum(0,.55-macro)*.16+edge*.10
    if damp:grime+=np.maximum(0,.74-macro)*.14
    # Most glazes retain a calm surface. Crazing and long scratches occur in
    # selected cells, while roughness includes fine wiped and eroded patches.
    fissure=Image.new('L',(W,H));draw=ImageDraw.Draw(fissure)
    if crazed:
        start=(R.uniform(-20,W),R.choice([-8,H+8]))
        pts=[start]
        for step in range(8):
            last=pts[-1];pts.append((last[0]+R.uniform(-40,40),last[1]+(-1 if start[1]>H else 1)*R.uniform(22,42)))
        draw.line(pts,fill=200,width=2)
        for j in (2,5):
            sx,sy=pts[j];draw.line([(sx,sy),(sx+R.uniform(15,60),sy+R.uniform(-35,35)),(sx+R.uniform(65,110),sy+R.uniform(-50,50))],fill=135,width=1)
    for _ in range(R.randrange(2,9)):
        x,y=R.randrange(W),R.randrange(H)
        draw.line([(x,y),(x+R.randrange(12,65),y+R.randrange(-8,8))],fill=R.randrange(18,60),width=1)
    crack=np.asarray(fissure,dtype=np.float32)/255
    eroded=np.maximum(0,.28-mid)*np.maximum(0,edge+.5)*1.5
    base=clay[None,None,:]*(1-grime[:,:,None])
    base+=((mid-.5)*5+(grain-.5)*2)[:,:,None]
    base-=crack[:,:,None]*np.array([67,66,58])
    base-=eroded[:,:,None]*np.array([35,37,35])
    rough=.29+mid*.19+grime*.55+eroded*.4+crack*.35
    if damp:rough-=.10*(macro>.42)
    height=(mid-.5)*.12+(grain-.5)*.032-crack*.55-eroded*.25
    row,col=divmod(index,8);sl=np.s_[row*H:(row+1)*H,col*W:(col+1)*W]
    color[sl]=base;roughness[sl]=rough;heightmap[sl]=height
manifest={'TileGlazeAtlas':save('TileGlazeAtlas',color,roughness,heightmap,1.65)}

w=h=2048;yy,xx=np.mgrid[0:h,0:w]
macro=noise(w,h,190);mid=noise(w,h,24);grain=noise(w,h,2)
# 0.5 m square mortar field: interrupted comb marks, sand, aggregate and pits.
comb=(np.sin(xx*.11+np.sin(yy*.004)*3)*.5+.5)**5
comb*=np.clip((macro-.26)*2,0,1)
pits=np.clip((.23-grain)*5,0,1)
height=mid*.3+grain*.15+comb*.32-pits*.3
base=np.array([115,107,92])[None,None,:]+((macro-.5)*18+(mid-.5)*17+(grain-.5)*10-comb*5-pits*18)[:,:,None]
manifest['TileMortar']=save('TileMortar',base,.80+mid*.14,height,2.1)
base=np.array([133,115,87])[None,None,:]+((mid-.5)*27+(grain-.5)*14)[:,:,None]
manifest['TileCeramicCore']=save('TileCeramicCore',base,.74+mid*.18,mid*.2+grain*.12,1.4)
mask=Image.new('L',(768,1536));draw=ImageDraw.Draw(mask)
for i in range(32):
    x=R.randrange(180,590);end=R.randrange(650,1530);width=R.randrange(5,33)
    points=[]
    for y in range(0,end,45):points.append((x+R.uniform(-9,9),y))
    draw.line(points,fill=R.randrange(45,180),width=width)
mask=mask.filter(ImageFilter.GaussianBlur(3))
values=np.asarray(mask,dtype=np.float32)/255
values*=.5+noise(768,1536,17)*.5
yy,xx=np.mgrid[0:1536,0:768]
values*=np.clip(np.minimum(yy,1535-yy)/75,0,1)
Image.fromarray(np.uint8(np.clip(values,0,1)*255)).save(OUT/'TileLeak_Opacity.png')
(OUT.parent/'material-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('TILE_PBR_AUTHORED: 64 glaze variants, rough mortar, ceramic fracture; original procedural sources')
