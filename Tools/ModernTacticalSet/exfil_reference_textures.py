"""Make physical-scale coating, polymer, upholstery and label textures for the game helmet."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

from exfil_reference_materials import ROOT,SURFACES,CLOTH_SHEEN


def unit_noise(rng,size,sigma):
    field=gaussian_filter(rng.standard_normal((size,size),dtype=np.float32),sigma,mode="wrap")
    return np.clip((field-field.mean())/max(field.std(),1.e-7),-3.,3.)/3.


def plaque(size):
    # The rectangular relief face occupies the full dedicated UV island.
    # Use squeezed, condensed caps and a raised center rule as on the supplied plaque.
    width,height=1024,560
    art=Image.new("L",(width,height));d=ImageDraw.Draw(art)
    d.rounded_rectangle((9,10,width-10,height-11),radius=36,outline=215,width=12)
    d.rounded_rectangle((28,29,width-29,height-30),radius=23,outline=75,width=3)
    d.rounded_rectangle((88,292,936,300),radius=3,fill=230)
    def line(text,y,w,h):
        font=ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf",168)
        box=font.getbbox(text)
        glyph=Image.new("L",(box[2]-box[0]+3,box[3]-box[1]+3))
        ImageDraw.Draw(glyph).text((1-box[0],1-box[1]),text,font=font,fill=247,stroke_width=1)
        glyph=glyph.resize((w,h),Image.Resampling.LANCZOS)
        art.paste(glyph,((width-w)//2,y))
    line("EXFIL BALLISTIC",105,857,128)
    line("DESIGNED IN CLEVELAND",345,382,32)
    line("MADE IN USA",394,210,31)
    return np.asarray(art.resize((size,size),Image.Resampling.LANCZOS),dtype=np.float32)/255


def images(name,series):
    color,rough,metal,n,span=SURFACES[name]
    rng=np.random.default_rng(12127+series*971)
    mid=unit_noise(rng,n,max(1,n/70))
    fine=unit_noise(rng,n,max(.60,n/1000))
    grit=unit_noise(rng,n,max(.7,n/750))
    macro=unit_noise(rng,n,n/19)
    yy,xx=np.indices((n,n),dtype=np.float32)/n
    variance=.021*macro+.021*mid+.032*grit
    height=.0030*grit+.0011*fine
    surface_rough=rough+.032*mid+.025*grit
    metallic=np.full((n,n),metal,np.float32)
    ao=np.full((n,n),.987,np.float32)
    relief=None
    if name=="Composite":
        grain=grit+.28*unit_noise(rng,n,n/325)
        pellets=(np.maximum(grain-.10,0)*1.55)**1.45
        stipple=unit_noise(rng,n,n/215)
        pores=unit_noise(rng,n,n/440)
        height=.008*pellets+.0025*fine+.007*stipple+.005*np.maximum(stipple,0)+.003*pores
        variance=.024*macro+.031*mid+.083*grit+.026*fine+.125*stipple+.048*pores
        surface_rough=rough+.048*grain+.018*mid-.054*stipple
        ao-=.025*np.maximum(-grain,0)
    elif name in ("Polymer","DarkPolymer"):
        # Subtle injection-moulded grain, visibly finer than the exterior coating.
        height=.0024*grit+.0008*fine
        variance=.025*mid+.018*fine
    elif name in ("Webbing","Stitch"):
        # Periodic over/under yarns with separate warp and weft and a fine twist.
        u=2*np.pi*xx*78
        v=2*np.pi*yy*50
        over=np.tanh(4*np.sin(u/2)*np.sin(v/2))
        warp=.5+.5*np.cos(u)
        weft=.5+.5*np.cos(v)
        threads=(.52+.45*over)*warp+(.48-.45*over)*weft
        twist=np.sin(2*np.pi*(xx*234+yy*100))
        height=.013*threads+.0016*twist+.0012*fine
        variance=.10*(threads-.5)+.024*twist+.025*mid+.03*fine
        ao-=.09*(1.-threads)
    elif name=="LoopPile":
        curls=unit_noise(rng,n,1.3)-.68*unit_noise(rng,n,4.)
        fiber=np.sin(2*np.pi*(xx*113+yy*101)+10*curls)
        height=.0105*grit+.0036*fiber+.0027*mid
        variance=.13*curls+.037*fiber+.035*mid
        ao-=.065*np.maximum(-curls,0)
    elif name=="PadMesh":
        u=2*np.pi*xx*38
        v=2*np.pi*yy*48
        aperture=np.maximum(0,np.cos(u+.65*np.sin(v/2))*np.cos(v))**2
        height=.003*grit-.021*aperture
        variance=.04*grit-.24*aperture+.02*mid
        ao-=.26*aperture
    elif name=="Metal":
        height=.0008*grit+.00025*np.sin(2*np.pi*(xx*146+yy*24))
        variance=.045*mid+.04*grit
    elif name=="Label":
        relief=plaque(n)
        height=.028*gaussian_filter(relief,1.9)+.0014*fine
        variance=.035*grit+.017*mid
        surface_rough-=.085*relief
    base=np.asarray(color,np.float32)[None,None,:]*(1+variance[:,:,None])
    if relief is not None:
        raised=np.array([197,166,119],np.float32)[None,None,:]*(1+.023*grit[:,:,None])
        base=base*(1-relief[:,:,None])+raised*relief[:,:,None]
    px=span/n
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*px)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*px)
    # PNG rows run down; +Y in a tangent-space OpenGL normal runs up.
    normals=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normals/=np.linalg.norm(normals,axis=2,keepdims=True)
    return {"BaseColor":base,"NormalGL":(normals*.5+.5)*255,
            "ORM":np.stack((ao,np.clip(surface_rough,.05,1),metallic),-1)*255}


def main():
    folder=ROOT/"Textures";folder.mkdir(parents=True,exist_ok=True)
    data={}
    for i,(name,(rgb,rough,metal,n,span)) in enumerate(SURFACES.items()):
        digests={}
        for channel,pixels in images(name,i).items():
            file=folder/f"H1_{name}_{channel}.png"
            Image.fromarray(np.uint8(np.clip(pixels,0,255))).save(file,compress_level=3)
            digests[channel]=hashlib.sha256(file.read_bytes()).hexdigest()
        data[name]=dict(resolution=n,tile_cm=span,specular=.40 if name in ("Metal","Label") else .26,
                        base_srgb=rgb,roughness=rough,metallic=metal,sha256=digests)
        if name in CLOTH_SHEEN:
            data[name]["sheen"]=CLOTH_SHEEN[name]
    (ROOT/"surfaces.json").write_text(json.dumps(data,indent=2),encoding="utf-8")


if __name__=="__main__":
    main()
