"""Bake textile PBR from explicit physical height fields; no painted lighting."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR2';OUT=R/'Textures';OUT.mkdir(exist_ok=True)
size=1024;tile_cm=8.;y,x=np.mgrid[:size,:size]/size;records={}
rng=np.random.default_rng(71114);noise=rng.normal(0,1,(size,size))
warp_x=gaussian_filter(rng.normal(0,1,(size,size)),3,mode='wrap');warp_y=gaussian_filter(rng.normal(0,1,(size,size)),3,mode='wrap');warp_x/=warp_x.std();warp_y/=warp_y.std()
for name,colour,rough,kind in [('CombatRipstop',[124,96,65],.80,'ripstop'),('CombatCarrier',[103,78,52],.77,'canvas'),('CombatStretch',[68,50,35],.84,'knit'),('CombatCuff',[89,66,45],.83,'rib'),('CombatLining',[51,39,29],.87,'lining'),('CombatThread',[151,119,82],.78,'lining')]:
    phase_x=x*160+.18*warp_x;phase_y=y*160+.18*warp_y;warp=np.cos(phase_x*2*np.pi);weft=np.cos(phase_y*2*np.pi);over=(np.floor(phase_x)+np.floor(phase_y))%2
    weave=(np.maximum(warp,0)**1.8*(.5+.5*over)+np.maximum(weft,0)**1.8*(1-.5*over))
    height=weave*.0015
    if kind=='ripstop':
        gx=np.minimum((x*16)%1,1-(x*16)%1);gy=np.minimum((y*16)%1,1-(y*16)%1)
        grid=np.maximum(np.exp(-(gx/.065)**2),np.exp(-(gy/.065)**2));height+=grid*.0025
    elif kind=='knit':height=.0018*(1+np.sin(2*np.pi*(x*112+.26*np.sin(y*112*2*np.pi)+.12*warp_x)))*(.72+.28*np.cos(y*112*2*np.pi))
    elif kind=='rib':height=.0022*np.cos(x*64*2*np.pi)**2+weave*.0008
    else:height*=.55
    # Fine fibres change roughness and normal, not the garment silhouette.
    fine=.00035*np.sin((x*431+y*73)*2*np.pi)*np.sin((y*389-x*59)*2*np.pi);height+=fine
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*tile_cm/size);dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*tile_cm/size)
    normal=np.dstack([-dx,-dy,np.ones_like(dx)]);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    # Dye variation is stochastic. Regular colour sine waves read as large
    # printed stripes in an inventory thumbnail, rather than woven fibres.
    dye=gaussian_filter(noise,18,mode='wrap');dye/=max(float(dye.std()),1e-8)
    modulation=1+.008*dye+.003*noise
    base=np.clip(np.array(colour)[None,None,:]*modulation[:,:,None],0,255).astype('uint8')
    normalized=(height-height.min())/(height.max()-height.min());orm=np.dstack([.93+.07*normalized,np.clip(rough+.025*noise+.025*(1-normalized),.65,.94),np.zeros_like(height)])
    relief=np.dstack([normalized,np.clip(.42+.18*noise,0,1),np.ones_like(height)])
    for channel,array in [('BaseColor',base),('NormalGL',np.clip((normal*.5+.5)*255,0,255).astype('uint8')),('ORM',np.clip(orm*255,0,255).astype('uint8')),('Relief',np.clip(relief*255,0,255).astype('uint8'))]:Image.fromarray(array).save(OUT/(name+'_'+channel+'.png'))
    np.savez_compressed(R/'Bakes'/(name+'_height_field.npz'),height_cm=height.astype('float32'),tile_cm=tile_cm)
    records[name]=dict(tile_cm=tile_cm,resolution=size,height_min_cm=float(height.min()),height_max_cm=float(height.max()),normal_convention='OpenGL',method='Normal/roughness/AO baked from the same explicit physical textile field; no directional-light shading in colour')
(R/'Bakes/textile-fields.json').write_text(json.dumps(records,indent=2));print('TS01_R2_TEXTILE_FIELDS',len(records),flush=True)
