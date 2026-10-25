"""Metric authored weave/leather fields; no image editing or validation renders."""
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
from workwear_common import *
rows=[]
for index,(name,n,color,rough,metal,span) in enumerate([
 ('Canvas',2048,[114,108,90],.76,0,8.),('Leather',2048,[88,60,41],.60,0,8.),
 ('Lining',1024,[42,44,40],.86,0,8.),('Brass',1024,[134,102,57],.45,.90,8.),
 ('Thread',512,[42,77,110],.84,0,8.),('HatCanvas',2048,[126,117,82],.81,0,25.)]):
    rng=np.random.default_rng(26102440+index);y,x=np.mgrid[:n,:n]/n
    def noise(s):
        a=gaussian_filter(rng.normal(size=(n,n)),s,mode='wrap');return a/max(a.std(),1e-8)
    fine=noise(.7);grain=noise(n/300);broad=noise(n/38);cloud=noise(n/12)
    if name in ('Canvas','HatCanvas','Lining'):
        freq=144 if name!='HatCanvas' else 310
        wx=np.sin(2*np.pi*x*freq);wy=np.sin(2*np.pi*y*freq)
        interlace=np.cos(np.pi*np.floor(x*freq))*np.cos(np.pi*np.floor(y*freq))
        h=.0010*(wx+wy)+.00065*interlace+.00035*fine+.00045*grain
        variation=.022*grain+.018*broad+.007*(wx+wy)
        if name=='HatCanvas':variation+=.045*np.tanh(cloud*1.4)+.018*np.tanh(broad)
    elif name=='Leather':
        pores=np.maximum(-grain-.2,0)**1.2;creases=np.exp(-((broad+.3)/.14)**2)
        h=.0018*grain-.0009*pores-.0010*creases+.00025*fine
        variation=.025*grain+.028*cloud-.013*pores
    elif name=='Brass':
        brush=noise((.6,14));h=.00020*brush+.00013*fine;variation=.035*brush+.028*cloud
    else:
        twist=np.sin(2*np.pi*(x*120+y*24));h=.0007*twist+.00015*fine;variation=.025*twist+.01*grain
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*span/n);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*span/n)
    normal=np.stack([-dx,dy,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    rgb=np.clip(np.array(color)[None,None,:]*(1+variation[...,None]),0,255).astype('uint8')
    orm=np.stack([np.clip(.977+.008*grain,.90,1),np.clip(rough+.02*grain+.015*cloud,.25,.96),np.full_like(h,metal)],-1)
    for channel,data in [('BaseColor',rgb),('Normal',((normal*.5+.5)*255).clip(0,255).astype('uint8')),('ORM',(orm*255).astype('uint8'))]:Image.fromarray(data).save(R/'Textures'/f'T_Workwear_{name}_{channel}.png')
    Image.fromarray(((h-h.min())/max(float(np.ptp(h)),1e-8)*65535).astype('uint16')).save(R/'Textures'/f'T_Workwear_{name}_Height.png')
    np.savez_compressed(R/'Exports'/f'HIGH_{name}.npz',height_cm=h.astype('float32'),span_cm=span)
    rows.append(dict(name=name,resolution=n,span_cm=span,height_range_cm=[float(h.min()),float(h.max())],normal_convention='OpenGL'))
    # The existing precise hat exporter consumes these names, at 25 cm UV scale.
    if name in ('HatCanvas','Leather'):
        for channel in ('BaseColor','Normal','ORM'):
            import shutil
            shutil.copy2(R/'Textures'/f'T_Workwear_{name}_{channel}.png',R/'Hat/Textures'/f'T_FieldHat_{"Canvas" if name=="HatCanvas" else name}_{channel}.png')
write(R/'textures.json',dict(completed=True,maps=rows,source='original shared metric height fields',runtime_maps_per_family=3))
print('WORKWEAR_TEXTURES_AUTHORED',len(rows)*4)
