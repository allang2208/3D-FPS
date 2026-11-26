"""Use the project's existing top-grain scan and physical height fields.

No image synthesis, runtime import, or acceptance render. The scan remains
subject to its original asset license; it is not a newly generated material.
"""
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/RangerLeatherPants20261021';R=BASE/'AtelierFinishV2';T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
SCAN=P/'SourceAssets/HandEquipmentAppearance/Source';PREFIX='Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_'
def read(channel,rgb=False):
    with Image.open(SCAN/(PREFIX+channel+'.jpg')) as im:return np.array(im.convert('RGB' if rgb else 'L'),np.float32)/255
def linear(c):return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
def srgb(c):return np.where(c<=.0031308,c*12.92,1.055*np.maximum(c,0)**(1/2.4)-.055)
def png(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(T/(name+'.png'))
def output(name,h,base,rough,ao,span):
    h=gaussian_filter(h,.6,mode='wrap').astype(np.float32);step=span/h.shape[0]
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*step);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*step)
    ns=np.stack((-dx,dy,np.ones_like(h)),-1);ns/=np.linalg.norm(ns,axis=2,keepdims=True)
    png(name+'_BaseColor',base);png(name+'_Normal',ns*.5+.5);png(name+'_ORM',np.stack((ao,rough,np.zeros_like(h)),-1))
    np.save(T/(name+'_height_cm.npy'),h);(T/'Exchange').mkdir(exist_ok=True);Image.fromarray(np.uint8(np.clip(rough,0,1)*255+.5)).save(T/'Exchange'/(name+'_Roughness.png'))
base=linear(read('BaseColor',True));bump=read('Bump');disp=read('Displacement');rough=read('Roughness');ao=read('AO')
mean=np.median(base.reshape(-1,3),axis=0);tone=np.clip(base/np.maximum(mean,1e-8),.65,1.40)
# Keep the source's irregular pores and vein structure. The bump/disp gains
# are intentionally art-calibrated micro relief, not the scan's full 14 mm range.
fine=bump-gaussian_filter(bump,18,mode='wrap');grain=bump-gaussian_filter(bump,130,mode='wrap');wrinkle=disp-gaussian_filter(disp,240,mode='wrap')
height=.0035*fine+.0055*grain+.070*wrinkle
rough=np.clip(.34+.35*rough+.020*(.5-bump),.47,.73);ao=np.clip(.94+.06*ao,.94,1)
output('WalnutLeather',height,srgb(linear(np.array([.325,.210,.130],np.float32))*tone),rough,ao,25)
output('ReinforcedLeather',height*.72,srgb(linear(np.array([.245,.148,.078],np.float32))*(.35+.65*tone)),np.clip(rough-.035,.45,.70),ao,25)
del base,bump,disp,rough,ao,tone,fine,grain,wrinkle,height
# Preserve the established cloth identity, refine yarn variation and fuzz in
# the scalar field; leather itself never receives this cloth/fiber treatment.
N=2048;v,u=np.mgrid[:N,:N].astype(np.float32)/N;rng=np.random.default_rng(2026102103)
def noise(s):
    a=gaussian_filter(rng.standard_normal((N,N)).astype(np.float32),s,mode='wrap');return np.clip(a/max(float(a.std()),1e-8),-3,3)/3
threads=184;warp=u*threads;weft=v*threads;cross=gaussian_filter((((np.floor(warp)+np.floor(weft))%4)<2).astype(np.float32),N/threads*.16,mode='wrap')
a=(.5-.5*np.cos(math.tau*warp))**2;b=(.5-.5*np.cos(math.tau*weft))**2;slub=noise(18);dye=noise(75);fiber=noise(1.5)
ha=.0024*a*(.42+.58*cross);hb=.0024*b*(1-.58*cross);height=.5*(ha+hb+np.sqrt((ha-hb)**2+.00008**2))+.00012*fiber+.00010*slub
output('OliveTwill',height,np.array([.185,.203,.129],np.float32)*(1+.022*dye+.012*slub)[...,None],np.clip(.83+.021*slub-.010*(a+b),.78,.9),.97+.03*np.maximum(a,b),8)
meta=json.loads((SCAN/'xjghdgl.json').read_text());sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in SCAN.glob('*.jpg') if any(p.stem.endswith(s) for s in ('BaseColor','Bump','Displacement','Roughness','AO'))}
(R/'surfaces.json').write_text(json.dumps(dict(completed=True,revision='AtelierFinishV2',source_scan_id='xjghdgl',source_scan=str(SCAN),source_scan_name=meta['name'],source_scan_area_cm=[25,25],source_hashes=sources,tile_cm_by_family={'WalnutLeather':25,'ReinforcedLeather':25,'OliveTwill':8},resolution_by_family={'WalnutLeather':4096,'ReinforcedLeather':4096,'OliveTwill':2048},normal_convention='OpenGL from same filtered height field; UV=(u,1-v); UE flips green once',height_gains_cm={'fine_bump':.0035,'grain_bump':.0055,'detrended_displacement':.070},color='retinted scan intrinsic color; no rendered lighting',families=['WalnutLeather','ReinforcedLeather','OliveTwill'],test_performed=False,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in T.glob('*.png')}),ensure_ascii=False,indent=2),encoding='utf-8')
print('ATELIER_SCAN_SURFACES_SAVED',flush=True)
