"""Tileable artist texture: a two-over, two-under diagonal carbon weave."""
from pathlib import Path
import numpy as np
from PIL import Image
out=Path(__file__).resolve().parent
n=1024
yy,xx=np.mgrid[:n,:n]/n*12.
# Slow variation stays periodic on all tile edges.
x=xx+.028*np.sin(2*np.pi*yy/6)+.014*np.sin(2*np.pi*(yy+xx)/4)
y=yy+.026*np.sin(2*np.pi*xx/4)+.010*np.cos(2*np.pi*(yy-xx)/3)
ix=np.floor(x).astype(int);iy=np.floor(y).astype(int)
fx=x-ix;fy=y-iy
# Each tow is visible for two cells then buried under the next family.
horizontal=(ix-iy)%4<2
ax=np.where(horizontal,fy,fx)
long_axis=np.where(horizontal,x,y)
cross=np.maximum(0.,np.sin(np.pi*ax))**.46
phase=(np.where(horizontal,ix-iy,iy-ix+1)%4 + long_axis%1)/2.
roll=.90+.10*np.cos(2*np.pi*phase)
fil=.5+.5*np.cos(2*np.pi*(ax*13+.09*np.sin(2*np.pi*long_axis/3)))
strand=.5+.5*np.sin(2*np.pi*(.5*ix+.25*iy))
height=np.clip(.16+.65*cross*roll+.085*cross*(fil-.5),0,1)
value=np.where(horizontal, 78+29*cross, 45+19*cross)
value=(value-30)*(0.30+.70*cross)+27+12*cross*(fil-.5)+4*(strand-.5)
rgb=np.stack([value*.94,value*.99,value*1.04],axis=-1)
Image.fromarray(np.clip(rgb,0,255).astype('uint8')).save(out/'woven_face.png')
Image.fromarray((height*255).astype('uint8')).save(out/'woven_height.png')
