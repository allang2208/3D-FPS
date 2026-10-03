"""Bake physical 4K steel/gold PBR from the shared ornament and relief recipe."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from surface_math import smooth, ornament, total_height
P = Path(__file__).resolve().parent
OUT = P/'Textures'
N = 4096
base = np.empty((N,N,3), np.uint8)
orm = np.empty_like(base)
normal = np.empty_like(base)
u = (np.arange(N,dtype=np.float32)+.5)[None,:]/N
front = u<.5
t = np.clip(np.where(front,(u-.02)/.46,(.98-u)/.46),0,1)
x = t*.066
edge = 1-smooth(.20,.30,t)
groove = np.exp(-((t-.855)/.041)**4)
for first in range(0,N,96):
    last = min(first+96,N)
    v = 1-(np.arange(first,last,dtype=np.float32)+.5)[:,None]/N
    z = .014+v*.866
    gate = smooth(.165,.20,z)*(1-smooth(.69,.755,z))
    phase = x*1420+z*15+1.15*np.sin(z*24+x*41)+.42*np.sin(z*71-x*87)
    grain = .55*np.sin(phase*np.pi*2)+.25*np.sin(phase*2.13*np.pi*2)
    cloud = np.sin(x*340+2.8*np.sin(z*19)+.6*np.sin(z*73))
    blend = smooth(.08,.15,z)
    panel = (.50*(1-blend)+.345*blend)*(1+.075*grain+.023*cloud)
    brightness = (panel*(1-edge)+(.63+.015*np.sin(z*340))*edge)*(1-.12*groove*gate)
    steel = brightness[...,None]*np.array([.965,1.,1.03],np.float32)
    mask, color = ornament(t,z)
    # Gold albedo is kept physical; the authored normal provides relief lighting.
    variation = .91+.18*(color[...,0]-.5)
    gold = variation[...,None]*np.array([.63,.405,.16],np.float32)
    linear = steel*(1-mask[...,None])+gold*mask[...,None]
    encoded = np.where(linear<=.0031308,linear*12.92,1.055*np.maximum(linear,0)**(1/2.4)-.055)
    base[first:last] = np.rint(np.clip(encoded,0,1)*255).astype(np.uint8)
    rough = (.295+.019*grain+.015*cloud-.12*edge+.09*groove*gate)*(1-mask)+(.255+.028*grain)*mask
    ambient = 1-.13*groove*gate-.035*mask
    orm[first:last] = np.rint(np.stack([ambient,np.clip(rough,.16,.46),np.ones_like(ambient)],-1)*255).astype(np.uint8)
    eps = .000012
    dx = (total_height(t+eps/.066,z)-total_height(t-eps/.066,z))/(2*eps)
    dz = (total_height(t,z+eps)-total_height(t,z-eps))/(2*eps)
    dx *= np.where(front,1,-1)
    strength = 1-.65*edge
    n = np.stack([-dx*strength,-dz*strength,np.ones_like(dx)],-1)
    n /= np.linalg.norm(n,axis=-1,keepdims=True)
    normal[first:last] = np.rint(np.clip(n*.5+.5,0,1)*255).astype(np.uint8)
for key, data in [('BaseColor',base),('ORM',orm),('Normal',normal)]:
    Image.fromarray(data).save(OUT/('TangDao_Tengyun_'+key+'.png'))
(P/'surface_recipe.json').write_text(json.dumps({
    'resolution':[N,N],'uv_channel':0,'uv_z_cm':[1.4,88.0],'normal_convention':'OpenGL; Unreal flips green',
    'orm_channels':['ambient_occlusion','roughness','metallic'],
    'ornament_source':'Tengyun_GildedDragon_Ornament.png','ornament_generation':'ornament_generation.json',
    'dragon_inlay_relief_mm':[.13,.195],'steel_linear_albedo':.345,
    'gold_linear_albedo':[.63,.405,.16],'long_fuller_depth_mm':.70,
    'steel_surface':'waterwave folded steel, flowing cloud etching, fine honing scratches',
    'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('TENGYUN_4K_PBR_AUTHORED',flush=True)
