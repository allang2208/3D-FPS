"""Subtle satin weave, fine stitched selvages and readable foil lettering."""
from pathlib import Path
import math,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
w=h=1024;y,x=np.mgrid[0:h,0:w];rng=np.random.default_rng(161016)
# The weave height is the common source for color, normals and roughness.
warp=np.sin(x*math.pi/3.5);weft=np.sin(y*math.pi/5)
height=.5+.06*warp+.035*weft+.025*warp*weft
color=np.zeros((h,w,3))
for side,base in enumerate(((79,35,43),(31,66,61))):
    a,b=side*512,(side+1)*512
    color[:,a:b]=np.array(base)+(height[:,a:b,None]-.5)*11+rng.normal(0,.5,(h,512,1))
im=Image.fromarray(color.clip(0,255).astype('uint8'));d=ImageDraw.Draw(im)
font=ImageFont.truetype(str(PROJECT/'Content/UI/AlchemyManual/Fonts/FolioSerif-Semibold.ttf'),142)
for side,label in enumerate(('首页','末页')):
    start=side*512
    for edge in (start+24,start+488):
        d.line((edge,0,edge,h),fill=(112,96,72),width=2)
        for j in range(8,h,20):d.line((edge+3,j,edge+3,j+8),fill=(151,132,94),width=2)
    d.text((start+256,518),label,font=font,fill=(224,202,149),anchor='mm')
    d.line((start+196,649,start+316,649),fill=(166,145,99),width=2)
    d.polygon([(start+256,688),(start+264,700),(start+256,712),(start+248,700)],fill=(190,168,119))
smooth=np.asarray(Image.fromarray((height*255).astype('uint8')).filter(ImageFilter.GaussianBlur(.8)),dtype=float)/255
dy,dx=np.gradient(smooth);n=np.stack((-dx*.65,dy*.65,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
normal=Image.fromarray(((n*.5+.5)*255).clip(0,255).astype('uint8'))
rough=Image.fromarray(((.57+.035*(height-.5))*255).clip(0,255).astype('uint8'))
records=[]
for name,img,kind in [('T_ManualRibbonV6',im,'color'),('T_ManualRibbonV6Normal',normal,'normal'),('T_ManualRibbonV6Roughness',rough,'mask')]:
    path=ROOT/'Textures'/(name+'.png');img.save(path)
    records.append(dict(name=name,file=str(path),kind=kind))
(ROOT/'textures.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('Tailored bookmark textures authored:',len(records))
