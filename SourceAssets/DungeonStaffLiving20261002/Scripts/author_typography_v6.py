"""Redraw existing wording with native glyphs at each plate's physical aspect."""
import json,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'WallInsetV6/Authored';OUT.mkdir(parents=True,exist_ok=True)
FONT='C:/Windows/Fonts/msyh.ttc';metrics=[]
labels=[('Dormitory','生活宿舍区','STAFF DORMITORY',1.10,.40),
 ('Changing','员工更衣区','CHANGING / DRY AREA',1.25,.42),('Showers','员工淋浴区','SHOWERS / WET AREA',1.35,.42),
 ('Recreation','员工活动区','STAFF RECREATION',1.65,.56),('Meals','茶水与用餐区','MEALS / REFRESHMENTS',1.25,.40),
 ('Quiet','休息区','QUIET LOUNGE',1.10,.37),('ToChanging','更衣淋浴区 →','CHANGING / SHOWERS',.90,.32),
 ('Exit','出口 →','ONWARD ACCESS',.48,.28)]
labels += [('Room'+str(i),'宿舍 '+str(i),'STAFF ROOM '+str(i),.40,.24) for i in range(101,107)]
labels += [('Shower'+str(i),'淋浴 '+str(i),'SHOWER '+str(i),.35,.22) for i in range(1,7)]
labels += [('Toilet','员工卫生间','STAFF RESTROOM',.45,.19)]
atlas=Image.new('RGB',(4096,2048),(179,177,159));d=ImageDraw.Draw(atlas);rects={};x=16;y=16;rowh=0
for key,title,sub,w,h in labels:
    px=round(w*1000);py=round(h*1000)
    if x+px+16>4096:x=16;y+=rowh+16;rowh=0
    if y+py>2048:raise RuntimeError('Sign atlas capacity exceeded')
    rects[key]=[x,y,x+px,y+py];sx=px/502;sy=py/308
    d.rectangle(rects[key],fill=(186,190,170),outline=(44,59,47),width=max(2,round(5*sy)))
    d.rectangle((x+11*sx,y+12*sy,x+491*sx,y+51*sy),fill=(55,79,69))
    fs=60 if key=='Toilet' else 40 if len(title)>7 else 48
    # Preserve the previous vertical type size; never squeeze glyph width.
    f=ImageFont.truetype(FONT,max(12,round(fs*py/(256 if key=='Toilet' else 308))))
    d.text((x+px/2,y+130*sy),title,font=f,fill=(27,42,33),anchor='mm')
    ef=ImageFont.truetype(FONT,max(10,round(21*sy)))
    d.text((x+px/2,y+207*sy),sub,font=ef,fill=(42,55,46),anchor='mm')
    d.line((x+20*sx,y+254*sy,x+482*sx,y+254*sy),fill=(105,117,96),width=max(1,round(3*sy)))
    metrics.append(dict(key=key,width_m=w,height_m=h,pixels=[px,py],
        old_aspect_scale=(w/h)/(640/256 if key=='Toilet' else 502/308),aspect_scale=(w/h)/(px/py),
        native_font_px=f.size,glyph_horizontal_rescale=False,
        old_font_height_m=fs*h/(256 if key=='Toilet' else 308),font_height_m=f.size/1000))
    x+=px+16;rowh=max(rowh,py)
atlas.save(OUT/'T_Staff_Labels_V6.png')
(OUT/'labels-atlas.json').write_text(json.dumps(dict(size=[4096,2048],rects=rects),ensure_ascii=False,indent=2),encoding='utf8')

# Keep the detailed V3 notice wording. Transform layout coordinates only and
# draw every glyph anew at a single scale derived from its physical height.
old=json.loads((ROOT/'RefinementV3/Authored/notice-atlas.json').read_text('utf8'))
new=dict(size=[4096,2048],pages={})
regions=[]
for i in range(4):
    a=[16+i*786,16,16+i*786+770,1350];new['pages'][str(i)]=a
    regions.append((old['pages'][str(i)],a,'NoticePage'+str(i),.385,.667))
new['header']=[16,1370,3216,1626];regions.append((old['header'],new['header'],'NoticeHeader',1.60,.128))
new['reminder']=[16,1646,1376,1876];regions.append((old['reminder'],new['reminder'],'NoticeReminder',.68,.115))
image=Image.new('RGB',(4096,2048),(190,185,166));native=ImageDraw.Draw(image);textmetrics=[]
class RemappedDraw:
    def region(self,p):
        x,y=p
        if y<1540:return regions[min(3,max(0,int(x//1024)))]
        return regions[4 if x<3050 else 5]
    def point(self,p,r):
        a,b,*_=r;sx=(b[2]-b[0])/(a[2]-a[0]);sy=(b[3]-b[1])/(a[3]-a[1])
        return b[0]+(p[0]-a[0])*sx,b[1]+(p[1]-a[1])*sy
    def rectangle(self,xy,**kw):
        r=self.region(xy[:2]);p=self.point(xy[:2],r)+self.point(xy[2:],r)
        if 'width' in kw:kw['width']=max(1,round(kw['width']*(r[1][3]-r[1][1])/(r[0][3]-r[0][1])))
        native.rectangle(p,**kw)
    def line(self,xy,**kw):
        r=self.region(xy[:2]);p=self.point(xy[:2],r)+self.point(xy[2:],r)
        if 'width' in kw:kw['width']=max(1,round(kw['width']*(r[1][3]-r[1][1])/(r[0][3]-r[0][1])))
        native.line(p,**kw)
    def text(self,xy,text,**kw):
        r=self.region(xy);a,b,key,w,h=r;sy=(b[3]-b[1])/(a[3]-a[1]);oldsize=kw['font'].size
        kw['font']=ImageFont.truetype(FONT,max(8,round(oldsize*sy)))
        p=self.point(xy,r);native.text(p,text,**kw)
        bbox=native.textbbox(p,text,font=kw['font'],anchor=kw.get('anchor'))
        textmetrics.append(dict(panel=key,text=text,native_font_px=kw['font'].size,bbox=list(bbox),
            overflow=bbox[0]<b[0] or bbox[1]<b[1] or bbox[2]>b[2] or bbox[3]>b[3],glyph_horizontal_rescale=False))
code=(ROOT/'Scripts/author_notices_v3.py').read_text('utf8')
ns=dict(FONT=FONT,ImageFont=ImageFont,d=RemappedDraw(),pages={})
exec(compile(code[code.index('def font(n)'):code.index('im.save(')],'existing_notice_wording','exec'),ns)
for a,b,key,w,h in regions:
    px=b[2]-b[0];py=b[3]-b[1]
    metrics.append(dict(key=key,width_m=w,height_m=h,pixels=[px,py],old_aspect_scale=(w/h)/((a[2]-a[0])/(a[3]-a[1])),
        aspect_scale=(w/h)/(px/py),glyph_horizontal_rescale=False))
image.save(OUT/'T_Staff_Notices_V6.png')
(OUT/'notice-atlas.json').write_text(json.dumps(new,ensure_ascii=False,indent=2),encoding='utf8')
report=dict(scope='All staff room signage and noticeboard text, plus the toilet sign',
    method='Physical width/height versus sampled atlas pixels; native raster fonts, no anisotropic glyph scaling',
    panels=metrics,notice_text_runs=textmetrics,overflow_runs=[m for m in textmetrics if m['overflow']],
    renders_run=False,game_run=False)
(OUT/'typography-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('STAFF_TYPOGRAPHY_V6_AUTHORED',len(metrics),'panels; overflow',len(report['overflow_runs']))
