"""Editable Norse rune paths; supersampled masks, bevel heights and real normals."""
from pathlib import Path
import json, math
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from PIL import Image, ImageDraw, ImageFont

P=Path(__file__).resolve().parent
P.mkdir(parents=True,exist_ok=True)

def curve(a,b,c,d,n=110):
    t=np.linspace(0,1,n)[:,None]
    return ((1-t)**3*np.array(a)+3*(1-t)**2*t*np.array(b)+3*(1-t)*t*t*np.array(c)+t**3*np.array(d)).tolist()

def motif(kind):
    paths=[]
    def line(points,w=30):paths.append((points,w))
    if kind=='lei_ming_rune':
        # A single S-shaped lightning spine, framed by opposed knotted arms.
        line([(540,75),(330,440),(518,440),(355,900),(700,350),(497,350),(640,75),(540,75)],26)
        for side in (-1,1):
            def p(x,y):return (500+side*x,y)
            line(curve(p(90,185),p(410,175),p(410,455),p(210,510))+
                 curve(p(210,510),p(45,550),p(35,730),p(265,810)),30)
            line(curve(p(155,245),p(320,275),p(325,425),p(152,478))+
                 curve(p(152,478),p(-5,535),p(30,695),p(196,740)),13)
            line([p(268,810),p(312,763),p(338,840),p(265,878),p(268,810)],22)
            line([p(200,140),p(265,85),p(295,148)],14)
        line([(465,55),(500,20),(535,55)],14)
        line([(470,940),(500,980),(530,940)],14)
    else:
        # Two opposed hooked loops keep two seeds around an open central lens.
        for side in (-1,1):
            def p(x,y):return (500+side*x,500+side*y)
            line(curve(p(-15,-400),p(420,-400),p(455,230),p(35,300))+
                 curve(p(35,300),p(-190,340),p(-230,65),p(-25,60)),34)
            line(curve(p(-12,-327),p(320,-325),p(342,172),p(42,220))+
                 curve(p(42,220),p(-90,243),p(-150,132),p(-65,110)),14)
            line([p(-30,-385),p(-115,-320),p(-86,-444),p(-30,-385)],22)
            x,y=p(0,-182)
            line([(x,y-34),(x+25,y),(x,y+34),(x-25,y),(x,y-34)],18)
        line([(500,385),(566,500),(500,615),(434,500),(500,385)],24)
        line([(500,450),(526,500),(500,550),(474,500),(500,450)],10)
    return paths

def raster(paths,w,h,scale=2):
    im=Image.new('L',(w*scale,h*scale));d=ImageDraw.Draw(im)
    for pts,width in paths:
        coords=[(round(x*scale),round(y*scale)) for x,y in pts]
        d.line(coords,fill=255,width=max(1,round(width*scale)),joint='curve')
        r=width*scale/2
        for x,y in (coords[0],coords[-1]):d.ellipse((x-r,y-r,x+r,y+r),fill=255)
    return im.resize((w,h),Image.Resampling.LANCZOS)

def svg(paths,w,h):
    body=''.join(f'<polyline points="'+ ' '.join(f'{x:.3f},{y:.3f}' for x,y in pts)+f'" stroke-width="{width}"/>' for pts,width in paths)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="black"/><g fill="none" stroke="white" stroke-linejoin="round" stroke-linecap="round">{body}</g></svg>'

report=[]
for kind in ('lei_ming_rune','hui_xiang_rune'):
    core=motif(kind)
    (P/(kind+'_core.svg')).write_text(svg(core,1000,1000),encoding='utf-8')
    raster(core,1000,1000).save(P/(kind+'_core.png'))
    # Full, unequal-scale ornament: one focal crest plus tapering interlace.
    # At 33.5 cm / 4096 px the crest is 3.44 cm wide, fitting either half
    # circumference of the actual shaft without cropping the hooked shoulders.
    strip=[([(x*.42+302,y*.42+600) for x,y in pts],width*.42) for pts,width in core]
    for sign in (-1,1):
        for phase in (0,math.pi):
            pts=[]
            for y in np.linspace(1100,3550,600):
                taper=1-(y-1100)/3000
                x=512+sign*(118+70*math.sin((y-1100)/210+phase))*taper
                pts.append((x,y))
            strip.append((pts,17 if phase else 24))
        for y in (1600,2070,2540,3010):
            x=512+sign*230*(1-(y-1490)/2900)
            strip.append(([(x-sign*35,y-50),(x,y),(x-sign*35,y+50)],12))
    strip.extend([([(512,130),(450,290),(512,390),(574,290),(512,130)],24),
                  ([(512,3680),(470,3810),(512,3950),(554,3810),(512,3680)],20)])
    mask=raster(strip,1024,4096)
    mask.save(P/('T_Mask_'+kind+'.png'))
    (P/(kind+'_shaft.svg')).write_text(svg(strip,1024,4096),encoding='utf-8')
    a=np.array(mask,dtype=np.float32)/255
    dist=distance_transform_edt(a>.5)
    height=np.minimum(dist/6,1)*a
    # A shallow chased channel inside each broad stroke leaves two precise rims.
    height-=.18*np.clip((dist-7)/2,0,1)*a
    height=gaussian_filter(height,.65)
    Image.fromarray(np.uint16(height*65535)).save(P/('T_Height_'+kind+'.png'))
    dy,dx=np.gradient(height)
    n=np.dstack((-dx*4,dy*4,np.ones_like(height)))
    n/=np.linalg.norm(n,axis=2,keepdims=True)
    Image.fromarray(np.uint8(np.clip(n*.5+.5,0,1)*255)).save(P/('T_Normal_'+kind+'.png'))
    Image.fromarray(np.uint8(255*(.34+.15*(1-height)))).save(P/('T_Roughness_'+kind+'.png'))
    report.append(dict(id=kind,mask=[1024,4096],normal='DirectX',height_bits=16,source='editable vector paths',shaft_height_cm=33.5))
(P/'art_source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RUNE_PATTERNS_AUTHORED',flush=True)
