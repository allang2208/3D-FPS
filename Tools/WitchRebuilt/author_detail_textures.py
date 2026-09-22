"""Original periodic textile and pore detail maps; no external texture source."""
import numpy as np
from PIL import Image
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Refinement20260922/Textures');out.mkdir(parents=True,exist_ok=True)
n=1024;y,x=np.mgrid[:n,:n].astype(np.float32)/n
warp=np.cos(np.pi*x*32)**6;weft=np.cos(np.pi*y*32)**6
over=.5+.5*np.sin(np.pi*x*32)*np.sin(np.pi*y*32)
fiber=.05*np.sin(x*np.pi*384+np.sin(y*np.pi*16))+.04*np.sin(y*np.pi*512)
cloth=warp*(.25+.45*over)+weft*(.70-.45*over)+fiber
cx=x*24-np.floor(x*24)-.5;cy=y*24-np.floor(y*24)-.5
pores=-np.exp(-(cx*cx+cy*cy)*85)*.35
skin=pores+.04*np.sin(x*np.pi*80+np.sin(y*np.pi*12))+.025*np.sin(y*np.pi*116+np.sin(x*np.pi*16))
for name,height,strength in [('Fabric',cloth,1.8),('Skin',skin,1.4)]:
    dx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*strength
    dy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*strength
    normal=np.dstack((-dx,dy,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(out/f'T_Witch_{name}Detail_N.png')
    rough=np.clip(.70+.12*height+.035*np.sin(x*np.pi*14)*np.cos(y*np.pi*18),0,1)
    Image.fromarray(np.uint8(rough*255)).save(out/f'T_Witch_{name}Detail_R.png')
print('Authored four 1024px seamless detail maps; fabric tile 4cm, skin tile 1.2cm')
