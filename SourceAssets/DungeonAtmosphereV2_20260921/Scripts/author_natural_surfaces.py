"""Original PBR authoring for the entrance's surface history revision."""
from pathlib import Path
import json
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/NaturalPass/Textures';OUT.mkdir(parents=True,exist_ok=True)
R=random.Random(921301);N=np.random.default_rng(921301)
def noise(w,h,scale):
    a=N.integers(0,256,(max(2,h//scale),max(2,w//scale)),dtype=np.uint8)
    return np.asarray(Image.fromarray(a).resize((w,h),Image.Resampling.BICUBIC),dtype=np.float32)/255
def normal(height,strength):
    dy,dx=np.gradient(height);v=np.stack((-dx*strength,dy*strength,np.ones_like(dx)),axis=-1)
    v/=np.linalg.norm(v,axis=-1,keepdims=True)
    return np.uint8(np.clip(v*.5+.5,0,1)*255)
def save(name,base,rough,height,strength):
    paths={}
    for channel,array in {'BaseColor':np.uint8(np.clip(base,0,255)),
        'Roughness':np.uint8(np.clip(rough,0,1)*255),'Normal':normal(height,strength)}.items():
        path=OUT/(name+'_'+channel+'.png');Image.fromarray(array).save(path);paths[channel]=str(path)
    return paths

w,h=512,256;yy,xx=np.mgrid[0:h,0:w]
edge=np.exp(-np.minimum.reduce([xx,w-1-xx,yy,h-1-yy])/9)
atlas=np.zeros((h*8,w*8,3),np.float32);rough_atlas=np.zeros((h*8,w*8),np.float32);height_atlas=np.zeros_like(rough_atlas)
for index in range(64):
    macro=noise(w,h,85);medium=noise(w,h,14);grain=noise(w,h,2)
    replacement=index>=56;damp=32<=index<40;worn=40<=index<48;crazed=48<=index<56
    tint=np.array([188,185,168] if not replacement else [182,185,176],np.float32)*R.uniform(.972,1.027)
    edge_dirt=edge*(.10+medium*.15)
    base=tint[None,None,:]+((macro-.5)*1.7+(grain-.5)*1.4)[:,:,None]
    base-=edge_dirt[:,:,None]*np.array([35,36,34])
    # Age lives primarily in reflectance and edge wear. Dry tile centres retain
    # a quiet glaze, with selected damp variants instead of universal clouding.
    if damp:base-=((.4+macro*.6)*8)[:,:,None]*np.array([.85,.9,1])
    scratches=Image.new('L',(w,h));draw=ImageDraw.Draw(scratches)
    for j in range(R.randrange(0,7)):
        x,y=R.randrange(w),R.randrange(h);length=R.randrange(6,42)
        draw.line([(x,y),(x+length,y+R.randrange(-3,4))],fill=R.randrange(15,65),width=1)
    if crazed:
        x=R.uniform(w*.2,w*.8);direction=R.uniform(-.3,.3);pts=[]
        for y in range(-5,h+12,8):
            direction=direction*.84+R.uniform(-.12,.12);x+=direction*11+R.uniform(-1.4,1.4);pts.append((x,y))
        draw.line(pts,fill=145,width=1)
        for j in R.sample(range(6,len(pts)-6),2):
            x,y=pts[j];branch=[(x,y)];angle=R.choice([-1,1])*R.uniform(.4,.7)
            for k in range(R.randrange(5,11)):
                x+=angle*9+R.uniform(-2,2);y+=R.uniform(2,7);branch.append((x,y))
            draw.line(branch,fill=65,width=1)
    crack=np.asarray(scratches,np.float32)/255
    spall=np.clip((.25-medium)*8,0,1)*np.clip((edge-.25)*3,0,1)*(1 if worn else .12)
    base-=crack[:,:,None]*48+spall[:,:,None]*np.array([45,49,54])
    rough=.29+medium*.095+(macro-.5)*.035+edge_dirt*.45+spall*.4+crack*.22
    if damp:rough-=.075
    if replacement:rough-=.025
    height=(medium-.5)*.03+(grain-.5)*.015-crack*.24-spall*.30
    row,col=divmod(index,8);sl=np.s_[row*h:(row+1)*h,col*w:(col+1)*w]
    atlas[sl]=base;rough_atlas[sl]=rough;height_atlas[sl]=height
manifest={'NaturalCeramicAtlas':save('NaturalCeramicAtlas',atlas,rough_atlas,height_atlas,1.5)}

w=h=2048;yy,xx=np.mgrid[0:h,0:w]
macro=noise(w,h,240);medium=noise(w,h,21);grain=noise(w,h,2)
pits=np.clip((.22-grain)*5,0,1);aggregate=np.clip((medium-.65)*3,0,1)
base=np.array([114,108,97])[None,None,:]+((macro-.5)*11+(medium-.5)*15+(grain-.5)*7-pits*15)[:,:,None]
manifest['NaturalMortar']=save('NaturalMortar',base,.82+medium*.12,medium*.22+grain*.14-pits*.25+aggregate*.12,1.7)
base=np.array([143,125,100])[None,None,:]+((medium-.5)*13+(grain-.5)*11)[:,:,None]
manifest['NaturalCeramicCore']=save('NaturalCeramicCore',base,.79+medium*.13,grain*.18+medium*.15,1.7)
base=np.array([133,131,122])[None,None,:]+((macro-.5)*6+(medium-.5)*8+(grain-.5)*3)[:,:,None]
smear=np.sin(xx*.007+np.sin(yy*.004)*2)*.02
manifest['NaturalRepair']=save('NaturalRepair',base,.72+medium*.11,grain*.05+medium*.08+smear,.9)
base=np.array([179,173,151])[None,None,:]+((medium-.5)*9+(grain-.5)*8)[:,:,None]
manifest['NaturalSalt']=save('NaturalSalt',base,.9+medium*.07,grain*.14+medium*.08,1.1)

# Leak image uses conventional horizontal U / top-to-bottom V. The UE decal
# material remaps its native Z/Y coordinates before sampling this texture.
w,h=768,1536;yy,xx=np.mgrid[0:h,0:w]
streak=Image.new('L',(w,h));d=ImageDraw.Draw(streak)
for i in range(42):
    x=R.gauss(w*.49,w*.09);top=R.randrange(15,180);end=R.randrange(int(h*.50),h-25)
    pts=[];drift=0
    for y in range(top,end,14):
        drift=drift*.8+R.uniform(-1.6,1.6);pts.append((x+drift,y))
    d.line(pts,fill=R.randrange(38,130),width=R.randrange(3,18))
veil=np.asarray(streak.filter(ImageFilter.GaussianBlur(12)),np.float32)/255
sharp=np.asarray(streak.filter(ImageFilter.GaussianBlur(1.3)),np.float32)/255
alpha=(veil*.55+sharp*.50)*(.58+noise(w,h,15)*.42)
alpha*=np.clip(np.minimum(yy,h-1-yy)/55,0,1)
Image.fromarray(np.uint8(np.clip(alpha,0,.62)*255)).save(OUT/'NaturalLeak_Opacity.png')

# Irregular floor dampness and impact dust, faded naturally into surrounding floor.
w=h=1024;yy,xx=np.mgrid[-1:1:complex(h),-1:1:complex(w)]
macro=noise(w,h,85);grain=noise(w,h,3)
footprint=np.clip((1-(xx*1.06)**2-(yy*1.35)**2)*2+(macro-.5)*.7,0,1)
wet=footprint*(.34+macro*.24)
dust=footprint*(.15+grain*.13)*np.clip((macro-.22)*2,0,1)
Image.fromarray(np.uint8(wet*255)).save(OUT/'NaturalWet_Opacity.png')
Image.fromarray(np.uint8(dust*255)).save(OUT/'NaturalDust_Opacity.png')
(OUT.parent/'material-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('NATURAL_PBR_AUTHORED: quiet glaze atlas, mortar, repair skim, ceramic core, mineral residue, local history masks')
