"""Bake physically scaled boot material fields from the project's leather scan.

Technical PBR authoring, not a preview image. Normal and retained height share
one physical field; colour is not used to infer relief.
"""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/BootFinishR8';T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
S=P/'SourceAssets/HandEquipmentAppearance/Source';PREFIX='Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_'
def read(channel):
    with Image.open(S/(PREFIX+channel+'.jpg')) as im:return np.asarray(im.convert('RGB' if channel=='BaseColor' else 'L'),dtype=np.float32)/255
def linear(c):return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
def srgb(c):return np.where(c<=.0031308,c*12.92,1.055*np.maximum(c,0)**(1/2.4)-.055)
def periodic(a,k=48):
    a=a.copy()
    for axis in (0,1):
        for j in range(k):
            w=.5+.5*j/(k-1);lo=[slice(None)]*a.ndim;hi=lo.copy();lo[axis]=j;hi[axis]=-1-j;x=a[tuple(lo)].copy();y=a[tuple(hi)].copy();a[tuple(lo)]=x*w+y*(1-w);a[tuple(hi)]=y*w+x*(1-w)
    return a
reports={}
def save(name,height,base,rough,ao,span,orm_size=None):
    height=periodic(height);base=periodic(base);rough=periodic(rough);ao=periodic(ao);step=span/height.shape[0]
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*step);dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*step)
    normal=np.stack((-dx,dy,np.ones_like(height)),-1);normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    for channel,data in [('BaseColor',base),('Normal',normal*.5+.5),('ORM',np.stack((ao,rough,np.zeros_like(height)),-1))]:
        image=Image.fromarray(np.uint8(np.clip(data,0,1)*255+.5))
        if channel=='ORM' and orm_size:image=image.resize((orm_size,orm_size),Image.Resampling.BOX)
        image.save(T/(name+'_'+channel+'.png'))
    np.save(T/(name+'_height_cm.npy'),height.astype(np.float32))
    Image.fromarray(np.uint16(np.clip(.5+height/.02,0,1)*65535+.5)).save(T/(name+'_Height16.png'))
    reports[name]={'base_normal_size':height.shape[0],'orm_size':orm_size or height.shape[0],'tile_span_cm':span,'roughness_range':[float(rough.min()),float(rough.max())],'height_range_cm':[float(height.min()),float(height.max())]}

base=linear(read('BaseColor'));bump=read('Bump');disp=read('Displacement');rough=read('Roughness');ao=read('AO')
tone=base/np.maximum(np.median(base.reshape(-1,3),axis=0),1e-6)
# Suppress scan illumination and large mottling while retaining pore colour.
for c in range(3):tone[...,c]/=np.maximum(gaussian_filter(tone[...,c],70,mode='wrap'),.1)
tone=np.clip(tone,.79,1.22)
h=.0011*(bump-gaussian_filter(bump,10,mode='wrap'))+.0017*(bump-gaussian_filter(bump,70,mode='wrap'))+.007*(disp-gaussian_filter(disp,140,mode='wrap'))
h=gaussian_filter(h,.65,mode='wrap')
save('NunBootLeather',h,srgb(linear(np.array([.265,.204,.151]))*(.18+.82*tone)),np.clip(.37+.22*rough,.43,.63),.985+.015*ao,25,2048)
del base,bump,disp,rough,ao,tone,h
rng=np.random.default_rng(20261117)
def noise(n,scale):
    a=gaussian_filter(rng.standard_normal((n,n)).astype(np.float32),scale,mode='wrap');return a/max(float(a.std()),1e-6)
n=1024;micro=noise(n,1.2);wide=noise(n,22);height=.00045*micro+.00045*noise(n,6)
save('NunBootRubber',height,np.array([.085,.081,.074])*(1+.028*np.clip(wide,-2,2))[...,None],np.clip(.77+.022*wide+.012*micro,.70,.86),np.ones((n,n))*.995,10)
n=2048;v=np.arange(n,dtype=np.float32)[:,None]/n;drift=noise(n,55);grain=noise(n,1.6)
strata=np.sin(2*np.pi*(v*180+.035*drift));height=.0018*strata+.00035*grain
save('NunBootWelt',height,np.array([.166,.127,.091])*(1+.035*strata+.022*np.clip(drift,-2,2))[...,None],np.clip(.58+.025*strata+.012*grain,.50,.68),.985+.015*(strata*.5+.5),25)
meta={'completed':True,'source_scan':'Existing project source: xjghdgl top-grain brown leather','source_hashes':{c:hashlib.sha256((S/(PREFIX+c+'.jpg')).read_bytes()).hexdigest() for c in ['BaseColor','Bump','Displacement','Roughness','AO']},'families':reports,'normal_convention':'OpenGL; UE flips green once','local_wear':'Native rest-position masks in nun-only materials; toe polish, heel rub, lower edge dust, curved flex zones','runtime_tested':False}
(R/'surfaces.json').write_text(json.dumps(meta,indent=2),encoding='utf-8');print('NUN_BOOT_R8_SURFACES_BAKED',json.dumps(reports),flush=True)
