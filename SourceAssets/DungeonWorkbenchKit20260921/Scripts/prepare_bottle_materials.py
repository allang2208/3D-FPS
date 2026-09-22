"""Author original packaging artwork and millimetre-scale bottle PBR maps."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';TEX=OUT/'Textures/Bottles';TEX.mkdir(parents=True,exist_ok=True)
N=1024;R=np.random.default_rng(2192201);Y,X=np.mgrid[0:N,0:N]/N
recipes={}

def noise(grid):
    im=Image.fromarray(np.uint8(R.random((grid,grid))*255)).resize((N,N),Image.Resampling.BICUBIC)
    return np.asarray(im,dtype=np.float32)/255-.5

def write(key,base,rough,height,metal=0):
    maps={};base=np.clip(base,0,255).astype('uint8')
    dy,dx=np.gradient(height);normal=np.stack([-dx,dy,np.ones_like(dx)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    for ch,data in [('BaseColor',base),('Roughness',np.uint8(np.clip(rough,0,1)*255)),('Normal',np.uint8(np.clip(normal*.5+.5,0,1)*255))]:
        path=TEX/(key+'_'+ch+'.png');Image.fromarray(data).save(path);maps[ch]=str(path)
    if not np.isscalar(metal):
        path=TEX/(key+'_Metallic.png');Image.fromarray(np.uint8(np.clip(metal,0,1)*255)).save(path);maps['Metallic']=str(path);metal=0
    recipes[key]=dict(maps=maps,metallic=metal,roughness=.5,color_tint=[1,1,1],normal_strength=1,
                      content_hash=hashlib.sha256(b''.join(Path(p).read_bytes() for p in maps.values())).hexdigest())

for key,color,roughness in [('OilPaint',[133,148,139],.43),('CleanerPlastic',[113,39,30],.47),('CapPolymer',[38,40,38],.53),('SpoutSteel',[165,167,158],.32)]:
    broad=noise(14);fine=noise(256);micro=R.normal(0,1,(N,N)).astype('float32')
    scuffs=Image.new('L',(N,N));d=ImageDraw.Draw(scuffs)
    for i in range(80 if key=='OilPaint' else 38):
        x=int(R.integers(0,N));y=int(R.integers(0,N));d.line([(x,y),(x+int(R.integers(-4,5)),y+int(R.integers(3,40)))],fill=int(R.integers(35,130)),width=1)
    marks=np.asarray(scuffs,dtype=np.float32)/255
    seam=np.exp(-((Y-.055)/.014)**2)+np.exp(-((Y-.78)/.018)**2)
    polish=np.exp(-((Y-.47)/.22)**2)*(.5+noise(7))
    base=np.array(color)[None,None,:]*(1+(broad*.045+fine*.012)[...,None])-marks[...,None]*11
    rough=np.full((N,N),roughness)+broad*.055+fine*.025+marks*.15-polish*.045
    h=fine*.55+micro*.025-marks*.65
    metal=0
    if key=='OilPaint':
        chips=np.clip((noise(80)+.06)*seam*1.25,0,.35)
        base=base*(1-chips[...,None])+np.array([78,77,67])*chips[...,None];rough+=chips*.24;metal=chips*1.8
    elif key=='SpoutSteel':
        brush=R.normal(0,1,(N,1));base+=brush[...,None]*2.2;rough+=brush*.014;h+=brush*.2;metal=.92
    write(key,base,rough,h,metal)

fontroot=Path('C:/Windows/Fonts')
def font(size,bold=False):return ImageFont.truetype(str(fontroot/('arialbd.ttf' if bold else 'arial.ttf')),size)
def textfit(draw,box,text,size=50,bold=False,fill=(30,37,34)):
    x,y,w=box
    while draw.textbbox((0,0),text,font=font(size,bold))[2]>w:size-=1
    draw.text((x,y),text,font=font(size,bold),fill=fill)

for key,product,grade,sub,volume,accent in [
    ('OilLabel','MACHINE OIL','ISO VG 32','PRECISION LUBRICANT','500 mL',(40,69,66)),
    ('CleanerLabel','DEGREASER','PARTS CLEANER','WORKSHOP SERVICE FLUID','750 mL',(128,57,31))]:
    im=Image.new('RGB',(N,N),(218,214,191));d=ImageDraw.Draw(im)
    d.rounded_rectangle((21,21,1002,1002),radius=20,outline=(121,121,103),width=3)
    d.rectangle((40,42,984,216),fill=accent)
    textfit(d,(70,64,870),'M-04  /  MAINTENANCE',56,True,(235,231,209))
    textfit(d,(72,143,866),'UNDERGROUND SERVICE DIVISION',30,False,(221,221,196))
    textfit(d,(64,258,896),product,101,True)
    textfit(d,(68,397,880),grade,73,True,accent)
    d.line((68,505,956,505),fill=accent,width=6)
    textfit(d,(68,534,880),sub,37,True)
    for i,line in enumerate(['CLEAN APPLICATOR BEFORE USE','KEEP CAP CLOSED AFTER SERVICE','STORE UPRIGHT / WIPE SPILLS']):
        textfit(d,(70,613+i*54,880),line,30)
    d.line((68,796,956,796),fill=(117,117,99),width=2)
    textfit(d,(68,822,540),'LOT  24-0918  /  BAY 04',30)
    textfit(d,(711,818,250),volume,49,True)
    x=70
    for i in range(92):
        width=int(R.integers(2,7));d.rectangle((x,886,x+width,951 if i%5 else 965),fill=(49,51,44));x+=width+int(R.integers(2,5))
        if x>687:break
    textfit(d,(750,914,215),'SERVICE USE',24,True)
    arr=np.asarray(im,dtype=np.float32)
    # Restrained handling marks: lettering stays readable; the paper is not a metal plate.
    edge=np.minimum.reduce([X,1-X,Y,1-Y]);dirt=np.exp(-edge/.018)*(.4+noise(34))
    grain=R.normal(0,1,(N,N));arr+=grain[...,None]*.65;arr-=dirt[...,None]*17
    write(key,arr,.71+noise(48)*.035,noise(256)*.24)

(OUT/'bottle-materials.json').write_text(json.dumps(recipes,indent=2),encoding='utf-8')
print('BOTTLE_PRODUCTION_MAPS_WRITTEN',len(recipes))
