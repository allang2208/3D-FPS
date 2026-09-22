"""Bake the installed shader's still frame onto the real module UV0 for icons."""
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
P=Path(__file__).resolve().parent;OUT=P/'IconMaterials';OUT.mkdir(exist_ok=True)
SRC=P.parent/'RuneSword20260913/Original/Meshy_AI_Azure_Starblade_0913123202_texture_fbx'
stem='Meshy_AI_Azure_Starblade_0913123202_texture'
def read(f):return np.asarray(Image.open(f).convert('RGB'),np.float32)/255
def linear(x):return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
def srgb(x):return np.where(x<=.0031308,x*12.92,1.055*np.maximum(x,0)**(1/2.4)-.055)
def save(f,x):Image.fromarray(np.uint8(np.round(np.clip(x,0,1)*255))).save(OUT/f)
base=linear(read(SRC/(stem+'.png')));original_emission=linear(read(SRC/(stem+'_emission.png')))*3.5
mask=read(P/'T_RuneSword_NativeMask.png');m=mask[:,:,0,None]
detail=.6+.4*np.clip((base@np.array([.2126,.7152,.0722]))/.75,0,1)
save('gold_base.png',srgb(base*(1-m)+np.array([.58,.285,.052])*detail[:,:,None]*m))
phase=.16;wave=2**(-((mask[:,:,2]-phase)/.085)**2*3)
glow=mask[:,:,0]*.75*(1+.055*np.sin(1.65)+.24*wave)+mask[:,:,1]*.75*.035
save('gold_emission.png',srgb(original_emission*(1-m)+glow[:,:,None]*np.array([1,.49,.1])))
d=np.load(P/'surface_mapping.npz');xyz=d['blade_xyz'];cover=d['blade_coverage'];x,y,z=np.moveaxis(xyz,-1,0)
u=.5+np.sign(y)*x/.106;v=1-(z-.10)/.63
inside=cover&(u>=0)&(u<=1)&(v>=0)&(v<=1)
radial=np.sqrt(x*x+y*y);fade=np.clip((radial-.106*.48)/(.106*.08),0,1);inside=inside*(1-fade*fade*(3-2*fade))
for i,key in enumerate(['resonance_rune','erosion_rune','conduction_rune']):
    tex=read(P.parent/'FrostSwordSurfaceFix20260915/RuneMasks'/(key+'.png'))[:,:,0]
    h,w=tex.shape
    coords=[np.clip(v,0,1)*(h-1),(.30+.40*np.clip(u,0,1))*(w-1)]
    sample=ndi.map_coordinates(tex,coords,order=1,mode='nearest')
    core=np.clip(sample*1.2,0,1);halo=np.zeros_like(core)
    for dy,dx in [(2.5,0),(-2.5,0),(0,2.5),(0,-2.5)]:
        halo+=ndi.map_coordinates(tex,[coords[0]+dy,coords[1]+dx],order=1,mode='nearest')*.25
    along=z*100
    pulse=(.88+.12*np.sin(2.2-along*.024)) if i==0 else (.86+.09*np.sin(3.6+along*.17)+.05*np.sin(8.4-along*.08)) if i==1 else (.83+.17*(.5+.5*np.sin(along*.17-2))**3)
    coverage=np.clip(core*.96+halo*.20,0,1)*inside
    weight=np.clip(core/np.maximum(core+halo*.20,.0001),0,1)
    color=np.array([.82,.89,1])*1.35+np.array([.55,.78,1])*2.8*pulse[:,:,None]
    halo_color=np.array([.55,.78,1])*2.8*.55*pulse[:,:,None]
    emission=halo_color*(1-weight[:,:,None])+color*weight[:,:,None]
    save(key+'_coverage.png',coverage)
    save(key+'_emission.png',srgb(emission/4))
print('ICON_SHADER_FRAMES_READY')
