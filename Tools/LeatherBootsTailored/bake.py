"""Material-scaled scan leather, layered welt and rubber height/normal/PBR fields."""
import hashlib,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
sys.path.insert(0,str(Path(__file__).parent));from boot_paths import *
T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
SCAN=P/'SourceAssets/HandEquipmentAppearance/Source';PREFIX='Fabric_Generic_Leather_Top_Grain_Brown_xjghdgl_4K_'
def load(c,rgb=False):
    with Image.open(SCAN/(PREFIX+c+'.jpg')) as im:return np.array(im.convert('RGB' if rgb else 'L'),np.float32)/255
def linear(c):return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)
def srgb(c):return np.where(c<=.0031308,c*12.92,1.055*np.maximum(c,0)**(1/2.4)-.055)
reports={}
def periodic(a,k=64):
    a=np.array(a,copy=True)
    for axis in (0,1):
        for j in range(k):
            w=.5+.5*(j/(k-1))**.6;lo=[slice(None)]*a.ndim;hi=lo.copy();lo[axis]=j;hi[axis]=-1-j;x=a[tuple(lo)].copy();y=a[tuple(hi)].copy();a[tuple(lo)]=x*w+y*(1-w);a[tuple(hi)]=y*w+x*(1-w)
    return a
def save(name,h,base,rough,ao,metal,span):
    h=gaussian_filter(periodic(h),.8,mode='wrap');base=periodic(base);rough=periodic(rough);ao=periodic(ao);step=span/h.shape[0];dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*step);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*step);n=np.stack((-dx,dy,np.ones_like(h)),-1);n/=np.linalg.norm(n,axis=2,keepdims=True)
    for channel,values in [('BaseColor',base),('Normal',n*.5+.5),('ORM',np.stack((ao,rough,np.broadcast_to(metal,h.shape)),-1))]:Image.fromarray(np.uint8(np.clip(values,0,1)*255+.5)).save(T/(name+'_'+channel+'.png'))
    np.save(T/(name+'_height_cm.npy'),h.astype(np.float32));reports[name]=dict(size=h.shape[0],span_cm=span,normal_z_mean=float(n[...,2].mean()),roughness_range=[float(rough.min()),float(rough.max())],height_range_cm=[float(h.min()),float(h.max())])
base=linear(load('BaseColor',True));bump=load('Bump');disp=load('Displacement');rough=load('Roughness');ao=load('AO');tone=np.clip(base/np.maximum(np.median(base.reshape(-1,3),axis=0),1e-8),.65,1.50)
h=.0007*(bump-gaussian_filter(bump,12,mode='wrap'))+.0014*(bump-gaussian_filter(bump,100,mode='wrap'))+.013*(disp-gaussian_filter(disp,200,mode='wrap'))
rr=np.clip(.34+.32*rough,.44,.69);occ=.97+.03*ao
patina=gaussian_filter(np.random.default_rng(20261023).standard_normal(bump.shape).astype(np.float32),75,mode='wrap');patina/=patina.std();patina=np.clip(patina*.14,-.27,.31)
rr=np.clip(rr-patina*.07,.44,.69)
save('BootLeather',h,srgb(linear(np.array([.292,.179,.112]))*(.08+.92*tone)*(1+patina[...,None])),rr,occ,0,25)
save('BootReinforced',h*.88,srgb(linear(np.array([.267,.156,.093]))*(.14+.86*tone)*(1+.8*patina[...,None])),np.clip(rr-.022,.43,.68),occ,0,25)
del base,bump,disp,rough,ao,tone,h,rr,occ
N=2048;v,u=np.mgrid[:N,:N].astype(np.float32)/N;rng=np.random.default_rng(20261022)
def noise(scale):
    a=gaussian_filter(rng.standard_normal((N,N)).astype(np.float32),scale,mode='wrap');return a/max(float(a.std()),1e-8)
micro=noise(1.6);broad=noise(42);height=.0008*micro+.0010*noise(7)
save('BootRubber',height,np.array([.066,.062,.055])*(1+.035*np.clip(broad,-2,2))[...,None],np.clip(.80+.015*broad+.010*micro,.74,.88),np.ones((N,N))*.99,0,10)
grain=noise(2);drift=noise(80);strata=np.sin(2*np.pi*(v*240+.045*drift));height=.0032*strata+.00055*grain
base=np.array([.155,.100,.060])*(1+.045*strata+.028*np.clip(drift,-2,2))[...,None]
save('BootWelt',height,base,np.clip(.65+.035*strata+.018*grain,.52,.78),.975+.025*(strata*.5+.5),0,25)
write(R/'surfaces.json',dict(completed=True,source_scan='xjghdgl',source_hashes={c:hashlib.sha256((SCAN/(PREFIX+c+'.jpg')).read_bytes()).hexdigest() for c in ('BaseColor','Bump','Displacement','Roughness','AO')},families=reports,normal_convention='OpenGL; UE flip green once; UV measured in centimetres',thread_linear_color=[.145,.078,.035],metal_linear_color=[.12,.125,.13],runtime_tested=False))
print('LEATHER_BOOT_PBR_BAKED',reports,flush=True)
