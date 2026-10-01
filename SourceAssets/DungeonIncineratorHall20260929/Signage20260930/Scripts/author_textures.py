"""Typeset original signs and worn floor paint; no preview/render or runtime work."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
CFG=json.loads((ROOT/'Config/layout.json').read_text(encoding='utf-8'))
FONT='C:/Windows/Fonts/msyhbd.ttc'
INK=(34,39,36);IVORY=(198,194,172);YELLOW=(191,151,47);RED=(145,45,34)

def lettering(draw,xy,text,maxwidth,height,color=INK,font=FONT):
    size=max(10,int(height))
    while True:
        f=ImageFont.truetype(font,size)
        if draw.textlength(text,font=f)<=maxwidth or size<=10:break
        size-=1
    draw.text(xy,text,font=f,fill=color,anchor='mm')

atlas=Image.new('RGB',(2048,2048),IVORY);ad=ImageDraw.Draw(atlas);rects={}
def panel(key,rect,color=IVORY):
    rects[key]=rect;ad.rectangle(rect,fill=color)
    x0,y0,x1,y1=rect;ad.rectangle((x0+9,y0+9,x1-9,y1-9),outline=INK,width=5)
    return x0,y0,x1,y1

for i in range(3):
    r=panel('furnace'+str(i+1),(24,24+i*400,2024,392+i*400))
    x0,y0,x1,y1=r
    ad.rectangle((x0+12,y0+12,x0+470,y1-12),fill=INK)
    lettering(ad,(x0+240,y0+169),f'{i+1:02d}',400,245,IVORY)
    lettering(ad,(x0+1225,y0+114),'医疗废物焚化炉',1400,139)
    lettering(ad,(x0+1225,y0+278),f'INCINERATOR  /  F-{i+1:02d}',1350,77)
r=panel('stop',(24,1232,1000,1512),RED)
lettering(ad,(512,1317),'设备停用',900,105,IVORY)
lettering(ad,(512,1434),'禁止投料 · 禁止启动',900,61,IVORY)
r=panel('biohazard',(1032,1232,2024,2024),YELLOW)
lettering(ad,(1528,1450),'☣',620,340,INK,'C:/Windows/Fonts/seguisym.ttf')
lettering(ad,(1528,1705),'医疗废物暂存',920,105)
lettering(ad,(1528,1828),'保持密闭 · 分类存放',920,63)
lettering(ad,(1528,1945),'BIOHAZARD',840,65)
r=panel('entry',(24,1544,1000,1934))
lettering(ad,(512,1630),'废弃焚化处理厅',900,92)
lettering(ad,(512,1744),'医疗废物处理区',900,65)
lettering(ad,(512,1840),'非工作人员禁止进入',900,58)
rects['steel']=[32,1960,200,2020]
ad.rectangle(rects['steel'],fill=(81,87,82))

# Restrained edge wear and fine surface variation, keeping the type legible.
rng=np.random.default_rng(93017)
pixels=np.array(atlas,dtype=np.float32)
pixels+=rng.normal(0,.85,pixels.shape[:2])[...,None]
Image.fromarray(np.clip(pixels,0,255).astype('uint8')).save(OUT/'T_IncineratorSigns_BaseColor.png')
orm=np.zeros((2048,2048,3),dtype=np.uint8);orm[:]=[255,172,0]
orm[1960:2021,32:201]=[255,135,210]
Image.fromarray(orm).save(OUT/'T_IncineratorSigns_ORM.png')
(ROOT/'Authored/sign_atlas.json').write_text(json.dumps({'size':[2048,2048],'rects':rects,
    'source':'Original typesetting; Windows fonts rendered to artwork, font files not distributed'},ensure_ascii=False,indent=2),encoding='utf-8')

def floor_texture(spec,index):
    w,h=spec['pixels'];x0,y0,x1,y1=spec['rect_m'];sx=w/(x1-x0);sy=h/(y1-y0)
    image=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(image)
    def p(x,y):return ((x-x0)*sx,(y1-y)*sy)
    def line(a,b,color=YELLOW,width=.085):
        # Line widths use world metres, even for non-square texture aspect ratios.
        if abs(a[0]-b[0])<.001:
            left,top=p(a[0]-width/2,max(a[1],b[1]));right,bottom=p(b[0]+width/2,min(a[1],b[1]))
        else:
            left,top=p(min(a[0],b[0]),a[1]+width/2);right,bottom=p(max(a[0],b[0]),b[1]-width/2)
        d.rectangle((left,top,right,bottom),fill=(*color,235))
    def label(x,y,text,width,height,color=YELLOW):
        lettering(d,p(x,y),text,width*sx,height*sy,(*color,235))
    kind=spec['kind']
    if kind=='loading':
        for x in (x0+.15,x1-.15):line((x,y0+.12),(x,y1-.12))
        line((x0+.15,y0+.12),(x1-.15,y0+.12))
        # Leave a central opening for loading traffic, and label the visible front strip.
        for a,b in ((x0+.15,x0+.82),(x1-.82,x1-.15)):line((a,y1-.12),(b,y1-.12))
        label((x0+x1)/2,y1-.17,spec['number']+'  投料位',2.05,.22)
    elif kind=='aisle':
        for y in (y0+.13,y1-.13):line((x0+.08,y),(x1-.08,y),IVORY,.10)
        label(0,0,'保持通道畅通',3.9,.48,IVORY)
        # Bidirectional route marks, not an invented emergency exit route.
        for x in (-10.3,10.3):
            for direction in (-1,1):
                pts=[(x+direction*.89,0),(x+direction*.37,.23),(x+direction*.37,.075),
                     (x,.075),(x,-.075),(x+direction*.37,-.075),(x+direction*.37,-.23)]
                d.polygon([p(*v) for v in pts],fill=(*IVORY,230))
    elif kind=='waste':
        for x in (x0+.10,x1-.10):line((x,y0+.10),(x,y1-.10))
        line((x0+.10,y0+.10),(x1-.10,y0+.10))
        for a,b in ((x0+.10,x0+.52),(x1-.52,x1-.10)):line((a,y1-.10),(b,y1-.10))
        label((x0+x1)/2,y1-.36,'医疗废物暂存',2.22,.26)
    else:
        yy,xx=np.mgrid[0:h,0:w];wx=xx/sx;wy=yy/sy
        stripes=((wx+wy)/.18).astype(int)%2
        array=np.empty((h,w,4),dtype=np.uint8)
        array[:,:,:3]=np.where(stripes[...,None]==0,np.array(YELLOW),np.array(INK))
        array[:,:,3]=235
        array[:max(2,int(.008*sy)),:,3]=0;array[-max(2,int(.008*sy)):,:,3]=0
        array[:,:max(2,int(.008*sx)),3]=0;array[:,-max(2,int(.008*sx)):,3]=0
        image=Image.fromarray(array)
    # Small chips and directional abrasion are transparent, revealing the actual floor.
    rand=np.random.default_rng(93030+index);mask=Image.new('L',(w,h),255);md=ImageDraw.Draw(mask)
    for _ in range(int(w*h/1800)):
        x=int(rand.integers(0,w));y=int(rand.integers(0,h))
        rx=max(1,int(rand.uniform(.002,.009)*sx));ry=max(1,int(rand.uniform(.002,.016)*sy))
        md.ellipse((x-rx,y-ry,x+rx,y+ry),fill=int(rand.integers(0,80)))
    for _ in range(25 if kind in ('loading','aisle','waste') else 5):
        x=int(rand.integers(0,w));y=int(rand.integers(0,h))
        md.line((x,y,x+int(.015*sx),y+int(rand.uniform(.04,.15)*sy)),fill=45,width=max(1,int(.004*sx)))
    array=np.array(image);alpha=array[:,:,3].astype(np.float32)*np.array(mask)/255
    alpha*=rand.uniform(.93,1.0,(h,w));array[:,:,3]=alpha.astype(np.uint8)
    # Dilate only RGB into transparent pixels to avoid dark mip fringes.
    if kind!='hazard':array[:,:,:3]=IVORY if kind=='aisle' else YELLOW
    name='T_IncineratorPaint_'+spec['id'];Image.fromarray(array).save(OUT/(name+'.png'))
    return dict(spec,texture=name,file=str(OUT/(name+'.png')))

records=[floor_texture(s,i) for i,s in enumerate(CFG['floor_paint'])]
(ROOT/'Authored/floor_paint.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('INCINERATOR_SIGN_TEXTURES_AUTHORED',len(records)+2,flush=True)
