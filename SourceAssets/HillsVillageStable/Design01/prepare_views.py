"""Prepare the independent review views from the three white-background image groups."""
from itertools import groupby
from pathlib import Path
import json

from PIL import Image, ImageDraw, ImageFont
import numpy as np

root=Path(__file__).resolve().parent
data=json.loads((root/"image-directions.json").read_text(encoding="utf-8"))["components"]
fontpath="C:/Windows/Fonts/msyh.ttc"
boldpath="C:/Windows/Fonts/msyhbd.ttc"
def font(s,b=False): return ImageFont.truetype(boldpath if b else fontpath,s)
im=Image.new("RGB",(2160,1410),"#f3f0e5")
draw=ImageDraw.Draw(im)
draw.text((65,36),"东门马厩 · 构件三视图",font=font(54,True),fill="#233b36")
draw.text((67,117),"四栏一库的南墙马房与东门前院     /     标注为目标宽 × 深 × 高，单位 cm",font=font(25),fill="#50645a")
draw.line((66,176,2095,176),fill="#9da899",width=2)
for i,item in enumerate(data):
    folder=root/"Components"/item["id"]
    sheet=Image.open(folder/"turnaround.png").convert("RGB")
    pixels=np.asarray(sheet)
    w,h=sheet.size
    mask=pixels.min(axis=2)<170
    empty=mask.sum(axis=0)<=4
    gaps=[]
    for is_gap,values in groupby(enumerate(empty),lambda pair:pair[1]):
        xs=[x for x,_ in values]
        if is_gap and xs[0]>0 and xs[-1]<w-1 and len(xs)>10:
            gaps.append((xs[0],xs[-1]))
    cuts=[0]+sorted((a+b)//2 for a,b in sorted(gaps,key=lambda g:g[1]-g[0],reverse=True)[:2])+[w]
    if len(cuts)!=4:
        raise ValueError(f"Three separated views required for {item['id']}")
    rects=[]
    for a,b in zip(cuts,cuts[1:]):
        yy,xx=np.nonzero(mask[:,a:b])
        rects.append((max(a,a+int(xx.min())-5),max(0,int(yy.min())-5),
                      min(b,a+int(xx.max())+6), min(h,int(yy.max())+6)))
    side=max(max(r-l,b-t) for l,t,r,b in rects)+64
    names=["front","right","top" if item["id"]=="A09" else "back"]
    for name,bounds in zip(names,rects):
        isolated=sheet.crop(bounds)
        single=Image.new("RGB",(side,side),"white")
        single.paste(isolated,((side-isolated.width)//2,(side-isolated.height)//2))
        single.save(folder/(name+".png"),optimize=True)
    # Keep the original equal-scale views together in the overview.
    x=66+(i%3)*685;y=199+(i//3)*394
    draw.rounded_rectangle((x,y,x+659,y+365),radius=10,fill="#fffcf5",outline="#d8d7ca",width=2)
    draw.text((x+19,y+18),item["id"],font=font(22,True),fill="#8b603b")
    draw.text((x+81,y+13),item["name"],font=font(30,True),fill="#213e36")
    top=min(r[1] for r in rects);bottom=max(r[3] for r in rects)
    strip=sheet.crop((0,max(0,top-15),w,min(h,bottom+15)))
    strip.thumbnail((621,219),Image.Resampling.LANCZOS)
    im.paste(strip,(x+(659-strip.width)//2,y+64+(219-strip.height)//2))
    draw.line((x+18,y+292,x+641,y+292),fill="#d9d9cc")
    draw.text((x+19,y+308),item["dims"]+" cm",font=font(21),fill="#33483f")
    draw.text((x+639,y+309),item["views"],font=font(19),fill="#617164",anchor="ra")
im.save(root/"组件三视图总览.jpg",quality=94,subsampling=0)
