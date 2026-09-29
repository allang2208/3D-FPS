"""Original surface and instrument artwork for the two facility props. No external art."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored'/'Textures';OUT.mkdir(parents=True,exist_ok=True)
N=1024;W=4096;H=2048
rng=np.random.default_rng(928271)
yy,xx=np.mgrid[0:N,0:N].astype(np.float32)/N
def noise(size):
    data=(rng.random((size,size))*255).astype('uint8')
    return np.asarray(Image.fromarray(data).resize((N,N),Image.Resampling.BICUBIC),dtype=np.float32)/255
base=np.zeros((H,W,3),dtype=np.uint8)
normal=np.empty((H,W,3),dtype=np.uint8);normal[:]=(128,128,255)
orm=np.empty((H,W,3),dtype=np.uint8);orm[:]=(255,160,0)
rects={}
def tile(index,name,color,height,rough,metal,ao=1,normal_scale=6):
    x=(index%4)*N;y=(index//4)*N
    base[y:y+N,x:x+N]=np.clip(color,0,255).astype('uint8')
    gy,gx=np.gradient(np.asarray(height,dtype=np.float32))
    vectors=np.stack((-gx*normal_scale,gy*normal_scale,np.ones_like(gx)),axis=-1)
    vectors/=np.linalg.norm(vectors,axis=-1,keepdims=True)
    normal[y:y+N,x:x+N]=np.clip((vectors*.5+.5)*255,0,255).astype('uint8')
    for channel,value in enumerate((ao,rough,metal)):
        orm[y:y+N,x:x+N,channel]=np.clip(np.asarray(value)*255,0,255).astype('uint8')
    rects[name]=[x+12,y+12,x+N-12,y+N-12]

for index,name,rgb in [(0,'enamel',(94,117,107)),(1,'red',(90,27,26))]:
    broad=noise(12);medium=noise(100);fine=noise(700)
    edge=np.minimum.reduce((xx,1-xx,yy,1-yy))
    threshold=.015+(medium-.5)*.065+(broad-.5)*.025
    chipped=np.clip((threshold-edge)*180,0,1)
    scratches=np.zeros((N,N),np.float32)
    canvas=Image.new('L',(N,N));draw=ImageDraw.Draw(canvas)
    for _ in range(70):
        x=int(rng.integers(25,N-25));y=int(rng.integers(25,N-25))
        if min(x,y,N-x,N-y)>120 and rng.random()<.83:continue
        draw.line((x,y,x+int(rng.integers(-18,22)),y+int(rng.integers(4,38))),fill=int(rng.integers(30,180)),width=1)
    scratches=np.asarray(canvas,dtype=np.float32)/255
    wear=np.maximum(chipped,scratches)
    dirt=np.clip((yy-.67)*1.5,0,.25)*(broad*.65+.35)
    color=np.asarray(rgb)[None,None,:]*(.90+broad[:,:,None]*.19+fine[:,:,None]*.035)
    if name=='red':
        grain=np.sin(xx*810+noise(24)*9)*.5+.5
        color*=.95+grain[:,:,None]*.09
        exposed=np.stack((94+medium*27,66+medium*23,39+medium*17),axis=-1)
        metal=np.zeros((N,N));height=grain*.012+fine*.009-wear*.1
    else:
        exposed=np.stack((61+medium*24,48+medium*15,35+medium*12),axis=-1)
        metal=chipped*.35;height=fine*.011+medium*.006-wear*.095
    color=color*(1-wear[:,:,None])+exposed*wear[:,:,None]
    color*=1-dirt[:,:,None]
    rough=.48+fine*.10+wear*.27+dirt*.3
    tile(index,name,color,height,rough,metal,1-wear*.12,normal_scale=9)

warp=noise(18)*5+noise(70)*.9
grain=(np.sin(xx*1150+warp*7)+np.sin(xx*330+warp*2)*.35)*.5
knots=np.zeros((N,N),np.float32)
for cx,cy in ((.21,.29),(.74,.78),(.48,.57)):
    dist=np.sqrt(((xx-cx)*2.4)**2+((yy-cy)*.52)**2)
    knots+=np.sin(dist*520)*np.exp(-dist*28)*.65
grain+=knots
rough_noise=noise(300);dark=noise(13)
wood=np.stack((81+grain*17+dark*10,62+grain*14+dark*7,41+grain*10+dark*6),axis=-1)
splits=(np.sin(xx*1390+warp*3)>.996)*(noise(40)>.52)
wood*=1-splits[:,:,None]*.36
tile(2,'wood',wood,grain*.045+rough_noise*.025-splits*.14,.72+rough_noise*.17,0,1-splits*.18,normal_scale=8)

grain=noise(950);cloud=noise(55)
lines=np.asarray(Image.fromarray((rng.random((1024,28))*255).astype('uint8')).resize((N,N),Image.Resampling.BILINEAR),np.float32)/255
steel=98+cloud*23+lines*11+grain*6
tile(3,'steel',np.stack((steel*.96,steel,steel*.99),axis=-1),grain*.008+lines*.02,.34+lines*.13+grain*.025,.92,normal_scale=7)

rubber=18+noise(90)*7
caps=np.repeat(rubber[:,:,None],3,axis=2)
caps[:512,512:]=np.asarray((37,69,49))*(.9+noise(50)[:512,512:,None]*.19)
caps[512:,:512]=np.asarray((100,28,24))*(.9+noise(50)[512:,:512,None]*.19)
caps[512:,512:]=np.asarray((148,118,48))*(.9+noise(50)[512:,512:,None]*.19)
tile(4,'dark',caps,noise(500)*.01,.69,0,normal_scale=5)
rects['dark']=[16,1040,496,1520]
rects['green_cap']=[528,1040,1008,1520]
rects['red_cap']=[16,1552,496,2032]
rects['yellow_cap']=[528,1552,1008,2032]

FONT=Path('C:/Windows/Fonts')
def font(size,bold=False):return ImageFont.truetype(str(FONT/('consolab.ttf' if bold else 'consola.ttf')),size)
def text_center(draw,xy,text,size,fill=(30,33,30),bold=False):
    draw.text(xy,text,font=font(size,bold),fill=fill,anchor='mm')
for index,unit,title,maximum in ((5,'V','AC VOLTMETER',600),(6,'A','LOAD CURRENT',60)):
    im=Image.new('RGB',(N,N),(205,207,186));d=ImageDraw.Draw(im)
    d.ellipse((28,28,996,996),outline=(72,79,71),width=8)
    def at(value,r):
        a=math.radians(140-value*280)
        return (512+math.cos(a)*r,512-math.sin(a)*r)
    for step in range(61):
        major=step%10==0;medium=step%5==0
        d.line((at(step/60,437),at(step/60,395 if major else 408 if medium else 420)),fill=(29,35,31),width=5 if major else 3)
        if major:text_center(d,at(step/60,350),str(int(step/60*maximum)),43,bold=True)
    for step in range(485,600):
        d.line((at(step/600,463),at((step+1)/600,463)),fill=(110,46,32),width=12)
    text_center(d,(512,425),title,32,bold=True)
    text_center(d,(512,603),unit,95,bold=True)
    text_center(d,(512,702),'TRANSIT / CLASS 1.5',25)
    text_center(d,(512,740),'50 Hz   /   PANEL 07',21)
    d.line((348,674,676,674),fill=(64,69,59),width=2)
    aging=noise(140)*3+noise(18)*6
    color=np.asarray(im,dtype=np.float32)-aging[:,:,None]
    tile(index,'dial_'+unit,color,np.zeros((N,N)),.23,.025,normal_scale=1)
    rects['dial_'+unit]=[(index%4)*1024,index//4*1024,(index%4+1)*1024,(index//4+1)*1024]

im=Image.new('RGB',(N,N),(55,59,55));d=ImageDraw.Draw(im)
regions={
    'cabinet_left':(18,18,502,145),'cabinet_right':(18,164,502,291),
    'warning':(18,313,502,513),'rating':(18,535,502,716),
    'buttons':(18,738,502,817),'service':(18,839,502,1005),
    'cargo_01':(523,18,1005,236),'cargo_02':(523,258,1005,476),
    'cargo_03':(523,498,1005,716),'arrows':(523,738,755,1005),
    'fragile':(778,738,1005,1005)}
for name,rect in regions.items():
    color=(182,166,112) if name.startswith('cabinet') else (173,157,105) if name=='warning' else (180,177,156) if name.startswith('cargo') else (135,145,138)
    d.rounded_rectangle(rect,radius=7,fill=color,outline=(37,43,38),width=4)
    x0,y0,x1,y1=rect;rects[name]=[3072+x0,1024+y0,3072+x1,1024+y1]
for key,label,number in [('cabinet_left','PUMP CONTROL','01'),('cabinet_right','AUXILIARY POWER','02')]:
    x,y,x1,y1=regions[key]
    text_center(d,((x+x1)/2,y+28),'TRANSIT / ELECTRICAL SERVICES',21,bold=True)
    text_center(d,((x+x1)/2,y+69),label,32,bold=True)
    text_center(d,((x+x1)/2,y+104),'SWITCHGEAR '+number+'  -  SECTION B',19)
x,y,x1,y1=regions['warning']
d.polygon([(x+44,y+17),(x+12,y+86),(x+78,y+86)],fill=(37,39,30))
d.line((x+47,y+31,x+35,y+57,x+51,y+54,x+40,y+74),fill=(192,167,72),width=4)
text_center(d,(x+286,y+51),'DANGER  /  380 V',35,bold=True)
text_center(d,((x+x1)/2,y+120),'ISOLATE BEFORE SERVICE',30,bold=True)
text_center(d,((x+x1)/2,y+163),'AUTHORIZED PERSONNEL ONLY',23)
x,y,x1,y1=regions['rating']
for k,line in enumerate(('TA  /  MUNICIPAL PUMP STATION','TYPE  C-07   /   3 PHASE','380 V AC       50 Hz       60 A','SERIAL  04-2781     IP 54')):
    d.text((x+20,y+14+k*38),line,font=font(23,k==0),fill=(26,35,31))
x,y,x1,y1=regions['buttons'];text_center(d,(x+120,y+37),'START',29,bold=True);text_center(d,(x+365,y+37),'STOP',29,bold=True)
x,y,x1,y1=regions['service']
for k,line in enumerate(('SERVICE RECORD / B-07','LAST INSPECTION:  14 / 09','DISCONNECTED - DO NOT ENERGIZE')):
    d.text((x+18,y+14+k*45),line,font=font(23,k==0),fill=(35,44,39))
for k,key in enumerate(('cargo_01','cargo_02','cargo_03')):
    x,y,x1,y1=regions[key]
    d.text((x+20,y+13),'TRANSIT / TECHNICAL STORES',font=font(24,True),fill=(35,38,33))
    d.text((x+20,y+51),('PUMP SERVICE PARTS','ELECTRICAL SPARES','INSTRUMENT ASSEMBLY')[k],font=font(26,True),fill=(35,38,33))
    d.text((x+20,y+91),'TA-B07  /  LOT 28-'+str(41+k),font=font(23),fill=(35,38,33))
    cursor=x+22
    for _ in range(62):
        width=int(rng.integers(1,5));d.rectangle((cursor,y+136,cursor+width,y+181),fill=(36,41,35));cursor+=width+int(rng.integers(2,4))
    d.text((x+20,y+190),'KEEP DRY  /  GROSS '+str((84,63,18)[k])+' kg',font=font(17),fill=(35,38,33))
x,y,x1,y1=regions['arrows']
for cx in (x+66,x+162):
    d.polygon(((cx,y+38),(cx-32,y+83),(cx-12,y+83),(cx-12,y+163),(cx+12,y+163),(cx+12,y+83),(cx+32,y+83)),fill=(35,43,36))
text_center(d,((x+x1)/2,y+209),'THIS SIDE UP',22,bold=True)
x,y,x1,y1=regions['fragile']
d.line((x+65,y+46,x+68,y+111,x+112,y+139,x+155,y+111,x+159,y+46),fill=(38,43,37),width=9)
d.line((x+113,y+139,x+113,y+185,x+76,y+185,x+150,y+185),fill=(38,43,37),width=8)
text_center(d,((x+x1)/2,y+225),'HANDLE WITH CARE',18,bold=True)
label_noise=noise(400)*2+noise(18)*4
tile(7,'label_sheet',np.asarray(im,dtype=np.float32)-label_noise[:,:,None],noise(500)*.003,.55,.10,normal_scale=4)
for suffix,data in [('BaseColor',base),('NormalGL',normal),('ORM',orm)]:
    Image.fromarray(data).save(OUT/('T_FacilityProp_'+suffix+'.png'))
(ROOT/'Authored'/'atlas.json').write_text(json.dumps({'size':[W,H],'rects':rects,'normal_convention':'OpenGL; flip green on Unreal import','orm_channels':'R ambient occlusion / G roughness / B metallic','source':'Original procedural surfaces, original technical typography and instrument artwork'},indent=2),encoding='utf-8')
print('FACILITY_PROP_TEXTURES_AUTHORED',W,H,flush=True)
