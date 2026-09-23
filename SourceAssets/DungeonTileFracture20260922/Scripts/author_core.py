"""Original fine porous ceramic-body PBR data; no input photograph or render."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
N=1024;rng=np.random.default_rng(922948);y,x=np.mgrid[0:N,0:N].astype(np.float32)/N
def noise(cells):
    return map_coordinates(rng.random((cells,cells),dtype=np.float32),[y*cells,x*cells],order=3,mode='grid-wrap')
fine=noise(237);grain=noise(83);broad=noise(13)
pores=np.clip((.22-fine)*5,0,1)*np.clip((.64-grain)*3,0,1)
height=(grain-.5)*.00010+(fine-.5)*.000055-pores*.00014
dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.5*N/.075
dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.5*N/.075
n=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
rgb=np.array([166,155,133],dtype=np.float32)[None,None,:]+((grain-.5)*9+(broad-.5)*5-pores*12)[...,None]
rough=np.clip(.87+(fine-.5)*.08+pores*.05,0,1)
maps={'BaseColor':np.uint8(np.clip(rgb,0,255)),'Roughness':np.uint8(rough*255),'Normal':np.uint8(np.clip(n*.5+.5,0,1)*255)}
manifest=dict(provenance='Project-authored porous ceramic body; no third-party source imagery',channels={},tile_size_m=.075)
for channel,array in maps.items():
    path=OUT/('CeramicFracture_'+channel+'.png');Image.fromarray(array).save(path);manifest['channels'][channel]=str(path)
(OUT.parent/'material-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('CERAMIC_CORE_SURFACES_AUTHORED')
