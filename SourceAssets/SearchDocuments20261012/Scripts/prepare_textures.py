"""Original product labels and restrained PBR surface atlases; no previews/renders."""
from pathlib import Path
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
OUT=ROOT/'Textures';OUT.mkdir(exist_ok=True)
FONT=PROJECT/'Content/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular.otf'
REGIONS={
 'aluminum':[0,0,512,512], 'steel':[512,0,1024,512], 'plastic':[1024,0,1536,512], 'rubber':[1536,0,2048,512],
 'paper':[0,512,512,1024], 'kraft':[512,512,1024,1024], 'brass':[1024,512,1536,1024], 'seal':[1536,512,2048,1024],
 'primary':[0,1024,2048,2560], 'barcode':[0,2688,2048,3072],
 'secondary':[0,3200,2048,3968], 'dark_label':[2176,0,3968,1024],
}
SURFACES={
 'aluminum':([185,188,191],.34,.96,'brushed'),
 'steel':([168,174,181],.25,.98,'brushed'),
 'plastic':([36,40,43],.47,0.,'molded'),
 'rubber':([24,26,27],.78,0.,'molded'),
 'paper':([227,222,208],.84,0.,'paper'),
 'kraft':([159,129,87],.87,0.,'paper'),
 'brass':([191,151,67],.31,.92,'brushed'),
 'seal':([136,33,30],.57,0.,'paper'),
}
ASSETS={
 'USB':dict(size=2048,id='search_usb_drive',name='U盘',mesh='SM_Search_USBDrive',dimensions=[6,2,1]),
 'Tape':dict(size=2048,id='search_archive_tape',name='档案备份磁带',mesh='SM_Search_ArchiveTape',dimensions=[11,10,2]),
 'Case':dict(size=4096,id='search_encrypted_archive_case',name='加密行政资料盒',mesh='SM_Search_EncryptedCase',dimensions=[24,18,6]),
 'Archive':dict(size=4096,id='search_certified_admin_archive',name='签章行政档案',mesh='SM_Search_CertifiedArchive',dimensions=[32,24,3]),
}

def font(size):return ImageFont.truetype(str(FONT),max(8,int(size)))
def rect(region,size):return tuple(round(n*size/4096) for n in REGIONS[region])
def text(draw,xy,string,size,fill,anchor=None):draw.text(xy,string,font=font(size),fill=fill,anchor=anchor)

def barcode(im,serial):
    d=ImageDraw.Draw(im);w,h=im.size
    d.rectangle((0,0,w,h),fill=(222,219,201))
    rng=np.random.default_rng(sum(map(ord,serial)))
    x=w*.04
    while x<w*.96:
        bar=float(rng.integers(1,4))*w/390
        d.rectangle((int(x),int(h*.12),int(x+bar),int(h*.65)),fill=(28,30,29))
        x+=bar+float(rng.integers(1,4))*w/390
    text(d,(w/2,h*.88),serial,h*.18,(24,25,23),'mm')

def label(key,region,size):
    x0,y0,x1,y1=rect(region,size);w,h=x1-x0,y1-y0
    bg=(222,219,204) if region!='dark_label' else (42,48,52)
    im=Image.new('RGB',(w,h),bg);d=ImageDraw.Draw(im)
    ink=(37,45,49);red=(135,39,36);blue=(41,58,72)
    if region=='barcode':barcode(im,{'USB':'CS-U4 008271','Tape':'A07429 L8','Case':'CS-ADM 0427 / 08','Archive':'ADM-0427-16'}[key]);return im
    if region=='dark_label':
        text(d,(w*.07,h*.13),'COLD STEEL',h*.13,(205,209,203))
        text(d,(w*.07,h*.37),'FACILITY RECORDS',h*.085,(165,176,180))
        d.line((w*.07,h*.56,w*.92,h*.56),fill=(114,124,127),width=max(1,int(h*.007)))
        text(d,(w*.07,h*.64),'CONTROLLED COPY  /  RX-0427',h*.07,(192,198,194))
        return im
    if region=='secondary':
        text(d,(w*.045,h*.11),'资料交接 / CHAIN OF CUSTODY',h*.105,ink)
        text(d,(w*.045,h*.30),'档案编号   RX-0427     经办  L. CHEN',h*.085,ink)
        for j in range(3):
            y=h*(.49+j*.13);d.line((w*.045,y,w*.95,y),fill=(147,151,142),width=max(1,int(h*.002)))
        text(d,(w*.06,h*.56),'复核：',h*.08,ink)
        # Original fictitious review signature, authored as a continuous ink stroke.
        points=[(w*(.28+i*.012),h*(.64+.12*math.sin(i*.73)*math.exp(-i/65))) for i in range(43)]
        d.line(points,fill=(45,60,89),width=max(2,int(h*.004)))
        return im
    if key=='USB':
        d.rectangle((w*.035,h*.05,w*.965,h*.95),outline=(108,113,112),width=max(2,int(w*.008)))
        text(d,(w*.07,h*.18),'CS / RECORDS',h*.16,ink)
        text(d,(w*.07,h*.49),'ARCHIVE 128',h*.105,ink)
        text(d,(w*.07,h*.72),'U4-008271  •  PROPERTY OF FACILITY',h*.058,ink)
    elif key=='Tape':
        d.rectangle((0,0,w,h*.19),fill=blue)
        text(d,(w*.05,h*.025),'ARCHIVE MEDIA',h*.095,(232,231,219))
        text(d,(w*.05,h*.255),'档案备份',h*.12,ink)
        text(d,(w*.05,h*.44),'VOLUME 07429  /  RETENTION COPY',h*.053,ink)
        text(d,(w*.05,h*.56),'FACILITY ADMINISTRATION',h*.055,ink)
        for y in (.71,.86):d.line((w*.05,h*y,w*.94,h*y),fill=(127,136,135),width=max(1,int(h*.002)))
        text(d,(w*.06,h*.725),'RECORDED 2024.08.16',h*.055,ink)
        text(d,(w*.06,h*.89),'WRITE PROTECT    ON',h*.048,red)
    elif key=='Case':
        d.rectangle((w*.025,h*.03,w*.975,h*.97),outline=ink,width=max(2,int(w*.003)))
        text(d,(w*.07,h*.08),'设施管理处',h*.12,ink)
        text(d,(w*.07,h*.275),'加密行政资料',h*.14,ink)
        text(d,(w*.07,h*.48),'SEALED MEDIA / CONTROLLED TRANSFER',h*.051,ink)
        d.line((w*.07,h*.60,w*.93,h*.60),fill=ink,width=max(2,int(h*.003)))
        text(d,(w*.07,h*.655),'档案编号  RX-0427',h*.075,ink)
        text(d,(w*.07,h*.80),'封签完整方可交接',h*.07,red)
    else:
        d.rectangle((w*.035,h*.025,w*.965,h*.975),outline=(115,91,65),width=max(2,int(w*.002)))
        text(d,(w*.5,h*.07),'设施管理处',h*.065,ink,'mt')
        text(d,(w*.5,h*.205),'行政归档卷宗',h*.12,ink,'mt')
        text(d,(w*.08,h*.41),'档案编号： RX-0427-16',h*.053,ink)
        text(d,(w*.08,h*.515),'归档部门： 综合事务室',h*.053,ink)
        text(d,(w*.08,h*.62),'保存期限： 长期',h*.053,ink)
        text(d,(w*.08,h*.725),'归档日期： 2024.08.16',h*.053,ink)
        # Fictional archive seal; never a copied government or company seal.
        cx,cy=w*.78,h*.74;rx,ry=w*.14,h*.17
        for inset in (0,.045):d.ellipse((cx-rx*(1-inset),cy-ry*(1-inset),cx+rx*(1-inset),cy+ry*(1-inset)),outline=red,width=max(2,int(w*.0025)))
        text(d,(cx,cy-h*.043),'资料归档',h*.042,red,'mm')
        text(d,(cx,cy+h*.031),'专用章',h*.045,red,'mm')
        text(d,(w*.08,h*.89),'卷内目录齐全  /  签章留存',h*.043,ink)
    return im

manifest={'assets':{},'regions':REGIONS,'texture_convention':'BaseColor sRGB; ORM=AO/Roughness/Metallic linear; Normal OpenGL tangent +Y, UE flips green',
 'reference_sources':[
   {'url':'https://www.kingston.com/datasheets/DTR30_en.pdf','use':'USB-A object scale and connector/casing proportions only; original design, no brand assets copied'},
   {'url':'https://www.ibm.com/docs/en/power6?topic=5746-cartridge-label-placement-fc','use':'LTO-style label location, write-protect switch and cartridge anatomy; original unbranded media prop'}],
 'authorship':'Original geometry and printed graphics for this project; font uses existing project Noto Sans SC.',
 'preview_rendered':False,'runtime_tested':False}
for index,(key,spec) in enumerate(ASSETS.items()):
    # Match the actual physical label aspect ratio so letters and seals are not stretched.
    primary_ratio={'USB':2.81/1.04,'Tape':7.94/6.23,'Case':15.25/10.91,'Archive':24.98/17.23}[key]
    REGIONS['primary']=[0,1024,2048,1024+round(2048/primary_ratio)]
    size=spec['size'];rng=np.random.default_rng(427+index)
    base=np.zeros((size,size,3),np.uint8);base[:]=[37,40,42]
    orm=np.zeros((size,size,3),np.uint8);orm[:]=[255,150,0]
    normal=np.zeros((size,size,3),np.uint8);normal[:]=[128,128,255]
    for region,(rgb,rough,metal,kind) in SURFACES.items():
        x0,y0,x1,y1=rect(region,size);h,w=y1-y0,x1-x0
        fine=rng.normal(0,1,(h,w)).astype(np.float32)
        if kind=='brushed':
            line=rng.normal(0,1,(h,1)).astype(np.float32)
            field=fine*.3+line*.8;strength=.22;color_amount=1.8
        elif kind=='paper':
            field=fine;strength=.32;color_amount=1.6
        else:field=fine;strength=.25;color_amount=.7
        color=np.array(rgb)[None,None,:]+field[:,:,None]*color_amount
        base[y0:y1,x0:x1]=np.uint8(np.clip(color,0,255))
        orm[y0:y1,x0:x1,1]=np.uint8(np.clip((rough+field*.016)*255,0,255))
        orm[y0:y1,x0:x1,2]=int(metal*255)
        dy,dx=np.gradient(field*.025*strength)
        n=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);n/=np.linalg.norm(n,axis=-1,keepdims=True)
        normal[y0:y1,x0:x1]=np.uint8(np.clip((n*.5+.5)*255,0,255))
    for region in ('primary','barcode','secondary','dark_label'):
        x0,y0,x1,y1=rect(region,size)
        art=label(key,region,size)
        array=np.array(art).astype(np.float32)
        grain=rng.normal(0,.65,array.shape[:2]).astype(np.float32)
        base[y0:y1,x0:x1]=np.uint8(np.clip(array+grain[:,:,None],0,255))
        orm[y0:y1,x0:x1]=[255,190 if region!='dark_label' else 145,0]
    files={}
    for suffix,data in (('BaseColor',base),('ORM',orm),('Normal',normal)):
        file=OUT/f'T_SD_{key}_{suffix}.png';Image.fromarray(data).save(file,compress_level=6);files[suffix]=str(file)
    manifest['assets'][key]={**spec,'textures':files,'material':'M_SD_'+key,'regions':{k:list(v) for k,v in REGIONS.items()}}
    print('PBR_ATLAS_AUTHORED',key,size,flush=True)
(ROOT/'texture_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
