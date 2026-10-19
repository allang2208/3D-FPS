"""Physical wool/satin height fields shared by high-detail patches and PBR maps."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
n=2048;span=4.;rng=np.random.default_rng(61019);y,x=np.mgrid[:n,:n]/n
fine=gaussian_filter(rng.normal(size=(n,n)),1.3,mode='wrap');fine/=fine.std()
cloud=gaussian_filter(rng.normal(size=(n,n)),28,mode='wrap');cloud/=cloud.std()
warp=np.sin(math_tau:=2*np.pi*x*112);weft=np.sin(2*np.pi*y*112)
twill=np.sin(2*np.pi*(x*56-y*112));fiber=np.sin(2*np.pi*(x*225+y*3))
fields={
    'Worsted':(.0011*(warp+weft)+.0007*twill+.0003*fine+.00013*fiber,np.array([40,42,46]),.82),
    'Cobalt':(.0009*warp+.00065*weft+.0002*fine,np.array([23,42,77]),.68),
    'Facing':(.00065*(warp+weft)+.00025*fine,np.array([25,27,31]),.90)}
receipt={}
for name,(h,color,roughness) in fields.items():
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*span/n);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*span/n);normal=np.stack([-dx,dy,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    rgb=np.clip(color[None,None,:]*(1+(.020*fine+.018*cloud)[...,None]),0,255).astype('uint8');orm=np.stack([np.clip(.97+.012*fine,.88,1),np.clip(roughness+.019*fine,.45,.96),np.zeros_like(h)],-1)
    height=(h-h.min())/max(np.ptp(h),1.e-9)
    for channel,value in [('BaseColor',rgb),('Normal',np.clip((normal*.5+.5)*255,0,255).astype('uint8')),('ORM',(orm*255).astype('uint8')),('Height',np.uint16(np.round(height*65535)))]:Image.fromarray(value).save(R/'Textures'/f'T_MagePants_{name}_{channel}.png')
    np.savez_compressed(R/f'HIGH_{name}.npz',height_cm=h.astype('float32'),span_cm=span)
    receipt[name]=dict(size=n,span_cm=span,height_range_cm=[float(h.min()),float(h.max())],channels=['BaseColor','Normal','ORM','Height'])
write(R/'surface_receipt.json',dict(fields=receipt,method='Analytic physical height source; finite-difference tangent-space normal; same field retained for displaced high mesh',runtime_tested=False));print('MAGE_PANTS_SURFACES_SAVED',flush=True)
