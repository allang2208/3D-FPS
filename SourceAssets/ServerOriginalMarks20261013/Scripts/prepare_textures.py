"""Reference-led surface atlases: graphite, satin metal, black PCB and printed identities."""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
CAT=json.loads((PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json').read_text('utf-8'))
ITEMS={i['id']:i for i in CAT['items']}
SURFACES={
 'silver':([140,146,154],.34,.89,'satin'),
 'steel':([154,161,169],.27,.96,'brush'),
 'aluminum':([170,176,181],.30,.94,'brush'),
 'graphite':([38,41,45],.42,.62,'satin'),
 'plastic':([18,20,23],.37,0,'fine'),
 'blade':([22,24,27],.29,0,'fine'),
 'rubber':([14,16,18],.83,0,'fine'),
 'gold':([193,153,77],.28,.96,'brush'),
 'copper':([142,78,45],.30,.94,'brush'),
 'chip':([19,22,23],.56,0,'fine'),
 'solder':([172,179,179],.27,.95,'fine'),
 'ceramic':([87,73,51],.57,0,'fine'),
 'fr4':([37,37,31],.59,0,'fine'),
 'white':([190,194,193],.57,0,'fine'),
 'blue':([32,38,45],.53,0,'fine'),
 'thermal':([97,104,111],.90,0,'fine'),
}
REGIONS={k:[i%8*512,i//8*512,(i%8+1)*512,(i//8+1)*512] for i,k in enumerate(SURFACES)}
REGIONS.update(pcb=[0,1152,3072,2176],primary=[0,2432,3072,3046],
               secondary=[0,3200,3072,3814],hub=[3200,1152,3968,1920],
               chipmark=[3200,2048,3968,2322],barcode=[3200,2432,3968,2576],
               silkscreen=[3200,2816,3968,2960],etch=[3200,3200,3968,3474])
IDS={'GPU':'search_graphics_card','RAM':'search_ram_module','SSD':'search_ssd'}
NAMES={'GPU':'SM_Search_TripleFanGPU_CSR3B','RAM':'SM_Search_ArmoredRAM_CSR3B','SSD':'SM_Search_M2SSD_CSR3B'}
DIMS={'GPU':[32.3,12.5,5.4],'RAM':[13.4,3.45,.76],'SSD':[8,2.2,.29]}
FONTS={'regular':'arial.ttf','bold':'arialbd.ttf','italic':'arialbi.ttf'}
def font(size,kind='regular'):return ImageFont.truetype('C:/Windows/Fonts/'+FONTS[kind],max(8,int(size)))
def txt(d,xy,s,size,fill=(181,184,185),kind='regular',anchor=None):d.text(xy,s,font=font(size,kind),fill=fill,anchor=anchor)
def rect(k):return REGIONS[k]
def pcb_art(key,w,h):
    image=Image.new('RGB',(w,h),(21,24,25));d=ImageDraw.Draw(image)
    rng=np.random.default_rng(154+sum(map(ord,key)))
    for j in range(110):
        x=float(rng.uniform(.025,.965))*w;y=float(rng.uniform(.035,.93))*h
        dx=float(rng.uniform(.016,.075))*w;dy=float(rng.uniform(-.17,.17))*h
        pts=[(x,y),(x+dx*.38,y),(x+dx*.66,y+dy),(x+dx,y+dy)]
        d.line(pts,fill=(30,36,35),width=max(1,w//1100))
        r=max(1,w//950);xx,yy=pts[-1]
        d.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(131,130,106));d.ellipse((xx-r*.4,yy-r*.4,xx+r*.4,yy+r*.4),fill=(16,18,18))
    for j in range(50):
        x=float(rng.uniform(.025,.94))*w;y=float(rng.uniform(.02,.96))*h
        txt(d,(x,y),('C' if j%2 else 'R')+str(100+j),min(h*.035,18),(154,165,160))
    txt(d,(w*.10,h*.10),'CS-S2 / REV 03' if key=='SSD' else 'CS BOARD / REV 03',h*.07,(162,170,160))
    return np.array(image)

def emblem(d,cx,cy,size,fill):
    # Project-designed offset rails: no borrowed wordmark, symbol or font treatment.
    for row in range(3):
        x=cx-size*.45+row*size*.13;y=cy-size*.34+row*size*.25
        d.rounded_rectangle((x,y,x+size*.65,y+size*.12),radius=max(1,int(size*.018)),fill=fill)

def art(key,region,w,h):
    base=(29,31,34) if key=='RAM' else (19,20,22)
    if region=='hub':base=(177,182,187)
    image=Image.new('RGB',(w,h),base);d=ImageDraw.Draw(image)
    if region=='hub':
        d.ellipse((w*.04,h*.04,w*.96,h*.96),outline=(69,72,74),width=max(2,w//140))
        emblem(d,w*.5,h*.42,h*.49,(37,38,40))
        txt(d,(w*.5,h*.73),'COLD STEEL',h*.077,(45,47,48),'bold','mm')
    elif region=='primary' and key=='RAM':
        emblem(d,w*.10,h*.43,h*.61,(188,192,193))
        txt(d,(w*.19,h*.27),'COLD STEEL',h*.205,(198,201,202),'bold')
        txt(d,(w*.19,h*.55),'FACILITY MEMORY',h*.086,(128,137,140))
        txt(d,(w*.775,h*.43),'CS-D4',h*.30,(215,218,218),'bold','mm')
        txt(d,(w*.948,h*.11),'DDR4',h*.12,(209,212,212),'bold','rm')
        for x in (.62,.66,.70):d.line([(w*x,h*.70),(w*(x+.035),h*.83)],fill=(48,53,57),width=max(2,int(h*.02)))
    elif region=='primary' and key=='SSD':
        emblem(d,w*.067,h*.26,h*.27,(188,193,191))
        txt(d,(w*.112,h*.12),'COLD STEEL',h*.115,(217,220,217),'bold')
        txt(d,(w*.035,h*.34),'CS-S2',h*.30,(230,232,230),'bold')
        txt(d,(w*.041,h*.83),'PCIe NVMe  M.2',h*.066,(167,176,173),'regular')
        txt(d,(w*.40,h*.73),'FACILITY SOLID STATE STORAGE',h*.064,(135,144,141),'regular')
        txt(d,(w*.40,h*.86),'CS-S2  /  BOARD REV 03',h*.056,(111,120,119),'regular')
    elif region=='primary':
        emblem(d,w*.071,h*.50,h*.59,(172,180,183))
        txt(d,(w*.15,h*.19),'COLD STEEL',h*.29,(189,196,198),'bold')
        txt(d,(w*.15,h*.66),'CS-G3 / GRAPHICS PROCESSOR',h*.12,(141,151,155),'bold')
    elif region=='secondary':
        txt(d,(w*.04,h*.10),{'GPU':'COLD STEEL CS-G3 / GRAPHICS','RAM':'COLD STEEL CS-D4 / DDR4','SSD':'COLD STEEL CS-S2 / NVMe'}[key],h*.18,(163,170,172),'bold')
        txt(d,(w*.04,h*.44),'SERIAL 0427-0816 / BOARD REV 04',h*.11,(131,141,143))
        txt(d,(w*.04,h*.76),'FACILITY SERVICE INVENTORY',h*.08,(110,119,123))
    elif region in ('chipmark','etch'):
        txt(d,(w*.07,h*.11),'CS / FACILITY IC',h*.15,(105,113,112),'bold')
        txt(d,(w*.07,h*.41),'CS-M08 / 0427',h*.12,(80,91,90))
        txt(d,(w*.07,h*.73),'REV C  /  427',h*.09,(73,80,79))
    elif region=='silkscreen':
        txt(d,(w*.06,h*.10),'CS-G3' if key=='GPU' else 'DDR4' if key=='RAM' else 'NVMe M.2',h*.50,(164,175,179),'bold')
    else:
        rng=np.random.default_rng(310)
        image=Image.new('RGB',(w,h),(181,190,188));d=ImageDraw.Draw(image);x=w*.04
        while x<w*.96:
            bar=int(rng.integers(1,4));d.rectangle((x,h*.12,x+bar,h*.67),fill=(31,39,40));x+=bar+int(rng.integers(1,4))
        txt(d,(w*.5,h*.87),'0427-0816  '+key,h*.14,(31,39,40),anchor='mm')
    return np.array(image)

manifest=dict(assets={},regions=REGIONS,reference_images={k:str(PROJECT/'SourceAssets/ServerReferenceRemodel20261013/Reference'/(k+'.png')) for k in IDS},
    source='User-provided single front reference per item; concealed rear geometry inferred',
    texture_convention='BaseColor sRGB; ORM R AO G roughness B metallic linear; normal OpenGL +Y',
    branding='Project-authored offset-rail emblem; COLD STEEL / CS-G3 / CS-D4 / CS-S2. Reference brand, series, part-code and country markings replaced on all produced surfaces.',
    runtime_tested=False,preview_rendered=False)
for key,identifier in IDS.items():
    item=ITEMS[identifier];ratio=DIMS[key][0]/DIMS[key][1]
    REGIONS['pcb']=[0,1152,3072,1152+round(3072/ratio)]
    label_ratio={'GPU':6.9,'RAM':13.4/2.83,'SSD':4.60}[key]
    REGIONS['primary']=[0,2432,3072,2432+round(3072/label_ratio)]
    size=4096;rng=np.random.default_rng(sum(map(ord,key))+790)
    base=np.full((size,size,3),22,np.uint8);orm=np.empty((size,size,3),np.uint8);orm[:]=[255,160,0]
    normal=np.empty((size,size,3),np.uint8);normal[:]=[128,128,255]
    for region,(rgb,rough,metal,kind) in SURFACES.items():
        x0,y0,x1,y1=rect(region);height,width=y1-y0,x1-x0
        field=rng.normal(0,1,(height,width)).astype(np.float32)
        if kind=='brush':field=field*.28+rng.normal(0,1,(height,1))*.70
        elif kind=='satin':field*=.60
        else:field*=.45
        base[y0:y1,x0:x1]=np.clip(np.array(rgb)[None,None,:]+field[:,:,None]*1.4,0,255).astype(np.uint8)
        orm[y0:y1,x0:x1,1]=np.clip((rough+field*.014)*255,0,255).astype(np.uint8);orm[y0:y1,x0:x1,2]=int(metal*255)
        dy,dx=np.gradient(field*.005);n=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
        normal[y0:y1,x0:x1]=np.clip((n*.5+.5)*255,0,255).astype(np.uint8)
    for region in ('pcb','primary','secondary','hub','chipmark','barcode','silkscreen','etch'):
        x0,y0,x1,y1=rect(region);pixels=pcb_art(key,x1-x0,y1-y0) if region=='pcb' else art(key,region,x1-x0,y1-y0)
        base[y0:y1,x0:x1]=pixels
        rough=.49 if region=='pcb' else .48 if region=='hub' else .62 if key=='SSD' else .45
        orm[y0:y1,x0:x1]=[255,int(rough*255),0]
        if key=='RAM' and region=='primary':
            ink=pixels.mean(axis=-1)>90;orm[y0:y1,x0:x1,2]=np.where(ink,90,140).astype(np.uint8)
            orm[y0:y1,x0:x1,1]=np.where(ink,93,122).astype(np.uint8)
    paths={}
    for kind,pixels in (('BaseColor',base),('ORM',orm),('Normal',normal)):
        path=ROOT/'Textures'/f'T_SR_{key}_{kind}.png';Image.fromarray(pixels).save(path,compress_level=6);paths[kind]=str(path)
    manifest['assets'][key]=dict(id=identifier,name=item['name'],mesh=NAMES[key],material='M_SR_'+key,size=size,
        dimensions=DIMS[key],textures=paths,regions={k:list(v) for k,v in REGIONS.items()},
        grid_w=item['grid_w'],grid_h=item['grid_h'],rarity=item['rarity'],max_stack=item['max_stack'],sell_souls=item['sell_souls'])
    print('REFERENCE_PBR_SAVED',key,flush=True)
(ROOT/'texture_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
