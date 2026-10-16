"""Rasterize text at equal physical pixel density in both ribbon directions."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
tile=1024;width=tile*2;height=round(tile*2.35/1.84)
y,x=np.mgrid[0:height,0:width];rng=np.random.default_rng(161016)
warp=np.sin(x*.5*math.pi/3.5);weft=np.sin(y*1024/height*math.pi/5)
weave=.5+.06*warp+.035*weft+.025*warp*weft
color=np.zeros((height,width,3))
for side,base in enumerate(((79,35,43),(31,66,61))):
    a,b=side*tile,(side+1)*tile
    color[:,a:b]=np.array(base)+(weave[:,a:b,None]-.5)*11+rng.normal(0,.5,(height,tile,1))
image=Image.fromarray(color.clip(0,255).astype('uint8'));draw=ImageDraw.Draw(image)
font=ImageFont.truetype(str(PROJECT/'Content/UI/AlchemyManual/Fonts/FolioSerif-Semibold.ttf'),284)
for side,label in enumerate(('首页','末页')):
    start=side*tile
    for edge in (start+48,start+976):
        draw.line((edge,0,edge,height),fill=(112,96,72),width=3)
        for j in range(10,height,26):draw.line((edge+6,j,edge+6,j+10),fill=(151,132,94),width=3)
    draw.text((start+tile/2,height*.506),label,font=font,fill=(224,202,149),anchor='mm')
    draw.line((start+392,height*.634,start+632,height*.634),fill=(166,145,99),width=3)
    cx,cy=start+tile/2,height*.684
    draw.polygon([(cx,cy-16),(cx+16,cy),(cx,cy+16),(cx-16,cy)],fill=(190,168,119))
path=ROOT/'Textures/T_ManualRibbonProportional.png';image.save(path)
(ROOT/'print-source.json').write_text(json.dumps(dict(file=str(path),width=width,height=height,
    tile_width=tile,ribbon_cm=[1.84,2.35],pixel_density_xy=[tile/1.84,height/2.35],
    font_px=284,text_resized=False,runtime_tested=False),indent=2),encoding='utf-8')
print('PROPORTIONAL_BOOKMARK_PRINT_AUTHORED',width,height)
