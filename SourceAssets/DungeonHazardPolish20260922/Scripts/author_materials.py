"""Original fractured aggregate PBR; one physical height field drives all channels."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates,gaussian_filter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
N=2048;r=np.random.default_rng(922634);y,x=np.mgrid[0:N,0:N].astype(np.float32);u=x/N;v=y/N
def noise(n):return map_coordinates(r.random((n,n),dtype=np.float32),[v*n,u*n],order=3,mode='grid-wrap')
def smooth(a,b,k):
    q=np.clip((k-a)/(b-a),0,1);return q*q*(3-2*q)
macro=noise(7);grain=noise(210);fine=noise(700);warp=noise(29);pores=smooth(.67,.87,noise(290))
# Broken gravel islands are irregular cells, not a stucco cloud pattern.
stone=np.zeros((N,N),np.float32);tone=np.zeros_like(stone);slope=np.zeros_like(stone)
for cy in range(23):
    for cx in range(23):
        px=(cx+r.uniform(.15,.85))/23;py=(cy+r.uniform(.15,.85))/23
        sx,sy=r.uniform(.007,.023,2);angle=r.uniform(-math.pi,math.pi)
        radius=math.ceil(max(sx,sy)*N*1.35)
        ix=np.arange(int(px*N)-radius,int(px*N)+radius+1);iy=np.arange(int(py*N)-radius,int(py*N)+radius+1)
        dx=(ix/N-px)[None,:];dy=(iy/N-py)[:,None]
        ax=(dx*math.cos(angle)+dy*math.sin(angle))/sx;ay=(-dx*math.sin(angle)+dy*math.cos(angle))/sy
        distance=(abs(ax)**r.uniform(1.3,2.7)+abs(ay)**r.uniform(1.3,2.7))**.5
        patch=smooth(1.08,.86,distance) # irregular angular border
        yy=iy%N;xx=ix%N;view=np.ix_(yy,xx);replace=patch>stone[view]
        stone[view]=np.maximum(stone[view],patch)
        tone[view]=np.where(replace,r.uniform(-16,25)*patch,tone[view])
        slope[view]=np.where(replace,(ax*r.uniform(-.05,.05)+ay*r.uniform(-.05,.05))*patch,slope[view])
edge=np.maximum(0,gaussian_filter(stone,2.2,mode='wrap')-stone)
height=np.clip(.44+(macro-.5)*.055+(grain-.5)*.16+(fine-.5)*.045+stone*.18+slope-pores*.22-edge*.36,0,1)
color=np.zeros((N,N,3),np.float32)+np.array([147,140,127],np.float32)
color+=((macro-.5)*12+(grain-.5)*14+tone)[...,None]
color+=stone[...,None]*np.array([4,5,5],np.float32)
rough=np.clip(.9-stone*.12+(fine-.5)*.065+pores*.055,.71,.99)
ao=np.clip(1-pores*.2-edge*.6, .64,1)
physical_range_cm=.35;tile_cm=64
dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.5;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.5
strength=physical_range_cm*N/tile_cm
normal=np.stack((-dx*strength,dy*strength,np.ones_like(height)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
maps={'BaseColor':np.uint8(np.clip(color,0,255)),'Normal':np.uint8(np.clip(normal*.5+.5,0,1)*255),'Surface':np.uint8(np.stack([rough,ao,stone],axis=-1)*255),'Height':np.uint16(height*65535)}
report={'channels':{},'tile_cm':tile_cm,'height_range_cm':physical_range_cm,'provenance':'Original procedural fractured concrete with gravel, mineral grain and pores; no external image source','tests_run':False}
for name,data in maps.items():
    path=OUT/('FractureAggregate_'+name+'.png');Image.fromarray(data).save(path);report['channels'][name]=str(path)
(ROOT/'Authored/materials.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FRACTURE_AGGREGATE_PBR_AUTHORED')
