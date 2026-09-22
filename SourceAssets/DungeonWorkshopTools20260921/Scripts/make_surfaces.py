"""Original workshop timber, woven rag, lamp finish and tool labels; no render."""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopTools20260921');OUT=ROOT/'Authored';TEX=OUT/'Textures'
TEX.mkdir(parents=True,exist_ok=True);R=np.random.default_rng(92152);N=1024
y,x=np.mgrid[0:1:complex(N),0:1:complex(N)]
def noise(n):
    a=Image.fromarray(R.integers(0,256,(n,n),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC)
    return (np.asarray(a,dtype=float)-128)/128
macro=noise(13);mid=noise(61);micro=noise(420)
recipes={}
def finish(name,color,rough,height,metal=0,**extra):
    dy,dx=np.gradient(height);normal=np.dstack((-dx*3,-dy*3,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2)[:,:,None]
    maps={}
    for key,arr in [('BaseColor',np.clip(color,0,255).astype('uint8')),('Roughness',(np.clip(rough,0,1)*255).astype('uint8')),('Normal',((normal*.5+.5)*255).astype('uint8'))]:
        path=TEX/(name+'_'+key+'.png');Image.fromarray(arr).save(path);maps[key]=str(path)
    recipes[name]={'maps':maps,'metallic':metal,**extra}
warp=x+.005*np.sin(y*16)+.006*macro
grain=np.sin(warp*370+3*mid);fine=np.sin(warp*1300+mid*4)
knots=np.zeros_like(x)
for cx,cy in ((.25,.30),(.70,.82)):
    rr=np.sqrt((x-cx)**2+((y-cy)*2.9)**2);mask=np.exp(-rr**2/.014)
    knots+=mask*(np.sin(rr*220)*.4-.6)
value=grain*3+fine*1.2+macro*5+mid*1.1+knots*20
color=np.array([105,88,65])[None,None,:]+value[:,:,None]*np.array([1,.88,.70])
finish('Timber',color,.67+macro*.075-grain*.012,.10*grain+.05*fine+mid*.08)
radius=np.sqrt(((x+.16)*1.0)**2+((y-.51)*1.14)**2);rings=np.sin(radius*153+macro*1.5)
finish('EndGrain',np.array([96,79,58])[None,None,:]+(rings*4+macro*6)[:,:,None],.79+macro*.05,rings*.12+micro*.035)
weave=(np.sin(x*N*math.pi*.82)+np.sin(y*N*math.pi*.82))*.5
stain=np.clip(np.exp(-((x-.66)**2/.039+(y-.37)**2/.056))+.28*macro,0,1)
finish('Canvas',np.array([127,129,111])[None,None,:]+(weave*2+macro*8-stain*57)[:,:,None],.87-stain*.25,weave*.12+mid*.01,two_sided=True)
finish('Enamel',np.array([133,142,141])[None,None,:]+(macro*3+micro*.4)[:,:,None],.48+macro*.035,micro*.014)
recipes['Lens']={'color':[.78,.85,.88],'roughness':.4,'metallic':0,'emission':[1.55,1.68,1.74]}
recipes['TaskLens']={'color':[.80,.72,.56],'roughness':.45,'metallic':0,'emission':[1.35,1.12,.79]}
# Fine local stain uses a mask rather than a rectangular dark plane.
rad=np.sqrt(((x-.5)*1.03)**2+((y-.5)*.93)**2)
alpha=np.clip((.42-rad+macro*.032)*24,0,1)*.76
oil=np.dstack([np.full_like(x,48),np.full_like(x,43),np.full_like(x,32),alpha*255]).astype('uint8')
Image.fromarray(oil).save(TEX/'OilFilm_BaseColor.png')
recipes['OilFilm']={'maps':{'BaseColor':str(TEX/'OilFilm_BaseColor.png')},'roughness':.28,'metallic':0,'masked':True,'mask_clip':.18}
atlas=Image.new('RGB',(2048,1024),(153,161,157));draw=ImageDraw.Draw(atlas)
labels=[('M-04 / SERVICE TOOLS','RETURN TO OUTLINE'),('10','COMBINATION'),('12','COMBINATION'),('14','COMBINATION'),
        ('17','COMBINATION'),('19','COMBINATION'),('PH / SL','DRIVERS'),('VISE / 100','KEEP JAWS CLEAN'),
        ('MACHINE OIL','ISO VG 32'),('DEGREASER','WIPE AFTER USE'),('M8 / M10','SORTED PARTS'),('M-04','DISASSEMBLY'),
        ('L-02','4500 K / SERVICE'),('MOTOR NOTES','BEARING / SEAL'),('MEASURE','0 - 150 mm'),('RAGS','USED / OILY')]
for i,(a,b) in enumerate(labels):
    xx=i%4*512;yy=i//4*256
    draw.rectangle((xx+9,yy+10,xx+501,yy+245),fill=(178,184,169),outline=(65,78,74),width=4)
    size=32 if len(a)>17 else 44 if len(a)>7 else 70
    draw.text((xx+28,yy+48),a,font=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',size),fill=(35,47,46))
    draw.text((xx+27,yy+163),b,font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',25),fill=(48,61,59))
atlas.save(TEX/'ToolLabels_BaseColor.png');recipes['ToolLabels']={'maps':{'BaseColor':str(TEX/'ToolLabels_BaseColor.png')},'roughness':.74,'metallic':0}
(OUT/'material-manifest.json').write_text(json.dumps(recipes,indent=2),encoding='utf-8')
print('TOOL_SURFACES_AUTHORED',len(recipes),'NO_RENDER')
