"""Make restrained, authored 2K PBR for aged iron and antique bronze.

No image generation service, external copyrighted texture or preview render.
BaseColor is linear -> sRGB encoded exactly once. ORM and normals are linear.
"""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE=Path(__file__).resolve().parents[1];OUT=HERE/'Textures';OUT.mkdir(exist_ok=True)
N=2048;rng=np.random.default_rng(20261003)
freq=np.fft.fftfreq(N)
rad=freq[:,None]**2+freq[None,:]**2
def lowpass(data,width):
    return np.fft.ifft2(np.fft.fft2(data)*np.exp(-rad*width*width)).real.astype(np.float32)
def noise(width):
    a=lowpass(rng.normal(0,1,(N,N)).astype(np.float32),width)
    return np.clip(a/(a.std()*5)+.5,0,1)
def stains(data,start,gain):
    x=np.clip((data-start)*gain,0,1);return x*x*(3-2*x)
def marks(count):
    img=Image.new('L',(N,N));d=ImageDraw.Draw(img)
    for _ in range(count):
        x,y=rng.integers(0,N,2);a=rng.uniform(-math.pi,math.pi)
        length=rng.uniform(10,175);dx,dy=math.cos(a)*length,math.sin(a)*length
        d.line((int(x),int(y),int(x+dx),int(y+dy)),fill=int(rng.integers(45,145)),width=int(rng.integers(1,3)))
    return np.array(img.filter(ImageFilter.GaussianBlur(.7)),dtype=np.float32)/255
def srgb(a):
    return np.where(a<=.0031308,a*12.92,1.055*np.maximum(a,0)**(1/2.4)-.055)
def write(name,data,color=False):
    encoded=srgb(np.clip(data,0,1)) if color else np.clip(data,0,1)
    Image.fromarray(np.round(encoded*255).astype(np.uint8)).save(OUT/(name+'.png'))
def normals(height):
    h=lowpass(height,3.7)
    # Height is in centimeters; UV0 spans one physical meter.
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*.5*N/100
    dy=(np.roll(h,-1,0)-np.roll(h,1,0))*.5*N/100
    n=np.stack((-dx,dy,np.ones_like(dx)),axis=2)
    n/=np.linalg.norm(n,axis=2,keepdims=True)
    # DirectX green: no inversion during Unreal import.
    return n*.5+.5

recipes={}
for family in ('Iron','Gold'):
    broad=noise(100);mid=noise(19);grain=noise(2.4);hammer=noise(43)
    pits=stains(noise(9),.64,5);scr=marks(760 if family=='Iron' else 460)
    if family=='Iron':
        oxide=stains(noise(68),.59,4.0)
        bare=stains(broad,.53,3.0)
        color=np.array([.043,.047,.052])[None,None,:]*(.74+broad[...,None]*.56)
        color=color*(1-bare[...,None]*.28)+np.array([.12,.13,.14])*bare[...,None]*.28
        color=color*(1-oxide[...,None]*.68)+np.array([.065,.021,.008])*oxide[...,None]*.68
        color+=scr[...,None]*np.array([.065,.067,.07])
        rough=np.clip(.43+mid*.18+oxide*.17+pits*.09-scr*.06,.32,.86)
        metal=np.clip(.91-oxide*.83-pits*.13,.05,.95)
        height=hammer*.07+mid*.015+grain*.002-pits*.021-scr*.009
    else:
        tarnish=stains(broad,.56,3.6)
        verdigris=stains(noise(74),.67,5.0)*tarnish
        color=np.array([.39,.22,.066])[None,None,:]*(.78+mid[...,None]*.34)
        color=color*(1-tarnish[...,None]*.62)+np.array([.055,.032,.012])*tarnish[...,None]*.62
        color=color*(1-verdigris[...,None]*.65)+np.array([.022,.048,.032])*verdigris[...,None]*.65
        color+=scr[...,None]*np.array([.075,.06,.025])
        rough=np.clip(.30+mid*.11+tarnish*.21+verdigris*.12-scr*.08,.22,.78)
        metal=np.clip(.95-tarnish*.25-verdigris*.72,.08,.97)
        height=hammer*.032+mid*.009+grain*.0015-pits*.009-scr*.005
    ao=np.clip(1-pits*.10-(oxide*.08 if family=='Iron' else tarnish*.05),.78,1)
    write('T_TreasureDetail_'+family+'_BaseColor',color,True)
    write('T_TreasureDetail_'+family+'_Normal',normals(height))
    write('T_TreasureDetail_'+family+'_ORM',np.stack((ao,rough,metal),axis=2))
    recipes[family]=dict(resolution=[N,N],physical_repeat_cm=100,
        channels='ORM: R ambient occlusion, G roughness, B metallic',
        normal='DirectX, height in cm, low-pass before derivation',
        provenance='Locally authored maps, seed 20261003')
(HERE/'Receipts').mkdir(exist_ok=True)
(HERE/'Receipts/surfaces.json').write_text(json.dumps(dict(families=recipes,
    interior='Existing licensed UnrealNormandy T_WoodSurface_00A PBR, referenced directly',
    rendered=False,tested=False),indent=2),encoding='utf-8')
print('TREASURE_PBR_AUTHORED 6 x 2048px')
