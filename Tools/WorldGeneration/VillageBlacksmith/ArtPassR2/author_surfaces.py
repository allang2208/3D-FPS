"""Deterministic textile, end-grain and aged sign paint maps; project scans remain authoritative."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2/Textures'
OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(1711172)
N=2048
y,x=np.mgrid[0:N,0:N].astype(np.float32)/N
def blurred(scale):
    a=(rng.random((scale,scale))*255).astype('uint8')
    return np.asarray(Image.fromarray(a).resize((N,N),Image.Resampling.BICUBIC),dtype=np.float32)/255
def png(name,a):Image.fromarray(np.clip(a*255,0,255).astype('uint8')).save(OUT/(name+'.png'))
def normal(name,h,strength):
    gx=(np.roll(h,-1,1)-np.roll(h,1,1))*strength
    gy=(np.roll(h,-1,0)-np.roll(h,1,0))*strength
    z=np.ones_like(gx);norm=np.sqrt(gx*gx+gy*gy+1)
    # DX tangent normal, green is down in texture-image coordinates.
    png(name,np.stack([-gx/norm*.5+.5,-gy/norm*.5+.5,z/norm*.5+.5],2))
macro=blurred(14);fiber=blurred(512)
warp=(.5+.5*np.cos(x*np.pi*2*320))**2
weft=(.5+.5*np.cos(y*np.pi*2*320))**2
over=((np.floor(x*320)+np.floor(y*320))%2)
h=(warp*(.35+.65*over)+weft*(1-.65*over))*.5
linen=(.77+.12*macro+.08*fiber+.03*h)
png('Linen_Color',linen[:,:,None]*np.array([.61,.565,.465]))
png('Linen_ORM',np.stack([.91+.09*h,.86+.1*macro,np.zeros_like(h)],2))
normal('Linen_NormalDX',h+fiber*.08,1.1)
rad=np.sqrt(((x+.35)*1.2)**2+((y+.21)*.94)**2)
rings=.5+.5*np.sin(rad*130+blurred(8)*4)
grain=.77+.05*rings+.13*macro+.05*fiber
png('Endgrain_Color',grain[:,:,None]*np.array([.40,.355,.285]))
normal('Endgrain_NormalDX',rings*.018+fiber*.06,.6)
png('Endgrain_ORM',np.stack([.9+.1*rings,.79+.12*macro,np.zeros_like(h)],2))
for name,label,w,hh in [('BlacksmithSign','铁匠铺',2048,900),('ClosedPlaque','待修复',1024,426)]:
    mask=Image.new('L',(w,hh),0);d=ImageDraw.Draw(mask)
    font=ImageFont.truetype('C:/Windows/Fonts/simkai.ttf',int(hh*(.49 if name=='BlacksmithSign' else .61)))
    # Board art only: geometry supplies the boards, wood grain, nails and iron emblem.
    center=(w*.61 if name=='BlacksmithSign' else w*.5,hh*.52)
    d.text(center,label,font=font,fill=240,anchor='mm',stroke_width=0)
    small=(rng.random((hh//3,w//3))*255).astype('uint8')
    erosion=np.asarray(Image.fromarray(small).resize((w,hh),Image.Resampling.BILINEAR),dtype=np.float32)
    m=np.asarray(mask,dtype=np.float32)/255
    m*=np.clip((erosion-64)/65,0,1)
    Image.fromarray((m*255).astype('uint8')).save(OUT/(name+'_Paint.png'))
report={'seed':1711172,'wood_source':'existing chapel scanned timber, no generated replacement',
 'cloth':'2048 px physical warp/weft normal + roughness; organic folds are geometry',
 'endgrain':'2048 px growth-ring texture',
 'sign':'opaque wood shader with local UV paint mask; KaiTi; no decals or projection',
 'packing':'ORM = R ambient occlusion, G roughness, B metalness; DX normals; only color sRGB'}
(OUT/'surface-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SURFACES_AUTHORED',OUT)
