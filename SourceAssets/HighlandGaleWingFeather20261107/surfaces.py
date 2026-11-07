"""One shared PBR atlas. Geometry provides broad facet shading, not painted illumination."""
from pathlib import Path
from PIL import Image
import numpy as np
P=Path(__file__).resolve().parent/'Textures'
W,H=2048,2048; B=H//8
base=np.zeros((H,W,3),'u1'); orm=base.copy(); normal=base.copy()
rng=np.random.default_rng(112703)
# satin, buff, quenched channels, champagne, ferrule, quartz, quartz-light, quartz-deep
palette=[(198,201,204),(213,215,216),(158,166,176),(217,192,155),(180,179,179),(139,192,210),(164,211,220),(110,166,194)]
roughs=[.315,.205,.388,.246,.345,.125,.105,.16]; mets=[.95,.98,.93,.92,.93,.035,.035,.035]
for i in range(8):
    def field(w,h,r):
        a=Image.fromarray(rng.normal(size=(h,w)).astype('float32')).resize((W,B),Image.Resampling.BICUBIC)
        return np.asarray(a)*r
    satin=(i<5)
    grime=field(45,18,1.0)+field(130,57,.36)
    grain=field(75,223,.65)+field(15,184,.3)+rng.normal(0,.25,(B,W))
    # A very small linear grain. Fissures and highlights on a gemstone come from its facets.
    if not satin: grain*=.11;grime*=.18
    amp=(grain*1.45+grime*.85)
    r=roughs[i]+grain*(.018 if i!=1 else .012)+.007*grime
    ht=.62*grain+.10*grime
    dy,dx=np.gradient(ht)
    mx=-.014*dx;my=.020*dy;nz=1/np.sqrt(1+mx*mx+my*my)
    block=slice(H-(i+1)*B,H-i*B)
    base[block]=np.clip(np.array(palette[i])+amp[:,:,None],0,255).astype('u1')
    orm[block]=np.stack((np.ones_like(r)*255,255*np.clip(r,.04,.95),np.ones_like(r)*255*mets[i]),axis=2).round().astype('u1')
    normal[block]=(127.5+127.5*np.stack((mx*nz,my*nz,nz),axis=2)).round().astype('u1')
# Reserve the upper half for the continuous unfolded quillon, lower half for jewel, collar and filigree swatches.
old=[base.copy(),orm.copy(),normal.copy()]
for dst,src in zip((base,orm,normal),old):
    dst[H//2:,:,:]=np.asarray(Image.fromarray(src).resize((W,H//2),Image.Resampling.LANCZOS))
U=np.clip((np.arange(W)[None,:]/(W-1)-.006)/.988,0,1);V=np.clip(((H//2-np.arange(H//2)[:,None]-.5)/(H//2)-.016)/.968,0,1)
x=391*U
def smooth(x):x=np.clip(x,0,1);return x*x*(3-2*x)
q1=.17+.19*smooth((x-108)/197);q2=.34+.14*smooth((x-169)/172)
lo=smooth((x-102)/47)*(1-smooth((x-281)/53));hi=smooth((x-159)/45)*(1-smooth((x-319)/44))
def ga(x,w):return np.exp(-np.minimum(45,(x/w)**2))
flute=lo*ga(V-q1-.035,.060)+hi*ga(V-q2-.029,.047)
# Fluted dark silver is subtly less polished than the bright lip and upper outer grind.
lip=lo*ga(V-q1+.021,.032)+hi*ga(V-q2+.015,.026)+1-smooth(np.minimum(V,1-V)/.085)
rgb=np.array((197.,201.,206.))[None,None,:]-np.minimum(flute,1)[:,:,None]*np.array((26,25,22))+lip[:,:,None]*8
def wash(ww,hh):
    return np.asarray(Image.fromarray(rng.normal(size=(hh,ww)).astype('float32')).resize((W,H//2),Image.Resampling.BICUBIC))
grain=wash(85,640)*.7+wash(221,1000)*.35+wash(28,20)*.48
base[:H//2]=np.clip(rgb+grain[:,:,None]*1.1,0,255).astype('u1')
rr=.324+.09*flute-.102*np.minimum(1,lip)+.016*grain
orm[:H//2]=np.stack([252-8*np.minimum(1,flute),255*rr,np.zeros_like(rr)+244],axis=2).round().astype('u1')
dy,dx=np.gradient(grain);nx=-.013*dx;ny=.019*dy;nz=1/np.sqrt(1+nx*nx+ny*ny)
normal[:H//2]=((np.stack([nx*nz,ny*nz,nz],axis=2)+1)*127.5).round().astype('u1')


for ch,buf in [('BaseColor',base),('ORM',orm),('NormalGL',normal)]:
    Image.fromarray(buf).save(P/('T_GaleFeather_'+ch+'.png'),compress_level=7)
