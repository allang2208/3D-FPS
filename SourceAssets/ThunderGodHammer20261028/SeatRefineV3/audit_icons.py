"""Resolve Thor's real merged runtime catalog; produce requested icon audit sheets."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
import numpy as np
P=Path(__file__).resolve().parent;R=P.parents[2];D=R/'Content/ColdSteelData';I=D/'AttachmentIcons20260913'
W='ue_thunder_god_hammer';rows=[]
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
catalog=read(D/'thunder-god-hammer-gunsmith.json')
for col in catalog['columns']:
    slot=col['key'];key=W+'_category_'+slot
    if not (I/(key+'.png')).exists():key='category_'+slot
    rows.append(dict(slot=slot,id='category',name=col['name'],key=key))
    options=[dict(id='false',name=col['default'])]+col.get('options',[])
    lib=read(D/col['options_library'])
    options+=next(c['options'] for c in lib['columns'] if c['key']==col['options_column']) if 'options_column' in col else lib['options']
    for o in options:
        oid=o['id']
        if slot=='rune' and oid not in ['false','strength_rune','haste_rune','resonance_rune','erosion_rune','conduction_rune']:continue
        icon_slot='blade_2' if slot=='rune' and oid!='false' else slot
        common=icon_slot+'_'+oid;own=W+'_'+common
        shared=oid!='false' and o.get('tier')!='legendary' and (I/(common+'.png')).exists()
        key=own if not shared and (I/(own+'.png')).exists() else common
        rows.append(dict(slot=slot,id=oid,name=o['name'],key=key))
unique={}
for row in rows:
    key=row['key'];path=I/(key+'.png');row['png']=str(path);row['exists']=path.exists()
    if key in unique:continue
    stat=dict(key=key,path=str(path),exists=path.exists(),name=row['name'])
    if path.exists():
        im=Image.open(path).convert('RGBA');a=np.array(im);rgb=a[:,:,:3].astype(float);ch=rgb.max(2)-rgb.min(2);opaque=a[:,:,3]>240
        stat.update(size=list(im.size),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),mean_chroma=float(ch[opaque].mean()),colored_fraction=float((ch[opaque]>12).mean()),alpha_center_min=int(a[im.height//4:im.height*3//4,im.width//4:im.width*3//4,3].min()),ue_asset_exists=(I/(key+'.uasset')).exists())
    unique[key]=stat
out={'scope':'Thor merged catalog only; 5 categories, defaults, shared options, legendary and removal. Hammer is melee, not gathering tool: no enhance category.', 'entries':rows,'unique':list(unique.values()),'runtime_tested':False}
(P/'icon_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',12)
items=list(unique.values())
for start in range(0,len(items),8):
    chunk=items[start:start+8];sheet=Image.new('RGB',(1200,700),(36,37,39));draw=ImageDraw.Draw(sheet)
    for idx,row in enumerate(chunk):
        x=(idx%4)*300;y=(idx//4)*350;draw.text((x+8,y+8),row['name'],font=font,fill='white')
        draw.text((x+8,y+32),row['key'].replace(W+'_','')[:39],font=small,fill='white')
        if row['exists']:
            im=Image.open(row['path']).convert('RGBA');p=im.resize((232,232),Image.Resampling.LANCZOS);sheet.paste(p,(x+7,y+54),p)
            for size,dx in [(64,5),(48,83)]:
                p=im.resize((size,size),Image.Resampling.LANCZOS);sheet.paste(p,(x+dx,y+286),p)
    sheet.save(P/f'icon_audit_{start//8+1}.png')
print(json.dumps({'entries':len(rows),'unique':len(unique),'missing':[k for k,v in unique.items() if not v['exists']],'color':[(k,round(v.get('colored_fraction',0),3)) for k,v in unique.items() if v.get('colored_fraction',0)>.01]},ensure_ascii=False))
