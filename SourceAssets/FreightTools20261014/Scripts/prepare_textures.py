"""Author original, deterministic industrial surface atlases. No preview rendering."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
OUT = ROOT / 'Textures'
OUT.mkdir(parents=True, exist_ok=True)
FONT = PROJECT / 'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
# These are linear reflectance values, encoded to sRGB once on output.
SURFACES = {
    'teal': ((.025,.105,.115),.43,0,'polymer'),
    'orange': ((.68,.185,.027),.46,0,'polymer'),
    'rubber': ((.012,.016,.019),.77,0,'rubber'),
    'plastic': ((.027,.034,.039),.51,0,'polymer'),
    'steel': ((.51,.55,.59),.25,.96,'brushed'),
    'satin': ((.48,.51,.54),.39,.94,'brushed'),
    'blacksteel': ((.065,.075,.085),.36,.87,'brushed'),
    'foam': ((.017,.020,.023),.91,0,'foam'),
    'screen': ((.075,.125,.104),.19,0,'screen'),
    'lcdink': ((.012,.025,.021),.34,0,'screen'),
    'white': ((.72,.76,.73),.50,0,'polymer'),
    'red': ((.45,.022,.018),.56,0,'rubber'),
    'gold': ((.62,.39,.11),.28,.95,'brushed'),
    'green': ((.05,.32,.08),.29,0,'screen'),
    'fabric': ((.032,.037,.041),.86,0,'fabric'),
    'aluminum': ((.61,.64,.67),.33,.98,'brushed'),
}
REGIONS = {name:[i%8*512,i//8*512,i%8*512+512,i//8*512+512] for i,name in enumerate(SURFACES)}
REGIONS.update(front=[0,1024,2048,4096],badge=[2048,1024,4096,2048],serial=[2048,2048,4096,2816],
               scale=[2048,2816,3072,3840],lcd=[3072,2816,4096,3328],controls=[3072,3328,4096,3840],etch=[2048,3840,4096,4096])
ASSETS = {
    'Multimeter':dict(id='search_industrial_multimeter',name='工业数字万用表',code='DM-620',mesh='SM_Freight_IndustrialMultimeter'),
    'ToolKit':dict(id='search_precision_tool_kit',name='精密检修工具组',code='TK-24',mesh='SM_Freight_PrecisionToolKit'),
    'ImpactWrench':dict(id='search_cordless_impact_wrench',name='充电式冲击扳手',code='IW-18',mesh='SM_Freight_CordlessImpactWrench'),
}

def srgb(x):
    x=np.clip(x,0,1)
    return np.where(x<=.0031308,x*12.92,1.055*np.power(x,1/2.4)-.055)

def font(s): return ImageFont.truetype(str(FONT),max(8,int(s)))
def write(d,xy,t,size,ink=(207,216,212),anchor=None): d.text(xy,t,font=font(size),fill=ink,anchor=anchor)

def artwork(key,region,w,h):
    bg=(46,52,56) if region not in ('lcd','serial') else (88,105,94) if region=='lcd' else (194,200,191)
    im=Image.new('RGB',(w,h),bg);d=ImageDraw.Draw(im)
    a=ASSETS[key];ink=(213,221,214);dark=(29,36,39);accent=(223,138,53)
    if region=='front':
        write(d,(w*.08,h*.015),'CS  /  COLD STEEL',w*.070)
        write(d,(w*.08,h*.071),'INDUSTRIAL '+a['code'],w*.047,accent)
        # Faceplate text positions are authored in the same coordinate system as the shell.
        write(d,(w*.50,h*.29),'HOLD     RANGE     SELECT',w*.034,ink,'mm')
        write(d,(w*.50,h*.77),'TRUE RMS  /  FIELD SERVICE',w*.035,ink,'mm')
        for u,s in ((.18,'10 A'),(.50,'COM'),(.82,'V / OHM')):
            write(d,(w*u,h*.815),s,w*.042,accent if s!='COM' else ink,'mm')
        write(d,(w*.50,h*.955),'FUSED INPUTS  /  CS DM-620',w*.028,ink,'mm')
    elif region=='scale':
        cx,cy=w*.5,h*.5
        for j,label in enumerate(['OFF','V~','V=','mV','OHM','DIODE','Hz','CAP','mA','A=','A~','TEMP']):
            t=np.deg2rad(90-j*30)
            x=cx+np.cos(t)*w*.405;y=cy-np.sin(t)*h*.405
            write(d,(x,y),label,w*.045,accent if j==0 else ink,'mm')
            x0=cx+np.cos(t)*w*.31;y0=cy-np.sin(t)*h*.31
            x1=cx+np.cos(t)*w*.345;y1=cy-np.sin(t)*h*.345
            d.line((x0,y0,x1,y1),fill=ink,width=3)
    elif region=='badge':
        d.rounded_rectangle((w*.025,h*.05,w*.975,h*.95),radius=h*.10,outline=(101,116,117),width=5)
        write(d,(w*.07,h*.12),'CS',h*.34,accent)
        write(d,(w*.30,h*.16),'COLD STEEL',h*.16)
        write(d,(w*.30,h*.48),a['code']+' / SERVICE EQUIPMENT',h*.085)
        write(d,(w*.07,h*.78),'MAINTENANCE DIVISION  /  PRECISION SERIES',h*.058)
    elif region=='serial':
        write(d,(w*.035,h*.06),'COLD STEEL  /  '+a['code'],h*.125,dark)
        write(d,(w*.035,h*.24),{'Multimeter':'FUSED / SERVICEABLE BATTERY COMPARTMENT','ToolKit':'CHROME-VANADIUM / DRY STORAGE','ImpactWrench':'18 V / BRUSHLESS / 1/2 IN SQUARE DRIVE'}[key],h*.07,dark)
        write(d,(w*.035,h*.39),'SERVICE LOT 26-104  /  SERIAL CS-014820',h*.07,dark)
        rng=np.random.default_rng(40+len(key));x=int(w*.04)
        while x<w*.94:
            bw=int(rng.integers(2,7));d.rectangle((x,h*.55,x+bw,h*.81),fill=dark);x+=bw+int(rng.integers(3,8))
        write(d,(w*.50,h*.92),'CS  0 1 4 8 2 0  6 2 0',h*.07,dark,'mm')
    elif region=='lcd':
        write(d,(w*.05,h*.07),'AUTO',h*.15,(28,46,35))
        write(d,(w*.84,h*.18),'V',h*.15,(28,46,35))
        for j in range(30):d.rectangle((w*(.06+j*.029),h*.84,w*(.06+j*.029)+w*.015,h*.88),fill=(40,58,44))
        write(d,(w*.07,h*.95),'0          20          40          60',h*.065,(28,46,35),'lm')
    elif region=='controls':
        write(d,(w*.50,h*.26),'18 V   /   4.0 Ah',h*.19,ink,'mm')
        write(d,(w*.50,h*.61),'LITHIUM  /  CS POWER',h*.11,accent,'mm')
        write(d,(w*.50,h*.86),'PRESS TO CHECK',h*.07,ink,'mm')
    else:
        write(d,(w*.50,h*.47),'CS  /  Cr-V  /  PRECISION TOOLING',h*.31,(93,103,110),'mm')
    return np.array(im)

result={'version':1,'size':4096,'regions':REGIONS,'assets':{},'normal_convention':'OpenGL +Y; UE flips green','surface_source':'Original authored industrial micro-surfaces and original CS markings'}
for key,a in ASSETS.items():
    base=np.full((4096,4096,3),35,dtype=np.uint8)
    orm=np.empty_like(base);orm[:]=(255,150,0)
    normal=np.empty_like(base);normal[:]=(128,128,255)
    rng=np.random.default_rng(20261014+sum(map(ord,key)))
    for region,(color,rough,metal,kind) in SURFACES.items():
        x0,y0,x1,y1=REGIONS[region];w=x1-x0;h=y1-y0
        grain=rng.normal(0,1,(h,w)).astype(np.float32)
        blurred=np.array(Image.fromarray(np.uint8(np.clip(grain*18+128,0,255))).filter(ImageFilter.GaussianBlur(1.4)),dtype=np.float32)/255-.5
        yy,xx=np.mgrid[:h,:w]
        height=blurred*(.45 if kind=='foam' else .16)
        if kind=='brushed':height+=.012*np.sin(yy*.9)+.006*np.sin(yy*2.2)
        if kind=='fabric':height+=.018*np.sin(xx*.6)*np.sin(yy*.6)
        if kind=='rubber':height+=.012*np.cos(xx*.45)*np.cos(yy*.45)
        strength=.08 if kind=='screen' else .85
        gy,gx=np.gradient(height*strength)
        n=np.stack((-gx,gy,np.ones_like(gx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
        normal[y0:y1,x0:x1]=np.uint8(np.clip((n*.5+.5)*255,0,255))
        variation=1+blurred[...,None]*(.18 if kind=='foam' else .065)
        base[y0:y1,x0:x1]=np.uint8(srgb(np.array(color)[None,None,:]*variation)*255)
        orm[y0:y1,x0:x1,0]=255
        orm[y0:y1,x0:x1,1]=np.uint8(np.clip(rough+blurred*.06,0,1)*255)
        orm[y0:y1,x0:x1,2]=int(metal*255)
    for region in ('front','badge','serial','scale','lcd','controls','etch'):
        x0,y0,x1,y1=REGIONS[region]
        base[y0:y1,x0:x1]=artwork(key,region,x1-x0,y1-y0)
        orm[y0:y1,x0:x1]=(255,65 if region=='lcd' else 155,190 if region=='etch' else 0)
    textures={}
    for kind,data in [('BaseColor',base),('ORM',orm),('Normal',normal)]:
        path=OUT/f'T_FT_{key}_{kind}.png';Image.fromarray(data).save(path);textures[kind]=str(path)
    result['assets'][key]={**a,'material':'M_Freight_'+key,'size':4096,'textures':textures}
    print('FREIGHT_TEXTURES_SAVED',key,flush=True)
(ROOT/'texture_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
