"""Author steel and quilted leather height fields for the detailed armet."""
from pathlib import Path
import json
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
R=Path('D:/FPS3D/FPSGAME/SourceAssets/SteelArmet20261019/ReferenceMatchV5');T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
n=2048;rng=np.random.default_rng(94119);yy,xx=np.mgrid[:n,:n]
def noise(s):
    a=gaussian_filter(rng.normal(size=(n,n)),s,mode='wrap');return a/max(a.std(),1e-8)
def write(name,h,color,rough,metal,span):
    step=span/n;du=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*step);dv=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*step)
    normals=np.stack([-du,dv,np.ones_like(h)],-1);normals/=np.linalg.norm(normals,axis=2,keepdims=True)
    rgb=np.where(color<=.0031308,color*12.92,1.055*np.maximum(color,0)**(1/2.4)-.055)
    cavity=np.clip(1+np.minimum(h,0)*12,.74,1)
    orm=np.stack([cavity,rough,np.broadcast_to(metal,h.shape)],-1)
    for key,a in [('BaseColor',rgb),('Normal',normals*.5+.5),('ORM',orm)]:Image.fromarray(np.round(np.clip(a,0,1)*255).astype('uint8')).save(T/f'T_Armet_{name}_{key}.png')
    np.savez_compressed(T/f'{name}_high_field.npz',height_cm=h,span_cm=span)
# Fine forging marks, sparse oxidation pits, and long worn polishing scratches.
broad=noise(85);fine=noise(1.2);pits=np.maximum(0,noise(3.0)-1.75)*np.clip(.65+.25*noise(42),.15,1)
wear=np.clip((noise(10)*.45+noise(28)*.55-.85)*.8,0,1)
scratches=np.zeros((n,n));scratchcolor=np.zeros((n,n))
for i in range(240):
    x,y=rng.uniform(0,n,2);length=rng.uniform(35,320);angle=rng.normal(.1,.32)
    dx=(xx-x+n/2)%n-n/2;dy=(yy-y+n/2)%n-n/2
    u=dx*np.cos(angle)+dy*np.sin(angle);v=-dx*np.sin(angle)+dy*np.cos(angle)
    stroke=np.exp(-(v/rng.uniform(.45,1.25))**2)*np.clip(1-abs(u)/length,0,1)
    scratches=np.maximum(scratches,stroke);scratchcolor+=stroke*.045
h=.00018*fine+.00035*noise(12)-.0030*pits-.0013*scratches-.0018*wear
base=np.array([.37,.385,.40])[None,None,:]*(1+.08*broad[...,None]-.50*np.clip(pits[...,None]*1.4,0,1))
base=base*(1-.48*wear[...,None])+scratchcolor[...,None]
base-=np.clip(pits[...,None],0,1)*np.array([.008,.015,.024])
write('Steel',h,base,np.clip(.44+.014*noise(3)+.07*pits+.10*wear-.065*scratches,.34,.64),np.clip(.99-wear*.24,0,1),12)
# Flattened leather grain, small pores, dark warm charcoal coloration.
grain=noise(3.6);creases=np.maximum(0,-grain-.4);h=.0034*grain-.0028*creases+.0008*noise(.7)
base=np.array([.024,.018,.013])[None,None,:]*(1+.20*noise(30)[...,None]+.09*grain[...,None])
write('Leather',h,base,np.clip(.77+.07*grain,.61,.93),0,6)
(R/'surfaces.json').write_text(json.dumps(dict(steel_span_cm=12,leather_span_cm=6,resolution=n,normal='OpenGL; UE flip green',orm='R cavity AO G roughness B metallic',source='Analytic forged pits, abrasion, oxidation and leather pore height fields'),indent=2))
print('REFINED_ARMET_SURFACES_AUTHORED',flush=True)
