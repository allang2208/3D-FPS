"""Original, periodic ice surface maps: thin fractures, trapped air, patchy frost."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DEST=Path(__file__).resolve().parents[2]/'SourceAssets/IceWall20260930/RealisticV2'
DEST.mkdir(parents=True,exist_ok=True)
N=2048
rng=np.random.default_rng(93042)

def noise(grid, seed):
    r=np.random.default_rng(seed)
    a=(r.random((grid,grid))*255).astype(np.uint8)
    # Wrapped tiling avoids bright lines at a material seam.
    tiled=np.tile(a,(3,3))
    im=Image.fromarray(tiled).resize((N*3,N*3),Image.Resampling.BICUBIC)
    return np.asarray(im.crop((N,N,N*2,N*2)),dtype=np.float32)/255

broad=noise(8,93001); medium=noise(32,93002); fine=noise(192,93003)
frost=np.clip((broad*.7+medium*.3-.45)*2.0,0,.64)
fracture=Image.new('L',(N,N),0); draw=ImageDraw.Draw(fracture)
for k in range(26):
    x=float(rng.uniform(0,N)); y=float(rng.uniform(0,N)); angle=float(rng.uniform(0,math.tau))
    points=[(x,y)]
    for j in range(int(rng.integers(5,11))):
        angle+=float(rng.normal(0,.17)); length=float(rng.uniform(28,75))
        x+=math.cos(angle)*length; y+=math.sin(angle)*length; points.append((x,y))
    for dx in (-N,0,N):
        for dy in (-N,0,N):
            draw.line([(px+dx,py+dy) for px,py in points],fill=int(rng.integers(60,125)),width=int(rng.integers(1,3)))
            at=points[len(points)//2]; end=(at[0]+math.cos(angle+.6)*100,at[1]+math.sin(angle+.6)*100)
            draw.line([(at[0]+dx,at[1]+dy),(end[0]+dx,end[1]+dy)],fill=48,width=1)
fracture=fracture.filter(ImageFilter.GaussianBlur(.65))
cracks=np.asarray(fracture,dtype=np.float32)/255
air=Image.new('L',(N,N),0); ad=ImageDraw.Draw(air)
for k in range(900):
    x,y=rng.integers(0,N,size=2); radius=float(rng.uniform(.5,2.3))
    ad.ellipse((x-radius,y-radius,x+radius,y+radius),fill=int(rng.integers(8,44)))
bubbles=np.asarray(air.filter(ImageFilter.GaussianBlur(.7)),dtype=np.float32)/255
# Map RGB: patch frost, sparse fractures, softly trapped air. Values are physical masks, not painted outlines.
masks=np.stack([frost,cracks,bubbles],axis=-1)
Image.fromarray(np.uint8(np.clip(masks,0,1)*255)).save(DEST/'T_IceSurfaceMasks.png')
height=broad*.33+medium*.14+fine*.035-cracks*.12
smooth=np.asarray(Image.fromarray(np.uint8(np.clip(height,0,1)*255)).filter(ImageFilter.GaussianBlur(2.5)),dtype=np.float32)/255
sx=(np.roll(smooth,-1,axis=1)-np.roll(smooth,1,axis=1))*2.8
sy=(np.roll(smooth,-1,axis=0)-np.roll(smooth,1,axis=0))*2.8
normal=np.stack([-sx,-sy,np.ones_like(sx)],axis=-1)
normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(DEST/'T_IceSurfaceNormal.png')
(DEST/'surface-source.json').write_text(json.dumps({'author':'original procedural source',
    'size':N,'seed':93042,'mask_channels':{'R':'patchy frost','G':'sparse fine fractures','B':'trapped air'},
    'normal':'low-pass height derivatives; shallow melt relief','runtime_tested':False},indent=2),encoding='utf-8')
