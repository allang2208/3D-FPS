"""Author the seating's tileable wood PBR maps, not a preview render."""
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(exist_ok=True)
n=1024;y,x=np.mgrid[0:n,0:n].astype(np.float32)/n;rng=np.random.default_rng(100127);tau=2*np.pi
grain=np.sin(x*tau*57+np.sin(y*tau*2)*2+np.sin(y*tau*7)*.6)
fine=np.sin(x*tau*233+np.sin(y*tau*4)*1.3)
grain=.5+.32*grain+.08*fine+rng.normal(0,.025,(n,n))
shade=.64+.4*grain
linear=np.stack([.14*shade,.064*shade,.025*shade],axis=-1)
srgb=np.where(linear<=.0031308,12.92*linear,1.055*np.maximum(linear,0)**(1/2.4)-.055)
Image.fromarray(np.uint8(np.clip(srgb,0,1)*255)).save(OUT/'T_TheatreWood_BaseColor.png')
orm=np.stack([np.full_like(x,.98),np.clip(.61+.12*grain,0,1),np.zeros_like(x)],axis=-1)
Image.fromarray(np.uint8(orm*255)).save(OUT/'T_TheatreWood_ORM.png')
h=grain*.06;dx=(np.roll(h,-1,1)-np.roll(h,1,1))*2;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*2
normal=np.stack([-dx,dy,np.ones_like(x)],axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(OUT/'T_TheatreWood_NormalDX.png')
print('ANATOMY_THEATRE_WOOD_AUTHORED')
