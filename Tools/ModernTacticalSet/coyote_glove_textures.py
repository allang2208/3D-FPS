"""Make the mesh, brushed microfibre, tricot, tape and closure finishes for TS01."""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

from coyote_glove_materials import ROOT,SURFACES


def noise(rng,n,sigma):
    a=gaussian_filter(rng.standard_normal((n,n),dtype=np.float32),sigma,mode="wrap")
    return np.clip((a-a.mean())/(a.std()+1.e-6),-3,3)


def emboss(n):
    w,h=1200,540
    alpha=Image.new("L",(w,h));d=ImageDraw.Draw(alpha)
    d.rounded_rectangle((24,24,w-24,h-24),radius=46,outline=180,width=14)
    d.rounded_rectangle((56,51,w-56,h-51),radius=32,outline=105,width=6)
    for i in range(4):
        x=77+i*39
        d.polygon([(x,161),(x+19,161),(x+72,356),(x+53,356)],fill=164)
        d.polygon([(w-x,161),(w-x-19,161),(w-x-72,356),(w-x-53,356)],fill=164)
    f=ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf",223)
    d.text((w//2,239),"TS01",font=f,anchor="mm",fill=236,stroke_width=1)
    d.line((339,344,861,344),fill=155,width=6)
    f=ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf",46)
    d.text((w//2,393),"F I E L D   S E R I E S",font=f,anchor="mm",fill=196)
    return np.asarray(alpha.resize((n,n),Image.Resampling.LANCZOS),dtype=np.float32)/255.


def make(kind,seed):
    color,rough,sheen,n=SURFACES[kind]
    rng=np.random.default_rng(seed)
    y,x=(np.indices((n,n),dtype=np.float32)+.5)/n
    fine=noise(rng,n,.70)
    mid=noise(rng,n,n/210)
    cloud=noise(rng,n,n/27)
    variation=.015*cloud+.015*mid+.012*fine
    height=.0019*fine
    ao=np.ones_like(x)*.993
    roughness=rough+.015*mid
    if kind=="Knit":
        # Staggered vent cells between interlooping yarn. Cells are roughly
        # 1.25 by 1.05 mm, with four fine filaments catching the light.
        u=x*32+.025*mid
        v=y*38+.021*mid
        row=np.floor(v)
        a=(u+.5*(row%2))%1-.5
        b=v%1-.5
        ellipse=(a/.28)**2+(b/.32)**2
        hole=np.exp(-1.18*ellipse**1.55)
        welt=np.exp(-((np.sqrt(ellipse)-1.12)/.31)**2)
        yarn=.5+.5*np.cos(2*np.pi*(x*128+.34*np.sin(2*np.pi*y*38)))
        height=.0105*welt-.0215*hole+.0056*yarn+.0008*fine
        variation+=.13*welt-.38*hole+.067*(yarn-.5)+.011*fine
        ao-=.35*hole
        roughness+=.045*hole-.019*welt
    elif kind=="Suede":
        # Directional raised nap; include individual fibre bundles and a
        # slower nap direction change, giving a different grazing response.
        pile_x=noise(rng,n,(1.0,n/330));pile_y=noise(rng,n,(n/360,1.15))
        grain=.5+.5*np.tanh(.78*cloud)
        nap=grain*pile_x+(1-grain)*pile_y
        height=.0028*nap+.0010*fine+.0008*mid
        variation+=.067*nap+.032*mid+.023*fine+.018*cloud
        roughness+=.022*nap
        ao-=.017*np.clip(-nap,0,2)
    elif kind in ("Stretch","Webbing","Thread"):
        cycles={"Stretch":(81,91),"Webbing":(50,66),"Thread":(68,14)}[kind]
        u=x*cycles[0];v=y*cycles[1]
        over=np.tanh(3.5*np.sin(np.pi*2*u/2)*np.sin(np.pi*2*v/2))
        warp=.5+.5*np.cos(2*np.pi*u)
        weft=.5+.5*np.cos(2*np.pi*v)
        weave=(.5+.43*over)*warp+(.5-.43*over)*weft
        if kind=="Thread":
            weave=.5+.5*np.sin(2*np.pi*(x*48+y*12))
        height=(.008 if kind=="Stretch" else .011)*weave+.001*fine
        variation+=.17*(weave-.5)+.022*fine
        ao-=.075*(1-weave)
    elif kind=="Label":
        glyph=emboss(n);ridge=gaussian_filter(glyph,2)
        height=.023*ridge+.00065*fine
        variation+=.14*ridge
        roughness-=.081*ridge
    else:
        height=.00125*fine+.0013*mid
        variation+=.015*mid
    base=np.array(color,dtype=np.float32)[None,None,:]*(1+variation[:,:,None])
    # OpenGL UV v points upwards whereas image pixel rows go downwards.
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*n/8
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*n/8
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=2,keepdims=True)
    return dict(BaseColor=base,NormalGL=(normal*.5+.5)*255,
                ORM=np.stack([ao,np.clip(roughness,.05,1.),np.zeros_like(ao)],axis=-1)*255)


def main():
    folder=ROOT/"Textures";folder.mkdir(parents=True,exist_ok=True)
    specs={}
    for idx,(kind,(color,rough,sheen,size)) in enumerate(SURFACES.items()):
        checksums={}
        for channel,values in make(kind,10481+idx*337).items():
            dst=folder/f"CG_{kind}_{channel}.png"
            Image.fromarray(np.uint8(np.clip(np.rint(values),0,255))).save(dst,compress_level=4)
            checksums[channel]=hashlib.sha256(dst.read_bytes()).hexdigest()
        specs[kind]=dict(resolution=size,tile_cm=4,roughness=rough,specular=.29,sheen=sheen,base_srgb=color,sha256=checksums)
    (ROOT/"surfaces.json").write_text(json.dumps(specs,indent=2),encoding="utf8")


if __name__=="__main__":
    main()
