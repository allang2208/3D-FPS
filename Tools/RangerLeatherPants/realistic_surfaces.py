"""Restrained scanned leather PBR for Concept03, in measured material units."""
import hashlib,json,math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

P=Path('D:/FPS3D/FPSGAME');BASE=P/'SourceAssets/RangerLeatherPants20261021';R=BASE/'RealisticCutV3'
T=R/'Textures';T.mkdir(parents=True,exist_ok=True);(T/'Exchange').mkdir(exist_ok=True)
SCAN=P/'SourceAssets/HandEquipmentAppearance/Source';PREFIX='Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_'

def read(channel,rgb=False):
    with Image.open(SCAN/(PREFIX+channel+'.jpg')) as im:return np.array(im.convert('RGB' if rgb else 'L'),np.float32)/255
def linear(c):return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
def srgb(c):return np.where(c<=.0031308,c*12.92,1.055*np.maximum(c,0)**(1/2.4)-.055)
def png(name,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(T/(name+'.png'))
def output(name,h,base,rough,ao,span):
    h=gaussian_filter(h,.75,mode='wrap').astype(np.float32);step=span/h.shape[0]
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*step);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*step)
    ns=np.stack((-dx,dy,np.ones_like(h)),-1);ns/=np.linalg.norm(ns,axis=2,keepdims=True)
    png(name+'_BaseColor',base);png(name+'_Normal',ns*.5+.5);png(name+'_ORM',np.stack((ao,rough,np.zeros_like(h)),-1))
    np.save(T/(name+'_height_cm.npy'),h);Image.fromarray(np.uint8(np.clip(rough,0,1)*255+.5)).save(T/'Exchange'/(name+'_Roughness.png'))

base=linear(read('BaseColor',True));bump=read('Bump');disp=read('Displacement');rough=read('Roughness');ao=read('AO')
median=np.median(base.reshape(-1,3),axis=0);tone=np.clip(base/np.maximum(median,1e-8),.64,1.50)
# Macro creases are authored in geometry. Pores are less than 0.1 mm and do not
# compete with those folds. Height, normal and high source share this one field.
fine=bump-gaussian_filter(bump,12,mode='wrap');grain=bump-gaussian_filter(bump,105,mode='wrap');wrinkle=disp-gaussian_filter(disp,210,mode='wrap')
height=.0011*fine+.0020*grain+.022*wrinkle
rough=np.clip(.33+.33*rough+.010*(.5-bump),.43,.68);ao=np.clip(.97+.03*ao,.97,1)
output('WalnutLeather',height,srgb(linear(np.array([.302,.201,.125],np.float32))*(.30+.70*tone)),rough,ao,25)
output('ReinforcedLeather',height*.87,srgb(linear(np.array([.280,.183,.111],np.float32))*(.38+.62*tone)),np.clip(rough-.015,.43,.68),ao,25)
del base,bump,disp,rough,ao,tone,fine,grain,wrinkle,height

N=2048;v,u=np.mgrid[:N,:N].astype(np.float32)/N;rng=np.random.default_rng(2026102106)
def noise(s):
    a=gaussian_filter(rng.standard_normal((N,N)).astype(np.float32),s,mode='wrap');return np.clip(a/max(float(a.std()),1e-8),-3,3)/3
warp=u*184;weft=v*184;cross=gaussian_filter((((np.floor(warp)+np.floor(weft))%4)<2).astype(np.float32),N/184*.16,mode='wrap')
a=(.5-.5*np.cos(math.tau*warp))**2;b=(.5-.5*np.cos(math.tau*weft))**2;slub=noise(18);dye=noise(75);fiber=noise(1.5)
ha=.0021*a*(.42+.58*cross);hb=.0021*b*(1-.58*cross);height=.5*(ha+hb+np.sqrt((ha-hb)**2+.00008**2))+.00010*fiber+.00008*slub
output('OliveTwill',height,np.array([.160,.178,.115],np.float32)*(1+.025*dye+.012*slub)[...,None],np.clip(.81+.021*slub-.010*(a+b),.77,.89),.97+.03*np.maximum(a,b),8)
sources={}
for channel in ('BaseColor','Bump','Displacement','Roughness','AO'):
    p=SCAN/(PREFIX+channel+'.jpg');sources[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
record=dict(completed=True,revision='RealisticCutV3',concept=str(BASE/'Design/LeatherPants_Concept03_Realistic.png'),source_scan_id='xjghdgl',source_scan=str(SCAN),source_scan_area_cm=[25,25],source_hashes=sources,tile_cm_by_family={'WalnutLeather':25,'ReinforcedLeather':25,'OliveTwill':8},resolution_by_family={'WalnutLeather':4096,'ReinforcedLeather':4096,'OliveTwill':2048},normal_convention='OpenGL from filtered scalar height; Blender UV=(u,1-v); UE flip green once',height_gains_cm={'fine_bump':.0011,'grain_bump':.0020,'detrended_displacement':.022},thread_linear_color=[.085,.052,.027],color='Retinted scan intrinsic color; close-value cut panels, no painted illumination',families=['WalnutLeather','ReinforcedLeather','OliveTwill'],test_performed=False,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in T.glob('*.png')})
(R/'surfaces.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print('REALISTIC_CUT_SURFACES_SAVED',flush=True)
