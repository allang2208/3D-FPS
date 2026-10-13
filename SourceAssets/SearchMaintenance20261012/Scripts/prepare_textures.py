"""Original maintenance-packaging artwork and physically separated PBR surfaces."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
OUT=ROOT/'Textures'
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
REGIONS={
 'steel':[0,0,1024,512], 'aluminum':[1024,0,2048,512],
 'brass':[2048,0,2560,512], 'plastic':[2560,0,3072,512],
 'rubber':[3072,0,3584,512], 'foam':[3584,0,4096,512],
 'kraft':[0,512,1024,1024], 'paper':[1024,512,2048,1024],
 'foil':[2048,512,3072,1024], 'seal':[3072,512,3584,1024],
 'blue':[3584,512,4096,1024], 'wood':[0,1024,3072,1536],
 'wood_end':[3072,1024,4096,1536],
 'primary':[0,1664,2048,2560], 'secondary':[2048,1664,4096,2560],
 'barcode':[0,2816,2048,3200], 'small_label':[2048,2816,4096,3584],
}
SURFACES={
 'steel':([117,126,136],.37,.95,'brush'),
 'aluminum':([176,181,183],.31,.95,'brush'),
 'brass':([170,130,62],.34,.91,'brush'),
 'plastic':([45,51,55],.52,0,'fine'),
 'rubber':([25,29,29],.78,0,'fine'),
 'foam':([34,39,40],.94,0,'pores'),
 'kraft':([150,118,78],.88,0,'paper'),
 'paper':([226,222,202],.86,0,'paper'),
 'foil':([158,170,174],.39,.78,'foil'),
 'seal':([126,61,37],.77,0,'paper'),
 'blue':([34,65,76],.70,0,'fine'),
 'wood':([157,112,63],.74,0,'wood'),
 'wood_end':([166,124,74],.82,0,'end'),
}
CAT=json.loads((PROJECT/'Docs/Gameplay/search-item-catalog-v2-20261012.json').read_text('utf-8'))
ITEMS={i['id']:i for i in CAT['items']}
NAMES={'Alloy':'search_forging_alloy_blank','Assembly':'search_assembly_component_box',
       'Resin':'search_resin_adhesive','Wood':'search_laminated_strip','Precision':'search_precision_mechanism'}
TITLES={'Alloy':('锻造合金坯','FORGING STOCK / ALLOY BILLET','B01-B03'),
        'Assembly':('装配组件盒','ASSEMBLY COMPONENTS','G-SERIES'),
        'Resin':('双组分树脂胶','RESIN / HARDENER','W01'),
        'Wood':('层压木条','LAMINATED WOOD STRIPS','W01'),
        'Precision':('精密机件组','PRECISION HARDWARE','G06 / G09-G11')}

def font(size):return ImageFont.truetype(str(FONT),max(9,int(size)))
def write(d,xy,s,size,color=(35,42,44),anchor=None):d.text(xy,s,font=font(size),fill=color,anchor=anchor)
def region_rect(region,size):return tuple(round(v*size/4096) for v in REGIONS[region])
def artwork(key,region,w,h):
    im=Image.new('RGB',(w,h),(225,221,201));d=ImageDraw.Draw(im)
    title,english,code=TITLES[key];ink=(36,43,46);accent=(45,75,81)
    if region=='barcode':
        rng=np.random.default_rng(sum(map(ord,key)))
        x=w*.06
        while x<w*.94:
            thickness=int(rng.integers(1,4))*max(1,w//450)
            d.rectangle((x,h*.13,x+thickness,h*.65),fill=ink)
            x+=thickness+int(rng.integers(1,4))*max(1,w//450)
        write(d,(w*.5,h*.86),'CS / '+key.upper()+' / LOT 0427',h*.16,ink,'mm')
    elif region=='secondary':
        d.rectangle((0,0,w,h*.20),fill=accent)
        write(d,(w*.06,h*.04),'MAINTENANCE STORES',h*.10,(230,232,223))
        write(d,(w*.06,h*.29),'配套材料  /  '+code,h*.09)
        for j,s in enumerate(('批次 0427   检修储备','整包领用 · 保持干燥','设施维护处 / MATERIALS')):
            write(d,(w*.06,h*(.46+j*.16)),s,h*.075)
    elif region=='small_label':
        write(d,(w*.08,h*.12),'A / RESIN' if key=='Resin' else code,h*.20)
        write(d,(w*.08,h*.44),'B / HARDENER' if key=='Resin' else 'QC  /  0427',h*.16)
        write(d,(w*.08,h*.77),'SEALED STOCK' if key=='Resin' else 'INSPECTED',h*.10,accent)
    else:
        d.rectangle((w*.025,h*.04,w*.975,h*.96),outline=accent,width=max(2,w//300))
        write(d,(w*.06,h*.10),'设施维护处 / SERVICE STORES',h*.085,accent)
        write(d,(w*.06,h*.31),title,h*.24)
        write(d,(w*.06,h*.62),english,h*.085)
        write(d,(w*.06,h*.79),'LOT 0427   |   '+code,h*.075)
    return np.array(im)

manifest=dict(assets={},regions=REGIONS,authorship='Original project geometry, labels and generated material maps; existing Noto Sans SC font',
              texture_convention='BaseColor sRGB; ORM linear R=AO G=roughness B=metallic; normal OpenGL +Y',
              runtime_tested=False)
for index,(key,identifier) in enumerate(NAMES.items()):
    item=ITEMS[identifier];size=4096 if key in ('Assembly','Precision') else 2048
    rng=np.random.default_rng(1031+index)
    base=np.full((size,size,3),40,np.uint8)
    orm=np.zeros((size,size,3),np.uint8);orm[:]=[255,180,0]
    normal=np.zeros((size,size,3),np.uint8);normal[:]=[128,128,255]
    for region,(rgb,rough,metal,kind) in SURFACES.items():
        x0,y0,x1,y1=region_rect(region,size);h,w=y1-y0,x1-x0
        yy,xx=np.mgrid[0:h,0:w].astype(np.float32);u=xx/max(1,w-1);v=yy/max(1,h-1)
        noise=rng.normal(0,1,(h,w)).astype(np.float32)
        field=noise*.5;amount=1.4;height=.004
        if kind=='brush':field=noise*.24+rng.normal(0,1,(h,1));amount=2.2;height=.003
        elif kind=='pores':field=noise;amount=1.5;height=.014
        elif kind=='paper':field=noise*.6+.3*np.sin(xx*.85+yy*.07);amount=1.6;height=.005
        elif kind=='foil':field=noise*.25+np.sin(u*85+np.sin(v*18)*1.5)*.35;amount=1.5;height=.01
        elif kind=='wood':
            warp=v*85+1.7*np.sin(u*10+v*6)+.35*np.sin(u*40)
            field=np.sin(warp*3)*.30+np.sin(warp*12)*.17+noise*.09
            amount=23;height=.006
        elif kind=='end':
            field=np.sin(v*55*np.pi)*.35+np.sin(np.hypot(u*1.2,v-.2)*160)*.16+noise*.15
            amount=19;height=.006
        base[y0:y1,x0:x1]=np.clip(np.array(rgb)[None,None,:]+field[:,:,None]*amount,0,255).astype(np.uint8)
        orm[y0:y1,x0:x1,1]=np.clip((rough+field*.015)*255,0,255).astype(np.uint8)
        orm[y0:y1,x0:x1,2]=int(metal*255)
        dy,dx=np.gradient(field*height)
        n=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
        normal[y0:y1,x0:x1]=np.clip((n*.5+.5)*255,0,255).astype(np.uint8)
    for region in ('primary','secondary','barcode','small_label'):
        x0,y0,x1,y1=region_rect(region,size)
        base[y0:y1,x0:x1]=artwork(key,region,x1-x0,y1-y0)
        orm[y0:y1,x0:x1]=[255,210,0]
    files={}
    for kind,array in (('BaseColor',base),('ORM',orm),('Normal',normal)):
        path=OUT/f'T_SM_{key}_{kind}.png';Image.fromarray(array).save(path,compress_level=6);files[kind]=str(path)
    manifest['assets'][key]=dict(id=identifier,name=item['name'],size=size,mesh='SM_Search_'+key,
        material='M_SM_'+key,textures=files,regions=REGIONS,dimensions=item['model']['dimensions_lwh_cm'],
        grid_w=item['grid_w'],grid_h=item['grid_h'],max_stack=item['max_stack'],
        rarity=item['rarity'],sell_souls=item['sell_souls'],recipe_uses=item['recipe_uses'])
    print('MAINTENANCE_PBR_SAVED',key,size,flush=True)
(ROOT/'texture_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
