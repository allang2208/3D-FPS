"""Physically scaled surface channels and native label artwork for the four requested details."""
from pathlib import Path
import json,math,shutil
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored';TEX=OUT/'Textures';TEX.mkdir(parents=True,exist_ok=True)
N=2048;R=np.random.default_rng(9212010);y,x=np.mgrid[0:1:complex(N),0:1:complex(N)].astype(np.float32)
recipes={}
def noise(n):return (np.asarray(Image.fromarray(R.integers(0,256,(n,n),dtype=np.uint8)).resize((N,N),Image.Resampling.BICUBIC),dtype=np.float32)-128)/128
large=noise(9);small=noise(190);fine=noise(1300)
def scratches(number,width=1):
    im=Image.new('L',(N,N));d=ImageDraw.Draw(im)
    for _ in range(number):
        xx=int(R.uniform(.03,.97)*N);yy=int(R.uniform(.03,.97)*N)
        d.line((xx,yy,xx+int(R.uniform(-24,24)),yy+int(R.uniform(9,95))),fill=int(R.integers(65,200)),width=width)
    return np.asarray(im,dtype=np.float32)/255
def save_surface(key,color,rough,metal,height,physical=(.18,.18)):
    dy,dx=np.gradient(height);n=np.dstack((-dx*N/physical[0],-dy*N/physical[1],np.ones_like(dx)));n/=np.linalg.norm(n,axis=2)[:,:,None]
    maps={}
    for ch,arr in [('BaseColor',np.clip(color,0,255).astype('uint8')),('Roughness',(np.clip(rough,0,1)*255).astype('uint8')),
        ('Metallic',(np.clip(np.broadcast_to(metal,x.shape),0,1)*255).astype('uint8')),('Normal',((n*.5+.5)*255).astype('uint8'))]:
        p=TEX/(key+'_'+ch+'.png');Image.fromarray(arr).save(p);maps[ch]=str(p)
    recipes[key]={'maps':maps,'metallic':0,'roughness':.5}
base=np.array([65,77,69],dtype=np.float32)
for variant in range(3):
    edge=np.minimum(np.minimum(x,1-x),np.minimum(y,1-y))
    cutoff=.005+(small+fine*.2)*.004
    chip=np.clip((cutoff-edge)*700,0,1)*(small>.04)
    # Handling leaves localized grime around the pull, not large camouflage patches.
    oil=np.exp(-((x-.5)**2/.054+(y-.43)**2/.015))*(.7+.3*large)
    dust=np.clip((y-.87)*5,0,.7)*(.85+.15*large)
    sc=scratches(115)
    color=base+np.array([variant*2,variant,variant*1.3])+large[:,:,None]*1.3+small[:,:,None]*.8+fine[:,:,None]*.4
    color=color-oil[:,:,None]*9+dust[:,:,None]*8-sc[:,:,None]*11
    color=color*(1-chip[:,:,None])+np.array([82,80,71])[None,None,:]*chip[:,:,None]
    rough=.60+large*.025+small*.02+fine*.006-oil*.12+dust*.12-sc*.08-chip*.12
    save_surface('DrawerPaint'+str(variant),color,rough,chip*.78,(small*.000007+fine*.0000017)-chip*.00011-sc*.00002,(.172,.077))
save_surface('SheetPaint',base+large[:,:,None]*1.5+small[:,:,None]*.6+fine[:,:,None]*.5,
    .61+large*.025+small*.025+fine*.006,0,small*.000006+fine*.0000016)
sc=scratches(180)
oxide=np.clip((large+.35)*.13,0,.13)
for key,rgb,rough in [('ToolSteel',[88,95,92],.50),('GroundSteel',[143,148,146],.37)]:
    brushed=np.broadcast_to(R.normal(0,.6,(N,1)),x.shape).astype(np.float32)
    c=np.array(rgb)[None,None,:]+large[:,:,None]*3+small[:,:,None]*.6+brushed[:,:,None]*.8-sc[:,:,None]*10
    c=c*(1-oxide[:,:,None])
    save_surface(key,c,rough+large*.05+small*.015+sc*.13,.93-oxide*.9,fine*.0000009+brushed*.00000035-sc*.000005)
save_surface('Grip',np.array([29,32,30])[None,None,:]+large[:,:,None]*1.8+fine[:,:,None]*.7,
    .70+large*.04+small*.012,0,small*.000010+fine*.0000018)
save_surface('Bakelite',np.array([158,154,133])[None,None,:]+large[:,:,None]*2+small[:,:,None]*.5,
    .49+large*.045+small*.015,0,fine*.0000006)
recipes['Recess']={'color':[.008,.010,.009],'roughness':.87,'metallic':0}
recipes['Rust']={'color':[.060,.040,.022],'roughness':.87,'metallic':0}
recipes['ExposedEdge']={'color':[.14,.15,.14],'roughness':.54,'metallic':.80}
recipes['GroundPatch']={'color':[.26,.28,.27],'roughness':.41,'metallic':.94}
# Keep original CC0 scan channels intact; UVs follow the physical handle grain direction.
WOOD=ROOT.parent/'AKMIntegration20260910/Redwood/Wood051'
recipes['WoodGrip']={'maps':{},'metallic':0,'normal_strength':.16,'color_tint':[1.30,1.18,1.04],'roughness_scale':.76,'roughness_bias':.19}
for ch,suffix in [('BaseColor','Color'),('Roughness','Roughness'),('Normal','NormalGL')]:
    src=WOOD/('Wood051_2K-JPG_'+suffix+'.jpg');dest=TEX/('WoodGrip_'+ch+'.jpg');shutil.copy2(src,dest);recipes['WoodGrip']['maps'][ch]=str(dest)
# Reuse the existing licensed Quixel imperfection as a shader mask, not as a metallic map.
masksrc=ROOT.parent/'ChestZiarat20260909/Source/dirty_metal_rmmodbdp_4k__extracted/Textures/T_rmmodbdp_4K_MR.png'
mask=TEX/'MetalImperfection_MaskR_RoughnessG.png';shutil.copy2(masksrc,mask)
for key in ('ToolSteel','GroundSteel'):recipes[key]['imperfection_mask']=str(mask)
# Labels use authored dimensions; their UV boxes exactly match their physical aspect ratios.
atlas=Image.new('RGB',(2048,2048),(190,185,163));draw=ImageDraw.Draw(atlas);regions={}
FONT='C:/Windows/Fonts/consola.ttf';BOLD='C:/Windows/Fonts/consolab.ttf'
def tile(key,rect,title,subtitle):
    left,top,w,h=rect;draw.rectangle((left,top,left+w-1,top+h-1),fill=(197,191,168))
    draw.rectangle((left+3,top+3,left+w-4,top+h-4),outline=(108,110,96),width=2)
    big=ImageFont.truetype(BOLD,int(h*.33));sm=ImageFont.truetype(FONT,int(h*.19))
    draw.text((left+h*.13,top+h*.14),title,font=big,fill=(31,39,36))
    draw.text((left+h*.13,top+h*.60),subtitle,font=sm,fill=(57,64,57))
    for _ in range(int(w*h/350)):
        px=int(R.integers(left+4,left+w-4));py=int(R.integers(top+4,top+h-4))
        if R.random()<.22:draw.point((px,py),fill=(161,155,133))
    regions[key]={'rect':[left,top,w,h],'aspect':w/h}
tile('header',(32,32,1400,170),'M-04  /  MAINTENANCE','HAND TOOLS  -  RETURN AFTER USE')
parts=[('M6 HEX','BOLTS / ZINC'),('M8 HEX','BOLTS / STEEL'),('M10','HEX NUTS'),('M6 / M8','FLAT WASHERS'),('M4 / M5','MACHINE SCREWS'),('M6 / M8','LOCK WASHERS'),('8 - 12 mm','SPLIT PINS'),('CIRCLIPS','INTERNAL'),('O-RINGS','NBR / ASSORTED'),('BEARINGS','608 / 6201'),('FUSES','250 V / 5 A'),('SPARES','M-04 SERVICE')]
for i,(a,b) in enumerate(parts):tile('drawer'+str(i),(32+(i%4)*370,240+(i//4)*136,350,130),a,b)
for i,size in enumerate(('10 mm','12 mm','14 mm','17 mm','19 mm')):tile('tool'+str(i),(32+i*300,680,280,112),size,'COMBINATION')
tile('socket',(32,840,640,128),'230 V  /  16 A','SERVICE SUPPLY')
path=TEX/'Labels_BaseColor.png';atlas.save(path);recipes['Labels']={'maps':{'BaseColor':str(path)},'roughness':.83,'metallic':0,'label_atlas':True}
(OUT/'labels.json').write_text(json.dumps(regions,indent=2),encoding='utf-8')
(OUT/'material-manifest.json').write_text(json.dumps(recipes,indent=2),encoding='utf-8')
print('SURFACE_MATERIALS_AUTHORED',len(recipes),'NO_RENDER')
