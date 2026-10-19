"""Physical leather grain, woven cloth, lining and rubber source fields."""
from common import *
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
n=2048;span=4.;rng=np.random.default_rng(6101908);y,x=np.mgrid[:n,:n]/n
fine=gaussian_filter(rng.normal(size=(n,n)),1.1,mode='wrap');fine/=fine.std()
grain=gaussian_filter(rng.normal(size=(n,n)),5.2,mode='wrap');grain/=grain.std()
cloud=gaussian_filter(rng.normal(size=(n,n)),32,mode='wrap');cloud/=cloud.std()
ridge=np.exp(-((grain+.15)/.20)**2);ridge-=ridge.mean()
warp=np.sin(2*np.pi*x*108);weft=np.sin(2*np.pi*y*108)
fields={
 'Leather':(-.0040*ridge+.0011*grain+.00035*fine,np.array([30,33,39]),.53),
 'Cobalt':(.0011*warp+.0008*weft+.0003*fine,np.array([26,47,90]),.68),
 'Lining':(.0007*(warp+weft)+.0003*fine,np.array([21,24,29]),.91),
 'Rubber':(.0007*grain+.00045*fine,np.array([21,23,26]),.86)}
receipt={}
for name,(h,color,roughness) in fields.items():
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*span/n);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*span/n);normal=np.stack([-dx,dy,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    rgb=np.clip(color[None,None,:]*(1+(.022*fine+.025*cloud+.016*grain)[...,None]),0,255).astype('uint8');orm=np.stack([np.clip(.97+.012*grain,.89,1),np.clip(roughness+.025*grain+.012*fine,.35,.98),np.zeros_like(h)],-1)
    height=(h-h.min())/max(np.ptp(h),1.e-9)
    for channel,value in [('BaseColor',rgb),('Normal',np.clip((normal*.5+.5)*255,0,255).astype('uint8')),('ORM',(orm*255).astype('uint8')),('Height',np.uint16(np.round(height*65535)))]:Image.fromarray(value).save(R/'Textures'/f'T_MageBoots_{name}_{channel}.png')
    np.savez_compressed(R/f'HIGH_{name}.npz',height_cm=h.astype('float32'),span_cm=span)
    receipt[name]=dict(size=n,span_cm=span,height_range_cm=[float(h.min()),float(h.max())],channels=['BaseColor','Normal','ORM','Height'])
write(R/'surface_receipt.json',dict(fields=receipt,method='Analytic physical surface fields; finite-difference tangent normal; retained displaced high source',runtime_tested=False));print('MAGE_BOOTS_SURFACES_SAVED',flush=True)
