"""Original PCB artwork and industrial PBR atlases for eight server collectibles."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'Textures'
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
SURFACES={
 'steel':([145,154,163],.31,.95,'brushed'),
 'aluminum':([186,190,192],.34,.95,'brushed'),
 'gold':([190,147,64],.28,.93,'fine'),
 'copper':([164,87,46],.33,.96,'fine'),
 'plastic':([35,40,44],.46,0,'fine'),
 'rubber':([20,23,25],.79,0,'fine'),
 'chip':([24,29,29],.55,0,'fine'),
 'ceramic':([104,89,68],.62,0,'fine'),
 'fr4':([60,92,65],.64,0,'laminate'),
 'blue':([43,65,78],.52,0,'fine'),
 'white':([188,191,174],.71,0,'fine'),
 'solder':([169,173,168],.36,.91,'fine'),
 'paper':([226,225,213],.82,0,'paper'),
 'thermal':([109,122,134],.89,0,'fine'),
 'red':([105,30,26],.56,0,'fine'),
 'green':([41,106,59],.46,0,'fine'),
}
REGIONS={name:[(i%8)*512,(i//8)*512,(i%8+1)*512,(i//8+1)*512] for i,name in enumerate(SURFACES)}
REGIONS.update(pcb=[0,1024,2048,2560],primary=[2176,1024,3968,1792],
               secondary=[2176,1920,3968,2688],barcode=[0,2816,2048,3200],
               chipmark=[2176,2816,3968,3456],silkscreen=[0,3328,2048,4096],etch=[2176,3584,3968,4096])
IDS={'RAM':'search_ram_module','NIC':'search_network_card','HDD':'search_hard_disk','SSD':'search_ssd',
     'CPU':'search_processor','GPU':'search_graphics_card','RAID':'search_raid_controller','Compute':'search_compute_accelerator'}
MESHES={'RAM':'ServerRAM','NIC':'ServerNIC','HDD':'HardDisk','SSD':'SSD','CPU':'ServerCPU',
        'GPU':'GraphicsCard','RAID':'RAIDController','Compute':'ComputeAccelerator'}
LINES={'RAM':('ECC REGISTERED MEMORY','RM-0427 / 32G'),
       'NIC':('DUAL PORT SERVER ADAPTER','NET-204 / REV C'),
       'HDD':('ENTERPRISE STORAGE DRIVE','HD-407 / 8TB'),
       'SSD':('SOLID STATE STORAGE','SSD-128 / 2TB'),
       'CPU':('SERVER PROCESSOR','CP-624 / REV B'),
       'GPU':('GRAPHICS PROCESSOR MODULE','GX-240 / DUAL FAN'),
       'RAID':('STORAGE ARRAY CONTROLLER','RA-806 / CACHE MODULE'),
       'Compute':('PASSIVE COMPUTE ACCELERATOR','CA-640 / SERVER MODULE')}
CAT=json.loads((PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json').read_text('utf-8'))
ITEMS={i['id']:i for i in CAT['items']}
def font(size):return ImageFont.truetype(str(FONT),max(8,int(size)))
def write(d,pos,s,size,color=(37,45,46),anchor=None):d.text(pos,s,font=font(size),fill=color,anchor=anchor)
def rect(region,size):return tuple(round(v*size/4096) for v in REGIONS[region])

def pcb_art(key,w,h):
    # Non-functional original board artwork: visible masked traces, vias and markings.
    im=Image.new('RGB',(w,h),(27,76,48));d=ImageDraw.Draw(im)
    rng=np.random.default_rng(917+sum(map(ord,key)))
    for j in range(74):
        x=float(rng.uniform(.03,.9))*w;y=float(rng.uniform(.05,.93))*h
        dx=float(rng.uniform(.025,.14))*w;dy=float(rng.uniform(-.16,.16))*h
        pts=[(x,y),(x+dx*.40,y),(x+dx*.40+abs(dy)*.30,y+dy*.45),(x+dx,y+dy*.45)]
        d.line(pts,fill=(39,91,60),width=max(1,round(w*.0012)))
        r=max(1,round(w*.0015));xe,ye=pts[-1]
        d.ellipse((xe-r,ye-r,xe+r,ye+r),fill=(155,145,94))
        d.ellipse((xe-r*.43,ye-r*.43,xe+r*.43,ye+r*.43),fill=(31,60,37))
    for j in range(22):
        x=float(rng.uniform(.03,.91))*w;y=float(rng.uniform(.09,.88))*h
        width=w*.03;height=min(h*.12,w*.021)
        d.rectangle((x,y,x+width,y+height),outline=(154,180,145),width=max(1,w//1000))
        write(d,(x,y-height*.77),('R' if j%2 else 'C')+str(101+j),height*.60,(169,190,155))
    write(d,(w*.035,h*.06),'CS '+key.upper()+'  PCB REV 03',min(w*.018,h*.08),(185,200,169))
    write(d,(w*.60,h*.86),'94V-0  /  LOT 0427',min(w*.013,h*.065),(163,185,151))
    return np.array(im)

def label(key,region,w,h):
    dark=region in ('chipmark','silkscreen')
    im=Image.new('RGB',(w,h),(145,154,163) if region=='etch' else (24,29,29) if dark else (224,226,215));d=ImageDraw.Draw(im)
    ink=(168,177,174) if dark else (36,44,47);accent=(51,80,87)
    english,serial=LINES[key];name=ITEMS[IDS[key]]['name']
    if region=='etch':
        write(d,(w*.06,h*.08),'CS '+english,h*.18,(54,62,66))
        write(d,(w*.06,h*.43),serial,h*.16,(54,62,66))
        write(d,(w*.06,h*.76),'LOT 0427  /  FACILITY COMPUTING',h*.10,(65,73,75))
    elif region=='barcode':
        rng=np.random.default_rng(sum(map(ord,key)))
        x=w*.04
        while x<w*.96:
            bar=int(rng.integers(1,4))*max(1,w//480)
            d.rectangle((x,h*.10,x+bar,h*.65),fill=ink);x+=bar+int(rng.integers(1,4))*max(1,w//480)
        write(d,(w*.5,h*.87),'CS-'+key.upper()+'-0427-0816',h*.16,ink,'mm')
    elif region=='chipmark':
        write(d,(w*.10,h*.12),'CS SEMICONDUCTOR',h*.13,ink)
        write(d,(w*.10,h*.43),key.upper()+' / 427-C',h*.18,ink)
        write(d,(w*.10,h*.78),'ASSEMBLED 2408',h*.10,ink)
    elif region=='silkscreen':
        write(d,(w*.06,h*.13),'CS  /  '+key.upper(),h*.19,ink)
        write(d,(w*.06,h*.47),'FACILITY COMPUTING',h*.11,ink)
        write(d,(w*.06,h*.72),'SERVICE MODULE / 0427',h*.085,ink)
    else:
        if region=='primary':
            write(d,(w*.055,h*.07),'COLD STEEL / DATA SERVICES',h*.085,accent)
            write(d,(w*.055,h*.27),name,h*.23,ink)
            write(d,(w*.055,h*.60),english,h*.08,ink)
            write(d,(w*.055,h*.80),serial,h*.077,ink)
        else:
            write(d,(w*.05,h*.07),serial,h*.12,ink)
            write(d,(w*.05,h*.34),'设备资产 / SERVICE INVENTORY',h*.093,ink)
            write(d,(w*.05,h*.60),'设施计算中心   LOT 0427',h*.09,ink)
            write(d,(w*.05,h*.82),'ORIGINAL INDUSTRIAL PROP',h*.07,accent)
    return np.array(im)

manifest=dict(assets={},regions=REGIONS,authorship='Original geometry and graphics; project Noto Sans SC font',
    texture_convention='BaseColor sRGB; ORM linear R AO G roughness B metallic; normal OpenGL +Y',
    references=[
        'https://www.kingston.com/dataSheets/KF556C40BBK2-32.pdf',
        'https://www.intel.com/content/dam/www/public/us/en/documents/product-briefs/ethernet-i350-server-adapter-brief.pdf',
        'https://www.broadcom.com/products/storage/raid-controllers/megaraid-9560-16i'],
    reference_use='Structural reference only; no third-party mesh, texture, logo or working circuit reproduced',
    runtime_tested=False,preview_rendered=False)
for key,identifier in IDS.items():
    item=ITEMS[identifier];dims=item['model']['dimensions_lwh_cm'];ratio=dims[0]/dims[1]
    w=min(2048,round(1536*ratio));h=round(w/ratio);REGIONS['pcb']=[0,1024,w,1024+h]
    # Artwork islands follow their physical label proportions.
    secondary_ratio=8.38/2.16 if key=='HDD' else 1792/768
    REGIONS['secondary']=[2176,1920,3968,1920+round(1792/secondary_ratio)]
    barcode_ratio={'HDD':8.38/1.12,'SSD':7.15/1.20}.get(key,2048/384)
    REGIONS['barcode']=[0,2816,2048,2816+round(2048/barcode_ratio)]
    side_ratio={'GPU':10.9/1.08,'Compute':14.6/1.60}.get(key,2048/768)
    REGIONS['silkscreen']=[0,3328,2048,3328+round(2048/side_ratio)]
    size=4096 if key in ('NIC','GPU','RAID','Compute') else 2048
    rng=np.random.default_rng(803+sum(map(ord,key)))
    base=np.full((size,size,3),30,np.uint8);orm=np.empty((size,size,3),np.uint8);orm[:]=[255,170,0]
    normal=np.empty((size,size,3),np.uint8);normal[:]=[128,128,255]
    for region,(rgb,rough,metal,kind) in SURFACES.items():
        x0,y0,x1,y1=rect(region,size);height,width=y1-y0,x1-x0
        field=rng.normal(0,1,(height,width)).astype(np.float32)
        field=field*.23+rng.normal(0,1,(height,1))*.8 if kind=='brushed' else field*.55
        base[y0:y1,x0:x1]=np.clip(np.array(rgb)[None,None,:]+field[:,:,None]*1.35,0,255).astype(np.uint8)
        orm[y0:y1,x0:x1,1]=np.clip((rough+field*.013)*255,0,255).astype(np.uint8)
        orm[y0:y1,x0:x1,2]=int(metal*255)
        dy,dx=np.gradient(field*.006);n=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
        normal[y0:y1,x0:x1]=np.clip((n*.5+.5)*255,0,255).astype(np.uint8)
    for region in ('pcb','primary','secondary','barcode','chipmark','silkscreen','etch'):
        x0,y0,x1,y1=rect(region,size)
        base[y0:y1,x0:x1]=pcb_art(key,x1-x0,y1-y0) if region=='pcb' else label(key,region,x1-x0,y1-y0)
        orm[y0:y1,x0:x1]=[255,150 if region in ('pcb','chipmark','silkscreen') else 205,0]
        if region=='etch':orm[y0:y1,x0:x1]=[255,85,240]
    paths={}
    for suffix,array in (('BaseColor',base),('ORM',orm),('Normal',normal)):
        path=OUT/f'T_SE_{key}_{suffix}.png';Image.fromarray(array).save(path,compress_level=6);paths[suffix]=str(path)
    manifest['assets'][key]=dict(id=identifier,name=item['name'],mesh='SM_Search_'+MESHES[key],material='M_SE_'+key,
        size=size,dimensions=dims,textures=paths,regions={k:list(v) for k,v in REGIONS.items()},
        grid_w=item['grid_w'],grid_h=item['grid_h'],max_stack=item['max_stack'],rarity=item['rarity'],sell_souls=item['sell_souls'])
    print('SERVER_PBR_SAVED',key,size,flush=True)
(ROOT/'texture_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
