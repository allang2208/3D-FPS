"""Bake the stable's local traffic mask, metres east/south projected into decal UVs."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[3]/"SourceAssets/HillsVillageStable/AssemblyR1"
ROOT.mkdir(parents=True,exist_ok=True)
N=2048
X0,Y0,WIDTH,HEIGHT=27.,3.,36.,42.
CART=[(59,5),(56.9,5.3),(55,6.3),(53.7,8.1),(52.7,10.7),(52.5,13.1),(52.5,16),
      (52.5,19),(52.6,25),(52.8,30.7),(52.8,35.7),(52.8,39.0)]
HORSE=[(51.4,5.05),(49.3,6.3),(47.7,8.2),(46.5,10.8),(46.25,13.5),(46.25,16),
       (46.25,30.7),(45,32.65),(43,33.6),(35.2,33.6),(32,34.6),(31.5,37.7),(31,40.9)]
mask=Image.new("L",(N,N))
rng=np.random.default_rng(5642)

def xy(x,y):
    return ((x-X0)*N/WIDTH,(y-Y0)*N/HEIGHT)

def band(points,width,level,blur):
    global mask
    sheet=Image.new("L",mask.size)
    brush=ImageDraw.Draw(sheet)
    brush.line([xy(*p) for p in points],fill=level,width=max(1,round(width*N/WIDTH)),joint="curve")
    sheet=sheet.filter(ImageFilter.GaussianBlur(blur*N/WIDTH))
    mask=Image.fromarray(np.maximum(np.asarray(mask),np.asarray(sheet)))

pad=ImageDraw.Draw(mask)
pad.ellipse([xy(48.15,19.9),xy(57.15,28.9)],fill=124)
pad.rectangle([xy(33,35.5),xy(55,43.5)],fill=183)
mask=mask.filter(ImageFilter.GaussianBlur(15))
band(CART,3.9,165,.28)
band(HORSE,2.05,147,.22)
for x in (35.2,39.6,44,48.4):
    band([(x,33.3),(x,35.7)],1.45,168,.20)
for side in (-1,1):
    points=np.array(CART)
    tangent=np.gradient(points,axis=0)
    normal=tangent[:,::-1]*[1,-1]/np.linalg.norm(tangent,axis=1)[:,None]
    band(points+normal*side*.75,.19,236,.05)
angle=np.linspace(-1.2,3.9,52)
for radius in (3.15,4.50):
    band(list(zip(52.65+radius*np.cos(angle),24.4+radius*np.sin(angle))),.16,188,.095)
value=np.asarray(mask,dtype=np.float32)/255.
for frequency,amplitude in ((24,.27),(117,.21),(580,.24)):
    tiles=Image.fromarray(rng.integers(0,256,(frequency,frequency),dtype=np.uint8))
    noise=np.asarray(tiles.resize(mask.size,Image.Resampling.BICUBIC),dtype=np.float32)/255.-.5
    value*=1+amplitude*noise
value*=rng.normal(1,.07,value.shape)
Image.fromarray(np.uint8(255*np.clip(value,0,1))).save(ROOT/"StableTraffic.png")
