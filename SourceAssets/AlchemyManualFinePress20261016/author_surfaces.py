"""Author layered paper and woven-cloth PBR from the editable material recipe."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Textures'
rng=np.random.default_rng(161005);records=[]
def save(array,name,kind='color',ui=False):
    im=array if isinstance(array,Image.Image) else Image.fromarray(np.asarray(array).clip(0,255).astype('uint8'))
    path=OUT/(name+'.png');im.save(path);records.append(dict(name=name,file=str(path),kind=kind,ui=ui))
def normal(height,amount):
    # Smooth height before differentiation, avoiding sparkling high-frequency normals.
    h=np.asarray(Image.fromarray((height*255).clip(0,255).astype('uint8')).filter(ImageFilter.GaussianBlur(.7)),dtype=float)/255
    dy,dx=np.gradient(h);n=np.stack((-dx*amount,dy*amount,np.ones_like(h)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return (n*.5+.5)*255
def noise(w,h,scale):
    small=Image.fromarray(rng.integers(0,255,(max(2,h//scale),max(2,w//scale)),dtype='uint8'))
    return np.asarray(small.resize((w,h),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(1.5)),dtype=float)/255-.5

w,h=2048,1536;y,x=np.mgrid[0:h,0:w];px=x%1024
macro=noise(w,h,100);fine=noise(w,h,5)
edge=np.minimum.reduce([px/1024,(1023-px)/1024,y/h,(h-1-y)/h])
wear=4.2*np.exp(-edge*45)
tone=macro*4.0+fine*1.1-wear
paper=np.stack([238+tone,231+tone,211+tone],axis=-1)
# Subtle deckle tint; no rectangular border or large coffee stains.
save(paper,'T_ManualPaper',ui=True)
s=1024;yy,xx=np.mgrid[0:s,0:s]
fiber=.5+.28*noise(s,s,5)+.12*noise(s,s,40)+.018*np.sin(yy*.9+xx*.17)
save(normal(fiber,1.6),'T_ManualPaperNormal','normal')
rough=(.84+.05*noise(s,s,48)+.018*noise(s,s,4))*255
save(rough,'T_ManualPaperRoughness','mask')

# Each atlas half is one bookmark. Warp/weft use the same height as its normal.
weave=.5+.12*np.sin(xx*math.pi/3)+.10*np.sin(yy*math.pi/4)+.06*np.sin((xx+yy)*math.pi/4)
cloth=np.zeros((s,s,3),dtype=float)
for half,color in [(0,(77,39,39)),(1,(39,64,54))]:
    a,b=half*512,(half+1)*512
    cloth[:,a:b,:]=np.array(color)+(weave[:,a:b,None]-.5)*12+noise(512,s,50)[:,:,None]*5
im=Image.fromarray(cloth.clip(0,255).astype('uint8'));d=ImageDraw.Draw(im)
font=ImageFont.truetype(str(PROJECT/'Content/UI/AlchemyManual/Fonts/FolioSerif-Semibold.ttf'),112)
for side,label in enumerate(('首页','末页')):
    start=side*512
    for edge_x in (start+26,start+486):
        d.line((edge_x,0,edge_x,1024),fill=(118,91,62),width=3)
        for j in range(0,1024,18):d.line((edge_x+5,j,edge_x+5,j+8),fill=(165,141,99),width=2)
    # Intentionally small woven label with air around it; no flat button rectangle.
    d.text((start+256,300),label,font=font,fill=(211,189,140),anchor='mm',stroke_width=0)
    d.line((start+184,403,start+328,403),fill=(150,124,82),width=2)
save(im,'T_ManualBookmarks')
save(normal(weave,1.1),'T_ManualRibbonNormal','normal')
save((.66+.10*(weave-.5)+.025*noise(s,s,20))*255,'T_ManualRibbonRoughness','mask')

# Edge grain represents tightly stacked sheets, not heavy dark stripes.
ew,eh=1024,512;ey,ex=np.mgrid[0:eh,0:ew]
layers=1.5*np.sin(ey*2.3+np.sin(ex/103)*.35)+.9*np.sin(ey*.87+ex/300)
et=layers+noise(ew,eh,25)*3
save(np.stack([222+et,212+et,187+et],axis=-1),'T_ManualPageEdges')
save(normal(.5+layers*.015,1.1),'T_ManualEdgeNormal','normal')

# Reuse item identity at its original fidelity; no painted UI framing.
recipes=json.loads((PROJECT/'Content/ColdSteelData/alchemy-recipes.json').read_text(encoding='utf-8-sig'))['recipes']
items=json.loads((PROJECT/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
ids=sorted({r['output'] for r in recipes}|{i['item'] for r in recipes for i in r['inputs']})
for key in ids:
    im=Image.open(PROJECT/'Content/ColdSteelData'/items[key]['ue_icon']).convert('RGBA')
    box=im.getbbox()
    if box:im=im.crop(box)
    im.thumbnail((384,384),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(384,384));canvas.alpha_composite(im,((384-im.width)//2,(384-im.height)//2))
    save(canvas,'T_Manual_'+key,ui=True)
(ROOT/'artwork.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
header='#pragma once\n#include "CoreMinimal.h"\n#include "UObject/SoftObjectPath.h"\nnamespace AlchemyManualArtwork {\n'
header+='inline FSoftObjectPath Texture(const FString& Name) {const FString N=TEXT("T_Manual")+Name;return FSoftObjectPath(TEXT("/Game/Building/PotionWorkbench20261015/ManualV5/Textures/")+N+TEXT(".")+N);}\n'
header+='inline void Gather(TArray<FSoftObjectPath>& Paths) {\n'
for record in records:
    if record['ui']:header+='Paths.Add(Texture(TEXT("'+record['name'][len('T_Manual'):]+'")));\n'
header+='}\n}\n'
(ROOT/'AlchemyManualArtwork.h').write_text(header,encoding='utf-8')
print('Authored paper, cloth and page-edge surfaces:',len(records))
