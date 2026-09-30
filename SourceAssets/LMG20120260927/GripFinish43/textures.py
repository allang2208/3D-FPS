"""Tileable authored PBR detail fields; no old receiver atlas reuse."""
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image,ImageDraw
O=Path(__file__).parent;(O/'Textures').mkdir(exist_ok=True);N=1024;rng=np.random.default_rng(20143)
def field(sigma):
 a=gaussian_filter(rng.normal(size=(N,N)),sigma,mode='wrap');return np.clip(.5+a/max(a.std(),1e-8)*.15,0,1)
grain=field(.8);patch=field(32);fine=field(3.0);marks=Image.new('L',(N,N));draw=ImageDraw.Draw(marks)
for i in range(110):
 x,y=rng.integers(0,N,2);length=int(rng.integers(4,32));draw.line((int(x),int(y),int(x+length),int(y+rng.integers(-2,3))),fill=int(rng.integers(60,170)),width=1)
scratch=np.asarray(marks)/255.;tile=np.stack([grain,patch,scratch,fine],axis=-1);Image.fromarray(np.uint8(np.clip(tile,0,1)*255)).save(O/'Textures/T_LMG201_G43_Finish.png')
height=gaussian_filter(grain,.9,mode='wrap')+.08*scratch;dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.24;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.24;n=np.stack([-dx,dy,np.ones_like(dx)],-1);n/=np.linalg.norm(n,axis=-1,keepdims=True);Image.fromarray(np.uint8((n*.5+.5)*255)).save(O/'Textures/T_LMG201_G43_MicroNormal.png');print('G43_DETAIL_TEXTURES_SAVED')
